import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path

from dotenv import load_dotenv
import lancedb
import pyarrow as pa

load_dotenv()


@dataclass
class RetrievedChunk:
    cite: str
    text: str
    score: float
    meta: Dict[str, Any]


class LanceVectorStore:
    """
    Lance vector search expects the vector column to be a FixedSizeList of float32.
    In pyarrow, this is created via: pa.list_(pa.float32(), DIM)
    """

    def __init__(self):
        self.db_dir = os.getenv("LANCEDB_DIR", "./db/lancedb")
        self.table_name = os.getenv("TABLE_NAME", "chunks")
        self.db = lancedb.connect(self.db_dir)

        self.dim = self._resolve_dim()

        if self.table_name not in self.db.table_names():
            self.db.create_table(self.table_name, schema=self._schema())

        self.tbl = self.db.open_table(self.table_name)

    def _resolve_dim(self) -> int:
        lock_path = Path("./db/embedding_dim.txt")
        if lock_path.exists():
            raw = lock_path.read_text(encoding="utf-8").strip()
            if raw.isdigit():
                return int(raw)

        env_dim = os.getenv("EMBEDDING_DIM", "").strip()
        if env_dim.isdigit():
            return int(env_dim)

        return 384  # sentence-transformers/all-MiniLM-L6-v2

    def _schema(self) -> pa.Schema:
        vec_type = pa.list_(pa.float32(), self.dim)

        return pa.schema([
            ("id", pa.string()),
            ("vector", vec_type),
            ("text", pa.string()),

            ("work", pa.string()),
            ("source", pa.string()),
            ("edition", pa.string()),
            ("title", pa.string()),
            ("chapter", pa.string()),
            ("section_path", pa.string()),
            ("loc", pa.string()),
            ("chunk_index", pa.int32()),

            ("source_reliability", pa.string()),
            ("edition_confidence", pa.string()),

            ("created_at", pa.string()),
            ("doc_id", pa.string()),
        ])

    def reset(self):
        if self.table_name in self.db.table_names():
            self.db.drop_table(self.table_name)
        self.db.create_table(self.table_name, schema=self._schema())
        self.tbl = self.db.open_table(self.table_name)

    def add_rows(self, rows: List[Dict[str, Any]]) -> None:
        cleaned: List[Dict[str, Any]] = []
        for r in rows:
            v = r.get("vector")

            if not isinstance(v, list):
                raise RuntimeError(f"Row vector is not a list for id={r.get('id')}")

            if len(v) != self.dim:
                raise RuntimeError(
                    f"Vector dim mismatch for id={r.get('id')} "
                    f"(got {len(v)} expected {self.dim}). "
                    f"If you changed embedding model, wipe DB + embedding_dim.txt and re-ingest."
                )

            # Force float32-compatible Python floats
            r["vector"] = [float(x) for x in v]
            cleaned.append(r)

        self.tbl.add(cleaned)

    def _sql_escape_string(self, s: str) -> str:
        # SQL string literal escape: single quote becomes doubled
        return s.replace("'", "''")

    def _where_clause(self, filters: Dict[str, Any]) -> Optional[str]:
        """
        LanceDB uses SQL-like expressions.
        IMPORTANT: string literals should be in single quotes.
        """
        if not filters:
            return None

        clauses = []
        for k, v in filters.items():
            if v is None:
                continue

            if isinstance(v, str):
                vv = self._sql_escape_string(v)
                clauses.append(f"{k} = '{vv}'")

            elif isinstance(v, (int, float)):
                clauses.append(f"{k} = {v}")

            elif isinstance(v, (list, tuple, set)):
                vals = []
                for item in v:
                    if item is None:
                        continue
                    if isinstance(item, str):
                        vals.append(f"'{self._sql_escape_string(item)}'")
                    else:
                        vals.append(str(item))
                if vals:
                    clauses.append(f"{k} IN ({', '.join(vals)})")

            else:
                vv = self._sql_escape_string(str(v))
                clauses.append(f"{k} = '{vv}'")

        return " AND ".join(clauses) if clauses else None

    def query(
        self,
        vector: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievedChunk]:
        search = self.tbl.search(vector, vector_column_name="vector")

        where = self._where_clause(filters or {})
        if where:
            search = search.where(where)

        results = search.limit(top_k).to_list()

        out: List[RetrievedChunk] = []
        for r in results:
            meta = {
                "id": r.get("id"),
                "doc_id": r.get("doc_id"),
                "work": r.get("work"),
                "source": r.get("source"),
                "edition": r.get("edition"),
                "title": r.get("title"),
                "chapter": r.get("chapter"),
                "section_path": r.get("section_path"),
                "loc": r.get("loc"),
                "chunk_index": r.get("chunk_index", -1),
                "source_reliability": r.get("source_reliability"),
                "edition_confidence": r.get("edition_confidence"),
                "created_at": r.get("created_at"),
            }

            work = meta.get("work") or ""
            edition = meta.get("edition") or ""
            section_path = meta.get("section_path") or meta.get("chapter") or ""
            loc = meta.get("loc") or ""
            chunk_index = meta.get("chunk_index", -1)

            cite_parts = [
                work + (f" ({edition})" if edition else ""),
                section_path,
                loc,
                f"Chunk#{chunk_index}",
            ]
            cite = "[" + " — ".join([p for p in cite_parts if p]) + "]"

            out.append(RetrievedChunk(
                cite=cite,
                text=r.get("text", "") or "",
                score=float(r.get("_distance", 0.0)),
                meta=meta
            ))

        return out
