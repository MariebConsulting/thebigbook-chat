# streamlit_app.py
import html
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict

import streamlit as st

import lancedb
import pyarrow as pa

from scripts.smoke_ask import ask

st.set_page_config(page_title="The Big Book .chat", layout="wide")

# ============================
# Modern (non-blue) palette
# ============================
PALETTE = {
    # Light mode (warm sand + paper + charcoal)
    "bg": "#F3EEE6",          # soft sand
    "bg2": "#E9E1D6",         # warm fog
    "card": "rgba(255,255,255,0.78)",
    "text": "#1C1B19",        # near-charcoal
    "muted": "rgba(28,27,25,0.70)",
    "border": "rgba(28,27,25,0.14)",
    "shadow": "0 18px 55px rgba(0,0,0,0.10)",

    # Accents (no blue)
    "accent": "#2E3A34",      # deep pine-charcoal
    "accent2": "#A45A3C",     # warm clay (sparingly)

    # Dark mode (espresso + ink)
    "d_bg": "#11100F",
    "d_bg2": "#1A1816",
    "d_card": "rgba(255,255,255,0.06)",
    "d_text": "#F4F0E8",
    "d_muted": "rgba(244,240,232,0.68)",
    "d_border": "rgba(244,240,232,0.14)",
    "d_accent": "#B9C3B8",    # muted sage-gray
}

# ============================
# LanceDB chat storage
# ============================
DB_DIR = "./db/lancedb"
CHAT_TABLE = "chat_messages"


def _db():
    os.makedirs(DB_DIR, exist_ok=True)
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

    # LanceDB create_table() can choke on empty data on some versions.
    # Create with a single dummy row, then delete it.
    dummy = [{
        "session_id": "init",
        "ts": datetime.now(timezone.utc),
        "role": "system",
        "content": "initialization",
    }]

    tbl = db.create_table(CHAT_TABLE, data=dummy, schema=schema)
    try:
        tbl.delete("session_id = 'init'")
    except Exception:
        # If delete isn't supported in that environment/version, it's harmless.
        pass
    return tbl


def _load_messages(session_id: str, limit: int = 400) -> List[Dict[str, str]]:
    tbl = _ensure_chat_table()
    df = tbl.to_pandas()
    if df.empty:
        return []
    df = df[df["session_id"] == session_id].sort_values("ts").tail(limit)
    out: List[Dict[str, str]] = []
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


def _reset_screen_only():
    # Clears current UI memory, keeps DB history intact.
    st.session_state.messages = []


def _new_chat_session():
    # New session id = new persistent thread
    st.session_state.chat_session_id = str(uuid.uuid4())
    st.session_state.messages = []


# Load persisted chat once per run (only if local state is empty)
if not st.session_state.messages:
    st.session_state.messages = _load_messages(st.session_state.chat_session_id, limit=400)


# ============================
# Session state
# ============================
if "dark" not in st.session_state:
    st.session_state.dark = False

if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    # Load prior messages from LanceDB (if any)
    st.session_state.messages = _load_messages(
        st.session_state.chat_session_id,
        limit=400
    )

    # Seed a warm welcome if this is a new session
    if not st.session_state.messages:
        welcome = (
            "Hey.\n\n"
            "Ask me anything about the Big Book or the Twelve & Twelve. "
            "I’ll stay grounded in the text and list sources at the end."
        )
        st.session_state.messages = [
            {"role": "assistant", "content": welcome}
        ]


# ============================
# CSS
# ============================
CSS = f"""
<style>
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}

.block-container {{
  padding-top: 22px;
  max-width: 980px;
}}

.stApp {{
  background: radial-gradient(1200px 600px at 20% 0%,
    {PALETTE["bg2"]} 0%,
    {PALETTE["bg"]} 55%,
    {PALETTE["bg"]} 100%);
  color: {PALETTE["text"]};
}}

body[data-dark="true"] .stApp {{
  background: radial-gradient(1200px 600px at 20% 0%,
    {PALETTE["d_bg2"]} 0%,
    {PALETTE["d_bg"]} 60%,
    {PALETTE["d_bg"]} 100%);
  color: {PALETTE["d_text"]};
}}

h1, h2, h3, p, label, span, div {{ color: inherit; }}

.bb-top {{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:16px;
  margin-bottom: 10px;
}}

.bb-title {{
  font-size: 40px;
  font-weight: 850;
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
  padding: 14px 14px 10px 14px;
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
  margin: 6px 0 10px 2px;
}}

.bb-controls {{
  display:flex;
  gap:10px;
  align-items:center;
  margin: 8px 0 8px 0;
}}

.bb-controls .stButton > button {{
  border-radius: 14px;
  padding: 10px 12px;
  border: 1px solid {PALETTE["border"]};
  background: rgba(255,255,255,0.74);
  font-weight: 850;
}}

body[data-dark="true"] .bb-controls .stButton > button {{
  border: 1px solid {PALETTE["d_border"]};
  background: rgba(255,255,255,0.06);
}}

.bb-chat {{
  margin-top: 6px;
  padding: 2px 2px 6px 2px;
}}

.bb-bubble {{
  border-radius: 16px;
  padding: 14px 14px;
  line-height: 1.55;
  border: 1px solid {PALETTE["border"]};
  white-space: pre-wrap;
}}

body[data-dark="true"] .bb-bubble {{
  border: 1px solid {PALETTE["d_border"]};
}}

.bb-user {{
  background: {PALETTE["user_bg"]};
}}

body[data-dark="true"] .bb-user {{
  background: {PALETTE["d_user_bg"]};
}}

.bb-assistant {{
  background: {PALETTE["asst_bg"]};
}}

body[data-dark="true"] .bb-assistant {{
  background: {PALETTE["d_asst_bg"]};
}}

.bb-sources-title {{
  margin-top: 12px;
  font-weight: 850;
}}

.bb-sources ul {{
  margin: 8px 0 0 18px;
}}

.bb-sources li {{
  margin: 6px 0;
}}

/* Make chat input look like a real composer */
div[data-testid="stChatInput"] > div {{
  border-radius: 14px !important;
  border: 1px solid {PALETTE["border"]} !important;
  background: rgba(255,255,255,0.78) !important;
  box-shadow: none !important;
}}

div[data-testid="stChatInput"] textarea {{
  border-radius: 14px !important;
}}

body[data-dark="true"] div[data-testid="stChatInput"] > div {{
  border: 1px solid {PALETTE["d_border"]} !important;
  background: rgba(255,255,255,0.06) !important;
}}

/* Toggle switch polish */
div[data-testid="stCheckbox"] label {{
  display:flex;
  align-items:center;
  gap:10px;
  user-select:none;
  font-weight: 850;
}}

div[data-testid="stCheckbox"] input {{
  width: 46px !important;
  height: 26px !important;
  appearance: none !important;
  background: rgba(0,0,0,0.10);
  border: 1px solid {PALETTE["border"]};
  border-radius: 999px !important;
  position: relative !important;
  outline: none !important;
  cursor: pointer !important;
}}

div[data-testid="stCheckbox"] input:checked {{
  background: rgba(122,62,43,0.75);
  border-color: rgba(122,62,43,0.75);
}}

div[data-testid="stCheckbox"] input::before {{
  content: "";
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: rgba(255,255,255,0.92);
  transition: transform 0.18s ease;
}}

div[data-testid="stCheckbox"] input:checked::before {{
  transform: translateX(20px);
}}

body[data-dark="true"] div[data-testid="stCheckbox"] input {{
  background: rgba(255,255,255,0.08);
  border: 1px solid {PALETTE["d_border"]};
}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# Apply dark mode marker
st.markdown(
    f"<script>document.body.setAttribute('data-dark','{str(st.session_state.dark).lower()}');</script>",
    unsafe_allow_html=True,
)

# ============================
# Header + prefs (clean)
# ============================
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

st.markdown('<div class="bb-card">', unsafe_allow_html=True)
st.markdown('<div class="bb-hint">Type below and press Enter to send. Use Daily Reflection for a quick grounded check-in.</div>', unsafe_allow_html=True)

# Controls row (keep top clean + move buttons away from title)
c1, c2, c3 = st.columns([1, 1, 2], gap="small")
with c1:
    daily_clicked = st.button("Daily Reflection", use_container_width=True)
with c2:
    clear_clicked = st.button("Clear on-screen", use_container_width=True)
with c3:
    # small “thread” control without cluttering the top
    new_thread = st.button("New chat thread", use_container_width=True)

if clear_clicked:
    _reset_screen_only()

if new_thread:
    _new_chat_session()

# ============================
# Render chat history
# ============================
st.markdown('<div class="bb-chat">', unsafe_allow_html=True)

for m in st.session_state.messages:
    role = m.get("role", "assistant")
    content = m.get("content", "")

    if role == "user":
        with st.chat_message("user", avatar="🧑"):
            st.markdown(
                f'<div class="bb-bubble bb-user">{html.escape(content)}</div>',
                unsafe_allow_html=True
            )
    else:
        # Split answer vs Sources section (prevents nested bullet weirdness)
        raw = content.strip()
        if "\nSources:" in raw:
            body, sources = raw.split("\nSources:", 1)
            sources_lines = [s.strip() for s in sources.splitlines() if s.strip()]
        elif raw.startswith("Sources:"):
            body = ""
            sources_lines = [s.strip() for s in raw[len("Sources:"):].splitlines() if s.strip()]
        else:
            body = raw
            sources_lines = []

        with st.chat_message("assistant", avatar="🍂"):
            if body:
                st.markdown(
                    f'<div class="bb-bubble bb-assistant">{html.escape(body.strip())}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="bb-bubble bb-assistant"> </div>',
                    unsafe_allow_html=True
                )

            if sources_lines:
                # normalize bullets (flat list)
                cleaned = []
                for line in sources_lines:
                    line = line.lstrip("-•").strip()
                    if line:
                        cleaned.append(line)

                st.markdown('<div class="bb-sources-title">Sources:</div>', unsafe_allow_html=True)
                st.markdown('<div class="bb-sources"><ul>' + "".join(
                    f"<li>{html.escape(x)}</li>" for x in cleaned
                ) + "</ul></div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)  # bb-chat
st.markdown("</div>", unsafe_allow_html=True)  # bb-card

# ============================
# Chat input (true composer)
# ============================
user_text = st.chat_input("Message…")

def _run_query(prompt: str):
    # persist user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    _append_message(st.session_state.chat_session_id, "user", prompt)

    # assistant response (with “thinking”)
    with st.chat_message("assistant", avatar="🍂"):
        with st.spinner("Thinking…"):
            reply = ask(prompt, filters=None, top_k=10)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    _append_message(st.session_state.chat_session_id, "assistant", reply)
    st.rerun()

if daily_clicked:
    daily_prompt = (
        "Give me today’s AA Daily Reflection style guidance grounded only in the Big Book and 12&12 excerpts you have. "
        "Keep it short, practical, and cite sources."
    )
    _run_query(daily_prompt)

if user_text and user_text.strip():
    _run_query(user_text.strip())


