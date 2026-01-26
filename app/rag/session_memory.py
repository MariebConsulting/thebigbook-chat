from typing import Dict, List

# Simple in-process session memory (good for local dev).
# In production, swap this for Redis/SQLite keyed by session_id.
_SESSIONS: Dict[str, List[dict]] = {}

def get_history(session_id: str, limit: int = 10) -> List[dict]:
    hist = _SESSIONS.get(session_id, [])
    return hist[-limit:]

def set_history(session_id: str, history: List[dict], limit: int = 10) -> None:
    _SESSIONS[session_id] = history[-limit:]
