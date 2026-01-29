"""
MAP GENERATOR - Gera mapa interativo HTML com Leaflet.js
Cada ponto clicavel abre Google Maps + botoes de acao
"""
from typing import List, Tuple
from dataclasses import dataclass
import json


class MapGenerator:
    """
    Gera mapa HTML interativo com:
    - Leaflet.js (OpenStreetMap)
    - Pins coloridos por status
    - Click abre Google Maps
    - Botoes: Entregue, Insucesso, Transferir
    """
    
    # Cores dos pins
    COLORS = {
        'current': '#4CAF50',    # Verde - atual
        'pending': '#9C27B0',    # Roxo - pendente
        'completed': '#FF9800',  # Laranja - entregue
        'failed': '#F44336'      # Vermelho - insucesso
    }
    
    @staticmethod
    def generate_interactive_map(
        stops: List[Tuple[float, float, str, int, str]],  # lat, lon, address, packages, status
        entregador_nome: str,
        current_stop: int = 0,
        total_packages: int = 0,
        total_distance_km: float = 0,
        total_time_min: float = 0,
        base_location: Tuple[float, float, str] = None  # (lat, lon, address)
    ) -> str:
        """
        Gera HTML do mapa interativo
        
        Args:
            stops: Lista de (lat, lon, endereco, num_pacotes, status)
            entregador_nome: Nome do entregador
            current_stop: Indice da parada atual
            total_packages: Total de pacotes
            total_distance_km: Distancia total
            total_time_min: Tempo estimado total
            base_location: (lat, lon, endereco) da base
            
        Returns:
            HTML completo do mapa
        """
        
        # Calcula bounds para zoom automático
        all_lats = [s[0] for s in stops]
        all_lons = [s[1] for s in stops]
        if base_location:
            all_lats.append(base_location[0])
            all_lons.append(base_location[1])
        
        # Centro e zoom inteligente
        if all_lats and all_lons:
            center_lat = sum(all_lats) / len(all_lats)
            center_lon = sum(all_lons) / len(all_lons)
            
            # Calcula distância máxima para definir zoom
            lat_range = max(all_lats) - min(all_lats)
            lon_range = max(all_lons) - min(all_lons)
            max_range = max(lat_range, lon_range)
            
            # Zoom baseado na dispersão (menor range = mais zoom)
            if max_range < 0.01:  # <1km
                zoom = 16
            elif max_range < 0.03:  # <3km
                zoom = 15
            elif max_range < 0.05:  # <5km
                zoom = 14
            elif max_range < 0.1:  # <10km
                zoom = 13
            else:
                zoom = 12
        else:
            center_lat = 0
            center_lon = 0
            zoom = 15
        
        # Prepara dados dos markers
        markers_data = []
        completed_count = 0
        
        for i, (lat, lon, address, packages, status) in enumerate(stops):
            if status == 'completed':
                completed_count += 1
                
            color = MapGenerator.COLORS.get(status, MapGenerator.COLORS['pending'])
            
            markers_data.append({
                'lat': lat,
                'lon': lon,
                'address': address,
                'packages': packages,
                'status': status,
                'number': i + 1,
                'color': color,
                'is_current': i == current_stop
            })
        
        markers_json = json.dumps(markers_data)
        
        # HTML completo
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rota - {entregador_nome}</title>
    
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <!-- Leaflet Routing Machine CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.css" />
    
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            overflow: hidden;
        }}
        
        /* Esconde painel de instruções do routing */
        .leaflet-routing-container {{
            display: none !important;
        }}
        
        #map {{
            width: 100vw;
            height: 100vh;
        }}
        
        .header {{
            position: absolute;
            top: 10px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1000;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 25px;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            font-weight: bold;
            text-align: center;
        }}
        
        .header .title {{
            font-size: 18px;
            margin-bottom: 5px;
        }}
        
        .header .stats {{
            font-size: 12px;
            opacity: 0.9;
        }}
        
        .bottom-card {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: white;
            border-radius: 20px 20px 0 0;
            box-shadow: 0 -4px 20px rgba(0,0,0,0.2);
            padding: 20px;
            z-index: 1000;
            max-height: 40vh;
            overflow-y: auto;
            display: none;
        }}
        
        .bottom-card.visible {{
            display: block;
        }}
        
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }}
        
        .card-number {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            font-weight: bold;
        }}
        
        .card-close {{
            background: #f5f5f5;
            border: none;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            font-size: 20px;
            cursor: pointer;
        }}
        
        .card-address {{
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .card-info {{
            color: #666;
            font-size: 14px;
            margin-bottom: 15px;
        }}
        
        .action-buttons {{
            display: flex;
            gap: 10px;
        }}
        
        .btn {{
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 10px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }}
        
        .btn:active {{
            transform: scale(0.95);
        }}
        
        .btn-success {{
            background: #4CAF50;
            color: white;
        }}
        
        .btn-danger {{
            background: #F44336;
            color: white;
        }}
        
        .btn-transfer {{
            background: #2196F3;
            color: white;
        }}
        
        .btn-maps {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin-bottom: 10px;
        }}
        
        .marker-icon {{
            background: white;
            border: 3px solid;
            border-radius: 50%;
            width: 35px;
            height: 35px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">{entregador_nome}</div>
        <div class="stats">
            <span id="progress">{completed_count} de {len(stops)} paradas</span> | 
            <span>{total_packages} pacotes</span>
        </div>
    </div>
    
    <div id="map"></div>
    
    <div id="bottom-card" class="bottom-card">
        <div class="card-header">
            <div id="card-number" class="card-number"></div>
            <button class="card-close" onclick="closeCard()">×</button>
        </div>
        <div id="card-address" class="card-address"></div>
        <div id="card-info" class="card-info"></div>
        
        <button id="btn-maps" class="btn btn-maps" onclick="openGoogleMaps()">
            Abrir no Google Maps
        </button>
        
        <div class="action-buttons">
            <button class="btn btn-success" onclick="markDelivered()">
                Entregue
            </button>
            <button class="btn btn-danger" onclick="markFailed()">
                Insucesso
            </button>
            <button class="btn btn-transfer" onclick="transferPackage()">
                Transferir
            </button>
        </div>
    </div>
    
    <!-- Leaflet JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <!-- Leaflet Routing Machine JS -->
    <script src="https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.js"></script>
    
    <script>
        // Dados dos markers
        const markers = {markers_json};
        let currentMarker = null;
        
        // Inicializa mapa com zoom automático
        const map = L.map('map').setView([{center_lat}, {center_lon}], {zoom});
        
        // Tile layer (OpenStreetMap)
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }}).addTo(map);
        
        // Adiciona marker da BASE se houver
        const baseLocation = {json.dumps(base_location) if base_location else 'null'};
        if (baseLocation) {{
            const baseIcon = L.divIcon({{
                className: 'marker-icon',
                html: '<div style="border-color: #FF5722; color: #FF5722; background: white; font-weight: bold;">🏠</div>',
                iconSize: [32, 32]
            }});
            
            const baseMarker = L.marker([baseLocation[0], baseLocation[1]], {{ icon: baseIcon }}).addTo(map);
            baseMarker.bindPopup(`<b>🏠 BASE</b><br>${{baseLocation[2]}}`);
        }}
        
        // Adiciona markers das entregas
        markers.forEach((m, idx) => {{
            const icon = L.divIcon({{
                className: 'marker-icon',
                html: `<div style="border-color: ${{m.color}}; color: ${{m.color}}">${{m.number}}</div>`,
                iconSize: [26, 26]
            }});
            
            const marker = L.marker([m.lat, m.lon], {{ icon }}).addTo(map);
            
            marker.on('click', () => {{
                openCard(m);
            }});
            
            // Destaca marker atual
            if (m.is_current) {{
                marker.setZIndexOffset(1000);
            }}
        }});
        
        // Desenha rota real pelas ruas usando OSRM
        const waypoints = markers.map(m => L.latLng(m.lat, m.lon));
        
        try {{
            L.Routing.control({{
                waypoints: waypoints,
                router: L.Routing.osrmv1({{
                    serviceUrl: 'https://router.project-osrm.org/route/v1',
                    profile: 'driving' // ou 'bike' se for modo scooter
                }}),
                lineOptions: {{
                    styles: [{{
                        color: '#667eea',
                        weight: 4,
                        opacity: 0.8
                    }}]
                }},
                show: false, // esconde painel de instrucoes
                addWaypoints: false,
                draggableWaypoints: false,
                fitSelectedRoutes: false,
                showAlternatives: false
            }}).addTo(map);
        }} catch(err) {{
            // Fallback: linha reta se routing falhar
            console.warn('Routing falhou, usando polyline:', err);
            L.polyline(waypoints, {{
                color: '#667eea',
                weight: 3,
                opacity: 0.7,
                dashArray: '10, 10'
            }}).addTo(map);
        }}
        
        // Funcoes
        function openCard(marker) {{
            currentMarker = marker;
            
            document.getElementById('card-number').textContent = marker.number;
            document.getElementById('card-address').textContent = marker.address;
            document.getElementById('card-info').textContent = 
                `Entrega ${{marker.packages}} unidade${{marker.packages > 1 ? 's' : ''}} | Status: ${{marker.status}}`;
            
            document.getElementById('bottom-card').classList.add('visible');
        }}
        
        function closeCard() {{
            document.getElementById('bottom-card').classList.remove('visible');
        }}
        
        function openGoogleMaps() {{
            if (!currentMarker) return;
            
            const url = `https://www.google.com/maps/dir/?api=1&destination=${{currentMarker.lat}},${{currentMarker.lon}}`;
            window.open(url, '_blank');
        }}
        
        function markDelivered() {{
            if (!currentMarker) return;
            
            // Envia callback pro bot
            window.Telegram.WebApp.sendData(JSON.stringify({{
                action: 'delivered',
                stop: currentMarker.number,
                address: currentMarker.address
            }}));
            
            alert(`Marcado como entregue: Stop ${{currentMarker.number}}`);
            closeCard();
        }}
        
        function markFailed() {{
            if (!currentMarker) return;
            
            window.Telegram.WebApp.sendData(JSON.stringify({{
                action: 'failed',
                stop: currentMarker.number,
                address: currentMarker.address
            }}));
            
            alert(`Marcado como insucesso: Stop ${{currentMarker.number}}`);
            closeCard();
        }}
        
        function transferPackage() {{
            if (!currentMarker) return;
            
            window.Telegram.WebApp.sendData(JSON.stringify({{
                action: 'transfer',
                stop: currentMarker.number,
                address: currentMarker.address
            }}));
            
            alert(`Solicitar transferencia: Stop ${{currentMarker.number}}`);
            closeCard();
        }}
        
        // Abre automaticamente primeiro marker
        if (markers.length > 0) {{
            const firstPending = markers.find(m => m.status === 'pending' || m.status === 'current');
            if (firstPending) {{
                openCard(firstPending);
            }}
        }}
    </script>
</body>
</html>
"""
        
        return html
    
    @staticmethod
    def save_map(html: str, filename: str):
        """Salva HTML do mapa em arquivo"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)


# Test
if __name__ == "__main__":
    # Dados fake para teste
    stops = [
        (-22.9450391, -43.1842129, "Rua Muniz Barreto, 396, Botafogo", 3, "completed"),
        (-22.9460000, -43.1850000, "Rua Marquês de Olinda, 18", 5, "current"),
        (-22.9470000, -43.1860000, "Rua Voluntários da Pátria, 1", 4, "pending"),
        (-22.9480000, -43.1870000, "Rua da Passagem, 7", 2, "pending"),
    ]
    
    html = MapGenerator.generate_interactive_map(
        stops=stops,
        entregador_nome="Henrique - Entregador 1",
        current_stop=1,
        total_packages=14,
        total_distance_km=2.5,
        total_time_min=15
    )
    
    MapGenerator.save_map(html, "teste_mapa.html")
    print("[OK] Mapa salvo em teste_mapa.html")
    print("Abra no navegador para testar!")
