import os
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List
from pathlib import Path

import yaml
from dotenv import load_dotenv

from app.rag.vectorstore import LanceVectorStore

load_dotenv()

# ============================================================
# EMBEDDING CONFIG — LOCKED TO OPENAI / 3072 DIM
# ============================================================
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "openai").strip().lower()
OPENAI_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large").strip()
EMBED_BATCH = int(os.getenv("EMBED_BATCH", "64"))

DIM_LOCK_PATH = Path("./db/embedding_dim.txt")
INGEST_REGISTRY = Path("./db/ingested_doc_ids.txt")

MANIFEST_PATH = os.getenv("SOURCES_MANIFEST", "./data/sources.yaml")
AUTO_INGEST_DIR = os.getenv("AUTO_INGEST_DIR", "").strip()
AUTO_EXTS = {".pdf", ".txt", ".md", ".html", ".htm", ".docx"}

store = LanceVectorStore()

# ============================================================
# HELPERS
# ============================================================
def normpath(p: str) -> str:
    return (p or "").replace("\\", "/").strip()

def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def ensure_dim_lock(expected_dim: int) -> None:
    DIM_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DIM_LOCK_PATH.exists():
        existing = int(DIM_LOCK_PATH.read_text().strip())
        if existing != expected_dim:
            raise RuntimeError(
                f"Embedding dimension mismatch:\n"
                f"  Existing DB dim: {existing}\n"
                f"  Current embed dim: {expected_dim}\n\n"
                f"Fix:\n"
                f"  python .\\scripts\\reset_db.py\n"
                f"  python .\\scripts\\ingest_manifest.py\n"
            )
    else:
        DIM_LOCK_PATH.write_text(str(expected_dim))

def load_ingested_ids() -> set[str]:
    if not INGEST_REGISTRY.exists():
        return set()
    return set(x.strip() for x in INGEST_REGISTRY.read_text().splitlines() if x.strip())

def save_ingested_ids(ids: set[str]) -> None:
    INGEST_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    INGEST_REGISTRY.write_text("\n".join(sorted(ids)) + "\n")

# ============================================================
# EMBEDDINGS (OPENAI ONLY)
# ============================================================
_openai_client = None

def embed_many(texts: List[str]) -> List[List[float]]:
    global _openai_client

    if EMBED_PROVIDER != "openai":
        raise RuntimeError("This project is locked to OpenAI embeddings (3072-dim).")

    from openai import OpenAI

    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    resp = _openai_client.embeddings.create(
        model=OPENAI_EMBEDDING_MODEL,
        input=texts,
    )

    vectors = [d.embedding for d in resp.data]
    ensure_dim_lock(len(vectors[0]))
    return vectors

# ============================================================
# CHUNKING
# ============================================================
def chunk_paragraphs(text: str, max_chars: int = 1200, overlap: int = 150) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []

    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, buf = [], ""

    for p in paras:
        if len(buf) + len(p) + 2 <= max_chars:
            buf = (buf + "\n\n" + p).strip()
        else:
            if buf:
                chunks.append(buf)
            buf = (buf[-overlap:] if buf else "") + "\n\n" + p

    if buf:
        chunks.append(buf.strip())

    return chunks

# ============================================================
# DOCUMENT LOADERS
# ============================================================
def read_document(path: str) -> str:
    ext = Path(path).suffix.lower()

    if ext in {".txt", ".md"}:
        return Path(path).read_text(encoding="utf-8", errors="ignore")

    if ext == ".pdf":
        import pdfplumber
        out = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    out.append(t.strip())
        return "\n\n".join(out)

    if ext == ".docx":
        import docx
        d = docx.Document(path)
        return "\n\n".join(p.text.strip() for p in d.paragraphs if p.text.strip())

    if ext in {".html", ".htm"}:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(Path(path).read_text(errors="ignore"), "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return "\n".join(l.strip() for l in soup.get_text("\n").splitlines() if l.strip())

    raise ValueError(f"Unsupported file type: {path}")

# ============================================================
# SOURCES
# ============================================================
def load_sources_from_manifest() -> List[Dict[str, Any]]:
    if not Path(MANIFEST_PATH).exists():
        return []
    return yaml.safe_load(Path(MANIFEST_PATH).read_text()).get("documents", [])

def load_sources_from_dir(dir_path: str, manifest_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    manifest_map = {normpath(d["path"]): d for d in manifest_docs}
    docs = []

    for p in Path(dir_path).rglob("*"):
        if not p.is_file() or p.suffix.lower() not in AUTO_EXTS:
            continue

        rel = normpath(p.as_posix())
        docs.append(dict(manifest_map.get(rel, {"path": rel, "work": "intake"})))

    return docs

# ============================================================
# MAIN INGEST
# ============================================================
def main():
    ingested_ids = load_ingested_ids()
    newly_ingested = set()

    manifest_docs = load_sources_from_manifest()
    documents = (
        load_sources_from_dir(AUTO_INGEST_DIR, manifest_docs)
        if AUTO_INGEST_DIR
        else manifest_docs
    )

    rows: List[Dict[str, Any]] = []

    for doc in documents:
        rel = normpath(doc["path"])
        full = os.path.abspath(rel)

        if not os.path.exists(full):
            print(f"⚠️ Missing file: {rel}")
            continue

        doc_id = doc.get("doc_id") or file_sha256(full)[:16]
        if doc_id in ingested_ids:
            continue

        text = read_document(full)
        chunks = chunk_paragraphs(text)
        created_at = utc_now_z()
        newly_ingested.add(doc_id)

        for i in range(0, len(chunks), EMBED_BATCH):
            vecs = embed_many(chunks[i:i + EMBED_BATCH])
            for j, (ch, vec) in enumerate(zip(chunks[i:i + EMBED_BATCH], vecs)):
                rows.append({
                    "id": str(uuid.uuid4()),
                    "doc_id": doc_id,
                    "created_at": created_at,
                    "vector": vec,
                    "text": ch,
                    "chunk_index": i + j,
                    **{k: doc.get(k, "") for k in [
                        "work", "source", "edition", "title",
                        "chapter", "section_path", "loc",
                        "source_reliability", "edition_confidence"
                    ]}
                })

        print(f"✅ Prepared {len(chunks)} chunks from {rel}")

    if rows:
        store.add_rows(rows)
        save_ingested_ids(ingested_ids | newly_ingested)
        print(f"✅ Added {len(rows)} chunks | dim=3072")

if __name__ == "__main__":
    main()
