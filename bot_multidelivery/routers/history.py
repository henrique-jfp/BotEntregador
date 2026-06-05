# -*- coding: utf-8 -*-
import logging
from fastapi import APIRouter
from bot_multidelivery.session import session_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/history", tags=["History"])



@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Exclui permanentemente uma sessão (limpando o histórico)"""
    success = session_manager.delete_session(session_id)
    if success:
        return {"status": "success", "message": "Sessão excluída com sucesso"}
    else:
        # Retornamos sucesso mesmo se não encontrado para atualizar a UI
        return {"status": "warning", "message": "Sessão não encontrada ou já excluída"}
@router.get("/sessions")
async def list_history_sessions(limit: int = 100):
    """Lista sessões (finalizadas e ativas) para o histórico do frontend"""
    sessions = session_manager.list_sessions(finalized_only=False)

    result = []
    for s in sessions[:limit]:
        is_completed = bool(s.is_finalized)
        
        # Determinar status detalhado
        if is_completed:
            status = "completed"
        elif s.total_packages == 0:
            status = "empty"
        elif s.current_step == "separating":
            status = "separating"
        else:
            status = "active"

        result.append({
            "id": s.session_id,
            "session_name": s.session_name,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "completed_at": s.finalized_at.isoformat() if s.finalized_at else None,
            "addresses_count": s.total_packages,
            "deliverers_count": s.num_deliverers or len(s.routes or []),
            "statistics": {
                "step": s.current_step,
                "is_finalized": is_completed
            },
            "status": status,
            "last_updated": (s.finalized_at or s.created_at).isoformat() if (s.finalized_at or s.created_at) else None,
            "is_completed": is_completed
        })

    return {"sessions": result}
