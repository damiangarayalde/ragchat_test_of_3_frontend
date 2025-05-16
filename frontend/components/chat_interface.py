import streamlit as st
from services.session_manager import SessionManager


def chat_interface(selected_bot_id: str):
    st.container()
    # Instead of checking session state, check actual documents from API
    documents = st.session_state.get(
        'api_client').fetch_documents(selected_bot_id)

    # Create container for messages
    messages_container = st.container()

    # Create container for input - placing it before message processing
    input_container = st.container()
    with input_container:
        with st.form(key=f"chat_form_{selected_bot_id}", clear_on_submit=True):
            cols = st.columns([6, 1])
            # Disable input if no documents
            user_input = cols[0].text_input(
                "",
                placeholder="Escribe tu mensaje..." if documents else "Sube un documento para comenzar...",
                key=f"input_{selected_bot_id}",
                label_visibility="collapsed",
                disabled=not documents  # Disable when no documents
            )
            # Disable button if no documents
            submit_button = cols[1].form_submit_button(
                "Enviar",
                disabled=not documents  # Disable when no documents
            )

            if submit_button and user_input.strip() and documents:  # Extra check for documents
                current_message = user_input.strip()
                handle_user_input(selected_bot_id, current_message)
                st.session_state.pending_message = {
                    "bot_id": selected_bot_id,
                    "message": current_message,
                    "processed": False
                }
                st.rerun()

    # Display messages and process responses in the messages container
    with messages_container:
        if not documents:
            st.warning("Para poder chatear primero subí algún archivo.")
            return

        # Display chat messages
        for message in st.session_state.bot_messages.get(selected_bot_id, []):
            role_class = "user-message" if message["role"] == "user" else "assistant-message"
            st.markdown(f"""
                <div class="{role_class}">
                    <div class="message-content">{message["content"]}</div>
                    <div class="timestamp">{message["timestamp"]}</div>
                </div>
            """, unsafe_allow_html=True)

        # Process pending message if exists
        if hasattr(st.session_state, 'pending_message') and \
           st.session_state.pending_message.get("bot_id") == selected_bot_id and \
           not st.session_state.pending_message.get("processed", False):
            with st.spinner("Procesando respuesta..."):
                response = handle_bot_response(
                    st.session_state.get('api_client'),
                    selected_bot_id,
                    st.session_state.pending_message["message"]
                )
                st.session_state.pending_message["processed"] = True
                if response:
                    st.rerun()


def handle_user_input(bot_id: str, message: str):
    SessionManager.add_message(bot_id, "user", message)


def handle_bot_response(api_client, bot_id: str, message: str):
    response = api_client.send_message(bot_id, message)
    if response and "response" in response:
        SessionManager.add_message(bot_id, "assistant", response["response"])
        return True
    return False
