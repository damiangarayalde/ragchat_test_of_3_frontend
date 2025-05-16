from fastapi import APIRouter, File, UploadFile, HTTPException
from backend.services.bot_manager import BotManager
import os

router = APIRouter()
bot_manager = BotManager()


@router.get("/{bot_id}")
async def get_documents(bot_id: str):
    if bot_id not in bot_manager.bots:
        raise HTTPException(status_code=404, detail="Bot not found")

    bot = bot_manager.bots[bot_id]
    try:
        if not os.path.exists(bot.data_dir):
            return {"documents": []}
        documents = os.listdir(bot.data_dir)
        return {"documents": documents}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve documents: {str(e)}"
        )


@router.post("/upload/{bot_id}")  # Define the upload endpoint here
async def upload_document(bot_id: str, file: UploadFile = File(...)):
    if bot_id not in bot_manager.bots:
        raise HTTPException(status_code=404, detail="Bot not found")

    try:
        bot = bot_manager.bots[bot_id]
        file_path = os.path.join(bot.data_dir, file.filename)

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Update index
        bot_manager.indices[bot_id] = bot_manager.index_manager.build_index(
            bot)

        return {"status": "success", "message": "File uploaded successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.delete("/{bot_id}/{filename}")
async def delete_document(bot_id: str, filename: str):
    if bot_id not in bot_manager.bots:
        raise HTTPException(status_code=404, detail="Bot not found")

    bot = bot_manager.bots[bot_id]
    file_path = os.path.join(bot.data_dir, filename)

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            bot_manager.indices[bot_id] = bot_manager.index_manager.build_index(
                bot)
            return {"status": "success", "message": f"Document {filename} deleted"}
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
        )
