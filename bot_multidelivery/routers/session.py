# -*- coding: utf-8 -*-
import logging
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from bot_multidelivery.schemas_models import (
    StartSessionInput, RouteValueInput, FinalizeSessionInput
)
from bot_multidelivery.session import session_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/session", tags=["Sessions"])


def build_session_route_preview(route):
    points = route.optimized_order or []
    return {
        "route_id": route.id,
        "id": route.id,
        "total_stops": len(points),
        "total_packages": len(points),
        "total_points": len(points),
        "packages_count": len(points),
        "percentage_load": 0,
        "color": route.color,
        "map_url": None,
        "points_sample": [
            {
                "id": p.package_id,
                "address": p.address,
                "lat": p.lat,
                "lng": p.lng,
                "bairro": getattr(p, "bairro", ""),
                "cep": getattr(p, "cep", ""),
            }
            for p in points
            if getattr(p, "lat", None) and getattr(p, "lng", None)
        ],
        "assigned_to": route.assigned_to_name,
        "assigned_to_id": route.assigned_to_telegram_id,
    }

@router.post("/start")
async def start_session(data: StartSessionInput):
    """
    Inicia (ou reutiliza) uma sessão ativa.
    Implementação REAL (Migrada de api_routes.py)
    """
    date_str = data.date or datetime.now().strftime('%Y-%m-%d')
    session = session_manager.get_current_session()

    if not session or session.is_finalized:
        session = session_manager.create_new_session(date_str, data.period)
    
    # Atualiza base se fornecida
    if data.base_address and data.base_lat is not None and data.base_lng is not None:
        session_manager.set_base_location(data.base_address, data.base_lat, data.base_lng, session.session_id)

    return {
        "session_id": session.session_id,
        "session_name": session.session_name,
        "date": session.date,
        "period": session.period,
        "base_address": session.base_address,
        "total_packages": session.total_packages,
        "routes_count": len(session.routes)
    }

@router.post("/route-value")
async def set_route_value(data: RouteValueInput):
    """Define valor da rota para a sessão"""
    if data.session_id:
        session = session_manager.get_session(data.session_id)
    else:
        session = session_manager.get_current_session()

    if session:
        session.route_value = data.value
        session_manager.save_session(session)
        return {"status": "success", "value": data.value}
        
    return {"status": "error", "message": "Sessão não encontrada"}

@router.post("/finalize")
async def finalize_session(data: FinalizeSessionInput):
    """Encerra a sessão e calcula totais"""
    if data.session_id:
        session_manager.finalize_session(data.session_id)
    else:
        # Finaliza atual
        s = session_manager.get_current_session()
        if s: session_manager.finalize_session(s.session_id)
        
    return {"status": "success", "message": "Sessão finalizada com sucesso!"}

@router.get("/state")
async def get_session_state():
    """
    Retorna o estado completo da sessão atual.
    Usado pelo frontend para restaurar estado (cross-device sync).
    """
    session = session_manager.get_current_session()
    
    if not session:
        return {
            "active": False,
            "session_id": None,
            "has_romaneio": False
        }
    
    return {
        "active": True,
        "session_id": session.session_id,
        "session_name": session.session_name,
        "date": session.date,
        "period": session.period,
        "base_address": session.base_address,
        "base_lat": session.base_lat,
        "base_lng": session.base_lng,
        "has_romaneio": len(session.romaneios) > 0,
        "route_value": session.route_value,
        "num_deliverers": session.num_deliverers,
        "total_packages": session.total_packages,
        "romaneios": [
            {
                "id": r.id,
                "filename": r.filename,
                "uploaded_at": r.uploaded_at.isoformat(),
                "package_count": len(r.points)
            }
            for r in session.romaneios
        ],
        "routes": [
            {
                **build_session_route_preview(r),
                "percentage_load": round(len(r.optimized_order or []) / (sum(len(route.optimized_order or []) for route in session.routes) or 1) * 100),
            }
            for r in session.routes
        ],
        "assignments": {
            r.id: r.assigned_to_telegram_id
            for r in session.routes
            if r.assigned_to_telegram_id
        }
    }

@router.get("/routes_status")
async def get_routes_status():
    """Retorna status simplificado das rotas da sessão ativa"""
    session = session_manager.get_current_session()

    if not session:
        raise HTTPException(status_code=404, detail="Nenhuma sessão ativa")

    routes = session.routes or []

    return [
        {
            "id": r.id,
            "assigned_to_name": r.assigned_to_name,
            "assigned_to_telegram_id": r.assigned_to_telegram_id,
            "color": r.color,
            "status": r.status,
            "total_packages": r.total_packages,
            "delivered": r.delivered_count,
            "pending": r.pending_count
        }
        for r in routes
    ]

@router.get("/{session_id}/resume")
async def resume_session(session_id: str):
    """Retorna dados mínimos para retomar uma sessão"""
    session = session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    current_step = session.current_step or "idle"
    is_completed = session.is_finalized

    if is_completed:
        resume_tab = "history"
    elif current_step in ["separating"]:
        resume_tab = "separation"
    else:
        resume_tab = "analysis"

    return {
        "session_id": session.session_id,
        "session_name": session.session_name,
        "current_step": current_step,
        "resume_tab": resume_tab,
        "total_packages": session.total_packages,
        "num_deliverers": session.num_deliverers,
        "routes_count": len(session.routes)
    }

@router.post("/cancel-import")
async def cancel_import():
    """Cancela a importação e limpa a sessão atual"""
    session = session_manager.get_current_session()
    
    if not session:
        raise HTTPException(status_code=404, detail="Nenhuma sessão ativa")
    
    # Limpa romaneios e rotas
    session.romaneios = []
    session.routes = []
    session.current_step = "idle"
    session.num_deliverers = 0
    session_manager.save_session(session)
    
    logger.info(f"✅ Sessão {session.session_id} cancelada (romaneios/rotas limpas)")
    
    return {
        "status": "success",
        "message": "Importação cancelada e sessão limpa"
    }


@router.get("/report")
async def get_report():
    """Retorna relatório da sessão ativa"""
    session = session_manager.get_current_session()
    
    if not session:
        return {
            "active_session": False,
            "revenue": 0.0,
            "packages_total": 0,
            "deliverers_active": 0
        }

    # Dados do resumo da sessão
    total_packages = sum(len(r.points) for r in session.romaneios)
    
    return {
        "active_session": True,
        "session_id": session.session_id,
        "session_name": session.session_name,
        "total_romaneios": len(session.romaneios),
        "total_packages": total_packages,
        "route_value": session.route_value,
        "romaneios": [
            {
                "id": r.id,
                "filename": r.filename,
                "uploaded_at": r.uploaded_at.isoformat(),
                "package_count": len(r.points)
            }
            for r in session.romaneios
        ],
        "revenue": session.route_value,
        "packages_total": total_packages,
        "delivered": getattr(session, 'total_delivered', 0),
        "pending": total_packages - getattr(session, 'total_delivered', 0),
        "routes_count": len(session.routes)
    }


@router.delete("/{session_id}")
async def delete_session(session_id: str, force: str = Query('false')):
    """
    Deleta uma sessão permanentemente
    Remove: sessão, romaneios, rotas, pacotes, ganhos e custos associados
    """
    try:
        # Loga o valor recebido de force
        logger.warning(f"[DEBUG] DELETE /session/{{session_id}} force param recebido: {force} (type={type(force)})")
        force_bool = force in [True, 'true', 'True', 1, '1']
        logger.warning(f"[DEBUG] DELETE /session/{{session_id}} force interpretado como: {force_bool}")
        session_manager.delete_session(session_id, force=force_bool)
        logger.info(f"🗑️ Sessão deletada: {session_id}")
        return {"status": "success", "message": f"Sessão {session_id} deletada com sucesso"}
    except Exception as e:
        msg = str(e)
        logger.error(f"❌ Erro ao deletar sessão {session_id}: {msg}")
        logger.error(f"[DEBUG] Exception type: {type(e)} | Exception: {e}")
        # Se é uma proteção de sessão em uso, retorna 400 com orientação
        if "Sessão em uso" in msg:
            raise HTTPException(status_code=400, detail=msg)
        raise HTTPException(status_code=500, detail=f"Erro ao deletar: {msg}")


@router.post("/{session_id}/release")
async def release_session(session_id: str):
    """Libera a aba 'Análise' sem deletar a sessão (mantém sessão ativa para mapa/separação)."""
    success = session_manager.release_session_from_analysis(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    logger.info(f"🔓 Sessão liberada da Análise: {session_id}")
    return {"status": "success", "message": "Sessão liberada da Análise. A sessão permanece ativa para mapa/separação."}


@router.get("/list/all")
async def list_all_sessions():
    """
    Lista TODAS as sessões abertas (para admin deletar as vazias)
    """
    return {
        "sessions": [
            {
                "id": sid,
                "name": s.session_name,
                "date": s.date,
                "total_packages": sum(len(r.points) for r in s.romaneios),
                "routes_count": len(s.routes),
                "is_finalized": s.is_finalized
            }
            for sid, s in session_manager.active_sessions.items()
        ]
    }
