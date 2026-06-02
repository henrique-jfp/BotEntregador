# -*- coding: utf-8 -*-
from fastapi import APIRouter
from bot_multidelivery.config import BotConfig
from bot_multidelivery.services import deliverer_service

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.get("/me")
async def get_me(user_id: int):
    """Retorna papel do usuário e dados básicos"""
    
    # 1. Check Admin
    if user_id == BotConfig.ADMIN_TELEGRAM_ID:
        return {
            "id": user_id,
            "role": "admin",
            "name": "Administrador",
            "access": "full"
        }

    # 2. Check Partner/Deliverer
    deliverer = deliverer_service.get_deliverer(user_id)
    if deliverer:
        return {
            "id": deliverer.telegram_id,
            "role": "admin" if deliverer.is_partner else "deliverer",  # Sócios têm acesso admin
            "name": deliverer.name,
            "is_partner": deliverer.is_partner,
            "access": "full" if deliverer.is_partner else "restricted"
        }
    
    # 3. Visitante
    return {
        "id": user_id,
        "role": "guest",
        "name": "Visitante",
        "access": "none"
    }
