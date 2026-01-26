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

# -------------------------
# Answer synthesis
# -------------------------
def synthesize_with_mini(question: str, hits: List[Any]) -> str:
    _check_budget_or_raise()

    evidence = []
    for h in hits[:8]:
        evidence.append({
            "cite": h.cite,
            "text": (h.text or "")[:900]
        })

    system = (
        "You are an AA Big Book / 12&12 assistant. "
        "Use ONLY the provided excerpts as evidence. "
        "If the excerpts don't support a claim, say so. "
        "Cite sources using the provided [cite] strings."
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
    return resp.output_text.strip()

def ask(question: str, filters: Optional[Dict[str, Any]] = None, top_k: int = 10) -> str:
    store = LanceVectorStore()
    v = embed_many([question])[0]
    hits = store.query(v, top_k=top_k, filters=filters)

    if not hits:
        return f"Question: {question}\n\nNo matches found in the current corpus."

    return synthesize_with_mini(question, hits)

if __name__ == "__main__":
    q = os.getenv("Q", "").strip() or "How does AA describe Step One?"
    print(ask(q, filters=None, top_k=10))
