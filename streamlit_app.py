import streamlit as st
from datetime import datetime, timezone
import uuid

import lancedb
import pyarrow as pa

from scripts.smoke_ask import ask

st.set_page_config(page_title="The Big Book .chat", layout="wide")

PALETTE = {
    "bg": "#E7E1D7",
    "bg2": "#DCD3C7",
    "card": "rgba(255,255,255,0.72)",
    "text": "#1F1F1D",
    "muted": "rgba(31,31,29,0.72)",
    "border": "rgba(31,31,29,0.14)",
    "shadow": "0 18px 55px rgba(0,0,0,0.10)",
    "accent": "#3F4A41",
    "accent2": "#5B5247",
    "d_bg": "#111312",
    "d_bg2": "#1A1F1C",
    "d_card": "rgba(255,255,255,0.06)",
    "d_text": "#F3F2EE",
    "d_muted": "rgba(243,242,238,0.70)",
    "d_border": "rgba(243,242,238,0.14)",
    "d_accent": "#A9B3A7",
}

# ----------------------------
# LanceDB chat storage
# ----------------------------
DB_DIR = "./db/lancedb"
CHAT_TABLE = "chat_messages"

def _db():
    return lancedb.connect(DB_DIR)

def _ensure_chat_table():
    db = _db()
    names = set(db.table_names())
    if CHAT_TABLE in names:
        return db.open_table(CHAT_TABLE)

    schema = pa.schema([
        pa.field("session_id", pa.string()),
        pa.field("ts", pa.timestamp("ms")),
        pa.field("role", pa.string()),     # "user" | "assistant"
        pa.field("content", pa.string()),
    ])
    # Create empty table with schema
    return db.create_table(CHAT_TABLE, data=[], schema=schema)

def _load_messages(session_id: str, limit: int = 200) -> list[dict]:
    tbl = _ensure_chat_table()
    # Lance filter support can vary by version; keep it robust:
    df = tbl.to_pandas()
    if df.empty:
        return []
    df = df[df["session_id"] == session_id].sort_values("ts").tail(limit)
    out = []
    for _, r in df.iterrows():
        out.append({"role": str(r["role"]), "content": str(r["content"])})
    return out

def _append_message(session_id: str, role: str, content: str) -> None:
    tbl = _ensure_chat_table()
    tbl.add([{
        "session_id": session_id,
        "ts": datetime.now(timezone.utc),
        "role": role,
        "content": content,
    }])

# ----------------------------
# State
# ----------------------------
if "dark" not in st.session_state:
    st.session_state.dark = False

if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = _load_messages(st.session_state.chat_session_id, limit=400)

# ----------------------------
# CSS (clean top + centered chat)
# ----------------------------
CSS = f"""
<style>
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}

.block-container {{
  padding-top: 18px;
  max-width: 980px;
}}

.stApp {{
  background: radial-gradient(1200px 600px at 20% 0%,
    {PALETTE["bg2"]} 0%,
    {PALETTE["bg"]} 45%,
    {PALETTE["bg"]} 100%);
  color: {PALETTE["text"]};
}}

body[data-dark="true"] .stApp {{
  background: radial-gradient(1200px 600px at 20% 0%,
    {PALETTE["d_bg2"]} 0%,
    {PALETTE["d_bg"]} 55%,
    {PALETTE["d_bg"]} 100%);
  color: {PALETTE["d_text"]};
}}

.bb-top {{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:16px;
  margin-bottom: 10px;
}}

.bb-title {{
  font-size: 40px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.05;
  margin: 0;
}}

.bb-sub {{
  margin-top: 6px;
  font-size: 14px;
  opacity: 0.78;
}}

.bb-card {{
  border: 1px solid {PALETTE["border"]};
  background: {PALETTE["card"]};
  border-radius: 18px;
  padding: 14px 14px 6px 14px;
  box-shadow: {PALETTE["shadow"]};
}}

body[data-dark="true"] .bb-card {{
  border: 1px solid {PALETTE["d_border"]};
  background: {PALETTE["d_card"]};
  box-shadow: 0 18px 55px rgba(0,0,0,0.35);
}}

.bb-hint {{
  font-size: 13px;
  opacity: 0.75;
  margin: 4px 0 10px 2px;
}}

.bb-controls {{
  margin-top: 6px;
}}

div[data-testid="stChatInput"] textarea {{
  border-radius: 14px !important;
}}

</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# Header
st.markdown(
    """
<div class="bb-top">
  <div>
    <div class="bb-title">The Big Book .chat</div>
    <div class="bb-sub">Warm guidance, grounded in the text. Sources at the bottom.</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

with st.expander("Preferences", expanded=False):
    st.checkbox("Dark mode", key="dark")
    if st.button("New chat", use_container_width=True):
        st.session_state.chat_session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

st.markdown(
    f"<script>document.body.setAttribute('data-dark','{str(st.session_state.dark).lower()}');</script>",
    unsafe_allow_html=True,
)

# Main chat “card”
st.markdown('<div class="bb-card">', unsafe_allow_html=True)
st.markdown('<div class="bb-hint">Type below and press Enter to send. Use <b>Daily Reflection</b> for a quick grounded check-in.</div>', unsafe_allow_html=True)

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Controls under the thread (Daily Reflection button)
c1, c2 = st.columns([1, 2], gap="small")
with c1:
    daily_clicked = st.button("Daily Reflection", use_container_width=True)
with c2:
    clear_clicked = st.button("Clear on-screen", use_container_width=True)

if clear_clicked:
    # Clears UI only; DB remains (so you can reload if you want later)
    st.session_state.messages = []
    st.rerun()

# Chat input (true chat box)
prompt = st.chat_input("Message…")

# If Daily Reflection clicked, treat it like a user prompt
if daily_clicked:
    prompt = (
        "Give me today’s AA Daily Reflection style guidance grounded only in the Big Book and 12&12 excerpts you have. "
        "Keep it short, practical, and end with Sources."
    )

# Handle a new prompt
if prompt and prompt.strip():
    user_text = prompt.strip()

    # Add user message to UI + DB
    st.session_state.messages.append({"role": "user", "content": user_text})
    _append_message(st.session_state.chat_session_id, "user", user_text)

    with st.chat_message("user"):
        st.markdown(user_text)

    # Assistant response with “thinking…”
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            answer = ask(user_text, filters=None, top_k=10)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    _append_message(st.session_state.chat_session_id, "assistant", answer)

st.markdown("</div>", unsafe_allow_html=True)

