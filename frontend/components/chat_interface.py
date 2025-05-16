import streamlit as st
from services.session_manager import SessionManager


def chat_messages(selected_bot_id: str):
    st.container()
    # Instead of checking session state, check actual documents from API
    documents = st.session_state.get(
        'api_client').fetch_documents(selected_bot_id)
    if not documents:
        st.warning("Para poder chatear primero subí algún archivo.")
        return

    for message in st.session_state.bot_messages.get(selected_bot_id, []):
        role_class = "user-message" if message["role"] == "user" else "assistant-message"
        st.markdown(f"""
            <div class="{role_class}">
                <div class="message-content">{message["content"]}</div>
                <div class="timestamp">{message["timestamp"]}</div>
            </div>
        """, unsafe_allow_html=True)

    # Process pending message if exists
    if hasattr(st.session_state, 'pending_message'):
        pending = st.session_state.pending_message
        if pending["bot_id"] == selected_bot_id and not pending.get("processed", False):
            # Mark as processed to prevent loops
            st.session_state.pending_message["processed"] = True
            # Process bot response
            handle_bot_response(st.session_state.get('api_client'),
                                pending["bot_id"],
                                pending["message"])
            # Clean up
            del st.session_state.pending_message


def chat_input(api_client, selected_bot_id: str):
    with st.form(key=f"chat_form_{selected_bot_id}", clear_on_submit=True):
        cols = st.columns([6, 1])
        user_input = cols[0].text_input(
            "",
            placeholder="Escribe tu mensaje...",
            key=f"input_{selected_bot_id}",
            label_visibility="collapsed"
        )

        if cols[1].form_submit_button("Enviar") and user_input.strip():
            current_message = user_input.strip()
            # Add user message
            handle_user_input(selected_bot_id, current_message)
            # Store the message to be processed
            st.session_state.pending_message = {
                "bot_id": selected_bot_id,
                "message": current_message,
                "processed": False
            }
            st.rerun()


def handle_user_input(bot_id: str, message: str):
    SessionManager.add_message(bot_id, "user", message)


def handle_bot_response(api_client, bot_id: str, message: str):
    response = api_client.send_message(bot_id, message)
    if response and "response" in response:
        SessionManager.add_message(bot_id, "assistant", response["response"])
