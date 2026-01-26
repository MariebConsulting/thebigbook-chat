# Big Book / 12&12 Local Agent (RAG + LanceDB)

## What this adds
- Future-proof LanceDB schema (work/edition/section_path/loc + trust fields)
- Safer prompt assembly (retrieved context in separate system message)
- Structured citations (no string parsing)
- Session memory helper (in-process for local dev)
- Manifest-driven ingestion (`data/sources.yaml`)

## Condensed steps

1) Put your text files in `data/processed/`
   - `data/processed/bigbook_3rd_ch05_how_it_works.txt`
   - `data/processed/12and12_step4.txt`

2) Update `data/sources.yaml` to match your files.

3) Create `.env` from `.env.example` and set `OPENAI_API_KEY`.

4) Install deps (inside your venv)
   - openai
   - python-dotenv
   - lancedb
   - pyarrow
   - pyyaml

5) Reset DB then ingest
   - `python scripts/reset_db.py`
   - `python scripts/ingest_manifest.py`

6) Minimal call example
```py
from app.rag.rag import answer
from app.rag.prompts import SYSTEM_PROMPT, USER_PROMPT

result = answer(
    "Where does it talk about resentment?",
    system_prompt=SYSTEM_PROMPT,
    user_prompt=USER_PROMPT,
    history=[],
    filters={"work": "Big Book"}  # optional
)
print(result["answer"])
print(result["citations_used"])
```

## Next steps
1) Split Big Book + 12&12 into chapter/step files (best quality retrieval).
2) Upgrade chunking to be heading-aware (cleaner citations + quotes).
3) Add reranking (retrieve 30, select best 6).
4) Add edition comparison mode via filters (no long diffs, just pointers).
5) Replace in-process session store with Redis/SQLite when you deploy.
