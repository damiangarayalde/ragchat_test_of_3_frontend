from fastapi import APIRouter, Body, HTTPException
from backend.services.bot_manager import BotManager

router = APIRouter()
bot_manager = BotManager()


@router.post("/{bot_id}")
async def chat(bot_id: str, query: str = Body(..., embed=True)):
    if bot_id not in bot_manager.bots:
        raise HTTPException(status_code=404, detail="Bot not found")

    bot = bot_manager.bots[bot_id]
    index = bot_manager.indices.get(bot_id)
    chat_memory = bot_manager.memories.get(bot_id)

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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat message: {str(e)}"
        )
