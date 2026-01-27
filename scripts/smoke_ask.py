import os
import json
from datetime import date
from pathlib import Path
from typing import Dict, Any, List, Optional

# Local dev convenience only (Streamlit Cloud usually won't have a .env file)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# Streamlit secrets (available on Cloud). Safe to import-guard.
def _get_secret(name: str) -> Optional[str]:
    try:
        import streamlit as st  # type: ignore
        val = st.secrets.get(name)
        return str(val).strip() if val else None
    except Exception:
        return None

from openai import OpenAI

from app.rag.vectorstore import LanceVectorStore
from scripts.ingest_manifest import embed_many  # must respect EMBED_PROVIDER

# -------------------------
# OpenAI (answer synthesis only)
# -------------------------
OPENAI_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini").strip()
DAILY_BUDGET_USD = float(os.getenv("DAILY_BUDGET_USD", "1.00"))
COST_LEDGER_PATH = Path("./db/cost_ledger.json")

def _require_openai_key() -> str:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        key = (_get_secret("OPENAI_API_KEY") or "").strip()

    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set.\n\n"
            "Local (PowerShell):\n"
            '  $Env:OPENAI_API_KEY = "sk-..."\n\n'
            "Streamlit Cloud:\n"
            "  App → Settings → Secrets\n"
            "  Add:\n"
            "  OPENAI_API_KEY = \"sk-...\"\n"
        )
    return key

client = OpenAI(api_key=_require_openai_key())

def _ledger() -> Dict[str, Any]:
    if COST_LEDGER_PATH.exists():
        try:
            return json.loads(COST_LEDGER_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_ledger(d: Dict[str, Any]) -> None:
    COST_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    COST_LEDGER_PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")

def _today_key() -> str:
    return str(date.today())

def _check_budget_or_raise() -> None:
    led = _ledger()
    spent = float(led.get(_today_key(), 0.0))
    if spent >= DAILY_BUDGET_USD:
        raise RuntimeError(
            f"Daily budget exceeded: spent=${spent:.4f} limit=${DAILY_BUDGET_USD:.4f}. "
            f"Increase DAILY_BUDGET_USD or wait until tomorrow."
        )

def _record_spend(usd: float) -> None:
    led = _ledger()
    k = _today_key()
    led[k] = float(led.get(k, 0.0)) + float(usd)
    _save_ledger(led)

PER_CALL_USD = float(os.getenv("PER_CALL_USD", "0.01"))

def _append_sources(answer_text: str, cites: List[str]) -> str:
    # Always end with a clean Sources section (flat bullet list)
    uniq = []
    for c in cites:
        c = (c or "").strip()
        if c and c not in uniq:
            uniq.append(c)

    # If the model included a "Sources:" section anyway, strip it (we re-add deterministically)
    lower = answer_text.lower()
    idx = lower.find("\nsources:")
    if idx != -1:
        answer_text = answer_text[:idx].rstrip()

    if not uniq:
        return answer_text.strip()

    lines = [answer_text.strip(), "", "Sources:"]
    lines.extend([f"- {c}" for c in uniq])
    return "\n".join(lines).strip()

# -------------------------
# Answer synthesis
# -------------------------
def synthesize_with_mini(question: str, hits: List[Any]) -> str:
    _check_budget_or_raise()

    evidence = []
    cites = []
    for h in hits[:8]:
        evidence.append({
            "cite": h.cite,
            "text": (h.text or "")[:900]
        })
        if getattr(h, "cite", None):
            cites.append(str(h.cite))

    system = (
        "You are a warm, grounded AA Big Book / 12&12 assistant.\n"
        "Your job is to help the user in a natural, conversational way — like a good sponsor-friend.\n\n"
        "Rules:\n"
        "1) Ground your answer primarily in the provided excerpts. Quote or paraphrase them naturally.\n"
        "2) You may add context, practical examples, or gentle insights that complement the literature "
        "if it helps the user — but make it clear when you're doing so.\n"
        "3) If the excerpts don't fully address something, acknowledge that and offer what you can.\n"
        "4) Do NOT put citations in the body of your answer.\n"
        "5) Do not mention 'blocks'.\n"
        "6) Do not include a Sources section — it will be appended automatically.\n\n"
        "Style:\n"
        "- Be human. Be kind. Short paragraphs. Practical.\n"
        "- Prefer 4–10 sentences unless the user asks for depth.\n"
        "- Avoid sterile outlines unless the user asks for a list.\n"
        "- When adding context beyond the excerpts, use phrases like 'Many people find...' or "
        "'In practice...' to signal you're offering broader perspective.\n"
    )

    user = {"question": question, "excerpts": evidence}

    resp = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user)}
        ],
        max_output_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "350")),
    )

    _record_spend(PER_CALL_USD)

    answer = resp.output_text.strip()
    return _append_sources(answer, cites)

def ask(question: str, filters: Optional[Dict[str, Any]] = None, top_k: int = 10) -> str:
    store = LanceVectorStore()
    v = embed_many([question])[0]
    hits = store.query(v, top_k=top_k, filters=filters)

    if not hits:
        return "I couldn’t find supporting excerpts in the current corpus for that question."

    return synthesize_with_mini(question, hits)

if __name__ == "__main__":
    q = os.getenv("Q", "").strip() or "How does AA describe Step One?"
    print(ask(q, filters=None, top_k=10))
