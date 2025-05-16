import streamlit as st
from datetime import datetime


class SessionManager:
    @staticmethod
    def initialize_session():
        if "active_bot" not in st.session_state:
            st.session_state.active_bot = None
        if "bot_messages" not in st.session_state:
            st.session_state.bot_messages = {}
        if "uploaded_files" not in st.session_state:
            st.session_state.uploaded_files = set()

    @staticmethod
    def add_message(bot_id: str, role: str, content: str):
        if bot_id not in st.session_state.bot_messages:
            st.session_state.bot_messages[bot_id] = []

        st.session_state.bot_messages[bot_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().strftime("%H:%M")
        })
