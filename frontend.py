import streamlit as st
import requests
from datetime import datetime

# Initialize bot selection and chat histories in session state
if "active_bot" not in st.session_state:
    st.session_state.active_bot = None

if "bot_messages" not in st.session_state:
    st.session_state.bot_messages = {}

# Initialize session state for file upload tracking
if "uploaded_files" not in st.session_state:
    # Track uploaded files for the current session
    st.session_state.uploaded_files = set()

# Function to fetch available bots


def fetch_bots():
    try:
        response = requests.get("http://localhost:8000/bots")
        if response.status_code == 200:
            return response.json().get("bots", [])
        else:
            st.error("Error al obtener la lista de bots.")
            return []
    except Exception as e:
        st.error(f"Error: {e}")
        return []

# Function to fetch documents for specific bot


def fetch_documents(bot_id):
    try:
        response = requests.get(f"http://localhost:8000/documents/{bot_id}")
        if response.status_code == 200:
            return response.json().get("documents", [])
        else:
            st.sidebar.error("Error al obtener la lista de documentos.")
            return []
    except Exception as e:
        st.sidebar.error(f"Error: {e}")
        return []


# Main title
st.title("Multi-Bot Chat System")

# Sidebar
with st.sidebar:
    st.title("Configuración")

    # Bot selection
    bots = fetch_bots()
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
    st.subheader("Documentos")

    # File uploader with a dynamic key to reset its state
    upload_key = f"uploader_{selected_bot_id}_{len(st.session_state.uploaded_files)}"

    uploaded_file = st.file_uploader(
        "Subir documento",
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
                    # Trigger a rerun to refresh the document list
                    st.rerun()
                else:
                    st.sidebar.error("Error al subir el archivo")
        except Exception as e:
            st.error(f"Error al subir el archivo: {e}")

    # Document list
    documents = fetch_documents(selected_bot_id)
    if documents:
        st.write("Archivos indexados:")
        for doc in documents:
            # Adjust column ratio for better layout
            col1, col2 = st.columns([8, 1])
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

# Chat interface

# Replace all existing style sections with this single, consolidated one
st.markdown("""
<style>
    /* Chat messages */
    .chat-container {
        padding: 20px;
        max-width: 800px;
        margin: 0 auto;
    }
    .user-message {
        background-color: #128C7E;
        color: white;
        padding: 12px;
        border-radius: 15px;
        margin: 8px 0;
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

    /* Input and button styling */
    .stTextInput > div > div > input {
        background-color: #E9FFE5 !important;
        color: #333333 !important;
        border: 1px solid #128C7E !important;
        border-radius: 5px !important;
        height: 46px !important;
        line-height: 46px !important;
        padding: 0 12px !important;
        margin: 0 !important;
    }
    
    .stButton > button {
        background-color: #128C7E !important;
        color: white !important;
        border: none !important;
        border-radius: 5px !important;
        height: 46px !important;
        padding: 0 1.5rem !important;
        margin: 0 !important;
    }
    
    .stButton > button:hover {
        background-color: #0C6B5B !important;
    }

    /* Column alignment */
    [data-testid="column"] {
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
    }

    /* Remove margins and padding */
    .stTextInput, .stButton {
        margin: 0 !important;
    }
    .stTextInput > div {
        margin: 0 !important;
    }

    /* Delete button specific styling */
    [data-testid="column"]:has(button:contains("Eliminar")) {
        padding-left: 8px !important;  /* Add some spacing between filename and button */
    }
    
    [data-testid="column"]:has(button:contains("Eliminar")) button {
        width: 100% !important;
        min-width: 100px !important;  /* Ensure minimum width */
        white-space: nowrap !important;  /* Prevent text wrapping */
        padding: 0 16px !important;  /* Add horizontal padding */
        background-color: #128C7E !important;
    }
</style>
""", unsafe_allow_html=True)

# Chat interface
chat_container = st.container()

# Display chat messages
with chat_container:
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
with st.container():
    cols = st.columns([6, 1])

    # Text input
    with cols[0]:
        user_input = st.text_input(
            "",
            placeholder="Escribe tu mensaje aquí...",
            key=f"user_input_{selected_bot_id}",
            label_visibility="collapsed"
        )

    # Send button
    with cols[1]:
        send_button = st.button("Enviar")

    # Message handling (keep existing code)
    if send_button and user_input.strip():
        timestamp = datetime.now().strftime("%H:%M")
        st.session_state.bot_messages[selected_bot_id].append({
            "role": "user",
            "content": user_input,
            "timestamp": timestamp
        })

        try:
            # Send message to backend
            response = requests.post(
                f"http://localhost:8000/chat/{selected_bot_id}",
                json={"query": user_input}
            )

            if response.status_code == 200:
                bot_response = response.json()
                # Add bot response to chat
                st.session_state.bot_messages[selected_bot_id].append({
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

        st.rerun()
