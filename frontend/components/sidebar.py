import streamlit as st
from services.api_client import APIClient


def show_sidebar(api_client: APIClient):
    with st.sidebar:
        st.title("Configuración")
        bots = api_client.fetch_bots()
        bot_options = {bot["name"]: bot["id"] for bot in bots}

        selected_bot_name = st.selectbox(
            "Selecciona una materia:",
            options=list(bot_options.keys()),
            key="bot_selector"
        )
        return bot_options[selected_bot_name]
