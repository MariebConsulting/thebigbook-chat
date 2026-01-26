import os
import json
from datetime import date
from pathlib import Path
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from app.rag.vectorstore import LanceVectorStore
from scripts.ingest_manifest import embed_many  # must respect EMBED_PROVIDER

load_dotenv()

# -------------------------
# OpenAI (answer synthesis only)
# -------------------------
OPENAI_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini").strip()
DAILY_BUDGET_USD = float(os.getenv("DAILY_BUDGET_USD", "1.00"))  # you can tune
COST_LEDGER_PATH = Path("./db/cost_ledger.json")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

# NOTE:
# We can't perfectly compute cost offline without a pricing table.
# So we do a pragmatic version:
# - require you to set PER_CALL_USD as a conservative estimate for now
# - later, we can swap to exact token pricing once you pick the final model/pricing.
PER_CALL_USD = float(os.getenv("PER_CALL_USD", "0.01"))  # conservative placeholder

# -------------------------
# Answer synthesis
# -------------------------
def synthesize_with_mini(question: str, hits: List[Any]) -> str:
    _check_budget_or_raise()

    # Build evidence packet (keep it small + grounded)
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

    user = {
        "question": question,
        "excerpts": evidence
    }

    resp = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user)}
        ],
        # keep this cheap + consistent
        max_output_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "350")),
    )

    # record spend (conservative fixed-per-call for now)
    _record_spend(PER_CALL_USD)

    return resp.output_text.strip()

def ask(question: str, filters: Optional[Dict[str, Any]] = None, top_k: int = 10) -> str:
    store = LanceVectorStore()
    v = embed_many([question])[0]          # embeddings stay local if EMBED_PROVIDER=local
    hits = store.query(v, top_k=top_k, filters=filters)

    if not hits:
        return f"Question: {question}\n\nNo matches found in the current corpus."

    answer = synthesize_with_mini(question, hits)
    return answer

if __name__ == "__main__":
    q = os.getenv("Q", "").strip() or "How does AA describe Step One?"
    # Example filters:
    # filters = {"work": "twelve_twelve", "chapter": "Step 1"}
    filters = None

    print(ask(q, filters=filters, top_k=10))
