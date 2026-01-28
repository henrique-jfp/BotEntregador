"""
🚀 MAIN RUNNER
Ponto de entrada do bot multi-entregador + Web Scanner
"""
import sys
import os
import threading
import uvicorn
from pathlib import Path

# Adiciona diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot_multidelivery.bot import run_bot
from bot_multidelivery.services.web_scanner import scanner_app

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
        run_bot()
    except KeyboardInterrupt:
        print("\n⚠️ Bot interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
