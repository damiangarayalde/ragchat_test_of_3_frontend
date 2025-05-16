import streamlit as st
from services.session_manager import SessionManager
from services.api_client import APIClient
from components.sidebar import show_sidebar
from components.document_manager import document_manager
from components.chat_interface import chat_messages, chat_input


def load_styles():
    with open("frontend/assets/styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def main():
    load_styles()
    SessionManager.initialize_session()
    api_client = APIClient()
    # Store API client in session state
    st.session_state.api_client = api_client

    selected_bot_id = show_sidebar(api_client)
    document_manager(api_client, selected_bot_id)

    if selected_bot_id:
        chat_messages(selected_bot_id)
        chat_input(api_client, selected_bot_id)


if __name__ == "__main__":
    main()
