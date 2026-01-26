import os
import json
import re
from datetime import date
from pathlib import Path
from typing import Dict, Any, List, Optional

# Local dev convenience only (Streamlit Cloud usually won't have a .env file)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# Streamlit secrets (available on Cloud)
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
# OpenAI config
# -------------------------
OPENAI_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini").strip()
DAILY_BUDGET_USD = float(os.getenv("DAILY_BUDGET_USD", "1.00"))
PER_CALL_USD = float(os.getenv("PER_CALL_USD", "0.01"))

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
            "  OPENAI_API_KEY = \"sk-...\""
        )
    return key

client = OpenAI(api_key=_require_openai_key())

# -------------------------
# Cost ledger
# -------------------------
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
            f"Daily budget exceeded: spent=${spent:.4f}, limit=${DAILY_BUDGET_USD:.4f}"
        )

def _record_spend(usd: float) -> None:
    led = _ledger()
    k = _today_key()
    led[k] = float(led.get(k, 0.0)) + float(usd)
    _save_ledger(led)

# -------------------------
# Formatting helper
# -------------------------
def _finalize_answer(text: str) -> str:
    """
    - Remove model-y language
    - Move citations to a clean Sources section
    """
    if not text:
        return text

    banned = [
        "excerpts", "excerpt", "evidence", "blocks", "block",
        "context", "retrieval", "database", "provided sources"
    ]
    cleaned = text
    for b in banned:
        cleaned = re.sub(rf"\b{b}\b", "", cleaned, flags=re.IGNORECASE)

    # extract [cite] blocks
    cites = re.findall(r"\[([^\[\]]+?)\]", cleaned)
    body = re.sub(r"\s*\[[^\[\]]+?\]\s*", " ", cleaned).strip()
    body = re.sub(r"[ \t]+", " ", body)

    seen = set()
    uniq = []
    for c in cites:
        c = c.strip()
        if c and c not in seen:
            seen.add(c)
            uniq.append(c)

    if not uniq:
        return body

    sources = "\n".join([f"- [{c}]" for c in uniq])
    return f"{body}\n\nSources:\n{sources}"

# -------------------------
# Answer synthesis
# -------------------------
def synthesize_with_mini(question: str, hits: List[Any]) -> str:
    _check_budget_or_raise()

    # Build minimal grounding packet (internal only)
    sources_payload = []
    for h in hits[:8]:
        sources_payload.append({
            "cite": h.cite,
            "text": (h.text or "")[:900]
        })

    system = (
        "You are a warm, grounded AA companion.\n\n"
        "Speak naturally and conversationally, as if helping someone face-to-face. "
        "Be calm, encouraging, and practical.\n\n"
        "Rules:\n"
        "- Use ONLY the provided source material.\n"
        "- If the sources don’t support something, say: "
        "'I don’t have that in my sources right now.'\n"
        "- Do NOT mention excerpts, blocks, databases, or retrieval.\n\n"
        "Citations:\n"
        "- Do not put citations inline.\n"
        "- End with a section titled exactly: 'Sources:'\n"
        "- List each source as a bullet using the provided citation strings.\n"
    )

    user = {
        "question": question,
        "sources": sources_payload
    }

    resp = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user)}
        ],
        max_output_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "350")),
    )

    _record_spend(PER_CALL_USD)
    return _finalize_answer(resp.output_text.strip())

# -------------------------
# Public entry
# -------------------------
def ask(question: str, filters: Optional[Dict[str, Any]] = None, top_k: int = 10) -> str:
    store = LanceVectorStore()
    vector = embed_many([question])[0]
    hits = store.query(vector, top_k=top_k, filters=filters)

    if not hits:
        return (
            "I don’t see anything in the Big Book or the Twelve & Twelve "
            "that directly speaks to that question yet."
        )

    return synthesize_with_mini(question, hits)

if __name__ == "__main__":
    q = os.getenv("Q", "").strip() or "How does AA describe fear?"
    print(ask(q))

