import streamlit as st
import requests
from datetime import datetime

# Initialize bot selection and chat histories in session state
if "active_bot" not in st.session_state:
    st.session_state.active_bot = None

if "bot_messages" not in st.session_state:
    st.session_state.bot_messages = {}

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
        "Selecciona un asistente",
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

    # File uploader
    uploaded_file = st.file_uploader(
        "Subir documento",
        type=["pdf", "docx", "txt"],
        key=f"uploader_{selected_bot_id}"
    )

    if uploaded_file:
        try:
            with st.spinner("Procesando archivo..."):
                files = {"file": (uploaded_file.name,
                                  uploaded_file.getvalue())}
                response = requests.post(
                    f"http://localhost:8000/upload/{selected_bot_id}",
                    files=files
                )
                if response.status_code == 200:
                    st.success("Documento subido correctamente")
                    st.rerun()
        except Exception as e:
            st.error(f"Error al subir el archivo: {e}")

    # Document list
    documents = fetch_documents(selected_bot_id)
    if documents:
        for doc in documents:
            col1, col2 = st.columns([3, 1])
            col1.write(doc)
            if col2.button("Eliminar", key=f"delete_{doc}_{selected_bot_id}"):
                try:
                    response = requests.delete(
                        f"http://localhost:8000/documents/{selected_bot_id}/{doc}"
                    )
                    if response.status_code == 200:
                        st.success(
                            f"Documento '{doc}' eliminado correctamente")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error al eliminar el documento: {e}")
    else:
        st.write("No hay documentos disponibles")

# Chat interface
chat_container = st.container()

# Display messages for active bot
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

# Chat input
with st.container():
    cols = st.columns([5, 1], gap="small")

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
        st.markdown("""
        <div style="height: 46px; display: flex; align-items: center; justify-content: center;">
        """, unsafe_allow_html=True)
        send_button = st.button("Enviar")
        st.markdown("</div>", unsafe_allow_html=True)

    if send_button and user_input.strip():
        # Add user message to chat
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
            else:
                st.error("Error al procesar el mensaje")
        except Exception as e:
            st.error(f"Error en la comunicación: {e}")

        st.rerun()
