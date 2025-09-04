import threading, os, urllib.parse, json
from http.server import BaseHTTPRequestHandler, HTTPServer
from bot.session import circuit_routes
from bot.config import logger

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
            return
        if self.path.startswith('/circuit/'):
            route_id = self.path.split('/')[-1]
            addresses = circuit_routes.get(route_id)
            if not addresses:
                self.send_response(404); self.end_headers(); return
            joined = '|'.join(addresses)
            deep = f"circuit://import?stops={urllib.parse.quote(joined)}"
            html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><meta http-equiv='refresh' content='0;url={deep}'></head><body>
<h3>Abrindo no Circuit...</h3>
<p><a href='{deep}'>Abrir manualmente</a></p>
<pre>{chr(10).join(addresses)}</pre>
</body></html>"""
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.end_headers(); self.wfile.write(html.encode('utf-8'))
            return
        self.send_response(404); self.end_headers()
    def log_message(self, format, *args):
        return

def start_health_server():
    port = int(os.getenv('PORT', 8000))
    try:
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True); t.start()
        logger.info(f"Health server porta {port}")
        return server
    except Exception as e:
        logger.error(f"Erro health server: {e}")
        return None
