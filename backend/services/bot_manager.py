# backend/services/bot_manager.py
import os
from typing import Dict
from llama_index.core import VectorStoreIndex  # Add this import
from llama_index.core.memory import ChatMemoryBuffer
from backend.models.bot import Bot
from backend.core.config import settings
from backend.services.index_manager import IndexManager
from backend.core.chroma_manager import ChromaManager


class BotManager:
    def __init__(self):
        self.chroma = ChromaManager(settings.CHROMA_DIR)
        self.index_manager = IndexManager(self.chroma)
        self.bots = self._initialize_bots()
        self.indices: Dict[str, VectorStoreIndex] = {}
        self.memories: Dict[str, ChatMemoryBuffer] = {}
        self._initialize_all()

    def _initialize_bots(self):
        return {
            bot_id: Bot(
                id=bot_id,
                **config
            ) for bot_id, config in settings.BOT_CONFIG.items()
        }

    def _initialize_all(self):
        for bot in self.bots.values():
            os.makedirs(bot.data_dir, exist_ok=True)
            self.memories[bot.id] = ChatMemoryBuffer.from_defaults(
                token_limit=2000)
            self.indices[bot.id] = self.index_manager.build_index(bot)
