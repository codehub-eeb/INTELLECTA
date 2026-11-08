
import os
import sqlite3
import uuid
import json
import html

from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pypdf import PdfReader


# =========================================================
# INTELLECTA — CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="INTELLECTA | Study Assistant",
    page_icon="I",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.5-flash-lite"
DB_NAME = "study_assistant.db"
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "intellecta-logo.png")

if not API_KEY:
    st.error("Gemini API key not found. Please check your .env file.")
    st.stop()

client = genai.Client(
    api_key=API_KEY,
    http_options=types.HttpOptions(timeout=60000)
)


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def initialize_database():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT
            )
        """)

        conn.commit()


def create_conversation():
    conversation_id = str(uuid.uuid4())
    created_at = datetime.now().strftime("%d %b %Y, %I:%M %p")

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO conversations (conversation_id, title, created_at)
            VALUES (?, ?, ?)
        """, (conversation_id, "New conversation", created_at))
        conn.commit()

    return conversation_id


def save_message(conversation_id, role, content):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO messages (conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            conversation_id,
            role,
            content,
            datetime.now().strftime("%d %b %Y, %I:%M %p")
        ))

        if role == "user":
            title = content.strip().replace("\n", " ")[:45] or "New conversation"

            cursor.execute("""
                UPDATE conversations
                SET title = ?
                WHERE conversation_id = ?
            """, (title, conversation_id))

        conn.commit()


def get_conversations():
    with get_connection() as conn:
        return conn.execute("""
            SELECT conversation_id, title, created_at
            FROM conversations
            ORDER BY rowid DESC
        """).fetchall()


def get_conversation_messages(conversation_id):
    with get_connection() as conn:
        return conn.execute("""
            SELECT role, content
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
        """, (conversation_id,)).fetchall()


initialize_database()


# =========================================================
# SESSION STATE
# =========================================================

defaults = {
    "page": "Dashboard",
    "conversation_id": None,
    "messages": [],
    "study_mode": "Normal Mode",
    "answer_marks": "5 Marks",
    "planner_tasks": [],
    "pdf_count": 0,
    "quiz_count": 0,
    "flashcards": None,
    "flashcard_index": 0,
"flashcard_show_answer": False,
    "generated_quiz": None,
    "pdf_summary": None
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

if st.session_state.conversation_id is None:
    st.session_state.conversation_id = create_conversation()


# =========================================================
# INTELLECTA DESIGN SYSTEM
# PREMIUM CHARCOAL + EMERALD + MINT
# =========================================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
    color-scheme: dark;

    --bg: #101311;
    --bg-soft: #151A17;

    --surface: rgba(27, 34, 30, .88);
    --surface-solid: #1B221E;
    --surface-raised: #222B25;

    --accent: #55D6A0;
    --accent-light: #8BE9BD;
    --accent-strong: #32BD83;

    --accent-soft: rgba(85, 214, 160, .13);
    --accent-glow: rgba(85, 214, 160, .16);

    --text: #F1F6F2;
    --muted: #A0ADA4;
    --muted-2: #7D8A81;

    --dark-text: #102018;

    --border: rgba(221, 241, 228, .11);
    --border-strong: rgba(85, 214, 160, .28);
}


/* GLOBAL */

html {
    scroll-behavior: smooth;
    scroll-padding-top: 24px;
    background: var(--bg);
}

body,
.stApp,
[data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Inter', sans-serif !important;
}

.stApp {
    background:
        radial-gradient(ellipse at 82% 0%, rgba(85,214,160,.105), transparent 34%),
        radial-gradient(ellipse at 0% 65%, rgba(85,214,160,.045), transparent 32%),
        linear-gradient(145deg, #101311 0%, #121814 52%, #101512 100%) !important;
}

[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
.main,
.block-container,
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"] {
    background-color: transparent !important;
}

.block-container {
    max-width: 1440px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}


/* SCROLLBAR */

::-webkit-scrollbar {
    width: 9px;
    height: 9px;
}

::-webkit-scrollbar-track {
    background: #101512;
}

::-webkit-scrollbar-thumb {
    background: #3B4940;
    border: 2px solid #101512;
    border-radius: 20px;
}

::-webkit-scrollbar-thumb:hover {
    background: #55A982;
}


/* ANIMATIONS */

@keyframes intellectaFadeUp {
    from {
        opacity: 0;
        transform: translateY(12px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.hero-title,
.hero-subtitle,
.metric-card,
.feature-card,
.glass-card {
    animation: intellectaFadeUp .48s ease both;
}

.metric-card,
.feature-card,
.glass-card,
.stButton > button,
.stDownloadButton > button,
[data-testid="stSegmentedControl"] button {
    transition:
        background .22s ease,
        border-color .22s ease,
        box-shadow .22s ease,
        transform .22s ease,
        color .22s ease !important;
}


/* HEADER */

[data-testid="stHeader"] {
    background: rgba(16, 19, 17, .82) !important;
    border-bottom: 1px solid rgba(221,241,228,.045);
}

[data-testid="stToolbar"] {
    background: transparent !important;
}

#MainMenu,
footer {
    visibility: hidden;
}


/* SIDEBAR */

[data-testid="stSidebar"] {
    background: rgba(19, 25, 21, .97) !important;
    border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] > div:first-child {
    background: transparent !important;
    padding-top: 1.35rem;
}

[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    background: transparent !important;
}

.brand {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 27px;
    font-weight: 800;
    letter-spacing: -1.6px;
    color: #F5FAF6;
    margin-bottom: 2px;
}

.brand span {
    color: var(--accent);
}

.brand-caption {
    color: var(--muted-2);
    font-size: 9px;
    letter-spacing: 1.75px;
    text-transform: uppercase;
    margin-bottom: 27px;
}

.sidebar-label {
    color: var(--muted-2);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.7px;
    text-transform: uppercase;
    margin: 20px 0 10px 5px;
}

[data-testid="stSidebar"] [data-testid="stRadio"] > div {
    gap: 6px;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 13px !important;
    padding: 8px 12px !important;
    transition: all .2s ease !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: rgba(255,255,255,.045) !important;
    border-color: var(--border) !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: var(--accent-soft) !important;
    border-color: var(--border-strong) !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {
    color: var(--accent) !important;
    font-weight: 700 !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] p {
    color: #D0DAD2 !important;
    font-size: 13px !important;
}


/* TYPOGRAPHY */

h1, h2, h3, h4 {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: var(--text) !important;
    letter-spacing: -.8px;
    font-weight: 800 !important;
}

p, li, label {
    color: #D3DDD5;
}

[data-testid="stMarkdownContainer"] {
    color: #D3DDD5;
}

.hero-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: clamp(36px, 4vw, 54px);
    line-height: 1.15;
    font-weight: 800;
    letter-spacing: -2px;
    color: #F5FAF6;
    margin-bottom: 14px;
}

.hero-title span {
    color: var(--accent);
}

.hero-subtitle {
    color: var(--muted);
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    line-height: 1.85;
    max-width: 700px;
    margin-bottom: 8px;
}

.section-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 21px;
    font-weight: 800;
    color: #F1F6F2;
    margin: 30px 0 15px;
    letter-spacing: -.6px;
}

.small-muted {
    color: var(--muted-2);
    font-size: 12px;
}


/* GLASS CARDS */

.glass-card,
.metric-card,
.feature-card {
    position: relative;
    overflow: hidden;

    background: linear-gradient(
        135deg,
        rgba(43, 57, 48, .78),
        rgba(27, 35, 30, .68) 58%,
        rgba(42, 73, 56, .32)
    ) !important;

    border: 1px solid rgba(220, 244, 228, .13) !important;
    border-top-color: rgba(235, 255, 241, .22) !important;

    border-radius: 20px !important;
    padding: 23px !important;

    backdrop-filter: blur(20px) saturate(140%) !important;
    -webkit-backdrop-filter: blur(20px) saturate(140%) !important;

    box-shadow:
        0 13px 34px rgba(0,0,0,.23),
        inset 0 1px 0 rgba(255,255,255,.055) !important;

    height: 100%;
}

.glass-card::before,
.metric-card::before,
.feature-card::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;

    background: linear-gradient(
        125deg,
        rgba(255,255,255,.055),
        transparent 40%,
        transparent 72%,
        rgba(85,214,160,.045)
    );
}

.glass-card:hover,
.metric-card:hover,
.feature-card:hover {
    transform: translateY(-3px);
    border-color: rgba(85,214,160,.35) !important;

    box-shadow:
        0 18px 40px rgba(0,0,0,.29),
        0 0 22px rgba(85,214,160,.055),
        inset 0 1px 0 rgba(255,255,255,.075) !important;
}


/* METRIC CARDS */

.metric-card {
    min-height: 145px;
    padding: 24px !important;
}

.metric-label {
    color: var(--muted);
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.2px;
    font-family: 'Inter', sans-serif;
}

.metric-value {
    color: #F5FAF6;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 32px;
    font-weight: 800;
    margin-top: 10px;
    letter-spacing: -1px;
}

.metric-note {
    color: var(--accent);
    font-size: 11px;
    margin-top: 5px;
}


/* FEATURE CARDS */

.feature-card {
    min-height: 160px;
    padding: 26px !important;
}

.feature-title {
    color: #F5FAF6;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 17px;
    font-weight: 800;
    letter-spacing: -.4px;
    margin-bottom: 12px;
    position: relative;
}

.feature-description {
    color: #B5C2B8;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    line-height: 1.8;
    position: relative;
}


/* WORKSPACE GRID SPACING */

[class*="st-key-workspace_grid"] {
    width: 100%;
}

[class*="st-key-workspace_grid"] [data-testid="stHorizontalBlock"] {
    gap: 1.5rem !important;
    align-items: stretch !important;
}

[class*="st-key-workspace_grid"] [data-testid="column"] {
    min-width: 0 !important;
}

[class*="st-key-workspace_grid"] .feature-card {
    min-height: 160px;
    height: 100%;
}

.workspace-row-spacer {
    height: 24px;
}


/* BUTTONS */

.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] button {
    background: linear-gradient(135deg, #63DDAA, #3FC58F) !important;
    color: #102018 !important;
    -webkit-text-fill-color: #102018 !important;
    border: 1px solid rgba(112,235,181,.72) !important;
    border-radius: 50px !important;
    padding: 9px 21px !important;
    min-height: 42px;
    font-size: 13px !important;
    font-weight: 800 !important;
    box-shadow: 0 4px 17px rgba(55,190,132,.11);
}

.stButton > button *,
.stDownloadButton > button *,
[data-testid="stFormSubmitButton"] button * {
    color: #102018 !important;
    -webkit-text-fill-color: #102018 !important;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover {
    background: #8BE9BD !important;
    color: #102018 !important;
    -webkit-text-fill-color: #102018 !important;
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(55,190,132,.20) !important;
}

.stButton > button:active,
.stDownloadButton > button:active {
    transform: scale(.985);
}


/* INPUTS */

.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
[data-testid="stDateInput"] input,
[data-testid="stTimeInput"] input {
    background: #1A211C !important;
    color: #F1F6F2 !important;
    -webkit-text-fill-color: #F1F6F2 !important;
    border: 1px solid #3B4940 !important;
    border-radius: 12px !important;
    caret-color: var(--accent) !important;
}

.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
    color: #839087 !important;
    -webkit-text-fill-color: #839087 !important;
}

.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus,
[data-testid="stDateInput"] input:focus {
    border-color: rgba(85,214,160,.78) !important;
    box-shadow: 0 0 0 1px rgba(85,214,160,.17) !important;
}


/* SELECTBOX AND DROPDOWNS */

[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
    background: #1A211C !important;
    color: #F1F6F2 !important;
    border: 1px solid #3B4940 !important;
    border-radius: 12px !important;
    min-height: 42px;
}

[data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stMultiSelect"] [data-baseweb="select"] span {
    color: #F1F6F2 !important;
}

[data-testid="stSelectbox"] svg,
[data-testid="stMultiSelect"] svg {
    color: var(--accent) !important;
    fill: var(--accent) !important;
}

[data-baseweb="popover"],
[data-baseweb="menu"],
[role="listbox"],
[data-testid="stPopoverBody"],
[data-testid="stDatePicker"] {
    background: #1B241E !important;
    color: #F1F6F2 !important;
    border: 1px solid rgba(85,214,160,.22) !important;
    border-radius: 13px !important;
    box-shadow: 0 14px 38px rgba(0,0,0,.48) !important;
}

[role="option"],
[data-baseweb="menu"] li {
    background: #1B241E !important;
    color: #DCE6DE !important;
}

[role="option"]:hover,
[data-baseweb="menu"] li:hover {
    background: rgba(85,214,160,.12) !important;
    color: var(--accent) !important;
}

[role="option"][aria-selected="true"] {
    background: rgba(85,214,160,.16) !important;
    color: var(--accent) !important;
}


/* SEGMENTED CONTROL */

[data-testid="stSegmentedControl"],
[data-baseweb="button-group"] {
    background: rgba(255,255,255,.045) !important;
    border: 1px solid var(--border) !important;
    border-radius: 50px !important;
    padding: 5px !important;
    gap: 5px !important;
}

[data-testid="stSegmentedControl"] button,
[data-baseweb="button-group"] button {
    background: transparent !important;
    color: #AEBAB1 !important;
    -webkit-text-fill-color: #AEBAB1 !important;
    border: 1px solid transparent !important;
    border-radius: 50px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 8px 18px !important;
}

[data-testid="stSegmentedControl"] button:not([aria-pressed="true"]):not([aria-checked="true"]),
[data-baseweb="button-group"] button:not([aria-pressed="true"]):not([aria-checked="true"]) {
    color: #AEBAB1 !important;
    -webkit-text-fill-color: #AEBAB1 !important;
}

[data-testid="stSegmentedControl"] button:hover:not([aria-pressed="true"]):not([aria-checked="true"]),
[data-baseweb="button-group"] button:hover:not([aria-pressed="true"]):not([aria-checked="true"]) {
    background: rgba(85,214,160,.08) !important;
    color: var(--accent-light) !important;
    -webkit-text-fill-color: var(--accent-light) !important;
}

[data-testid="stSegmentedControl"] button[aria-pressed="true"],
[data-testid="stSegmentedControl"] button[aria-checked="true"],
[data-baseweb="button-group"] button[aria-pressed="true"],
[data-baseweb="button-group"] button[aria-checked="true"] {
    background: linear-gradient(135deg, #63DDAA, #3FC58F) !important;
    color: #102018 !important;
    -webkit-text-fill-color: #102018 !important;
    border: 1px solid rgba(112,235,181,.75) !important;
    box-shadow: 0 3px 15px rgba(55,190,132,.15) !important;
    font-weight: 800 !important;
}

[data-testid="stSegmentedControl"] button[aria-pressed="true"] *,
[data-testid="stSegmentedControl"] button[aria-checked="true"] *,
[data-baseweb="button-group"] button[aria-pressed="true"] *,
[data-baseweb="button-group"] button[aria-checked="true"] * {
    color: #102018 !important;
    -webkit-text-fill-color: #102018 !important;
    font-weight: 800 !important;
}

[data-testid="stSegmentedControl"] button:focus,
[data-baseweb="button-group"] button:focus {
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(85,214,160,.25) !important;
}


/* CHECKBOXES, RADIO AND SLIDER */

[data-testid="stCheckbox"] label,
[data-testid="stRadio"] label {
    color: #D3DDD5 !important;
}

[data-testid="stCheckbox"] input,
[data-testid="stRadio"] input {
    accent-color: var(--accent) !important;
}

[data-testid="stSlider"] [role="slider"] {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
}

[data-testid="stSlider"] [data-testid="stThumbValue"] {
    color: var(--accent) !important;
}


/* CHAT MESSAGES */

[data-testid="stChatMessage"] {
    background: rgba(39, 51, 43, .62) !important;
    border: 1px solid rgba(220,244,228,.10) !important;
    border-radius: 17px !important;
    padding: 15px !important;
    margin-bottom: 13px !important;
    backdrop-filter: blur(15px);
    -webkit-backdrop-filter: blur(15px);
}

[data-testid="stChatInput"] {
    background: rgba(26, 34, 29, .96) !important;
    border: 1px solid rgba(85,214,160,.25) !important;
    border-radius: 17px !important;
    transition: all .22s ease !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 22px rgba(85,214,160,.09) !important;
}

[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: #F1F6F2 !important;
    -webkit-text-fill-color: #F1F6F2 !important;
    caret-color: var(--accent) !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #839087 !important;
    -webkit-text-fill-color: #839087 !important;
}

[data-testid="stChatInput"] button {
    color: var(--accent) !important;
    background: transparent !important;
}


/* FILE UPLOADER */

[data-testid="stFileUploader"],
[data-testid="stFileUploader"] section,
[data-testid="stFileUploader"] section > div {
    background: rgba(39,51,43,.52) !important;
    color: #DCE6DE !important;
    border: 1px dashed rgba(85,214,160,.35) !important;
    border-radius: 16px !important;
}

[data-testid="stFileUploader"] button {
    background: #29352D !important;
    color: var(--accent) !important;
    border: 1px solid #45564A !important;
    border-radius: 50px !important;
}

[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span {
    color: #AAB7AD !important;
}


/* ALERTS, EXPANDERS, TABS AND TABLES */

[data-testid="stAlert"] {
    background: rgba(39,51,43,.68) !important;
    color: #EAF2EC !important;
    border: 1px solid rgba(220,244,228,.12) !important;
    border-radius: 13px !important;
}

[data-testid="stExpander"] {
    background: rgba(39,51,43,.42) !important;
    border: 1px solid rgba(220,244,228,.11) !important;
    border-radius: 14px !important;
}

[data-testid="stExpander"] details,
[data-testid="stExpander"] summary {
    background: transparent !important;
    color: #EAF2EC !important;
}

[data-testid="stTabs"] button {
    color: #AEBAB1 !important;
}

[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
}

[data-testid="stDataFrame"],
[data-testid="stTable"] {
    background: #1A211C !important;
    color: #EAF2EC !important;
    border: 1px solid var(--border) !important;
    border-radius: 13px !important;
    overflow: hidden;
}

[data-testid="stDataFrame"] * {
    color: #EAF2EC !important;
}


/* METRICS, CAPTIONS AND PROGRESS */

[data-testid="stMetric"] {
    background: rgba(39,51,43,.55) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    padding: 12px !important;
}

[data-testid="stMetricLabel"],
[data-testid="stMetricValue"] {
    color: #EAF2EC !important;
}

[data-testid="stCaptionContainer"],
.stCaption {
    color: var(--muted) !important;
}

.stProgress > div > div {
    background: #2A352D !important;
    border-radius: 20px !important;
}

.stProgress > div > div > div {
    background: linear-gradient(90deg, #35B982, #83E6B8) !important;
    border-radius: 20px !important;
}

hr {
    border-color: rgba(220,244,228,.10) !important;
}

a {
    color: var(--accent) !important;
}

::selection {
    background: rgba(85,214,160,.28);
    color: #fff;
}


/* ACCESSIBILITY */

@media (prefers-reduced-motion: reduce) {
    html {
        scroll-behavior: auto;
    }

    *,
    *::before,
    *::after {
        animation-duration: .01ms !important;
        transition-duration: .01ms !important;
    }
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def generate_ai_response(prompt, max_tokens=1500):
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.4,
            max_output_tokens=max_tokens
        )
    )

    return response.text or "I couldn't generate a response. Please try again."


def load_conversation(conversation_id):
    records = get_conversation_messages(conversation_id)

    st.session_state.messages = [
        {"role": role, "content": content}
        for role, content in records
    ]

    st.session_state.conversation_id = conversation_id
    st.session_state.page = "AI Chatbot"


def new_conversation():
    st.session_state.conversation_id = create_conversation()
    st.session_state.messages = []
    st.session_state.page = "AI Chatbot"


def show_metric(label, value, note):
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
    """, unsafe_allow_html=True)


def show_feature(title, description):
    st.markdown(f"""
        <div class="feature-card">
            <div class="feature-title">{title}</div>
            <div class="feature-description">{description}</div>
        </div>
    """, unsafe_allow_html=True)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=175)
    else:
        st.markdown("""
            <div class="brand">INTELLECTA<span>.</span></div>
        """, unsafe_allow_html=True)

    st.markdown(
        '<div class="brand-caption">Intelligent Learning Platform</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="sidebar-label">Workspace</div>',
        unsafe_allow_html=True
    )

    pages = [
        "Dashboard",
        "AI Chatbot",
        "PDF Summarizer",
        "Quiz Generator",
        "Flashcards",
        "Study Planner"
    ]

    selected_page = st.radio(
        "Navigation",
        pages,
        index=pages.index(st.session_state.page),
        label_visibility="collapsed"
    )

    st.session_state.page = selected_page

    st.markdown("---")

    st.markdown(
        '<div class="sidebar-label">Chat History</div>',
        unsafe_allow_html=True
    )

    if st.button("＋  New conversation", use_container_width=True):
        new_conversation()
        st.rerun()

    conversations = get_conversations()

    if conversations:

        history_options = {
            f"{title or 'New conversation'}  ·  {created_at}": conversation_id
            for conversation_id, title, created_at in conversations[:15]
        }

        selected_history = st.selectbox(
            "Recent conversations",
            options=list(history_options.keys()),
            label_visibility="collapsed"
        )

        if st.button("Open selected chat", use_container_width=True):
            load_conversation(history_options[selected_history])
            st.rerun()

    else:
        st.markdown(
            '<div class="small-muted">Your conversations will appear here.</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    st.markdown("""
        <div class="small-muted">
            INTELLECTA<br>
            Personal learning workspace<br><br>
            <span style="color:#55D6A0;">●</span> Gemini connection configured
        </div>
    """, unsafe_allow_html=True)


# =========================================================
# DASHBOARD
# =========================================================

if st.session_state.page == "Dashboard":

    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=125)

    st.markdown("""
        <div class="hero-title">
            Learn smarter.<br>
            Think <span>further.</span>
        </div>

        <div class="hero-subtitle">
            Your personal AI-powered learning workspace.
            Understand concepts, organize your preparation,
            and make every study session more productive.
        </div>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="section-title">Overview</div>',
        unsafe_allow_html=True
    )

    conversations = get_conversations()

    col1, col2, col3 = st.columns(3, gap="large")

    with col1:
        show_metric(
            "CONVERSATIONS",
            len(conversations),
            "Saved in your workspace"
        )

    with col2:
        show_metric(
            "PDF DOCUMENTS",
            st.session_state.pdf_count,
            "Processed this session"
        )

    with col3:
        show_metric(
            "QUIZZES CREATED",
            st.session_state.quiz_count,
            "Generated this session"
        )

    st.markdown(
        '<div class="section-title">Your workspace</div>',
        unsafe_allow_html=True
    )

    features = [
        (
            "AI Chatbot",
            "Ask questions, understand difficult concepts and get structured explanations."
        ),
        (
            "PDF Summarizer",
            "Upload study material and convert lengthy documents into clear summaries."
        ),
        (
            "Quiz Generator",
            "Generate topic-based questions to test your understanding."
        ),
        (
            "Flashcards",
            "Create concise question-and-answer cards for revision."
        ),
        (
            "Study Planner",
            "Organize your tasks and keep track of your study sessions."
        ),
        (
            "Study Mode",
            "Get academic answers structured according to university marks."
        )
    ]

    with st.container(key="workspace_grid"):

        for start in range(0, len(features), 3):

            cols = st.columns(3, gap="large")

            for col, (title, description) in zip(
                cols,
                features[start:start + 3]
            ):
                with col:
                    show_feature(title, description)

            if start + 3 < len(features):
                st.markdown(
                    '<div class="workspace-row-spacer"></div>',
                    unsafe_allow_html=True
                )

    st.markdown(
        '<div class="section-title">Get started</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2, gap="large")

    with c1:
        if st.button("Start learning with AI", use_container_width=True):
            st.session_state.page = "AI Chatbot"
            st.rerun()

    with c2:
        if st.button("Open study planner", use_container_width=True):
            st.session_state.page = "Study Planner"
            st.rerun()


# =========================================================
# AI CHATBOT
# =========================================================

elif st.session_state.page == "AI Chatbot":

    st.markdown("""
        <div class="hero-title">
            AI <span>Assistant</span>
        </div>

        <div class="hero-subtitle">
            Ask anything. Understand everything.
            Your learning companion, powered by Gemini.
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1], gap="large")

    with col1:

        study_mode = st.segmented_control(
            "Response style",
            ["Normal Mode", "Study Mode"],
            default=st.session_state.study_mode,
            key="study_mode_control"
        )

        if study_mode:
            st.session_state.study_mode = study_mode

    with col2:

        if st.session_state.study_mode == "Study Mode":

            marks_options = [
                "2 Marks",
                "5 Marks",
                "7 Marks",
                "10 Marks"
            ]

            marks = st.selectbox(
                "Answer format",
                marks_options,
                index=marks_options.index(st.session_state.answer_marks)
            )

            st.session_state.answer_marks = marks

        st.markdown("---")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

        if not st.session_state.messages:
            st.markdown(
            """
            <div class="glass-card">
                <div class="feature-title">
                    What would you like to learn today?
                </div>
                <div class="feature-description">
                    Ask a technical question, understand a difficult
                    topic, or prepare an exam-oriented answer.
                </div>
            </div>
            """,
            unsafe_allow_html=True
            )

    user_prompt = st.chat_input("Ask your question here...")


    if user_prompt:

        st.session_state.messages.append({
            "role": "user",
            "content": user_prompt
        })

        save_message(
            st.session_state.conversation_id,
            "user",
            user_prompt
        )

        with st.chat_message("user"):
            st.markdown(user_prompt)

        if st.session_state.study_mode == "Study Mode":

            system_prompt = f"""
You are Intellecta, a professional academic AI study assistant.

Answer the following question in clear academic English.
The answer is for a university examination worth {st.session_state.answer_marks}.

Follow these rules:

- Start with a clear definition or introduction.
- Use meaningful headings and subheadings.
- Use numbered points or bullet points.
- Explain concepts in understandable language.
- Add examples wherever useful.
- For comparison questions, use a comparison table.
- Include advantages, disadvantages or applications when relevant.
- End with a short conclusion.
- Match the depth of the answer to the requested marks.
- Avoid unnecessary repetition.
- Do not invent facts.

Question: {user_prompt}
"""

            max_tokens = 1800

        else:

            previous_messages = st.session_state.messages[-6:]

            conversation_context = "\n".join([
                f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
                for m in previous_messages
            ])

            system_prompt = f"""
You are Intellecta, a helpful and professional learning assistant.

Explain concepts in simple, clear language.
Use step-by-step explanations when useful.
Include practical examples.
Use headings and bullet points for readability.
Be accurate, friendly and concise.
Avoid unnecessary repetition.

Recent conversation:
{conversation_context}

Respond to the latest user question.
"""

            max_tokens = 1500

        with st.chat_message("assistant"):

            response_placeholder = st.empty()
            full_response = ""

            try:

                stream = client.models.generate_content_stream(
                    model=MODEL_NAME,
                    contents=system_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.4,
                        max_output_tokens=max_tokens
                    )
                )

                for chunk in stream:

                    if chunk.text:
                        full_response += chunk.text

                        response_placeholder.markdown(
                            full_response + "▌"
                        )

                response_placeholder.markdown(
                    full_response or "I couldn't generate a response. Please try again."
                )

                if full_response:

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_response
                    })

                    save_message(
                        st.session_state.conversation_id,
                        "assistant",
                        full_response
                    )

            except Exception as error:
                st.error(f"Unable to generate response: {error}")


# =========================================================
# PDF SUMMARIZER
# =========================================================

elif st.session_state.page == "PDF Summarizer":

    st.markdown("""
        <div class="hero-title">
            Document <span>Intelligence</span>
        </div>

        <div class="hero-subtitle">
            Convert lengthy study material into structured,
            understandable summaries.
        </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload your PDF document",
        type=["pdf"]
    )

    if uploaded_file and st.button("Generate summary"):

        with st.spinner("Analyzing your document..."):

            try:

                reader = PdfReader(uploaded_file)

                document_text = "\n".join([
                    page.extract_text() or ""
                    for page in reader.pages
                ])

                if not document_text.strip():

                    st.warning(
                        "No selectable text found. This PDF may contain scanned pages."
                    )

                else:

                    prompt = f"""
Summarize the following academic document.

Provide:

1. Main topic and introduction
2. Important concepts
3. Key definitions
4. Important points
5. Short conclusion

Use clear headings and understandable academic English.

Document:
{document_text[:25000]}
"""

                    summary = generate_ai_response(prompt, 2500)

                    st.session_state.pdf_summary = summary
                    st.session_state.pdf_count += 1

            except Exception as error:
                st.error(f"PDF processing failed: {error}")

    if st.session_state.pdf_summary:

        st.markdown(
            '<div class="section-title">Document summary</div>',
            unsafe_allow_html=True
        )

        st.markdown(st.session_state.pdf_summary)


# =========================================================
# QUIZ GENERATOR
# =========================================================

elif st.session_state.page == "Quiz Generator":

    st.markdown("""
        <div class="hero-title">
            Knowledge <span>Check</span>
        </div>

        <div class="hero-subtitle">
            Generate practice questions from any academic topic.
        </div>
    """, unsafe_allow_html=True)

    topic = st.text_input(
        "Enter your topic",
        placeholder="Example: Database Management System"
    )

    number_of_questions = st.selectbox(
        "Number of questions",
        [5, 10, 15, 20]
    )

    difficulty = st.selectbox(
        "Difficulty level",
        ["Easy", "Medium", "Hard"]
    )

    if st.button("Generate quiz"):

        if not topic.strip():

            st.warning("Please enter a topic first.")

        else:

            with st.spinner("Creating your quiz..."):

                try:

                    prompt = f"""
Create {number_of_questions} multiple-choice questions
on the topic: {topic}.

Difficulty: {difficulty}

For every question:

- Give four options (A, B, C, D).
- Clearly mention the correct answer.
- Add a short explanation.

Use a clean numbered format.
"""

                    st.session_state.generated_quiz = generate_ai_response(
                        prompt,
                        2500
                    )

                    st.session_state.quiz_count += 1

                except Exception as error:
                    st.error(f"Quiz generation failed: {error}")

    if st.session_state.generated_quiz:

        st.markdown(
            '<div class="section-title">Generated quiz</div>',
            unsafe_allow_html=True
        )

        st.markdown(st.session_state.generated_quiz)



# =========================================================
# FLASHCARDS — INTERACTIVE QUESTION & ANSWER CARDS
# =========================================================

elif st.session_state.page == "Flashcards":

    st.markdown("""
        <div class="hero-title">
            Smart <span>Revision</span>
        </div>

        <div class="hero-subtitle">
            Turn important concepts into interactive revision cards.
            Reveal answers, navigate cards and track your progress.
        </div>
    """, unsafe_allow_html=True)

    topic = st.text_input(
        "Enter a topic for flashcards",
        placeholder="Example: Operating System"
    )

    card_count = st.selectbox(
        "Number of flashcards",
        [5, 10, 15, 20]
    )

    if st.button("Create flashcards"):

        if not topic.strip():
            st.warning("Please enter a topic.")

        else:
            with st.spinner("Creating your flashcards..."):

                try:

                    prompt = f"""
Create exactly {card_count} academic study flashcards
about the topic: {topic.strip()}.

Return ONLY valid JSON in this format:

{{
    "flashcards": [
        {{
            "question": "Question here",
            "answer": "Answer here"
        }}
    ]
}}

Rules:
- Generate exactly {card_count} cards.
- Questions must be short and meaningful.
- Answers must be clear and accurate.
- Cover important academic concepts.
- Avoid duplicate questions.
- Do not include Markdown or text outside JSON.
"""

                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.3,
                            max_output_tokens=2500,
                            response_mime_type="application/json"
                        )
                    )

                    result = json.loads(response.text or "")

                    cards = result.get("flashcards", [])

                    valid_cards = [
                        {
                            "question": str(card.get("question", "")).strip(),
                            "answer": str(card.get("answer", "")).strip()
                        }
                        for card in cards
                        if isinstance(card, dict)
                        and str(card.get("question", "")).strip()
                        and str(card.get("answer", "")).strip()
                    ]

                    if len(valid_cards) != card_count:
                        st.error(
                            "The AI did not generate the expected number "
                            "of valid cards. Please try again."
                        )

                    else:
                        st.session_state.flashcards = valid_cards
                        st.session_state.flashcard_index = 0
                        st.session_state.flashcard_show_answer = False
                        st.success("Flashcards created successfully!")

                except Exception as error:
                    st.error(f"Flashcard generation failed: {error}")

    # -----------------------------------------------------
    # INTERACTIVE FLASHCARD DISPLAY
    # -----------------------------------------------------

    if st.session_state.flashcards:

        cards = st.session_state.flashcards

        # Handle old text-based flashcards safely
        if not isinstance(cards, list):

            st.info(
                "These are older flashcards. Generate a new set "
                "to use interactive revision."
            )

        elif cards:

            total_cards = len(cards)

            # Keep index within valid range
            current_index = min(
                max(st.session_state.flashcard_index, 0),
                total_cards - 1
            )

            st.session_state.flashcard_index = current_index

            current_card = cards[current_index]
            question_text = html.escape(str(current_card.get("question", "")))
            answer_text = html.escape(str(current_card.get("answer", "")))

            st.markdown(
                '<div class="section-title">Your flashcards</div>',
                unsafe_allow_html=True
            )

            # Progress information
            st.progress((current_index + 1) / total_cards)

            st.caption(
                f"Card {current_index + 1} of {total_cards}"
            )

            # Flashcard container
            with st.container(border=True):

                st.markdown(
                    f"""
                    <div style="
                        text-align:center;
                        padding:28px 12px;
                        min-height:180px;
                    ">
                        <div style="
                            color:#55D6A0;
                            font-size:11px;
                            font-weight:800;
                            letter-spacing:2px;
                            margin-bottom:22px;
                        ">
                            {"ANSWER" if st.session_state.flashcard_show_answer else "QUESTION"}
                        </div>

                    
                           {answer_text if st.session_state.flashcard_show_answer else question_text}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.write("")

            # Reveal / hide answer
            if not st.session_state.flashcard_show_answer:

                if st.button(
                    "Show Answer",
                    use_container_width=True,
                    key="show_flashcard_answer"
                ):
                    st.session_state.flashcard_show_answer = True
                    st.rerun()

            else:

                if st.button(
                    "Hide Answer",
                    use_container_width=True,
                    key="hide_flashcard_answer"
                ):
                    st.session_state.flashcard_show_answer = False
                    st.rerun()

            st.write("")

            # Previous and Next navigation
            previous_col, next_col = st.columns(2, gap="large")

            with previous_col:

                if st.button(
                    "← Previous",
                    use_container_width=True,
                    disabled=(current_index == 0),
                    key="previous_flashcard"
                ):
                    st.session_state.flashcard_index -= 1
                    st.session_state.flashcard_show_answer = False
                    st.rerun()

            with next_col:

                if st.button(
                    "Next →",
                    use_container_width=True,
                    disabled=(current_index == total_cards - 1),
                    key="next_flashcard"
                ):
                    st.session_state.flashcard_index += 1
                    st.session_state.flashcard_show_answer = False
                    st.rerun()

            st.caption(
                "Use Show Answer to reveal the answer. "
                "Navigate between cards using Previous and Next."
            )

# =========================================================
# STUDY PLANNER
# =========================================================

elif st.session_state.page == "Study Planner":

    st.markdown("""
        <div class="hero-title">
            Study <span>Planner</span>
        </div>

        <div class="hero-subtitle">
            Organize your preparation and keep your learning goals clear.
        </div>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="section-title">Add a study task</div>',
        unsafe_allow_html=True
    )

    task_name = st.text_input(
        "Task name",
        placeholder="Example: Complete DBMS Unit 3"
    )

    subject = st.text_input(
        "Subject",
        placeholder="Example: Database Management System"
    )

    if st.button("Add task"):

        if task_name.strip():

            st.session_state.planner_tasks.append({
                "task": task_name.strip(),
                "subject": subject.strip() or "General",
                "completed": False
            })

            st.success("Task added successfully.")
            st.rerun()

        else:
            st.warning("Please enter a task name.")

    st.markdown(
        '<div class="section-title">Your tasks</div>',
        unsafe_allow_html=True
    )

    tasks = st.session_state.planner_tasks

    if not tasks:

        st.markdown("""
            <div class="glass-card">
                <div class="feature-title">
                    Your planner is clear.
                </div>

                <div class="feature-description">
                    Add your first task to organize your study schedule.
                </div>
            </div>
        """, unsafe_allow_html=True)

    else:

        for index, task in enumerate(tasks):

            col1, col2 = st.columns([5, 1], gap="large")

            with col1:

                completed = st.checkbox(
                    f"{task['task']}  ·  {task['subject']}",
                    value=task["completed"],
                    key=f"task_{index}"
                )

                task["completed"] = completed

            with col2:

                if st.button("Remove", key=f"remove_{index}"):

                    st.session_state.planner_tasks.pop(index)
                    st.rerun()

        completed_count = sum(
            1 for task in tasks if task["completed"]
        )

        progress = completed_count / len(tasks)

        st.markdown(
            '<div class="section-title">Progress</div>',
            unsafe_allow_html=True
        )

        st.progress(progress)

        st.caption(
            f"{completed_count} of {len(tasks)} tasks completed"
        )


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.markdown("""
    <div style="
        text-align:center;
        padding:15px 0;
        color:#7D8A81;
        font-family:'Inter', sans-serif;
        font-size:11px;
        letter-spacing:1px;
    ">
        INTELLECTA &nbsp; · &nbsp; INTELLIGENT LEARNING PLATFORM
    </div>
""", unsafe_allow_html=True)
