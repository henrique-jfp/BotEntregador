"""
🚀 MAIN RUNNER
Ponto de entrada do bot multi-entregador + Web Scanner
"""

import sys
import os
import threading
import uvicorn
import time
from pathlib import Path
from contextlib import asynccontextmanager

# Carrega variáveis do .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Variáveis de ambiente carregadas do .env")
except ImportError:
    print("⚠️ python-dotenv não instalado. Variáveis do .env podem não ser lidas.")

# Adiciona diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 🔧 Aplicar migrações do banco de dados antes de iniciar
def run_migrations():
    """Executa migrações do Alembic se necessário"""
    try:
        from alembic.config import Config
        from alembic import command
        
        alembic_cfg = Config("alembic.ini")
        print("🔄 Verificando migrações do banco...")
        command.upgrade(alembic_cfg, "head")
        print("✅ Banco de dados atualizado")
    except ImportError as e:
        print(f"⚠️ Alembic não disponível (migrations skipped): {e}")
    except Exception as e:
        print(f"⚠️ Erro ao executar migrações: {e}")

# Executa migrations primeiro
run_migrations()

from bot_multidelivery.bot import get_telegram_app, setup_webhook, run_bot
from bot_multidelivery.services.web_scanner import scanner_app
from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

# --- Gerenciamento de Vida do App (Bot + FastAPI) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Controla inicialização e deslocamento do sistema"""
    print("🚀 Iniciando BotEntregador V2...")
    
    # 1. Inicializa App do Telegram
    bot_app = get_telegram_app()
    if bot_app:
        await bot_app.initialize()
        await bot_app.start()
        
        # 2. Configura Webhook se habilitado
        webhook_enabled = os.getenv('TELEGRAM_WEBHOOK_ENABLED', '0').lower() in ('1', 'true', 'yes')
        if webhook_enabled:
            await setup_webhook()
        else:
            # Se não for webhook, inicia polling em background
            print("ℹ️ Modo Polling: Iniciando bot em thread separada...")
            threading.Thread(target=run_bot, daemon=True).start()

    yield # Servidor rodando...

    # 3. Desligamento Limpo
    print("🛑 Desligando sistema...")
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()

# Reaplica lifespan ao app existente (definido em web_scanner.py)
scanner_app.router.lifespan_context = lifespan

# --- CORS GLOBAL PARA API E FRONTEND ---
ALLOWED_ORIGINS = [
    "https://maestrofin-production.up.railway.app",
    "https://jackqueline-inversive-materially.ngrok-free.dev",
    "http://localhost:5173",
    "http://localhost:8080",
    "*"
]
scanner_app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Injeta Health Check e Routers Modulares
from bot_multidelivery.health import router as health_router
from bot_multidelivery.routers import admin, auth, session, logistic, romaneio, separation, deliverer, neighborhoods, analytics, history, webhook, map_realtime

scanner_app.include_router(health_router)

api_router = APIRouter(prefix="/api")

@api_router.get("/ping")
async def ping():
    return {"status": "online", "version": "SISTEMA ATUALIZADO V2", "timestamp": time.time()}

api_router.include_router(admin.router)
api_router.include_router(auth.router)
api_router.include_router(session.router)
api_router.include_router(logistic.router)
api_router.include_router(romaneio.router)
api_router.include_router(separation.router)
api_router.include_router(deliverer.router)
api_router.include_router(neighborhoods.router)
api_router.include_router(analytics.router)
api_router.include_router(history.router)
api_router.include_router(webhook.router)
api_router.include_router(map_realtime.router)

scanner_app.include_router(api_router)
print("✅ Routers Modulares incluídos com sucesso.")

# Servir Frontend (SPA)
frontend_path = Path("webapp/dist")
if frontend_path.exists():
    print(f"✅ Servindo frontend estático de: {frontend_path}")
    scanner_app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="static")

    @scanner_app.get("/dashboard")
    async def dashboard_spa(request: Request):
        index_file = frontend_path / "index.html"
        return FileResponse(index_file)

    @scanner_app.exception_handler(StarletteHTTPException)
    async def spa_404_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404 and not request.url.path.startswith('/api'):
            index_file = frontend_path / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🔥 Iniciando Servidor na porta {port}")
    uvicorn.run(scanner_app, host="0.0.0.0", port=port, log_level="info")
