# backend/services/index_manager.py
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
import logging
import os  # Add this import
from typing import Optional

logger = logging.getLogger(__name__)


class IndexManager:
    def __init__(self, chroma_manager):
        self.chroma_manager = chroma_manager

    def build_index(self, bot) -> Optional[VectorStoreIndex]:
        try:
            if not os.path.exists(bot.data_dir) or not os.listdir(bot.data_dir):
                return None

            documents = SimpleDirectoryReader(bot.data_dir).load_data()
            collection = self.chroma_manager.get_collection(
                bot.collection_name)
            vector_store = ChromaVectorStore(chroma_collection=collection)

            return VectorStoreIndex.from_documents(
                documents,
                storage_context=StorageContext.from_defaults(
                    vector_store=vector_store),
                show_progress=False
            )
        except Exception as e:
            logger.error(f"Index build failed: {str(e)}")
            return None
