# backend/routes/bots.py
from fastapi import APIRouter
from backend.services.bot_manager import BotManager

router = APIRouter()
bot_manager = BotManager()


@router.get("")
async def get_bots():
    return {
        "bots": [
            {
                "id": bot.id,
                "name": bot.name,
                "description": bot.description
            } for bot in bot_manager.bots.values()
        ]
    }
