import logging
import os
from typing import Optional, Dict, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling for the application."""

    @staticmethod
    def handle_api_error(operation: str, error: Exception, bot_id: Optional[str] = None) -> HTTPException:
        error_msg = f"Error during {operation}"
        if bot_id:
            error_msg += f" for bot {bot_id}"
        logger.error(f"{error_msg}: {str(error)}")
        return HTTPException(status_code=500, detail=f"Failed to {operation}")


class FileManager:
    """Manages file operations for bots."""

    @staticmethod
    def ensure_directory(directory: str) -> None:
        """Ensure a directory exists."""
        os.makedirs(directory, exist_ok=True)

    @staticmethod
    def validate_file_exists(file_path: str) -> bool:
        """Check if a file exists."""
        return os.path.exists(file_path)

    @staticmethod
    def get_directory_files(directory: str) -> list:
        """Get list of files in a directory."""
        if not os.path.exists(directory):
            return []
        return os.listdir(directory)


class ConfigManager:
    """Manages configuration for the application."""

    @staticmethod
    def load_bot_config() -> Dict[str, Any]:
        """Load bot configuration from environment or config file."""
        return {
            "bot1": {
                "id": "bot1",
                "name": "Derechos Humanos",
                "description": "Asistente general para consultas de documentos",
                "system_prompt": "Responde siempre en español de manera formal y técnica.",
                "collection_name": "documents_collection_bot1",
                "data_dir": "./data_bot1"
            },
            "bot2": {
                "id": "bot2",
                "name": "Penal II",
                "description": "Especialista en documentación técnica",
                "system_prompt": "Responde en español, enfocándote en detalles técnicos y específicos.",
                "collection_name": "documents_collection_bot2",
                "data_dir": "./data_bot2"
            }
        }
