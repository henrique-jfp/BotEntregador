"""
📡 WEBSOCKET SERVER - Dashboard em tempo real
Streaming de dados de entregas ao vivo
"""
import json
import asyncio
from datetime import datetime
from typing import Set
from aiohttp import web
import aiohttp_cors


class DashboardWebSocket:
    """Servidor WebSocket para dashboard"""
    
    def __init__(self, port: int = 8765):
        self.port = port
        self.clients: Set[web.WebSocketResponse] = set()
        self.app = web.Application()
        self._setup_routes()
    
    def _setup_routes(self):
        """Configura rotas HTTP + WebSocket"""
        self.app.router.add_get('/ws', self.websocket_handler)
        self.app.router.add_get('/dashboard', self.dashboard_page)
        self.app.router.add_get('/api/stats', self.api_stats)
        
        # CORS para aceitar qualquer origem
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })
        
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def websocket_handler(self, request):
        """Handler WebSocket"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.clients.add(ws)
        print(f"🔌 Cliente conectado. Total: {len(self.clients)}")
        
        # Envia estado inicial
        await self.send_initial_state(ws)
        
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    # Cliente pode enviar comandos
                    data = json.loads(msg.data)
                    await self.handle_client_message(ws, data)
                elif msg.type == web.WSMsgType.ERROR:
                    print(f'❌ WebSocket error: {ws.exception()}')
        finally:
            self.clients.discard(ws)
            print(f"🔌 Cliente desconectado. Total: {len(self.clients)}")
        
        return ws
    
    async def dashboard_page(self, request):
        """Serve página HTML do dashboard"""
        html = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Dashboard Entregas - Tempo Real</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; font-size: 2.5em; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-value { font-size: 3em; font-weight: bold; margin: 10px 0; }
        .stat-label { font-size: 0.9em; opacity: 0.8; text-transform: uppercase; letter-spacing: 1px; }
        .deliveries-container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            max-height: 500px;
            overflow-y: auto;
        }
        .delivery-item {
            background: rgba(255, 255, 255, 0.15);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            animation: slideIn 0.3s ease-out;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        .delivery-info { flex: 1; }
        .delivery-id { font-weight: bold; font-size: 1.1em; margin-bottom: 5px; }
        .delivery-address { opacity: 0.8; font-size: 0.9em; }
        .delivery-status {
            padding: 8px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.85em;
        }
        .status-pending { background: #fbbf24; color: #78350f; }
        .status-transit { background: #3b82f6; color: white; }
        .status-delivered { background: #10b981; color: white; }
        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            border-radius: 20px;
            font-weight: bold;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .connected { background: #10b981; }
        .disconnected { background: #ef4444; }
        .ranking-container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            margin-top: 20px;
        }
        .ranking-item {
            display: flex;
            align-items: center;
            padding: 10px;
            margin-bottom: 10px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
        }
        .rank-medal { font-size: 2em; margin-right: 15px; }
        .rank-info { flex: 1; }
        .rank-name { font-weight: bold; font-size: 1.1em; }
        .rank-score { opacity: 0.8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Dashboard Entregas - Tempo Real</h1>
        
        <div class="connection-status" id="connection-status">🔴 Desconectado</div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">📦 Total Entregas</div>
                <div class="stat-value" id="total-deliveries">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">✅ Entregues</div>
                <div class="stat-value" id="delivered">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">🚚 Em Trânsito</div>
                <div class="stat-value" id="in-transit">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">⏱️ Tempo Médio</div>
                <div class="stat-value" id="avg-time">0m</div>
            </div>
        </div>
        
        <div class="ranking-container">
            <h2>🏆 Top Entregadores</h2>
            <div id="ranking-list"></div>
        </div>
        
        <div class="deliveries-container">
            <h2>📋 Entregas Ativas</h2>
            <div id="deliveries-list"></div>
        </div>
    </div>
    
    <script>
        let ws;
        let reconnectInterval;
        
        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.hostname}:8765/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                console.log('✅ WebSocket conectado');
                document.getElementById('connection-status').textContent = '🟢 Conectado';
                document.getElementById('connection-status').className = 'connection-status connected';
                clearInterval(reconnectInterval);
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
            };
            
            ws.onclose = () => {
                console.log('🔴 WebSocket desconectado');
                document.getElementById('connection-status').textContent = '🔴 Desconectado';
                document.getElementById('connection-status').className = 'connection-status disconnected';
                
                // Tenta reconectar a cada 5s
                reconnectInterval = setInterval(() => {
                    console.log('🔄 Tentando reconectar...');
                    connect();
                }, 5000);
            };
        }
        
        function updateDashboard(data) {
            if (data.type === 'stats') {
                document.getElementById('total-deliveries').textContent = data.total_deliveries;
                document.getElementById('delivered').textContent = data.delivered;
                document.getElementById('in-transit').textContent = data.in_transit;
                document.getElementById('avg-time').textContent = `${data.avg_time}m`;
            }
            
            if (data.type === 'deliveries') {
                const list = document.getElementById('deliveries-list');
                list.innerHTML = data.deliveries.map(d => `
                    <div class="delivery-item">
                        <div class="delivery-info">
                            <div class="delivery-id">📦 ${d.id}</div>
                            <div class="delivery-address">📍 ${d.address}</div>
                            <div style="margin-top: 5px; opacity: 0.7;">
                                👤 ${d.deliverer} | ⏱️ Estimado: ${d.estimated_time}min
                            </div>
                        </div>
                        <div class="delivery-status status-${d.status}">
                            ${d.status === 'pending' ? '⏳ Pendente' : 
                              d.status === 'transit' ? '🚚 Em Trânsito' : 
                              '✅ Entregue'}
                        </div>
                    </div>
                `).join('');
            }
            
            if (data.type === 'ranking') {
                const list = document.getElementById('ranking-list');
                const medals = ['🥇', '🥈', '🥉'];
                list.innerHTML = data.ranking.map((r, i) => `
                    <div class="ranking-item">
                        <div class="rank-medal">${medals[i] || `${i+1}º`}</div>
                        <div class="rank-info">
                            <div class="rank-name">${r.name}</div>
                            <div class="rank-score">⭐ ${r.score} pts | 📦 ${r.deliveries} entregas</div>
                        </div>
                    </div>
                `).join('');
            }
        }
        
        // Conecta ao iniciar
        connect();
    </script>
</body>
</html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def api_stats(self, request):
        """API REST para stats"""
        from ..services import deliverer_service, gamification_service
        from ..persistence import data_store
        
        packages = data_store.get_all_packages()
        deliverers = deliverer_service.get_all_deliverers()
        
        stats = {
            'total_deliveries': len(packages),
            'delivered': len([p for p in packages if p.get('status') == 'delivered']),
            'in_transit': len([p for p in packages if p.get('status') == 'in_transit']),
            'active_deliverers': len([d for d in deliverers if d.is_active])
        }
        
        return web.json_response(stats)
    
    async def send_initial_state(self, ws: web.WebSocketResponse):
        """Envia estado inicial ao cliente"""
        from ..services import deliverer_service, gamification_service
        from ..persistence import data_store
        
        packages = data_store.get_all_packages()
        leaderboard = gamification_service.get_leaderboard(limit=3)
        
        # Stats
        await ws.send_json({
            'type': 'stats',
            'total_deliveries': len(packages),
            'delivered': len([p for p in packages if p.get('status') == 'delivered']),
            'in_transit': len([p for p in packages if p.get('status') == 'in_transit']),
            'avg_time': 15  # TODO: calcular real
        })
        
        # Ranking
        await ws.send_json({
            'type': 'ranking',
            'ranking': [{
                'name': e.name,
                'score': e.score,
                'deliveries': deliverer_service.get_deliverer(e.deliverer_id).total_deliveries
            } for e in leaderboard]
        })
    
    async def handle_client_message(self, ws: web.WebSocketResponse, data: dict):
        """Processa mensagens do cliente"""
        if data.get('action') == 'refresh':
            await self.send_initial_state(ws)
    
    async def broadcast(self, message: dict):
        """Envia mensagem para todos os clientes"""
        dead_clients = set()
        
        for client in self.clients:
            try:
                await client.send_json(message)
            except:
                dead_clients.add(client)
        
        # Remove clientes mortos
        self.clients -= dead_clients
    
    async def notify_delivery_update(self, package_id: str, status: str):
        """Notifica atualização de entrega"""
        await self.broadcast({
            'type': 'delivery_update',
            'package_id': package_id,
            'status': status,
            'timestamp': datetime.now().isoformat()
        })
    
    def run(self):
        """Inicia servidor"""
        web.run_app(self.app, host='0.0.0.0', port=self.port)
    
    async def start_background(self):
        """Inicia em background (não bloqueia)"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        print(f"🌐 Dashboard WebSocket rodando em http://0.0.0.0:{self.port}/dashboard")


# Singleton
dashboard_ws = DashboardWebSocket()
