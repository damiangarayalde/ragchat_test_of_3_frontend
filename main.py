import shutil
from llama_index.core import Settings, VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from fastapi import Body, FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import chromadb
import os
from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI
from typing import List, Dict, Optional
from llama_index.core.memory import ChatMemoryBuffer  # Updated import path
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables and configure LLM
load_dotenv()
Settings.llm = OpenAI(
    model="gpt-3.5-turbo",
    temperature=0.1,
    system_prompt="Responde siempre en español de manera formal y técnica."
)


class Bot(BaseModel):
    id: str
    name: str
    description: str
    system_prompt: str
    collection_name: str
    data_dir: str


class ChromaManager:
    """Manages ChromaDB operations for each bot."""

    def __init__(self, base_dir: str = "./chroma-data"):
        self.base_dir = base_dir
        self.client = chromadb.PersistentClient(path=base_dir)

    def get_collection(self, name: str, create: bool = True) -> chromadb.Collection:
        """Get or create a collection for a specific bot."""
        if create:
            return self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
        return self.client.get_collection(name)

    def delete_collection(self, name: str) -> None:
        """Safely delete a collection."""
        try:
            self.client.delete_collection(name)
        except Exception as e:
            logger.warning(f"Could not delete collection {name}: {e}")


class IndexManager:
    """Manages vector index operations."""

    def __init__(self, chroma_manager: ChromaManager):
        self.chroma_manager = chroma_manager

    def build_or_update_index(self, bot: Bot) -> Optional[VectorStoreIndex]:
        """Build or update index for a specific bot."""
        try:
            if not os.path.exists(bot.data_dir) or not os.listdir(bot.data_dir):
                return None

            documents = SimpleDirectoryReader(bot.data_dir).load_data()
            collection = self.chroma_manager.get_collection(
                bot.collection_name)
            vector_store = ChromaVectorStore(chroma_collection=collection)
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store)

            return VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                show_progress=False
            )
        except Exception as e:
            logger.error(f"Error building index for bot {bot.id}: {e}")
            return None

    async def delete_document(self, bot: Bot, filename: str) -> bool:
        """Delete a document and update the index."""
        file_path = os.path.join(bot.data_dir, filename)

        if not os.path.exists(file_path):
            return False

        try:
            os.remove(file_path)
            self.chroma_manager.delete_collection(bot.collection_name)

            if os.listdir(bot.data_dir):
                return bool(self.build_or_update_index(bot))
            return True
        except Exception as e:
            logger.error(
                f"Error deleting document {filename} for bot {bot.id}: {e}")
            return False


class BotConfig:
    def __init__(self):
        self.chroma_manager = ChromaManager()
        self.index_manager = IndexManager(self.chroma_manager)
        self.bots: Dict[str, Bot] = {
            "bot1": Bot(
                id="bot1",
                name="Derechos Humanos",
                description="Asistente general para consultas de documentos",
                system_prompt="Responde siempre en español de manera formal y técnica.",
                collection_name="documents_collection_bot1",
                data_dir="./data_bot1"
            ),
            "bot2": Bot(
                id="bot2",
                name="Penal II",
                description="Especialista en documentación técnica",
                system_prompt="Responde en español, enfocándote en detalles técnicos y específicos.",
                collection_name="documents_collection_bot2",
                data_dir="./data_bot2"
            ),
        }
        self.indices: Dict[str, VectorStoreIndex] = {}
        self.chat_memories: Dict[str, ChatMemoryBuffer] = {}

        # Initialize each bot
        for bot in self.bots.values():
            self.initialize_bot(bot)

    def initialize_bot(self, bot: Bot) -> None:
        """Initialize a bot's data directory, chat memory, and index."""
        os.makedirs(bot.data_dir, exist_ok=True)
        self.chat_memories[bot.id] = ChatMemoryBuffer.from_defaults(
            token_limit=2000)
        self.indices[bot.id] = self.index_manager.build_or_update_index(bot)


bot_config = BotConfig()

# FastAPI setup
app = FastAPI(
    title="Multi-Bot Chat System",
    description="API for managing multiple chat bots with document indexing capabilities"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    for bot in bot_config.bots.values():
        bot_config.initialize_bot(bot)
    yield

# The rest of your endpoints remain the same, but remove the old endpoints
# (/upload, /chat, /documents, /chat/clear) that don't use bot_id


@app.get("/bots")
async def get_bots():
    """Get list of available bots."""
    return {
        "bots": [
            {
                "id": bot.id,
                "name": bot.name,
                "description": bot.description
            } for bot in bot_config.bots.values()
        ]
    }


@app.post("/upload/{bot_id}")
async def upload_file(bot_id: str, file: UploadFile = File(...)):
    if bot_id not in bot_config.bots:
        raise HTTPException(status_code=404, detail="Bot not found")

    bot = bot_config.bots[bot_id]

    # Save the uploaded file
    os.makedirs(bot.data_dir, exist_ok=True)
    file_path = f"{bot.data_dir}/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Rebuild the index
    try:
        print(
            f"Adding new file to the index for bot {bot_id}: {file.filename}")
        bot_config.indices[bot_id] = bot_config.index_manager.build_or_update_index(
            bot)
        if bot_config.indices[bot_id] is None:
            raise HTTPException(
                status_code=500, detail="Failed to build index")
        return {"status": "File uploaded and added to the index successfully"}
    except Exception as e:
        print(f"Error updating index for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update the index")


@app.post("/chat/{bot_id}")
async def chat(bot_id: str, query: str = Body(..., embed=True)):
    if bot_id not in bot_config.bots:
        raise HTTPException(status_code=404, detail="Bot not found")

    bot = bot_config.bots[bot_id]
    index = bot_config.indices.get(bot_id)
    chat_memory = bot_config.chat_memories.get(bot_id)

    if index is None:
        raise HTTPException(
            status_code=400,
            detail="Index is not initialized. Please upload a file first."
        )
    try:
        chat_engine = index.as_chat_engine(
            chat_memory=chat_memory,
            similarity_top_k=3,
            system_prompt=bot.system_prompt
        )
        response = chat_engine.chat(query)

        # Access chat messages directly from the memory buffer
        messages = chat_memory.get() if chat_memory else []

        return {
            "response": str(response),
            "context": [
                {"role": "user" if msg.role == "human" else "assistant",
                 "content": msg.content}
                for msg in messages[-2:]
            ] if messages else []
        }
    except Exception as e:
        print(f"Error during chat execution for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process the chat message"
        )


@app.get("/documents/{bot_id}")
async def get_documents(bot_id: str):
    if bot_id not in bot_config.bots:
        raise HTTPException(status_code=404, detail="Bot not found")

    bot = bot_config.bots[bot_id]

    try:
        if not os.path.exists(bot.data_dir):
            return {"documents": []}
        documents = os.listdir(bot.data_dir)
        return {"documents": documents}
    except Exception as e:
        print(f"Error retrieving documents for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve documents"
        )


@app.delete("/documents/{bot_id}/{filename}")
async def delete_document(bot_id: str, filename: str):
    """Delete a file and update the vector index for a specific bot."""
    if bot_id not in bot_config.bots:
        raise HTTPException(status_code=404, detail="Bot not found")

    bot = bot_config.bots[bot_id]

    success = await bot_config.index_manager.delete_document(bot, filename)
    if not success:
        raise HTTPException(
            status_code=404, detail="File not found or error during deletion")

    # Reset chat memory
    bot_config.chat_memories[bot_id] = ChatMemoryBuffer.from_defaults(
        token_limit=2000)

    return {"status": f"Document '{filename}' deleted successfully"}
