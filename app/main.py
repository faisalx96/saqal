"""Main entry point for Saqal - Prompt Refinement Workbench."""

import sys
from pathlib import Path

# Ensure project root is on the module path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize database
from core.database import init_db

init_db()

# Initialize MLflow memory layer
from memory.mlflow_config import init_mlflow

init_mlflow()

# Page configuration
st.set_page_config(
    page_title="Saqal - Prompt Refinement Workbench",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
from app.state import init_state

init_state()

# Main page content
st.title("Saqal")
st.subheader("Prompt Refinement Workbench")

st.markdown("""
Welcome to Saqal, an interactive tool for iteratively improving LLM prompts through
human-in-the-loop feedback.

### How it works

1. **Setup**: Create a session with your prompt and test inputs
2. **Review**: Run your prompt on a batch of inputs and provide feedback
3. **Adapt**: Let GEPA analyze your feedback and propose improvements
4. **Compare**: See side-by-side how the new prompt performs
5. **Iterate**: Repeat until satisfied with results

### Getting Started

Use the sidebar to navigate between pages:

- **Setup**: Create a new refinement session
- **Review**: Review outputs and provide feedback
- **Adapt**: View and approve proposed changes
- **Compare**: Compare prompt versions
- **History**: View session history and export

---

*Powered by GEPA (Genetic-Pareto) optimization*
""")

# Show current session info if one is active
from app.state import get_current_session_id
from core.session_manager import SessionManager

session_id = get_current_session_id()
if session_id:
    session_manager = SessionManager()
    session = session_manager.get_session(session_id)
    if session:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Current Session")
        st.sidebar.markdown(f"**{session.name}**")
        st.sidebar.markdown(f"Status: {session.status}")
