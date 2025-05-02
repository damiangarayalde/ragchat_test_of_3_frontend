import streamlit as st
import requests

st.title("Chatbot MVP")

# Chat interface
user_input = st.text_input("Preguntame algo:")

if user_input:
    response = requests.post(
        "http://localhost:8000/chat",
        json={"query": user_input}
    )
    st.write(response.json()["response"])

# File upload
uploaded_file = st.file_uploader(
    "Subi un documento (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])

if uploaded_file:
    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
    response = requests.post("http://localhost:8000/upload", files=files)

    if response.status_code == 200:
        try:
            response_data = response.json()
            st.write(response_data.get(
                "status", "No se encontró la clave 'status' en la respuesta."))
        except ValueError:
            st.error(
                "Error al procesar la respuesta del servidor. No es un JSON válido.")
    else:
        st.error(f"Error en la solicitud: {response.status_code}")
