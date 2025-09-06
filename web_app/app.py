#!/usr/bin/env python3
"""
🚀 ENTREGADOR WEB APP - Versão PWA
Aplicativo web pessoal para controle de entregas
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
import os
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import threading

# Simulação das funcionalidades do bot (versão simplificada)
def extract_addresses(text):
    """Simula extração de endereços - substituir por OCR real depois"""
    sample_addresses = [
        "Rua das Flores, 123 - Centro, São Paulo - SP",
        "Av. Paulista, 456 - Bela Vista, São Paulo - SP", 
        "Travessa do Comércio, 789 - Liberdade, São Paulo - SP"
    ]
    return [{'original_text': addr, 'cleaned_address': addr, 'confidence': 0.9} for addr in sample_addresses]

def append_gain(record):
    """Salva ganho em arquivo JSON"""
    gains_file = Path('gains.jsonl')
    try:
        with open(gains_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"Erro ao salvar ganho: {e}")

def load_gains(user_id, start_date, end_date):
    """Carrega ganhos do arquivo"""
    gains_file = Path('gains.jsonl')
    if not gains_file.exists():
        return []
    
    gains = []
    try:
        with open(gains_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    if record.get('user') == user_id:
                        gains.append(record)
                except:
                    continue
    except:
        pass
    return gains

def summarize_gains(gains):
    """Resume ganhos por app"""
    if not gains:
        return "Nenhum ganho registrado"
    
    by_app = {}
    total = 0
    for gain in gains:
        app = gain.get('app', 'Outro')
        value = float(gain.get('valor', 0))
        by_app[app] = by_app.get(app, 0) + value
        total += value
    
    lines = [f"{app}: R$ {val:.2f}" for app, val in by_app.items()]
    lines.append(f"TOTAL: R$ {total:.2f}")
    return '\n'.join(lines)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Cria pasta de uploads
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)

class WebUserSession:
    def __init__(self):
        self.user_id = session.get('user_id', str(uuid.uuid4()))
        session['user_id'] = self.user_id
        self.photos = []
        self.addresses = []
        self.optimized_route = []
        self.current_delivery_index = 0
        self.completed_deliveries = []
        self.config = {
            'valor_entrega': float(session.get('valor_entrega', 8.0)),
            'custo_km': float(session.get('custo_km', 0.5)),
            'service_time_min': 2.0
        }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_photos():
    if 'photos' not in request.files:
        return jsonify({'error': 'Nenhuma foto enviada'}), 400
    
    files = request.files.getlist('photos')
    photo_paths = []
    
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                                   f"{session['user_id']}_{filename}")
            file.save(file_path)
            photo_paths.append(file_path)
    
    session['photos'] = photo_paths
    return jsonify({'success': True, 'count': len(photo_paths)})

@app.route('/process', methods=['POST'])
async def process_photos():
    photo_paths = session.get('photos', [])
    if not photo_paths:
        return jsonify({'error': 'Nenhuma foto para processar'}), 400
    
    try:
        # Simula OCR - na implementação real usaria o ImageProcessor
        # Por simplicidade, vamos permitir entrada manual
        sample_text = """
        Rua das Flores, 123 - Centro
        Av. Paulista, 456 - Bela Vista
        Travessa do Comércio, 789 - Liberdade
        """
        
        addresses = extract_addresses(sample_text)
        
        # Converte para formato serializável
        addresses_data = []
        for addr in addresses:
            addresses_data.append({
                'original_text': addr.original_text,
                'cleaned_address': addr.cleaned_address,
                'confidence': addr.confidence
            })
        
        session['addresses'] = addresses_data
        return jsonify({
            'success': True, 
            'addresses': addresses_data,
            'count': len(addresses_data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro no processamento: {str(e)}'}), 500

@app.route('/optimize', methods=['POST'])
async def optimize_route():
    addresses_data = session.get('addresses', [])
    if not addresses_data:
        return jsonify({'error': 'Nenhum endereço para otimizar'}), 400
    
    try:
        # Reconstrói objetos de endereço (versão simplificada)
        addresses = []
        for addr_data in addresses_data:
            addresses.append(addr_data)  # Usar dicionário simples por agora
        
        # Otimiza rota (versão simplificada - na real usaria a função completa)
        optimized = addresses  # Por simplicidade
        
        route_data = []
        for i, addr in enumerate(addresses):
            route_data.append({
                'index': i,
                'address': addr['cleaned_address'],
                'status': 'pending'
            })
        
        session['optimized_route'] = route_data
        session['current_delivery_index'] = 0
        
        return jsonify({
            'success': True,
            'route': route_data,
            'stats': {
                'total_km': 15.2,
                'total_time': 45,
                'total_deliveries': len(route_data)
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro na otimização: {str(e)}'}), 500

@app.route('/navigation')
def navigation():
    route = session.get('optimized_route', [])
    current_index = session.get('current_delivery_index', 0)
    
    if not route:
        return redirect(url_for('home'))
    
    return render_template('navigation.html', 
                         route=route, 
                         current_index=current_index,
                         total=len(route))

@app.route('/deliver/<int:index>', methods=['POST'])
def mark_delivered(index):
    route = session.get('optimized_route', [])
    
    if 0 <= index < len(route):
        route[index]['status'] = 'delivered'
        route[index]['delivered_at'] = datetime.now().isoformat()
        session['optimized_route'] = route
        
        # Move para próxima entrega
        current = session.get('current_delivery_index', 0)
        if index == current:
            session['current_delivery_index'] = current + 1
    
    return jsonify({'success': True})

@app.route('/gains')
def gains():
    return render_template('gains.html')

@app.route('/gains/add', methods=['POST'])
def add_gain():
    data = request.json
    
    # Garante que há um user_id na sessão
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    gain_record = {
        'user': session['user_id'],
        'date': data.get('date'),
        'app': data.get('app'),
        'valor': float(data.get('value', 0))
    }
    
    append_gain(gain_record)
    
    return jsonify({'success': True})

@app.route('/gains/summary')
def gains_summary():
    # Garante que há um user_id na sessão
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        
    user_id = session['user_id']
    period = request.args.get('period', 'today')
    
    now = datetime.now()
    if period == 'today':
        start = end = now
    elif period == 'week':
        start = now - timedelta(days=6)
        end = now
    elif period == 'month':
        start = now.replace(day=1)
        end = now
    
    gains = load_gains(user_id, start, end)
    summary = summarize_gains(gains)
    
    return jsonify({
        'period': period,
        'summary': summary,
        'gains': gains
    })

@app.route('/map')
def map_view():
    route = session.get('optimized_route', [])
    current_index = session.get('current_delivery_index', 0)
    
    if not route:
        return redirect(url_for('home'))
    
    # Geocodifica endereços para mostrar no mapa
    locations = []
    for i, delivery in enumerate(route):
        # Por enquanto usando coordenadas simuladas para São Paulo
        # Na versão real, usaria geocoding da Google API
        base_lat = -23.5505 + (i * 0.01)  # Simula diferentes localizações
        base_lng = -46.6333 + (i * 0.01)
        locations.append({
            'index': i,
            'address': delivery['address'],
            'lat': base_lat,
            'lng': base_lng,
            'status': delivery.get('status', 'pending'),
            'is_current': i == current_index
        })
    
    return render_template('map.html', 
                         locations=locations,
                         current_index=current_index,
                         total=len(route))

@app.route('/api/directions')
def get_directions():
    """API para obter direções entre pontos"""
    origin = request.args.get('origin')
    destination = request.args.get('destination')
    
    if not origin or not destination:
        return jsonify({'error': 'Origin e destination são obrigatórios'}), 400
    
    # Por enquanto retorna direções simuladas
    # Na versão real, usaria Google Directions API
    directions = {
        'routes': [{
            'legs': [{
                'distance': {'text': '2.5 km', 'value': 2500},
                'duration': {'text': '8 mins', 'value': 480},
                'steps': [
                    {
                        'instruction': f'Siga pela {origin} em direção à {destination}',
                        'distance': {'text': '2.5 km', 'value': 2500},
                        'duration': {'text': '8 mins', 'value': 480}
                    }
                ]
            }]
        }]
    }
    
    return jsonify(directions)

@app.route('/api/geocode')
def geocode_address():
    """API para geocodificar endereços"""
    address = request.args.get('address')
    if not address:
        return jsonify({'error': 'Endereço é obrigatório'}), 400
    
    # Simulação - na versão real usaria Google Geocoding API  
    simulated_coords = {
        'lat': -23.5505 + (hash(address) % 100) * 0.001,
        'lng': -46.6333 + (hash(address) % 100) * 0.001
    }
    
    return jsonify({
        'results': [{
            'geometry': {
                'location': simulated_coords
            },
            'formatted_address': address
        }]
    })

@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        data = request.json
        session['valor_entrega'] = float(data.get('valor_entrega', 8.0))
        session['custo_km'] = float(data.get('custo_km', 0.5))
        return jsonify({'success': True})
    
    return render_template('config.html', 
                         valor_entrega=session.get('valor_entrega', 8.0),
                         custo_km=session.get('custo_km', 0.5))

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "Entregador App",
        "short_name": "Entregador",
        "description": "App pessoal para controle de entregas",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#007bff",
        "icons": [
            {
                "src": "/static/icon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/icon-512.png", 
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
