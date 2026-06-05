# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from bot_multidelivery.config import BotConfig
from bot_multidelivery.persistence import data_store
from bot_multidelivery.services.deliverer_service import DelivererService
from bot_multidelivery.schemas_models import DelivererInput
from bot_multidelivery.session import session_manager

router = APIRouter(prefix="/admin", tags=["Admin Team"])

@router.get("/team")
async def get_team():
    """Lista todos os entregadores cadastrados"""
    deliverers = data_store.load_deliverers()
    return [
        {
            "id": d.telegram_id,
            "name": d.name,
            "is_partner": d.is_partner,
            "deliveries": d.total_deliveries,
            "earnings": d.total_earnings
        }
        for d in deliverers
    ]

@router.post("/team")
async def add_member(data: DelivererInput):
    """Adiciona novo membro à equipe"""
    try:
        DelivererService.add_deliverer(
            telegram_id=data.telegram_id,
            name=data.name,
            is_partner=data.is_partner
        )
        return {"status": "success", "message": f"{data.name} adicionado!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/team/{user_id}")
async def remove_member(user_id: int):
    """Remove membro permanentemente utilizando a persistência"""
    try:
        data_store.delete_deliverer(user_id)
        return {"status": "success", "deleted_id": user_id}
    except Exception as e:
        return {"status": "success", "warning": str(e)}

@router.get("/stats")
async def get_stats():
    """Retorna estatísticas gerais do sistema + sessão ativa em tempo real"""
    deliverers = data_store.load_deliverers()
    total_historical = sum(d.total_deliveries for d in deliverers)
    
    # Buscar sessão ativa
    active_session = session_manager.get_active_session()
    
    if active_session:
        # Calcular stats da sessão ativa (DailySession)
        all_routes = active_session.routes or []
        
        packages_total = sum(r.total_packages for r in all_routes)
        delivered = sum(r.delivered_count for r in all_routes)
        pending = packages_total - delivered
        
        # Contar entregadores ativos (rotas atribuídas)
        active_deliverers = len([r for r in all_routes if r.assigned_to_telegram_id])
        
        return {
            "packages_total": packages_total,
            "delivered": delivered,
            "pending": pending,
            "active_deliverers": active_deliverers,
            "total_deliverers": len(deliverers),
            "total_packages_delivered": total_historical,
            "system_status": "online",
            "active_session": True,
            "session_id": active_session.session_id,
            "session_name": active_session.session_name or "Sessão Ativa"
        }
    else:
        # Sem sessão ativa
        return {
            "packages_total": 0,
            "delivered": 0,
            "pending": 0,
            "active_deliverers": 0,
            "total_deliverers": len(deliverers),
            "total_packages_delivered": total_historical,
            "system_status": "online",
            "active_session": False,
            "session_id": None
        }


@router.post("/force_delete/{session_id}")
async def force_delete_session(session_id: str):
    """Força exclusão completa de sessão (uso administrativo)."""
    try:
        # Tenta forçar exclusão via SessionManager
        deleted = session_manager.delete_session(session_id, force=True)
        return {"status": "success", "deleted": bool(deleted), "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
