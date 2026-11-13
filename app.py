
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
# PREMIUM WHITE + ROYAL BLUE
# =========================================================

st.markdown(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

:root {
    color-scheme: light;
    --bg: #F5F8FF;
    --surface: #FFFFFF;
    --surface-soft: #F0F5FF;
    --blue: #1457C5;
    --blue-dark: #0A347E;
    --blue-light: #E8F0FF;
    --text: #14233D;
    --muted: #64748B;
    --border: #DCE6F5;
}

html, body, .stApp, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stApp {
    background:
      radial-gradient(ellipse at 80% 0%, rgba(37,99,235,.09), transparent 34%),
      radial-gradient(ellipse at 0% 65%, rgba(59,130,246,.055), transparent 30%),
      linear-gradient(145deg, #F8FAFF 0%, #F2F6FD 100%) !important;
}
[data-testid="stMain"], [data-testid="stMainBlockContainer"], .main,
.block-container, [data-testid="stVerticalBlock"], [data-testid="stHorizontalBlock"] {
    background-color: transparent !important;
}
.block-container { max-width: 1440px; padding-top: 2rem; padding-bottom: 3.5rem; }
[data-testid="stHeader"] { background: rgba(248,250,255,.88) !important; border-bottom: 1px solid #E5ECF7; }
[data-testid="stToolbar"] { background: transparent !important; }
#MainMenu, footer { visibility: hidden; }

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #F1F5FB; }
::-webkit-scrollbar-thumb { background: #C4D2E7; border: 2px solid #F1F5FB; border-radius: 20px; }
::-webkit-scrollbar-thumb:hover { background: #8EABD5; }

@keyframes intellectaFadeUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.hero-title, .hero-subtitle, .metric-card, .feature-card, .glass-card {
  animation: intellectaFadeUp .42s ease both;
}
.metric-card, .feature-card, .glass-card, .stButton > button,
.stDownloadButton > button, [data-testid="stSegmentedControl"] button {
  transition: background .2s ease, border-color .2s ease, box-shadow .2s ease,
              transform .2s ease, color .2s ease !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
  background: rgba(255,255,255,.96) !important;
  border-right: 1px solid var(--border) !important;
  box-shadow: 5px 0 24px rgba(20,55,105,.035);
}
[data-testid="stSidebar"] > div:first-child { background: transparent !important; padding-top: 1.25rem; }
[data-testid="stSidebar"] [data-testid="stSidebarContent"] { background: transparent !important; }
.brand {
  font-family: 'Plus Jakarta Sans', sans-serif; font-size: 27px; font-weight: 800;
  letter-spacing: -1.5px; color: var(--blue-dark); margin-bottom: 2px;
}
.brand span { color: #3B82F6; }
.brand-caption {
  color: #8292AA; font-size: 9px; letter-spacing: 1.7px;
  text-transform: uppercase; margin-bottom: 26px;
}
.sidebar-label {
  color: #8A9AB2; font-size: 10px; font-weight: 800;
  letter-spacing: 1.6px; text-transform: uppercase; margin: 18px 0 9px 5px;
}
[data-testid="stSidebar"] [data-testid="stRadio"] > div { gap: 5px; }
[data-testid="stSidebar"] [data-testid="stRadio"] label {
  background: transparent !important; border: 1px solid transparent !important;
  border-radius: 12px !important; padding: 8px 11px !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
  background: #F3F7FF !important; border-color: #E2EAF8 !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
  background: #EAF1FF !important; border-color: #C9DAFA !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {
  color: var(--blue) !important; font-weight: 800 !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] p { color: #43536C !important; font-size: 13px !important; }

/* Typography */
h1, h2, h3, h4 {
  font-family: 'Plus Jakarta Sans', sans-serif !important; color: var(--text) !important;
  letter-spacing: -.7px; font-weight: 800 !important;
}
p, li, label, [data-testid="stMarkdownContainer"] { color: #34445E; }
.hero-title {
  font-family: 'Plus Jakarta Sans', sans-serif; font-size: clamp(36px, 4vw, 55px);
  line-height: 1.12; font-weight: 800; letter-spacing: -2.2px;
  color: #102D5B; margin-bottom: 13px;
}
.hero-title span { color: #2463D4; }
.hero-subtitle {
  color: #667792; font-size: 14px; line-height: 1.85;
  max-width: 720px; margin-bottom: 9px;
}
.section-title {
  font-family: 'Plus Jakarta Sans', sans-serif; font-size: 21px;
  font-weight: 800; color: #17345F; margin: 29px 0 15px; letter-spacing: -.5px;
}
.small-muted { color: #8291A8; font-size: 12px; }

/* Premium white glass cards */
.glass-card, .metric-card, .feature-card {
  position: relative; overflow: hidden; height: 100%;
  background: linear-gradient(145deg, rgba(255,255,255,.98), rgba(245,249,255,.94)) !important;
  border: 1px solid rgba(195,211,237,.85) !important;
  border-top-color: #FFFFFF !important; border-radius: 20px !important;
  padding: 23px !important; backdrop-filter: blur(18px) saturate(140%) !important;
  -webkit-backdrop-filter: blur(18px) saturate(140%) !important;
  box-shadow: 0 10px 30px rgba(27,67,126,.065), inset 0 1px 0 #FFFFFF !important;
}
.glass-card::before, .metric-card::before, .feature-card::before {
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(125deg, rgba(255,255,255,.8), transparent 45%, rgba(59,130,246,.035));
}
.glass-card:hover, .metric-card:hover, .feature-card:hover {
  transform: translateY(-3px); border-color: #A9C4F1 !important;
  box-shadow: 0 16px 36px rgba(27,67,126,.11), 0 0 0 3px rgba(37,99,235,.035) !important;
}
.metric-card { min-height: 142px; padding: 23px !important; }
.metric-label { color: #71819A; font-size: 10px; font-weight: 800; letter-spacing: 1.15px; }
.metric-value {
  color: #173F83; font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 32px; font-weight: 800; margin-top: 10px; letter-spacing: -1px;
}
.metric-note { color: #3470D1; font-size: 11px; margin-top: 5px; }
.feature-card { min-height: 158px; padding: 25px !important; }
.feature-title {
  color: #183967; font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 17px; font-weight: 800; letter-spacing: -.35px;
  margin-bottom: 10px; position: relative;
}
.feature-description { color: #65758E; font-size: 13px; line-height: 1.8; position: relative; }
[class*="st-key-workspace_grid"] { width: 100%; }
[class*="st-key-workspace_grid"] [data-testid="stHorizontalBlock"] {
  gap: 1.35rem !important; align-items: stretch !important;
}
[class*="st-key-workspace_grid"] [data-testid="column"] { min-width: 0 !important; }
.workspace-row-spacer { height: 22px; }

/* Buttons */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button {
  background: linear-gradient(135deg, #2463D4, #164BAA) !important;
  color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important;
  border: 1px solid rgba(31,91,190,.25) !important; border-radius: 50px !important;
  padding: 9px 21px !important; min-height: 42px; font-size: 13px !important;
  font-weight: 800 !important; box-shadow: 0 5px 16px rgba(36,99,212,.16);
}
.stButton > button *, .stDownloadButton > button *, [data-testid="stFormSubmitButton"] button * {
  color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important;
}
.stButton > button:hover, .stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover {
  background: #0F3F98 !important; transform: translateY(-2px);
  box-shadow: 0 9px 22px rgba(36,99,212,.23) !important;
}
.stButton > button:active, .stDownloadButton > button:active { transform: scale(.985); }

/* Inputs */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
[data-testid="stDateInput"] input, [data-testid="stTimeInput"] input {
  background: #FFFFFF !important; color: #1E2F4A !important;
  -webkit-text-fill-color: #1E2F4A !important; border: 1px solid #D5E0F0 !important;
  border-radius: 12px !important; caret-color: #2463D4 !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
  color: #91A0B5 !important; -webkit-text-fill-color: #91A0B5 !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus,
[data-testid="stDateInput"] input:focus {
  border-color: #6C98E5 !important; box-shadow: 0 0 0 3px rgba(37,99,235,.09) !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
  background: #FFFFFF !important; color: #243752 !important;
  border: 1px solid #D5E0F0 !important; border-radius: 12px !important; min-height: 42px;
}
[data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stMultiSelect"] [data-baseweb="select"] span { color: #243752 !important; }
[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"],
[data-testid="stPopoverBody"], [data-testid="stDatePicker"] {
  background: #FFFFFF !important; color: #243752 !important;
  border: 1px solid #DCE6F5 !important; border-radius: 13px !important;
  box-shadow: 0 14px 38px rgba(22,54,102,.14) !important;
}
[role="option"], [data-baseweb="menu"] li { background: #FFFFFF !important; color: #34445E !important; }
[role="option"]:hover, [data-baseweb="menu"] li:hover { background: #EDF3FF !important; color: #1457C5 !important; }
[data-testid="stSegmentedControl"], [data-baseweb="button-group"] {
  background: #EDF2FA !important; border: 1px solid #DCE6F5 !important;
  border-radius: 50px !important; padding: 4px !important; gap: 4px !important;
}
[data-testid="stSegmentedControl"] button, [data-baseweb="button-group"] button {
  background: transparent !important; color: #61728D !important;
  -webkit-text-fill-color: #61728D !important; border: 1px solid transparent !important;
  border-radius: 50px !important; font-size: 13px !important; font-weight: 700 !important;
  padding: 8px 17px !important;
}
[data-testid="stSegmentedControl"] button[aria-pressed="true"],
[data-testid="stSegmentedControl"] button[aria-checked="true"],
[data-baseweb="button-group"] button[aria-pressed="true"],
[data-baseweb="button-group"] button[aria-checked="true"] {
  background: linear-gradient(135deg, #2463D4, #164BAA) !important;
  color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important;
  border: 1px solid #1B55B7 !important; box-shadow: 0 3px 12px rgba(36,99,212,.17) !important;
}
[data-testid="stCheckbox"] label, [data-testid="stRadio"] label { color: #40516B !important; }
[data-testid="stCheckbox"] input, [data-testid="stRadio"] input { accent-color: #2463D4 !important; }
[data-testid="stSlider"] [role="slider"] { background: #2463D4 !important; border-color: #2463D4 !important; }

/* Chat */
[data-testid="stChatMessage"] {
  background: rgba(255,255,255,.88) !important; border: 1px solid #DCE6F5 !important;
  border-radius: 17px !important; padding: 15px !important; margin-bottom: 12px !important;
  box-shadow: 0 5px 18px rgba(28,61,110,.045);
}
[data-testid="stChatInput"] {
  background: rgba(255,255,255,.98) !important; border: 1px solid #C9D9F1 !important;
  border-radius: 17px !important; box-shadow: 0 8px 24px rgba(28,61,110,.07);
}
[data-testid="stChatInput"]:focus-within {
  border-color: #5C8FE2 !important; box-shadow: 0 0 0 3px rgba(37,99,235,.09) !important;
}
[data-testid="stChatInput"] textarea {
  background: transparent !important; color: #1E2F4A !important;
  -webkit-text-fill-color: #1E2F4A !important; caret-color: #2463D4 !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #91A0B5 !important; -webkit-text-fill-color: #91A0B5 !important; }
[data-testid="stChatInput"] button { color: #2463D4 !important; background: transparent !important; }

/* Uploaders, alerts, tabs */
[data-testid="stFileUploader"], [data-testid="stFileUploader"] section,
[data-testid="stFileUploader"] section > div {
  background: #F7FAFF !important; color: #40516B !important;
  border: 1px dashed #AFC5E8 !important; border-radius: 15px !important;
}
[data-testid="stFileUploader"] button {
  background: #EAF1FF !important; color: #1457C5 !important;
  border: 1px solid #C9DAFA !important; border-radius: 50px !important;
}
[data-testid="stFileUploader"] small, [data-testid="stFileUploader"] span { color: #667792 !important; }
[data-testid="stAlert"] {
  background: #F0F6FF !important; color: #28466F !important;
  border: 1px solid #D6E5FC !important; border-radius: 13px !important;
}
[data-testid="stExpander"] {
  background: rgba(255,255,255,.8) !important; border: 1px solid #DCE6F5 !important;
  border-radius: 14px !important;
}
[data-testid="stExpander"] details, [data-testid="stExpander"] summary {
  background: transparent !important; color: #29456E !important;
}
[data-testid="stTabs"] button { color: #61728D !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color: #1457C5 !important; border-bottom-color: #2463D4 !important; }
[data-testid="stDataFrame"], [data-testid="stTable"] {
  background: #FFFFFF !important; color: #34445E !important;
  border: 1px solid #DCE6F5 !important; border-radius: 13px !important; overflow: hidden;
}
[data-testid="stMetric"] {
  background: #FFFFFF !important; border: 1px solid #DCE6F5 !important;
  border-radius: 14px !important; padding: 12px !important;
}
[data-testid="stMetricLabel"], [data-testid="stMetricValue"] { color: #24436F !important; }
[data-testid="stCaptionContainer"], .stCaption { color: #71819A !important; }
.stProgress > div > div { background: #E5EDF9 !important; border-radius: 20px !important; }
.stProgress > div > div > div { background: linear-gradient(90deg, #2463D4, #70A3F2) !important; border-radius: 20px !important; }
hr { border-color: #E1E9F5 !important; }
a { color: #1457C5 !important; }
::selection { background: rgba(37,99,235,.18); color: #102D5B; }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; }
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
        <div class="hero-title">AI <span>Assistant</span></div>
        <div class="hero-subtitle">
            Ask questions, upload study material, and work through concepts with your AI learning companion.
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
            marks_options = ["2 Marks", "5 Marks", "7 Marks", "10 Marks"]
            marks = st.selectbox(
                "Answer format",
                marks_options,
                index=marks_options.index(st.session_state.answer_marks)
            )
            st.session_state.answer_marks = marks

    with st.expander("＋  Attach files to your question", expanded=False):
        st.caption("Upload PDFs or images and ask Intellecta to explain, summarize, extract, or analyze their content.")
        chat_files = st.file_uploader(
            "Choose PDF or image files",
            type=["pdf", "png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key="chat_attachments",
            help="Supported: PDF, PNG, JPG, JPEG and WEBP. Keep each file under 15 MB."
        )
        if chat_files:
            total_size = sum(file.size for file in chat_files)
            st.caption(f"{len(chat_files)} file(s) selected · {total_size / (1024 * 1024):.1f} MB total")
            for file in chat_files:
                st.write(f"📎 {file.name}")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if not st.session_state.messages:
        st.markdown("""
            <div class="glass-card">
                <div class="feature-title">What would you like to learn today?</div>
                <div class="feature-description">
                    Ask a technical question, prepare an exam answer, or attach a PDF/image
                    and ask questions about the material.
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("**Try asking**")
        suggestion_cols = st.columns(3)
        suggestions = [
            "Explain a difficult concept simply",
            "Create 5 exam questions on DBMS",
            "Give me a step-by-step example"
        ]
        for suggestion_col, suggestion in zip(suggestion_cols, suggestions):
            with suggestion_col:
                if st.button(suggestion, use_container_width=True):
                    st.session_state["suggested_chat_prompt"] = suggestion
                    st.rerun()

    suggested_prompt = st.session_state.pop("suggested_chat_prompt", "")
    user_prompt = st.chat_input("Ask Intellecta anything...")
    if not user_prompt and suggested_prompt:
        user_prompt = suggested_prompt

    if user_prompt:
        selected_files = chat_files if "chat_files" in locals() and chat_files else []
        file_parts = []
        file_names = []
        total_size = sum(f.size for f in selected_files)

        if total_size > 30 * 1024 * 1024:
            st.error("The combined attachment size is over 30 MB. Please upload fewer or smaller files.")
            st.stop()

        for uploaded in selected_files:
            if uploaded.size > 15 * 1024 * 1024:
                st.error(f"{uploaded.name} is larger than 15 MB. Please upload a smaller file.")
                st.stop()
            mime_type = uploaded.type or ""
            if mime_type == "application/pdf" or uploaded.name.lower().endswith(".pdf"):
                mime_type = "application/pdf"
            elif uploaded.name.lower().endswith((".jpg", ".jpeg")):
                mime_type = "image/jpeg"
            elif uploaded.name.lower().endswith(".png"):
                mime_type = "image/png"
            elif uploaded.name.lower().endswith(".webp"):
                mime_type = "image/webp"

            if mime_type not in ["application/pdf", "image/jpeg", "image/png", "image/webp"]:
                continue

            file_parts.append(types.Part.from_bytes(data=uploaded.getvalue(), mime_type=mime_type))
            file_names.append(uploaded.name)

        visible_prompt = user_prompt
        if file_names:
            visible_prompt += "\n\nAttached files: " + ", ".join(file_names)

        st.session_state.messages.append({"role": "user", "content": visible_prompt})
        save_message(st.session_state.conversation_id, "user", visible_prompt)

        with st.chat_message("user"):
            st.markdown(user_prompt)
            if file_names:
                st.caption("📎 Attached: " + ", ".join(file_names))

        recent_messages = st.session_state.messages[-7:]
        conversation_context = "\n".join([
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in recent_messages[:-1]
        ])

        if st.session_state.study_mode == "Study Mode":
            system_prompt = f"""
You are Intellecta, a professional academic AI study assistant.
Answer in clear academic English for a university examination worth {st.session_state.answer_marks}.
Use a clear definition/introduction, meaningful headings, numbered points, simple explanations,
examples where useful, comparison tables when relevant, and a short conclusion.
Match the depth to the marks. Avoid repetition and do not invent facts.
"""
            max_tokens = 2200
        else:
            system_prompt = """
You are Intellecta, a helpful, accurate and professional learning assistant.
Explain concepts in simple language, use step-by-step reasoning and practical examples when useful.
Use headings and bullets for readability. Be friendly, concise and honest about uncertainty.
When files are attached, carefully inspect their contents and answer the user's specific request.
For PDFs, use the supplied document as the primary source. For images, describe only what is relevant
to the user's question. If a file is unreadable or unsupported, explain the limitation.
"""
            max_tokens = 1800

        full_prompt = f"""
{system_prompt}

Recent conversation:
{conversation_context}

Latest user question:
{user_prompt}

If one or more files are attached, analyze them in the context of the latest question.
Clearly distinguish information found in the uploaded files from general explanation.
"""
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            try:
                request_contents = [full_prompt] + file_parts
                stream = client.models.generate_content_stream(
                    model=MODEL_NAME,
                    contents=request_contents,
                    config=types.GenerateContentConfig(
                        temperature=0.4,
                        max_output_tokens=max_tokens
                    )
                )
                for chunk in stream:
                    if chunk.text:
                        full_response += chunk.text
                        response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(
                    full_response or "I couldn't generate a response. Please try again."
                )
                if full_response:
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    save_message(st.session_state.conversation_id, "assistant", full_response)
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
