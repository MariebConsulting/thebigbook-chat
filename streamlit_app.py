
import re
import html
import streamlit as st
from scripts.smoke_ask import ask

st.set_page_config(page_title="The Big Book .chat", layout="wide")

# ----------------------------
# Palette
# ----------------------------
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

if "dark" not in st.session_state:
    st.session_state.dark = False

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hey — ask me anything about the Big Book or the 12&12. I’ll stay grounded in your corpus and include sources at the end.",
        }
    ]

# ----------------------------
# Helpers
# ----------------------------
def normalize_sources(text: str) -> str:
    """
    Ensures:
    - No citations in body required (your system prompt handles that)
    - "Sources:" exists
    - sources are a FLAT bullet list
    - removes nested bullet weirdness
    """
    if not text:
        return text

    # Split on Sources: (case-insensitive), keep body separate
    parts = re.split(r"\n\s*Sources:\s*\n|\n\s*Sources:\s*", text, flags=re.IGNORECASE)
    body = parts[0].strip()

    # Collect cite strings from anywhere in the response (prefer bracketed cites)
    # Example: [bigbook (4th) — bigbook/ch05 — Chunk#10]
    cites = re.findall(r"\[[^\[\]]+?\]", text)

    # Also accept raw cite-like lines if model returns them without brackets
    # (rare, but helps)
    if not cites and len(parts) > 1:
        tail = parts[1]
        for line in tail.splitlines():
            line = line.strip("•- \t")
            if line:
                cites.append(line)

    # Dedup while keeping order
    seen = set()
    flat = []
    for c in cites:
        c = c.strip()
        if c and c not in seen:
            seen.add(c)
            flat.append(c)

    if not flat:
        # If none, return body as-is
        return body

    sources_block = "Sources:\n" + "\n".join([f"- {c}" for c in flat])
    return f"{body}\n\n{sources_block}".strip()

def safe_text(s: str) -> str:
    # Keep things safe + predictable inside markdown
    return html.escape(s or "").replace("\n", "\n\n")

# ----------------------------
# CSS
# ----------------------------
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

h1, h2, h3, p, label, span, div {{ color: inherit; }}

.bb-top {{
  margin-bottom: 10px;
}}

.bb-title {{
  font-size: 42px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.05;
}}

.bb-sub {{
  margin-top: 6px;
  font-size: 14px;
  opacity: 0.78;
}}

.bb-toolbar {{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  margin: 10px 0 14px;
}}

.bb-pill {{
  border: 1px solid {PALETTE["border"]};
  background: rgba(255,255,255,0.55);
  border-radius: 999px;
  padding: 8px 12px;
}}

body[data-dark="true"] .bb-pill {{
  border: 1px solid {PALETTE["d_border"]};
  background: rgba(255,255,255,0.05);
}}

.bb-chat-wrap {{
  border: 1px solid {PALETTE["border"]};
  background: {PALETTE["card"]};
  border-radius: 18px;
  padding: 14px 14px;
  box-shadow: {PALETTE["shadow"]};
}}

body[data-dark="true"] .bb-chat-wrap {{
  border: 1px solid {PALETTE["d_border"]};
  background: {PALETTE["d_card"]};
}}

.bb-hint {{
  font-size: 13px;
  opacity: 0.75;
  margin: 6px 2px 10px;
}}

.bb-divider {{
  height: 8px;
}}

/* Chat message bubble styling */
div[data-testid="stChatMessage"] > div {{
  border-radius: 16px !important;
  padding: 10px 12px !important;
}}

div[data-testid="stChatMessage"][data-testid="stChatMessage-user"] > div {{
  background: rgba(255,255,255,0.78) !important;
  border: 1px solid {PALETTE["border"]} !important;
}}

body[data-dark="true"] div[data-testid="stChatMessage"][data-testid="stChatMessage-user"] > div {{
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid {PALETTE["d_border"]} !important;
}}

div[data-testid="stChatMessage"][data-testid="stChatMessage-assistant"] > div {{
  background: rgba(255,255,255,0.52) !important;
  border: 1px solid {PALETTE["border"]} !important;
}}

body[data-dark="true"] div[data-testid="stChatMessage"][data-testid="stChatMessage-assistant"] > div {{
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid {PALETTE["d_border"]} !important;
}}

/* Make the input feel intentional */
div[data-testid="stChatInput"] textarea {{
  border-radius: 14px !important;
}}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ----------------------------
# Header
# ----------------------------
st.markdown(
    """
<div class="bb-top">
  <div class="bb-title">The Big Book .chat</div>
  <div class="bb-sub">Ask anything. Citations enforced.</div>
</div>
""",
    unsafe_allow_html=True,
)

# Preferences (kept minimal)
with st.expander("Preferences", expanded=False):
    st.checkbox("Dark mode", key="dark")

st.markdown(
    f"<script>document.body.setAttribute('data-dark','{str(st.session_state.dark).lower()}');</script>",
    unsafe_allow_html=True,
)

# Toolbar (keeps top clean)
t1, t2 = st.columns([1, 1], gap="small")
with t1:
    if st.button("Daily Reflection", use_container_width=True):
        st.session_state._trigger_daily = True
with t2:
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hey — ask me anything about the Big Book or the 12&12. I’ll stay grounded in your corpus and include sources at the end.",
            }
        ]
        st.session_state._trigger_daily = False
        st.rerun()

st.markdown('<div class="bb-divider"></div>', unsafe_allow_html=True)

# Chat wrapper (centered card)
st.markdown('<div class="bb-chat-wrap">', unsafe_allow_html=True)
st.markdown('<div class="bb-hint">Type below and press Enter to send.</div>', unsafe_allow_html=True)

# Render history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(safe_text(m["content"]))

st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------
# Input + Actions
# ----------------------------
user_msg = st.chat_input("Message… (e.g., What does AA say about fear?)")

# Daily Reflection triggered by button (above) — runs as if user asked it
if st.session_state.get("_trigger_daily"):
    user_msg = (
        "Give me today’s AA Daily Reflection style guidance grounded only in the Big Book and 12&12 excerpts you have. "
        "Keep it short, practical, and include sources."
    )
    st.session_state._trigger_daily = False

if user_msg:
    st.session_state.messages.append({"role": "user", "content": user_msg})

    # Show assistant "thinking" bubble immediately
    with st.chat_message("assistant"):
        thinking = st.empty()
        thinking.markdown("Thinking…")

        try:
            result = ask(user_msg, filters=None, top_k=10)
            result = normalize_sources(result)
        except Exception as e:
            result = (
                "I hit an error while answering.\n\n"
                f"Details: {e}"
            )

        thinking.empty()
        st.markdown(safe_text(result))

    st.session_state.messages.append({"role": "assistant", "content": result})
