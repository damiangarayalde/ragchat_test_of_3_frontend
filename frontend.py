import streamlit as st
from datetime import datetime
import requests
from typing import Optional, Dict, Any
from styles import StyleManager


class SessionManager:
    """Manages Streamlit session state."""

    @staticmethod
    def initialize_session():
        """Initialize all required session state variables."""
        if "active_bot" not in st.session_state:
            st.session_state.active_bot = None
        if "bot_messages" not in st.session_state:
            st.session_state.bot_messages = {}
        if "uploaded_files" not in st.session_state:
            st.session_state.uploaded_files = set()


class APIClient:
    """Handles API communication."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def fetch_bots(self) -> list:
        """Fetch available bots from the API."""
        try:
            response = requests.get(f"{self.base_url}/bots")
            if response.status_code == 200:
                return response.json().get("bots", [])
            return []
        except Exception as e:
            st.error(f"Error fetching bots: {e}")
            return []

    def fetch_documents(self, bot_id: str) -> list:
        """Fetch documents for a specific bot."""
        try:
            response = requests.get(f"{self.base_url}/documents/{bot_id}")
            if response.status_code == 200:
                return response.json().get("documents", [])
            return []
        except Exception as e:
            st.error(f"Error fetching documents: {e}")
            return []


# Initialize managers
session_manager = SessionManager()
api_client = APIClient()

# Initialize session state
session_manager.initialize_session()

# Main title
st.title("Multi-Bot Chat System")

# Sidebar
with st.sidebar:
    st.title("Configuración")

    # Bot selection
    bots = api_client.fetch_bots()
    bot_options = {bot["name"]: bot["id"] for bot in bots}

    selected_bot_name = st.selectbox(
        "Selecciona una materia:",
        options=list(bot_options.keys()),
        key="bot_selector"
    )

    selected_bot_id = bot_options[selected_bot_name]

    # Update active bot if changed
    if st.session_state.active_bot != selected_bot_id:
        st.session_state.active_bot = selected_bot_id
        if selected_bot_id not in st.session_state.bot_messages:
            st.session_state.bot_messages[selected_bot_id] = [{
                "role": "assistant",
                "content": next((bot["description"] for bot in bots if bot["id"] == selected_bot_id), ""),
                "timestamp": datetime.now().strftime("%H:%M")
            }]

    # Document management section
    st.markdown("---")

    # Document list
    st.subheader("Tu biblioteca:")
    documents = api_client.fetch_documents(selected_bot_id)
    if documents:
        for doc in documents:
            # Adjust column ratio for better layout
            col1, col2 = st.columns([8, 3])
            col1.write(doc)
            if col2.button(
                "Eliminar",
                key=f"delete_{doc}_{selected_bot_id}",
                use_container_width=True
            ):
                try:
                    response = requests.delete(
                        f"http://localhost:8000/documents/{selected_bot_id}/{doc}"
                    )
                    if response.status_code == 200:
                        st.success(
                            f"Documento '{doc}' eliminado correctamente")
                        # Remove the file from the session state
                        st.session_state.uploaded_files.discard(doc)
                        st.rerun()
                    else:
                        st.error("Error al eliminar el documento")
                except Exception as e:
                    st.error(f"Error al eliminar el documento: {e}")
    else:
        st.write("No hay documentos disponibles")

    # File uploader
    upload_key = f"uploader_{selected_bot_id}_{len(st.session_state.uploaded_files)}"
    uploaded_file = st.file_uploader(
        "",  # "Subir documento",
        type=["pdf", "docx", "txt"],
        key=upload_key
    )

    # File upload handling
    if uploaded_file and uploaded_file.name not in st.session_state.uploaded_files:
        try:
            with st.spinner("Procesando archivo..."):
                files = {"file": (uploaded_file.name,
                                  uploaded_file.getvalue())}
                response = requests.post(
                    f"http://localhost:8000/upload/{selected_bot_id}",
                    files=files
                )
                if response.status_code == 200:
                    st.sidebar.success(
                        f"Documento '{uploaded_file.name}' subido correctamente")
                    # Add the file to the session state to prevent re-upload
                    st.session_state.uploaded_files.add(uploaded_file.name)
                    st.rerun()
                else:
                    st.sidebar.error("Error al subir el archivo")
        except Exception as e:
            st.error(f"Error al subir el archivo: {e}")

# Chat interface

# Apply styles (replace the existing st.markdown style section)
StyleManager.apply_styles()

# Chat interface
chat_container = st.container()

# Display chat messages
with chat_container:
    if not documents:  # Check if there are no files in the database
        st.warning("Para poder chatear primero subí algún archivo.")
    else:
        for message in st.session_state.bot_messages.get(selected_bot_id, []):
            if message["role"] == "user":
                st.markdown(f"""
                    <div class="user-message">
                        <div class="message-content">{message["content"]}</div>
                        <div class="timestamp">{message["timestamp"]}</div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="assistant-message">
                        <div class="message-content">{message["content"]}</div>
                        <div class="timestamp">{message["timestamp"]}</div>
                    </div>
                """, unsafe_allow_html=True)

# Input and button section
if documents:  # Enable chat input only if there are files in the database
    with st.container():
        # Create a form for the input field
        with st.form(key=f"chat_input_form_{selected_bot_id}", clear_on_submit=True):
            cols = st.columns([6, 1])

            # Text input in first column
            with cols[0]:
                user_input = st.text_input(
                    "",
                    placeholder="Escribe tu mensaje aquí...",
                    key=f"user_input_{selected_bot_id}",
                    label_visibility="collapsed"
                )

            # Submit button in second column
            with cols[1]:
                submit_button = st.form_submit_button("Enviar")

        # Handle form submission
        if submit_button and user_input.strip():
            # Store the user input before rerun
            current_input = user_input.strip()

            # Add user message immediately
            timestamp = datetime.now().strftime("%H:%M")
            st.session_state.bot_messages[selected_bot_id].append({
                "role": "user",
                "content": current_input,
                "timestamp": timestamp
            })

            # Store a flag to indicate we need to process this message
            st.session_state.process_message = {
                "bot_id": selected_bot_id,
                "content": current_input
            }

            # Rerun to show the user message
            st.rerun()

# Check if we need to process a message (after the rerun)
if "process_message" in st.session_state:
    msg_data = st.session_state.process_message

    try:
        # Send message to backend
        response = requests.post(
            f"http://localhost:8000/chat/{msg_data['bot_id']}",
            json={"query": msg_data["content"]}
        )

        if response.status_code == 200:
            bot_response = response.json()
            st.session_state.bot_messages[msg_data['bot_id']].append({
                "role": "assistant",
                "content": bot_response["response"],
                "timestamp": datetime.now().strftime("%H:%M")
            })
        elif response.status_code == 400:
            st.warning(
                "Por favor, sube un documento antes de realizar una consulta.")
        else:
            st.error(f"Error en la solicitud: {response.status_code}")
    except Exception as e:
        st.error(f"Error al procesar la consulta: {e}")

    # Clear the processing flag
    del st.session_state.process_message

    # Final rerun to show the bot response
    st.rerun()
