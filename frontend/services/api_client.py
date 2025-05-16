import requests
import streamlit as st


class APIClient:
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

    def send_message(self, bot_id: str, message: str):
        try:
            response = requests.post(
                f"{self.base_url}/chat/{bot_id}",
                json={"query": message}
            )
            return response.json() if response.ok else None
        except Exception as e:
            st.error(f"Error sending message: {e}")
            return None
