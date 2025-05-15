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

Settings.llm = OpenAI(
    model="gpt-3.5-turbo",
    temperature=0.1,
    system_prompt="Responde siempre en español de manera formal y técnica."
)
# Load environment variables
load_dotenv()

# ChromaDB setup
chroma_dir = "./chroma-data"
chroma_client = chromadb.PersistentClient(path=chroma_dir)

# Global variable for the index
index = None
chat_memory = ChatMemoryBuffer.from_defaults(token_limit=2000)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize indices for all bots
    for bot_id in bot_config.bots:
        initialize_index(bot_id)
    yield


def initialize_index():
    global index
    if os.path.exists("./data") and os.listdir("./data"):
        try:
            print("Initializing index from existing data...")
            documents = SimpleDirectoryReader("./data").load_data()
            collection = chroma_client.get_or_create_collection(
                name="documents_collection",
                metadata={"hnsw:space": "cosine"}
            )
            vector_store = ChromaVectorStore(chroma_collection=collection)
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store)
            index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                show_progress=False
            )
            print("Index initialized successfully")
        except Exception as e:
            print(f"Error initializing index: {e}")
            index = None


app = FastAPI(lifespan=lifespan)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def clear_chroma_data():
    """Delete the ChromaDB collection and storage directory."""
    try:
        chroma_client.delete_collection("documents_collection")
        if os.path.exists(chroma_dir):
            shutil.rmtree(chroma_dir)
        os.makedirs(chroma_dir, exist_ok=True)
    except Exception as e:
        print(f"Error clearing ChromaDB: {e}")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    global index

    # Save the uploaded file
    os.makedirs("./data", exist_ok=True)
    file_path = f"./data/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Rebuild the index with all documents in the "./data" directory
    try:
        print(f"Adding new file to the index: {file.filename}")
        documents = SimpleDirectoryReader("./data").load_data()
        collection = chroma_client.get_or_create_collection(
            name="documents_collection",
            metadata={"hnsw:space": "cosine"}
        )
        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store)

        # Rebuild the index with all documents
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            show_progress=False
        )

        return {"status": "File uploaded and added to the index successfully"}
    except Exception as e:
        print(f"Error updating index: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update the index"
        )


@app.post("/chat")
async def chat(query: str = Body(..., embed=True)):
    global index, chat_memory
    if index is None:
        raise HTTPException(
            status_code=400,
            detail="Index is not initialized. Please upload a file first."
        )
    try:
        chat_engine = get_chat_engine(index)
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
        print(f"Error during chat execution: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process the chat message"
        )


@app.post("/chat/clear")
async def clear_chat_history():
    """Clear the chat history."""
    global chat_memory
    try:
        chat_memory.clear()
        return {"status": "Chat history cleared successfully"}
    except Exception as e:
        print(f"Error clearing chat history: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to clear chat history"
        )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "index_ready": index is not None}


@app.get("/documents")
async def get_documents():
    """Retrieve the list of indexed files."""
    try:
        if not os.path.exists("./data"):
            return {"documents": []}
        documents = os.listdir("./data")
        return {"documents": documents}
    except Exception as e:
        print(f"Error retrieving documents: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve documents"
        )


@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    """Delete a file and update the vector index."""
    global index, chat_memory
    file_path = os.path.join("./data", filename)

    try:
        # Delete the file from the data directory
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            raise HTTPException(status_code=404, detail="File not found")

        # Clear the existing collection to remove old vectors
        try:
            chroma_client.delete_collection("documents_collection")
        except Exception as e:
            print(f"Warning: Could not delete collection: {e}")

        # Rebuild the index after deletion if there are remaining files
        if os.listdir("./data"):
            documents = SimpleDirectoryReader("./data").load_data()
            # Create a new collection
            collection = chroma_client.create_collection(
                name="documents_collection",
                metadata={"hnsw:space": "cosine"}
            )
            vector_store = ChromaVectorStore(chroma_collection=collection)
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store
            )
            index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                show_progress=False
            )
        else:
            # Clear the vector store if no documents remain
            clear_chroma_data()
            index = None

        # Clear chat history when document is deleted
        chat_memory.clear()

        return {"status": f"Document '{filename}' deleted successfully"}

    except Exception as e:
        print(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to delete the document"
        )


def get_chat_engine(index: VectorStoreIndex):
    """Create a chat engine with memory."""
    return index.as_chat_engine(
        chat_memory=chat_memory,
        similarity_top_k=3,
        system_prompt=(
            "Responde en español. Usa un tono profesional, técnico y simple. "
            "Asegúrate de transmitir los conceptos claramente y evita alucinar. "
            "Si no tienes suficiente información, indica que no puedes responder con certeza. "
            "Utiliza el contexto de la conversación anterior cuando sea relevante."
        )
    )

# -----a partir de aca es nuevo
# Data Models


class Bot(BaseModel):
    id: str
    name: str
    description: str
    system_prompt: str
    collection_name: str
    data_dir: str


class BotConfig:
    def __init__(self):
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
            # Add more bots as needed
        }
        self.indices: Dict[str, VectorStoreIndex] = {}
        self.chat_memories: Dict[str, ChatMemoryBuffer] = {}

        # Initialize directories and collections
        for bot in self.bots.values():
            os.makedirs(bot.data_dir, exist_ok=True)
            self.chat_memories[bot.id] = ChatMemoryBuffer.from_defaults(
                token_limit=2000)


bot_config = BotConfig()


# Modified initialization function
def initialize_index(bot_id: str):
    """Initialize index for a specific bot."""
    bot = bot_config.bots[bot_id]
    if os.path.exists(bot.data_dir) and os.listdir(bot.data_dir):
        try:
            documents = SimpleDirectoryReader(bot.data_dir).load_data()
            collection = chroma_client.get_or_create_collection(
                name=bot.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            vector_store = ChromaVectorStore(chroma_collection=collection)
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store)

            bot_config.indices[bot_id] = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                show_progress=False
            )
            print(f"Index initialized successfully for bot {bot_id}")
        except Exception as e:
            print(f"Error initializing index for bot {bot_id}: {e}")
            bot_config.indices[bot_id] = None
    else:
        print(f"No documents found for bot {bot_id}")
        bot_config.indices[bot_id] = None


# Modified endpoints
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

    # Rebuild the index with all documents in the bot-specific directory
    try:
        print(
            f"Adding new file to the index for bot {bot_id}: {file.filename}")
        documents = SimpleDirectoryReader(bot.data_dir).load_data()
        collection = chroma_client.get_or_create_collection(
            name=bot.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store)

        # Rebuild the index with all documents
        bot_config.indices[bot_id] = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            show_progress=False
        )

        return {"status": "File uploaded and added to the index successfully"}

    except Exception as e:
        print(f"Error updating index for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update the index"
        )


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
    file_path = os.path.join(bot.data_dir, filename)

    try:
        # Delete the file from the bot's data directory
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            raise HTTPException(status_code=404, detail="File not found")

        # Clear the existing collection to remove old vectors
        try:
            chroma_client.delete_collection(bot.collection_name)
        except Exception as e:
            print(
                f"Warning: Could not delete collection for bot {bot_id}: {e}")

        # Reset chat memory for this bot with a new instance
        bot_config.chat_memories[bot_id] = ChatMemoryBuffer.from_defaults(
            token_limit=2000)

        # Rebuild the index after deletion if there are remaining files
        if os.listdir(bot.data_dir):
            documents = SimpleDirectoryReader(bot.data_dir).load_data()
            # Create a new collection
            collection = chroma_client.create_collection(
                name=bot.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            vector_store = ChromaVectorStore(chroma_collection=collection)
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store
            )
            bot_config.indices[bot_id] = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                show_progress=False
            )
        else:
            # Clear the vector store if no documents remain
            bot_config.indices[bot_id] = None

        return {"status": f"Document '{filename}' deleted successfully"}

    except Exception as e:
        print(f"Error deleting document for bot {bot_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to delete the document"
        )
