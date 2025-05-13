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


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_index()
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
    global index
    if index is None:
        raise HTTPException(
            status_code=400,
            detail="Index is not initialized. Please upload a file first."
        )
    try:
        query_engine = index.as_query_engine(
            similarity_top_k=3,
            response_mode="tree_summarize",
            system_prompt=(
                "Responde en español. Usa un tono profesional, técnico y simple. "
                "Asegúrate de transmitir los conceptos claramente y evita alucinar. "
                "Si no tienes suficiente información, indica que no puedes responder con certeza."
            )
        )
        response = query_engine.query(query)
        return {"response": str(response)}
    except Exception as e:
        print(f"Error during query execution: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process the query"
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
    global index
    file_path = os.path.join("./data", filename)

    try:
        # Delete the file from the data directory
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            raise HTTPException(status_code=404, detail="File not found")

        # Rebuild the index after deletion
        if os.listdir("./data"):  # Check if there are remaining files
            documents = SimpleDirectoryReader("./data").load_data()
            collection = chroma_client.get_or_create_collection(
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

        return {"status": f"Document '{filename}' deleted successfully"}
    except Exception as e:
        print(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to delete the document"
        )
