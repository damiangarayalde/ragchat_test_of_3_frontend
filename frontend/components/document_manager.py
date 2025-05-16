import streamlit as st
import requests
import os


def document_manager(api_client, bot_id: str):
    with st.sidebar:
        st.markdown("---")
        st.subheader("Tu biblioteca:")

        documents = api_client.fetch_documents(bot_id)
        if documents:
            for doc in documents:
                col1, col2 = st.columns([8, 3])
                col1.write(doc)
                if col2.button("Eliminar", key=f"delete_{doc}_{bot_id}", use_container_width=True):
                    handle_delete(bot_id, doc)
        else:
            st.write("No hay documentos disponibles")

        handle_file_upload(bot_id)


def handle_delete(bot_id: str, filename: str):
    try:
        response = requests.delete(
            f"http://localhost:8000/documents/{bot_id}/{filename}"
        )
        if response.status_code == 200:
            st.success(f"Documento '{filename}' eliminado")
            st.session_state.uploaded_files.discard(filename)
            # Update the flag if no documents remain
            if not st.session_state.uploaded_files:
                st.session_state[f"docs_uploaded_{bot_id}"] = False
            st.rerun()
    except Exception as e:
        st.error(f"Error al eliminar: {e}")


def handle_file_upload(bot_id: str):
    upload_key = f"uploader_{bot_id}_{len(st.session_state.uploaded_files)}"

    uploaded_file = st.file_uploader(
        "",
        type=["pdf", "docx", "txt"],
        key=upload_key
    )

    # Update session state with current documents when component mounts
    current_docs = set(st.session_state.get(
        'api_client').fetch_documents(bot_id))
    st.session_state.uploaded_files.update(current_docs)

    if uploaded_file and uploaded_file.name not in st.session_state.uploaded_files:
        try:
            with st.spinner("Procesando..."):
                files = {"file": (uploaded_file.name,
                                  uploaded_file.getvalue())}
                response = requests.post(
                    f"http://localhost:8000/upload/{bot_id}",
                    files=files
                )
                if response.status_code == 200:
                    st.sidebar.success(
                        f"Documento '{uploaded_file.name}' subido correctamente")
                    st.session_state.uploaded_files.add(uploaded_file.name)
                    st.rerun()
                else:
                    st.sidebar.error("Error al subir el archivo")
        except Exception as e:
            st.error(f"Error al subir: {e}")
