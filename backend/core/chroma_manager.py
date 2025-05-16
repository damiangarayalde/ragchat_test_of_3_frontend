# backend/core/chroma_manager.py
import chromadb
import logging

logger = logging.getLogger(__name__)


class ChromaManager:
    def __init__(self, base_dir: str):
        self.client = chromadb.PersistentClient(path=base_dir)

    def get_collection(self, name: str):
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )

    def delete_collection(self, name: str):
        try:
            self.client.delete_collection(name)
        except Exception as e:
            logger.warning(f"Collection deletion failed: {str(e)}")
