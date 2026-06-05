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
        project_root = Path(__file__).resolve().parent
        removed_paths = []

        for entry in list(sys.path):
            if entry in ("", ".", str(project_root)):
                removed_paths.append(entry)
                sys.path.remove(entry)

        try:
            from alembic.config import Config
            from alembic import command
        finally:
            for entry in reversed(removed_paths):
                sys.path.insert(0, entry)
        
        alembic_cfg = Config("alembic.ini")
        print("🔄 Verificando migrações do banco...")
        command.upgrade(alembic_cfg, "head")
        print("✅ Banco de dados atualizado")
    except ImportError as e:
        print(f"⚠️ Alembic não disponível (migrations skipped): {e}")
    except Exception as e:
        print(f"⚠️ Erro ao executar migrações: {e}")
        # Não falha - continua mesmo se migrations falharem

# Executa migrations primeiro
run_migrations()

from bot_multidelivery.bot import run_bot
from bot_multidelivery.services.web_scanner import scanner_app
from fastapi.middleware.cors import CORSMiddleware
import logging
# --- CORS GLOBAL PARA API E FRONTEND ---
ALLOWED_ORIGINS = [
    "https://maestrofin-production.up.railway.app",
    "https://maestrofin-production.up.railway.app/",
    "https://jackqueline-inversive-materially.ngrok-free.dev",
    "http://localhost:5173",
    "http://localhost:8080",
    "*"  # Remova em produção se quiser restringir
]
scanner_app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de inspeção: detecta quando uma rota /api está retornando HTML (index.html)
logger = logging.getLogger("ApiInspector")

@scanner_app.middleware("http")
async def api_response_inspector(request, call_next):
    response = await call_next(request)
    try:
        path = request.url.path or ''
        ctype = response.headers.get('content-type', '')
        if path.startswith('/api') and 'text/html' in ctype:
            logger.warning(f"[/api] resposta HTML inesperada para {path} (Content-Type: {ctype})")
    except Exception as e:
        logger.exception(f"Erro no middleware de inspeção: {e}")
    return response
from bot_multidelivery.health import router as health_router
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import Request, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse

# Injeta Health Check (Observabilidade)
scanner_app.include_router(health_router)

# --- 🚀 LOAD MODULAR API ROUTERS ---
from fastapi import APIRouter
from bot_multidelivery.routers import admin, auth, session, logistic, romaneio, routes, separation, deliverer, neighborhoods, analytics, history

api_router = APIRouter(prefix="/api")

@api_router.get("/ping")
async def ping():
    return {"status": "online", "version": "SISTEMA ATUALIZADO V2", "timestamp": time.time()}

api_router.include_router(admin.router)
api_router.include_router(auth.router)
api_router.include_router(session.router)
api_router.include_router(logistic.router)
api_router.include_router(romaneio.router)
api_router.include_router(routes.router)
api_router.include_router(separation.router)
api_router.include_router(deliverer.router)
api_router.include_router(neighborhoods.router)
api_router.include_router(analytics.router)
api_router.include_router(history.router)
from bot_multidelivery.routers import map_realtime
api_router.include_router(map_realtime.router)

scanner_app.include_router(api_router)
print("✅ Routers Modulares incluídos com sucesso.")
# -------------------------------------

# Servir Frontend (SPA) se existir build
frontend_path = Path("webapp/dist")
if frontend_path.exists():
    print(f"✅ Servindo frontend estático de: {frontend_path}")
    scanner_app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="static")

    # Força a rota do entregador a carregar o React App (SPA)
    # Isso garante que não caia em rotas antigas ou 404
    @scanner_app.get("/public/deliverer/{token}")
    async def public_deliverer_spa(token: str, request: Request):
        print(f"🌐 Servindo SPA para entregador: {token}")
        index_file = frontend_path / "index.html"
        return FileResponse(index_file)

    # Rota explícita para o dashboard (SPA)
    @scanner_app.get("/dashboard")
    async def dashboard_spa(request: Request):
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend build (index.html) not found.")

    @scanner_app.get("/public/{full_path:path}")
    async def public_paths(full_path: str, request: Request):
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Not Found")

    # Handler global para 404: se a rota não for encontrada (e não for API), servir o index.html (SPA fallback)
    # Isso permite que rotas como /deliverer/123 funcionem com React Router
    @scanner_app.exception_handler(StarletteHTTPException)
    async def spa_404_handler(request: Request, exc: StarletteHTTPException):
        try:
            # Se não for uma chamada de API, tenta servir o index.html
            if exc.status_code == 404 and not request.url.path.startswith('/api'):
                index_file = frontend_path / "index.html"
                if index_file.exists():
                    return FileResponse(index_file)
        except Exception:
            pass
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})

# --- Metrics endpoint (Prometheus) ---
if os.environ.get('PROMETHEUS_ENABLED', '0') == '1':
    @scanner_app.get('/metrics')
    async def metrics_endpoint():
        data = generate_latest()
        return JSONResponse(content=data.decode('utf-8'), media_type=CONTENT_TYPE_LATEST)

# --- WEB SERVER PARA SCANNER + HEALTH CHECK ---
def start_web_server():
    """Inicia servidor FastAPI com scanner em /scanner"""
    port = int(os.environ.get("PORT", 8080))
    
    print(f"🌐 Web server iniciando na porta {port}")
    print(f"📱 Acesse o scanner em: http://localhost:{port}/scanner")
    
    try:
        # Configura uvicorn
        config = uvicorn.Config(
            scanner_app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=False
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        print(f"⚠️ Erro ao iniciar web server: {e}")

if __name__ == "__main__":
    # Inicia web server em thread separada
    threading.Thread(target=start_web_server, daemon=True).start()

    print("🔥 Iniciando Bot Multi-Entregador...")
    print("🎯 Pressione CTRL+C para parar\n")
    
    try:
        telegram_enabled = os.environ.get('TELEGRAM_ENABLED', '1').lower()
        if telegram_enabled in ('1', 'true', 'yes'):
            run_bot()
        else:
            print('⛔ TELEGRAM_ENABLED is false — bot polling skipped. Running only web server.')
            # Keep main thread alive so daemon threads (web server) keep running
            while True:
                time.sleep(60)
    except KeyboardInterrupt:
        print("\n⚠️ Processo interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
