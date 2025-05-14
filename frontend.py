import streamlit as st
import requests
from datetime import datetime


# Initialize chat history in session state if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "¡Hola! Soy un bot diseñado para responder consultas basadas en la información de tu biblioteca. ¿Cómo puedo ayudarte?",
        "timestamp": datetime.now().strftime("%H:%M")
    }]

st.title("Chatbot MVP")

# Function to fetch the list of documents


def fetch_documents():
    try:
        response = requests.get("http://localhost:8000/documents")
        if response.status_code == 200:
            return response.json().get("documents", [])
        else:
            st.sidebar.error("Error al obtener la lista de documentos.")
            return []
    except Exception as e:
        st.sidebar.error(f"Error: {e}")
        return []


# Sidebar: List of documents and file upload
st.sidebar.title("Tu Biblioteca")

# Add a horizontal line for separation
st.sidebar.markdown("---")

# Fetch and display the list of documents
documents = fetch_documents()

if documents:
    for doc in documents:
        col1, col2, col3 = st.sidebar.columns([1, 7, 3])
        col1.markdown("📄")  # File icon
        col2.write(doc)
        # Delete button with an icon
        if col3.button("Delete", key=f"delete_{doc}"):
            # Delete the document
            try:
                response = requests.delete(
                    f"http://localhost:8000/documents/{doc}")
                if response.status_code == 200:
                    st.sidebar.success(
                        f"Documento '{doc}' eliminado correctamente.")
                    # Trigger a page reload
                    st.rerun()
                else:
                    st.sidebar.error(
                        f"Error al eliminar el documento: {response.status_code}")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")
else:
    st.sidebar.write("No hay documentos disponibles.")


# Initialize file upload state if it doesn't exist
if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0

# File upload in the sidebar
uploaded_file = st.sidebar.file_uploader(
    label=".",  # Remove the "Sube un documento..." text
    type=["pdf", "docx", "txt"],
    label_visibility="collapsed",
    key=f"uploader_{st.session_state.file_uploader_key}"  # Dynamic key
)

if uploaded_file is not None:
    try:
        st.sidebar.info("Procesando archivo...")
        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
        response = requests.post("http://localhost:8000/upload", files=files)

        if response.status_code == 200:
            response_data = response.json()
            st.sidebar.success(response_data.get(
                "status", "Documento subido correctamente."))
            # Increment the file uploader key to force a reset
            st.session_state.file_uploader_key += 1
            # Rerun the app with the new key
            st.rerun()
        else:
            st.sidebar.error(f"Error en la solicitud: {response.status_code}")
            # Reset the file uploader on error
            st.session_state.file_uploader_key += 1
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"Error al subir el archivo: {e}")
        # Reset the file uploader on error
        st.session_state.file_uploader_key += 1
        st.rerun()

# Chat interface

# Replace all existing style sections with this single, consolidated one
st.markdown("""
<style>
    /* Chat messages styling */
    .chat-container {
        padding: 20px;
    }
    .user-message {
        background-color: #128C7E;
        color: white;
        padding: 12px;
        border-radius: 15px;
        margin: 8px 8px;
        max-width: 70%;
        margin-left: 30%;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .assistant-message {
        background-color: #262626;
        color: white;
        padding: 12px;
        border-radius: 15px;
        margin: 8px 0;
        max-width: 70%;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .timestamp {
        font-size: 0.75em;
        color: rgba(255,255,255,0.7);
        margin-top: 4px;
        text-align: right;
    }
    .message-content {
        margin-bottom: 4px;
        line-height: 1.4;
    }

    /* Input and button container */
    .chat-input-container {
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
        padding: 1rem !important;
        width: 100% !important;
    }

    /* Column container */
    [data-testid="column"] {
        padding: 0 !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        gap: 0 !important;
    }

    /* Text input styling */
    .stTextInput {
        margin: 0 !important;
    }
    .stTextInput > div {
        margin: 0 !important;
    }
    .stTextInput > div > div > input {
        background-color: #E9FFE5 !important;
        color: #333333 !important;
        border: 1px solid #128C7E !important;
        border-radius: 5px !important;
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        padding: 0 12px !important;
        margin: 0 !important;
        line-height: 42px !important;
    }

    /* Button styling */
    .stButton {
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
    }
    .stButton > button {
        background-color: #128C7E !important;
        color: white !important;
        border: none !important;
        border-radius: 5px !important;
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        padding: 0 1.5rem !important;
        margin: 0 !important;
        line-height: 42px !important;
    }
    .stButton > button:hover {
        background-color: #0C6B5B !important;
    }
</style>
""", unsafe_allow_html=True)

# Crear un contenedor para el chat
chat_container = st.container()

# Mostrar los mensajes del chat dentro del contenedor
with chat_container:
    for message in st.session_state.messages:
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

# Input del usuario (mover al final de la página)
st.markdown("""
<style>
    /* Chat input container and elements */
    .chat-input-container {
        display: flex !important;
        justify-content: center !important;
        align-items: stretch !important;
        gap: 10px !important;
        padding: 1rem !important;
        max-width: 800px !important;
        margin: 0 auto !important;
    }

    /* Reset Streamlit's default styles */
    .stTextInput > div {
        margin-bottom: 0 !important;
    }

    .stTextInput > div > div {
        margin-bottom: 0 !important;
    }

    /* Input field styles */
    .stTextInput > div > div > input {
        background-color: #E9FFE5 !important;
        color: #333333 !important;
        border: 1px solid #128C7E !important;
        border-radius: 5px !important;
        height: 40px !important;
        min-height: 40px !important;
        max-height: 40px !important;
        padding: 0 12px !important;
        margin: 0 !important;
        line-height: 40px !important;
    }

    /* Button container and button styles */
    .stButton {
        height: 40px !important;
        margin-top: 0 !important;
    }

    .stButton > button {
        background-color: #128C7E !important;
        color: white !important;
        border: none !important;
        border-radius: 5px !important;
        height: 40px !important;
        min-height: 40px !important;
        max-height: 40px !important;
        margin: 0 !important;
        padding: 0 1.5rem !important;
        line-height: 40px !important;
    }
    
    .stButton > button:hover {
        background-color: #0C6B5B !important;
    }

    /* Column styles */
    [data-testid="column"] {
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
    }
</style>
""", unsafe_allow_html=True)
# First, update the style section for input and button alignment
st.markdown("""
<style>
    /* Container for input and button */
    .chat-input-container {
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
        padding: 1rem !important;
        width: 100% !important;
    }

    /* Column container */
    [data-testid="column"] {
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
    }

    /* Text input styling */
    .stTextInput {
        margin: 0 !important;
    }

    .stTextInput > div {
        margin: 0 !important;
    }

    .stTextInput > div > div > input {
        background-color: #E9FFE5 !important;
        color: #333333 !important;
        border: 1px solid #128C7E !important;
        border-radius: 5px !important;
        height: 46px !important;
        min-height: 46px !important;
        padding: 0 12px !important;
        margin: 0 !important;
    }

    /* Button styling */
    .stButton {
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
    }

    .stButton > button {
        background-color: #128C7E !important;
        color: white !important;
        border: none !important;
        border-radius: 5px !important;
        height: 46px !important;
        min-height: 46px !important;
        padding: 0 1.5rem !important;
        margin: 0 !important;
    }

    .stButton > button:hover {
        background-color: #0C6B5B !important;
    }
</style>
""", unsafe_allow_html=True)

# Then, update the input/button section
with st.container():
    # Create two columns with a 6:1 ratio
    cols = st.columns([6, 1])

    # Text input
    with cols[0]:
        user_input = st.text_input(
            "",
            placeholder="Escribe tu mensaje aquí...",
            key=f"user_input_{len(st.session_state.messages)}",
            label_visibility="collapsed"
        )

    # Send button
    with cols[1]:
        send_button = st.button("Enviar")

    # Message handling (keep existing code)
    if send_button and user_input.strip():
        timestamp = datetime.now().strftime("%H:%M")

        # Add user message to history
        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": timestamp
        })

        try:
            response = requests.post(
                "http://localhost:8000/chat",
                json={"query": user_input}
            )

            if response.status_code == 200:
                response_data = response.json()
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_data["response"],
                    "timestamp": datetime.now().strftime("%H:%M")
                })
            elif response.status_code == 400:
                st.warning(
                    "Por favor, sube un documento antes de realizar una consulta.")
            else:
                st.error(f"Error en la solicitud: {response.status_code}")
        except Exception as e:
            st.error(f"Error al procesar la consulta: {e}")

        # Rerun to update the UI and clear the input
        st.rerun()
