from typing import Dict
from bot.models.core import UserSession
from bot.persistence import DataPersistence

user_sessions: Dict[int, UserSession] = {}
# rotas para circuito
circuit_routes: Dict[str, list] = {}

async def get_session(user_id: int) -> UserSession:
    if user_id not in user_sessions:
        loaded = await DataPersistence.load(user_id)
        if loaded:
            user_sessions[user_id] = loaded
        else:
            user_sessions[user_id] = UserSession(user_id=user_id, photos=[])
    return user_sessions[user_id]
