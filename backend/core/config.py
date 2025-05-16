# backend/core/config.py
import os
from dotenv import load_dotenv


class Settings:
    def __init__(self):
        load_dotenv()
        self.CHROMA_DIR = "./chroma-data"
        self.BOT_CONFIG = {
            "bot1": {
                "name": "Derechos Humanos",
                "description": "Asistente general para consultas de documentos",
                "system_prompt": "Responde siempre en español de manera formal y técnica.",
                "collection_name": "documents_collection_bot1",
                "data_dir": "./data_bot1"
            },
            "bot2": {
                "name": "Penal II",
                "description": "Especialista en documentación técnica",
                "system_prompt": "Responde en español, enfocándote en detalles técnicos y específicos.",
                "collection_name": "documents_collection_bot2",
                "data_dir": "./data_bot2"
            }
        }


settings = Settings()
