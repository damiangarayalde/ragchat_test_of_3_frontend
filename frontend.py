import streamlit as st
import requests

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
                    st.experimental_set_query_params(reload="true")
                else:
                    st.sidebar.error(
                        f"Error al eliminar el documento: {response.status_code}")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")
else:
    st.sidebar.write("No hay documentos disponibles.")


# File upload in the sidebar
uploaded_file = st.sidebar.file_uploader(
    label="",  # Remove the "Sube un documento..." text
    type=["pdf", "docx", "txt"],
    # Custom placeholder text
    help="Arrastra y suelta un archivo aquí o haz clic para seleccionar uno."

)

if uploaded_file:
    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
    try:
        response = requests.post("http://localhost:8000/upload", files=files)
        if response.status_code == 200:
            response_data = response.json()
            st.sidebar.success(response_data.get(
                "status", "Documento subido correctamente."))
            # Trigger a page reload
            st.experimental_set_query_params(reload="true")
        else:
            st.sidebar.error(f"Error en la solicitud: {response.status_code}")
    except Exception as e:
        st.sidebar.error(f"Error al subir el archivo: {e}")


# Chat interface
user_input = st.text_input("Pregúntame algo:")

if user_input:
    try:
        response = requests.post(
            "http://localhost:8000/chat",
            json={"query": user_input}
        )
        if response.status_code == 200:
            st.write(response.json()["response"])
        elif response.status_code == 400:  # Handle "index not initialized" error
            st.warning(
                "Por favor, sube un documento antes de realizar una consulta.")
        else:
            st.error(f"Error en la solicitud: {response.status_code}")
    except Exception as e:
        st.error(f"Error al procesar la consulta: {e}")
