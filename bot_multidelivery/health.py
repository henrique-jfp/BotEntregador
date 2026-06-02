# -*- coding: utf-8 -*-
"""
🏥 HEALTH CHECK SYSTEM
Módulo de Observabilidade nível Produção.
Monitora: Banco de Dados, Disco, Variáveis de Ambiente e Frontend.
"""
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Response, status
from sqlalchemy import text
from pydantic import BaseModel
from typing import Dict, Any, Optional

from bot_multidelivery.database import db_manager

# Configuração
router = APIRouter(tags=["Health Check"])
logger = logging.getLogger("HealthCheck")
START_TIME = datetime.now()

class HealthStatus(BaseModel):
    status: str
    uptime: str
    timestamp: str
    environment: str
    checks: Dict[str, Any]

@router.get("/health", response_model=HealthStatus)
@router.get("/api/health", response_model=HealthStatus)
async def health_check(response: Response):
    """
    Endpoint de diagnóstico completo.
    Retorna 200 se OK, 503 se houver falha crítica (ex: DB down).
    """
    checks = {}
    critical_failure = False

    # 1. 💾 Checar Banco de Dados
    try:
        if db_manager.is_connected:
            with db_manager.get_session() as session:
                session.execute(text("SELECT 1"))
            checks["database"] = {"status": "ok", "type": "postgres" if "postgres" in str(db_manager.engine.url) else "sqlite"}
        else:
            checks["database"] = {"status": "warning", "detail": "Using fallback/disconnected"}
    except Exception as e:
        logger.error(f"Health Check DB Fail: {e}")
        checks["database"] = {"status": "error", "error": str(e)}
        critical_failure = True

    # 2. 📂 Checar Frontend
    frontend_path = Path("webapp/dist")
    if frontend_path.exists() and (frontend_path / "index.html").exists():
        checks["frontend"] = {"status": "ok", "path": str(frontend_path)}
    else:
        checks["frontend"] = {"status": "warning", "detail": "Build not found (Serving API Only)"}

    # 3. 💾 Checar Disco (Permissão de Escrita)
    try:
        test_file = Path("data/health_test.tmp")
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("ok")
        test_file.unlink() # Deleta após escrever
        checks["storage"] = {"status": "ok", "writeable": True}
    except Exception as e:
        checks["storage"] = {"status": "error", "detail": f"Read-only filesystem? {e}"}
    
    # 4. 💾 Checar Persistência de Sessões
    try:
        from bot_multidelivery.session_persistence import session_store
        session_persistence_mode = "postgresql" if session_store.using_database else "json_local"
        
        # Conta sessões salvas
        sessions_loaded = session_store.list_sessions(limit=100)
        session_count = len(sessions_loaded) if sessions_loaded else 0
        
        if session_store.using_database:
            checks["session_persistence"] = {
                "status": "ok",
                "mode": session_persistence_mode,
                "sessions_count": session_count
            }
        else:
            # JSON local em produção é um problema!
            is_production = bool(os.getenv("RAILWAY_ENVIRONMENT"))
            checks["session_persistence"] = {
                "status": "error" if is_production else "warning",
                "mode": session_persistence_mode,
                "sessions_count": session_count,
                "warning": "Dados serão perdidos ao reiniciar!" if is_production else None
            }
            if is_production:
                critical_failure = True
    except Exception as e:
        checks["session_persistence"] = {"status": "error", "error": str(e)}

    # 5. 🔑 Variáveis de Ambiente Críticas
    env_vars = {
        "TELEGRAM_BOT_TOKEN": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "WEBAPP_URL": os.getenv("WEBAPP_URL", "Not Set"),
        "DATABASE_URL": "Set" if os.getenv("DATABASE_URL") else "NOT SET!"
    }
    checks["env"] = {"status": "ok" if env_vars["TELEGRAM_BOT_TOKEN"] else "error", "vars": env_vars}
    if not env_vars["TELEGRAM_BOT_TOKEN"]:
        critical_failure = True

    # Resultado Final
    uptime = datetime.now() - START_TIME
    
    if critical_failure:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        overall_status = "unhealthy"
    else:
        response.status_code = status.HTTP_200_OK
        overall_status = "healthy"

    return HealthStatus(
        status=overall_status,
        uptime=str(uptime).split('.')[0],
        timestamp=datetime.now().isoformat(),
        environment=os.getenv("RAILWAY_ENVIRONMENT", "local"),
        checks=checks
    )
