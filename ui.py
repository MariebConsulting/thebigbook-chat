
import datetime as dt
import streamlit as st
from scripts.smoke_ask import ask

# --------------------------------------
# Sherwin palette (from your image)
# --------------------------------------
SW = {
    # Neutrals / foundations
    "limestone": "#6E6A60",     # SW 9599 Limestone (approx)
    "sable": "#5A4B3F",         # SW 6083 Sable (approx)
    "black_bean": "#2B1F1B",    # SW 6006 Black Bean (approx)
    "rock_bottom": "#3D3F3E",   # SW 7062 Rock Bottom (approx)

    # Accents
    "relic_bronze": "#8B6A3D",  # SW 6132 Relic Bronze (approx)
    "dark_auburn": "#4A2A2A",   # SW 6034 Dark Auburn (approx)
    "rojo_marron": "#3F2A25",   # SW 9182 Rojo Marrón (approx)
    "plum_brown": "#3A2D33",    # SW 6272 Plum Brown (approx)

    # Cool tones
    "garden_gate": "#5A5A4B",   # SW 6167 Garden Gate (approx)
    "tarragon": "#3B4A4B",      # SW 9660 Tarragon (approx)
    "sea_mariner": "#39414B",   # SW 9640 Sea Mariner (approx)

    # Warm red (sparingly)
    "royd_copper_red": "#7A2E22",  # SW 2839 Roycroft Copper Red (approx)
}

# --------------------------------------
# Streamlit base config
# --------------------------------------
st.set_page_config(
    page_title="The Big Book .chat",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --------------------------------------
# Daily reflection prompts (no long quotes)
# --------------------------------------
DAILY_REFLECTIONS = [
    ("Step One check-in", "Where am I trying to control what I can’t? What would acceptance look like today?"),
    ("Inventory light", "What emotion is driving me right now—fear, pride, resentment, or shame? What’s the next right action?"),
    ("Amends lens", "Is there someone I owe clarity or kindness to—today? What would a simple repair look like?"),
    ("Prayer / meditation", "What’s one thing I can release today, and one thing I can do with full integrity?"),
    ("Service", "Who can I help in a small, real way in the next hour?"),
]

def pick_daily_reflection() -> str:
    i = dt.date.today().toordinal() % len(DAILY_REFLECTIONS)
    title, prompt = DAILY_REFLECTIONS[i]
    return f"{title}: {prompt}"

# --------------------------------------
# Session state
# --------------------------------------
if "q" not in st.session_state:
    st.session_state.q = ""
if "last_answer" not in st.session_state:
    st.session_state.last_answer = None
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# --------------------------------------
# Dark/Light themed CSS via CSS variables
# --------------------------------------
def inject_css(dark: bool):
    if dark:
        # Dark mode
        bg = SW["black_bean"]
        bg2 = SW["rojo_marron"]
        card = "#141110"
        text = "#F2EFEA"
        muted = "rgba(242,239,234,0.68)"
        border = "rgba(242,239,234,0.14)"
        pill = "#171312"
        accent = SW["relic_bronze"]
        accent2 = SW["royd_copper_red"]  # sparingly as a highlight
        soft = "rgba(139,106,61,0.18)"
        shadow = "rgba(0,0,0,0.45)"
    else:
        # Light mode
        bg = "#F4F2EC"
        bg2 = "#EFEADF"
        card = "#FFFFFF"
        text = "#1F1A17"
        muted = "rgba(31,26,23,0.62)"
        border = "rgba(31,26,23,0.12)"
        pill = "#FFFFFF"
        accent = SW["tarragon"]          # cool modern accent
        accent2 = SW["relic_bronze"]     # warm secondary
        soft = "rgba(59,74,75,0.12)"
        shadow = "rgba(0,0,0,0.10)"

    CSS = f"""
    <style>
    /* Hide Streamlit chrome */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    :root {{
      --bg: {bg};
      --bg2: {bg2};
      --card: {card};
      --text: {text};
      --muted: {muted};
      --border: {border};
      --pill: {pill};
      --accent: {accent};
      --accent2: {accent2};
      --soft: {soft};
      --shadow: {shadow};
      --radius: 18px;
    }}

    .stApp {{
      background: radial-gradient(1200px 600px at 30% 0%, var(--bg2) 0%, var(--bg) 55%, var(--bg) 100%);
      color: var(--text);
    }}

    html, body, [class*="css"] {{
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
    }}

    /* Centered mobile-first layout */
    .bb-wrap {{
      max-width: 820px;
      margin: 0 auto;
      padding: 16px 16px 26px 16px;
    }}

    .bb-top {{
      display:flex;
      align-items:flex-start;
      justify-content:space-between;
      gap: 12px;
      margin-top: 6px;
      margin-bottom: 10px;
    }}

    .bb-title {{
      font-size: 34px;
      line-height: 1.08;
      font-weight: 900;
      letter-spacing: -0.02em;
      margin: 0;
    }}

    .bb-sub {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 14px;
    }}

    .bb-pill {{
      background: var(--pill);
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 10px 12px;
      display:flex;
      align-items:center;
      gap:10px;
      box-shadow: 0 14px 34px var(--shadow);
    }}

    div[data-testid="stTextInput"] input {{
      border: none !important;
      outline: none !important;
      box-shadow: none !important;
      background: transparent !important;
      padding: 10px 8px !important;
      font-size: 16px !important;
      color: var(--text) !important;
    }}

    div[data-testid="stTextInput"] label {{
      display:none !important;
    }}

    /* Buttons */
    .bb-actions {{
      display:flex;
      gap:10px;
      margin-top: 12px;
      flex-wrap: wrap;
    }}

    .bb-btn-primary button {{
      background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
      color: white !important;
      border: 1px solid rgba(0,0,0,0.05) !important;
      border-radius: 14px !important;
      padding: 10px 14px !important;
      font-weight: 800 !important;
      box-shadow: 0 12px 26px var(--shadow) !important;
    }}

    .bb-btn-ghost button {{
      background: var(--card) !important;
      color: var(--text) !important;
      border: 1px solid var(--border) !important;
      border-radius: 14px !important;
      padding: 10px 14px !important;
      font-weight: 800 !important;
    }}

    /* Cards */
    .bb-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 16px 16px;
      margin-top: 14px;
      box-shadow: 0 14px 34px var(--shadow);
    }}

    .bb-muted {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }}

    .bb-answer {{
      font-size: 16px;
      line-height: 1.55;
    }}

    /* Toggle container styling */
    .bb-toggle {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 6px 10px;
      box-shadow: 0 10px 22px var(--shadow);
    }}

    /* Make checkbox/toggle area tighter */
    div[data-testid="stCheckbox"] label {{
      gap: 8px !important;
    }}

    @media (max-width: 560px) {{
      .bb-title {{ font-size: 28px; }}
      .bb-wrap {{ padding: 14px 12px 22px 12px; }}
    }}
    </style>
    """
    st.markdown(CSS, unsafe_allow_html=True)

inject_css(st.session_state.dark_mode)

# --------------------------------------
# Header + toggle
# --------------------------------------
st.markdown('<div class="bb-wrap">', unsafe_allow_html=True)

left, right = st.columns([3, 1], vertical_alignment="top")
with left:
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

with right:
    st.markdown('<div class="bb-toggle">', unsafe_allow_html=True)
    st.session_state.dark_mode = st.checkbox("Dark mode", value=st.session_state.dark_mode)
    st.markdown("</div>", unsafe_allow_html=True)

# If user toggles, re-inject CSS immediately
inject_css(st.session_state.dark_mode)

# --------------------------------------
# Single “pill” input
# --------------------------------------
st.markdown('<div class="bb-pill">', unsafe_allow_html=True)
st.text_input(
    "Ask",
    key="q",
    placeholder="Ask anything… (e.g., What does AA say about fear?)",
    label_visibility="collapsed",
)
st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------
# Actions (Ask / Daily Reflection / Clear)
# --------------------------------------
colA, colB, colC = st.columns([1.2, 1.6, 1.2], vertical_alignment="center")
with colA:
    st.markdown('<div class="bb-btn-primary">', unsafe_allow_html=True)
    run = st.button("Ask", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with colB:
    st.markdown('<div class="bb-btn-ghost">', unsafe_allow_html=True)
    daily = st.button("Daily Reflection", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with colC:
    st.markdown('<div class="bb-btn-ghost">', unsafe_allow_html=True)
    clear = st.button("Clear", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

if clear:
    st.session_state.q = ""
    st.session_state.last_answer = None
    st.rerun()

if daily:
    st.session_state.q = pick_daily_reflection()
    run = True  # auto-run

# --------------------------------------
# Run query
# --------------------------------------
if run and st.session_state.q.strip():
    with st.spinner("Searching…"):
        st.session_state.last_answer = ask(
            st.session_state.q.strip(),
            filters=None,
            top_k=10,
        )

# --------------------------------------
# Output
# --------------------------------------
if st.session_state.last_answer:
    st.markdown('<div class="bb-card">', unsafe_allow_html=True)
    st.markdown('<div class="bb-muted">Answer</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="bb-answer">{st.session_state.last_answer}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.markdown(
        '<div class="bb-card"><div class="bb-muted">Tip</div>'
        '<div class="bb-answer">Tap <b>Daily Reflection</b> or ask your own question above.</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("</div>", unsafe_allow_html=True)
