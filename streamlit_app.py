import html
import streamlit as st
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

if "dark" not in st.session_state:
    st.session_state.dark = False

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hey — ask me anything about the Big Book or the 12&12. I’ll stay grounded in your corpus and include citations."
        }
    ]

CSS = f"""
<style>
/* Hide Streamlit chrome */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}
[data-testid="stToolbar"] {{display:none !important;}}
[data-testid="stHeader"] {{display:none !important;}}

/* Layout */
.block-container {{
  padding-top: 22px;
  max-width: 980px;
}}

/* Background */
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

/* Header */
.bb-top {{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:16px;
  margin-bottom: 6px;
}}

.bb-title {{
  font-size: 42px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.05;
  margin: 0;
}}

.bb-sub {{
  margin-top: 8px;
  font-size: 14px;
  opacity: 0.78;
}}

/* Settings bar (prevents the toggle looking like an input) */
.bb-settings {{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  margin: 12px 0 14px 0;
  padding: 10px 12px;
  border: 1px solid {PALETTE["border"]};
  background: {PALETTE["card"]};
  border-radius: 14px;
  box-shadow: {PALETTE["shadow"]};
}}

body[data-dark="true"] .bb-settings {{
  border: 1px solid {PALETTE["d_border"]};
  background: {PALETTE["d_card"]};
  box-shadow: 0 18px 55px rgba(0,0,0,0.35);
}}

.bb-chip {{
  display:inline-flex;
  align-items:center;
  gap:8px;
  font-weight: 700;
  opacity: .9;
}}

.bb-hint {{
  font-size: 13px;
  opacity: .75;
}}

/* Chat container feel */
.bb-chat-wrap {{
  border: 1px solid {PALETTE["border"]};
  background: {PALETTE["card"]};
  border-radius: 18px;
  padding: 14px 14px 6px 14px;
  box-shadow: {PALETTE["shadow"]};
}}

body[data-dark="true"] .bb-chat-wrap {{
  border: 1px solid {PALETTE["d_border"]};
  background: {PALETTE["d_card"]};
  box-shadow: 0 18px 55px rgba(0,0,0,0.35);
}}

/* Make chat bubbles nicer */
[data-testid="stChatMessage"] > div {{
  border-radius: 16px;
}}

[data-testid="stChatMessage"] p {{
  line-height: 1.45;
}}

</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# Apply dark-mode marker (so CSS can switch)
st.markdown(
    f"<script>document.body.setAttribute('data-dark','{str(st.session_state.dark).lower()}');</script>",
    unsafe_allow_html=True,
)

# Title
st.markdown(
    """
<div class="bb-top">
  <div>
    <div class="bb-title">The Big Book .chat</div>
    <div class="bb-sub">Ask anything. Citations enforced.</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# Settings row (toggle here, not next to your input)
left, right = st.columns([1, 1], vertical_alignment="center")
with left:
    st.markdown('<div class="bb-chip">⚙️ Settings</div>', unsafe_allow_html=True)
with right:
    st.session_state.dark = st.toggle("Dark mode", value=st.session_state.dark)

# Re-apply marker after toggle
st.markdown(
    f"<script>document.body.setAttribute('data-dark','{str(st.session_state.dark).lower()}');</script>",
    unsafe_allow_html=True,
)

# Action buttons (kept out of the chat input area)
btn1, btn2 = st.columns([1, 1], gap="medium")
daily_clicked = btn2.button("Daily Reflection", use_container_width=True)

if daily_clicked:
    daily_prompt = (
        "Give me today’s AA Daily Reflection style guidance grounded only in the Big Book and 12&12 excerpts you have. "
        "Keep it short, practical, and cite sources."
    )
    st.session_state.messages.append({"role": "user", "content": "Daily Reflection"})
    with st.spinner("Searching..."):
        result = ask(daily_prompt, filters=None, top_k=10)
    st.session_state.messages.append({"role": "assistant", "content": result})
    st.rerun()

# Chat “window”
st.markdown('<div class="bb-chat-wrap">', unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        # Allow markdown + keep safe rendering
        st.markdown(html.escape(m["content"]).replace("\n", "  \n"))

st.markdown("</div>", unsafe_allow_html=True)

# Chat input (this is what makes it feel like a real bot)
prompt = st.chat_input("Ask about fear, resentment, Step work, prayer, amends…")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Searching..."):
            result = ask(prompt, filters=None, top_k=10)
        st.markdown(html.escape(result).replace("\n", "  \n"))

    st.session_state.messages.append({"role": "assistant", "content": result})
    st.rerun()
