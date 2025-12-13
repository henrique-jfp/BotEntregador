"""
🚀 MAIN RUNNER
Ponto de entrada do bot multi-entregador
"""
import sys
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Adiciona diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot_multidelivery.bot import run_bot

# --- HACK PARA O RENDER (Fake Port Binding) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        print(f"🌍 Dummy server rodando na porta {port} (pra enganar o Render)")
        server.serve_forever()
    except Exception as e:
        print(f"⚠️ Nao foi possivel iniciar o dummy server: {e}")

if __name__ == "__main__":
    # Inicia o servidor fake em uma thread separada
    threading.Thread(target=start_dummy_server, daemon=True).start()

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
