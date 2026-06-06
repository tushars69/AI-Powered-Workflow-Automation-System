import streamlit as st
from core.database import init_db

# Initialize DB on every cold start
init_db()

st.set_page_config(
    page_title="BiztelAI – Doc Digitizer",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏭 BiztelAI – Manufacturing Document Digitizer")
st.markdown("""
Welcome! Use the sidebar to navigate between sections.

| Page | What it does |
|---|---|
| 📤 Upload | Upload a handwritten document image or PDF |
| 🔍 Review | See extracted data, edit and save records |
| 📋 History | Search and browse all processed records |
| 📊 Dashboard | Analytics and operational insights |
""")

st.info("👈 Select a page from the sidebar to get started.")
