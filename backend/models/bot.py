# backend/models/bot.py
from pydantic import BaseModel


class Bot(BaseModel):
    id: str
    name: str
    description: str
    system_prompt: str
    collection_name: str
    data_dir: str
