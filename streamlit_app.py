import streamlit as st
from scripts.smoke_ask import ask

st.set_page_config(page_title="The Big Book .chat", layout="wide")

# ----------------------------
# Palette (Sherwin-ish, darker + calmer)
# ----------------------------
PALETTE = {
    # Light mode
    "bg": "#E7E1D7",          # darker warm neutral (less khaki blast)
    "bg2": "#DCD3C7",         # secondary wash
    "card": "rgba(255,255,255,0.72)",
    "text": "#1F1F1D",
    "muted": "rgba(31,31,29,0.72)",
    "border": "rgba(31,31,29,0.14)",
    "shadow": "0 18px 55px rgba(0,0,0,0.10)",
    # Accents pulled from your SW palette vibe
    "accent": "#3F4A41",      # Rock Bottom-ish green/charcoal
    "accent2": "#5B5247",     # warm taupe
    # Dark mode
    "d_bg": "#111312",
    "d_bg2": "#1A1F1C",
    "d_card": "rgba(255,255,255,0.06)",
    "d_text": "#F3F2EE",
    "d_muted": "rgba(243,242,238,0.70)",
    "d_border": "rgba(243,242,238,0.14)",
    "d_accent": "#A9B3A7",
}

# ----------------------------
# State
# ----------------------------
if "dark" not in st.session_state:
    st.session_state.dark = False

# ----------------------------
# CSS
# ----------------------------
CSS = f"""
<style>
/* Hide Streamlit chrome */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}

/* Layout: constrain width for mobile feel */
.block-container {{
  padding-top: 24px;
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

/* Dark mode override (we toggle a class on body via an injected marker) */
html:has(body[data-dark="true"]) .stApp {{
  background: radial-gradient(1200px 600px at 20% 0%,
    {PALETTE["d_bg2"]} 0%,
    {PALETTE["d_bg"]} 55%,
    {PALETTE["d_bg"]} 100%);
  color: {PALETTE["d_text"]};
}}

h1, h2, h3, p, label, span, div {{ color: inherit; }}

/* Header row */
.bb-top {{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:16px;
  margin-bottom: 14px;
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

/* Card */
.bb-card {{
  border: 1px solid {PALETTE["border"]};
  background: {PALETTE["card"]};
  border-radius: 18px;
  padding: 18px;
  box-shadow: {PALETTE["shadow"]};
}}

html:has(body[data-dark="true"]) .bb-card {{
  border: 1px solid {PALETTE["d_border"]};
  background: {PALETTE["d_card"]};
  box-shadow: 0 18px 55px rgba(0,0,0,0.35);
}}

/* Input pill (kills the "bubble" look) */
div[data-testid="stTextInput"] > div {{
  border-radius: 999px !important;
  background: rgba(255,255,255,0.82) !important;
  border: 1px solid {PALETTE["border"]} !important;
  box-shadow: none !important;
}}

html:has(body[data-dark="true"]) div[data-testid="stTextInput"] > div {{
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid {PALETTE["d_border"]} !important;
}}

div[data-testid="stTextInput"] input {{
  padding: 14px 16px !important;
  font-size: 16px !important;
}}

div[data-testid="stTextInput"] label {{
  display:none !important;
}}

/* Buttons */
div.stButton > button {{
  width: 100%;
  border-radius: 14px;
  padding: 12px 14px;
  border: 1px solid {PALETTE["border"]};
  background: rgba(255,255,255,0.75);
  font-weight: 700;
}}

div.stButton > button:hover {{
  border-color: rgba(0,0,0,0.22);
  transform: translateY(-1px);
}}

html:has(body[data-dark="true"]) div.stButton > button {{
  border: 1px solid {PALETTE["d_border"]};
  background: rgba(255,255,255,0.06);
}}

html:has(body[data-dark="true"]) div.stButton > button:hover {{
  border-color: rgba(255,255,255,0.24);
}}

/* Answer area */
.bb-answer {{
  margin-top: 16px;
  border-radius: 18px;
  padding: 16px 18px;
  border: 1px solid {PALETTE["border"]};
  background: rgba(255,255,255,0.58);
}}

html:has(body[data-dark="true"]) .bb-answer {{
  border: 1px solid {PALETTE["d_border"]};
  background: rgba(255,255,255,0.04);
}}

/* Toggle switch (we restyle Streamlit checkbox) */
div[data-testid="stCheckbox"] label {{
  display:flex;
  align-items:center;
  gap:10px;
  user-select:none;
  font-weight: 700;
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
  background: rgba(63,74,65,0.75);
  border-color: rgba(63,74,65,0.75);
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

html:has(body[data-dark="true"]) div[data-testid="stCheckbox"] input {{
  background: rgba(255,255,255,0.08);
  border: 1px solid {PALETTE["d_border"]};
}}

html:has(body[data-dark="true"]) div[data-testid="stCheckbox"] input:checked {{
  background: rgba(169,179,167,0.45);
  border-color: rgba(169,179,167,0.45);
}}

/* Remove extra spacing that can look like a "ghost bar" */
div[data-testid="stTextInput"] {{
  margin-bottom: 6px;
}}
</style>
"""

# Inject CSS + a dark-mode marker attribute (so CSS can switch)
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    f"<script>document.body.setAttribute('data-dark', '{str(st.session_state.dark).lower()}');</script>",
    unsafe_allow_html=True,
)

# ----------------------------
# UI
# ----------------------------
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

# Dark mode toggle (styled checkbox)
st.checkbox("Dark mode", key="dark")

st.markdown('<div class="bb-card">', unsafe_allow_html=True)

question = st.text_input(
    "Ask",
    placeholder="Ask anything… (e.g., What does AA say about fear?)",
)

col1, col2 = st.columns([1, 1], gap="medium")

ask_clicked = col1.button("Ask", use_container_width=True)
daily_clicked = col2.button("Daily Reflection", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------
# Actions
# ----------------------------
if ask_clicked and question.strip():
    with st.spinner("Searching..."):
        result = ask(question, filters=None, top_k=10)
    st.markdown(f'<div class="bb-answer">{result}</div>', unsafe_allow_html=True)

elif daily_clicked:
    daily_prompt = (
        "Give me today’s AA Daily Reflection style guidance grounded only in the Big Book and 12&12 excerpts you have. "
        "Keep it short, practical, and cite sources."
    )
    with st.spinner("Searching..."):
        result = ask(daily_prompt, filters=None, top_k=10)
    st.markdown(f'<div class="bb-answer">{result}</div>', unsafe_allow_html=True)
