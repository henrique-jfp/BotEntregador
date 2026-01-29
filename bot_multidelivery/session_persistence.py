"""
💾 PERSISTÊNCIA DE SESSÕES - Auto-save em PostgreSQL ou JSON
Salva sessões automaticamente com histórico completo
"""
import json
import os
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from .session import DailySession, Route, Romaneio, DeliveryPoint

try:
    from .database import db_manager, SessionDB, RouteDB
    HAS_DATABASE = db_manager.is_connected
except Exception as e:
    print(f"⚠️ Database import failed: {e}")
    HAS_DATABASE = False


class SessionStore:
    """Gerencia persistência de sessões em disco ou PostgreSQL"""
    
    def __init__(self, data_dir: str = "data"):
        self.sessions_dir = Path(data_dir) / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        self.using_database = HAS_DATABASE
        if self.using_database:
            print("✅ SessionStore usando PostgreSQL")
        else:
            print("📁 SessionStore usando JSON local")
    
    def _session_file(self, session_id: str) -> Path:
        """Path do arquivo da sessão"""
        return self.sessions_dir / f"{session_id}.json"
    
    def save_session(self, session: DailySession):
        """Salva sessão em disco ou PostgreSQL (auto-save)"""
        if self.using_database:
            # Salva no PostgreSQL
            try:
                with db_manager.get_session() as db_session:
                    # Serializa romaneios para JSON
                    romaneios_data = [
                        {
                            'id': r.id,
                            'uploaded_at': r.uploaded_at.isoformat(),
                            'points': [
                                {
                                    'package_id': p.package_id,
                                    'romaneio_id': p.romaneio_id,
                                    'address': p.address,
                                    'lat': p.lat,
                                    'lng': p.lng,
                                    'priority': p.priority
                                } for p in r.points
                            ]
                        } for r in session.romaneios
                    ]
                    
                    # Verifica se sessão já existe
                    session_db = db_session.query(SessionDB).filter_by(session_id=session.session_id).first()
                    
                    if session_db:
                        # Atualiza existente
                        session_db.session_name = session.session_name
                        session_db.date = session.date
                        session_db.period = session.period
                        session_db.base_address = session.base_address
                        session_db.base_lat = session.base_lat
                        session_db.base_lng = session.base_lng
                        session_db.is_finalized = session.is_finalized
                        session_db.finalized_at = session.finalized_at
                        session_db.romaneios_data = romaneios_data
                        
                        # Remove rotas antigas
                        db_session.query(RouteDB).filter_by(session_id=session.session_id).delete()
                    else:
                        # Cria nova
                        session_db = SessionDB(
                            session_id=session.session_id,
                            session_name=session.session_name,
                            date=session.date,
                            period=session.period,
                            created_at=session.created_at,
                            base_address=session.base_address,
                            base_lat=session.base_lat,
                            base_lng=session.base_lng,
                            is_finalized=session.is_finalized,
                            finalized_at=session.finalized_at,
                            romaneios_data=romaneios_data
                        )
                        db_session.add(session_db)
                    
                    # Salva rotas
                    for route in session.routes:
                        route_db = RouteDB(
                            id=route.id,
                            session_id=session.session_id,
                            assigned_to_telegram_id=route.assigned_to_telegram_id,
                            assigned_to_name=route.assigned_to_name,
                            color=route.color,
                            map_file=route.map_file,
                            optimized_order=[
                                {
                                    'package_id': p.package_id,
                                    'romaneio_id': p.romaneio_id,
                                    'address': p.address,
                                    'lat': p.lat,
                                    'lng': p.lng,
                                    'priority': p.priority
                                } for p in route.optimized_order
                            ],
                            delivered_packages=route.delivered_packages
                        )
                        db_session.add(route_db)
                    
                return
            except Exception as e:
                print(f"⚠️ Erro ao salvar sessão no PostgreSQL: {e}, usando fallback JSON")
        
        # Fallback: JSON
        try:
            # Garante que diretório existe
            self.sessions_dir.mkdir(parents=True, exist_ok=True)
            
            data = {
                'session_id': session.session_id,
                'session_name': session.session_name,
                'date': session.date,
                'period': session.period,
                'created_at': session.created_at.isoformat(),
                'base_address': session.base_address,
                'base_lat': session.base_lat,
                'base_lng': session.base_lng,
                'is_finalized': session.is_finalized,
                'finalized_at': session.finalized_at.isoformat() if session.finalized_at else None,
                'romaneios': [
                    {
                        'id': r.id,
                        'uploaded_at': r.uploaded_at.isoformat(),
                        'points': [
                            {
                                'package_id': p.package_id,
                                'romaneio_id': p.romaneio_id,
                                'address': p.address,
                                'lat': p.lat,
                                'lng': p.lng,
                                'priority': p.priority
                            } for p in r.points
                        ]
                    } for r in session.romaneios
                ],
                'routes': [
                    {
                        'id': r.id,
                        'assigned_to_telegram_id': r.assigned_to_telegram_id,
                        'assigned_to_name': r.assigned_to_name,
                        'color': r.color,
                        'optimized_order': [
                            {
                                'package_id': p.package_id,
                                'romaneio_id': p.romaneio_id,
                                'address': p.address,
                                'lat': p.lat,
                                'lng': p.lng,
                                'priority': p.priority
                            } for p in r.optimized_order
                        ],
                        'delivered_packages': r.delivered_packages,
                        'map_file': r.map_file
                    } for r in session.routes
                ]
            }
            
            file_path = self._session_file(session.session_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Erro ao salvar sessão {session.session_id}: {e}")
            import traceback
            traceback.print_exc()
    
    def load_session(self, session_id: str) -> Optional[DailySession]:
        """Carrega sessão do PostgreSQL ou disco"""
        if self.using_database:
            # Carrega do PostgreSQL
            try:
                with db_manager.get_session() as db_session:
                    session_db = db_session.query(SessionDB).filter_by(session_id=session_id).first()
                    
                    if not session_db:
                        return None
                    
                    # Reconstrói romaneios
                    romaneios = []
                    for r_data in (session_db.romaneios_data or []):
                        points = [
                            DeliveryPoint(
                                package_id=p['package_id'],
                                romaneio_id=p['romaneio_id'],
                                address=p['address'],
                                lat=p['lat'],
                                lng=p['lng'],
                                priority=p.get('priority', 'normal')
                            ) for p in r_data['points']
                        ]
                        romaneios.append(Romaneio(
                            id=r_data['id'],
                            uploaded_at=datetime.fromisoformat(r_data['uploaded_at']),
                            points=points
                        ))
                    
                    # Reconstrói rotas
                    routes = []
                    for route_db in session_db.routes:
                        optimized = [
                            DeliveryPoint(
                                package_id=p['package_id'],
                                romaneio_id=p['romaneio_id'],
                                address=p['address'],
                                lat=p['lat'],
                                lng=p['lng'],
                                priority=p.get('priority', 'normal')
                            ) for p in (route_db.optimized_order or [])
                        ]
                        
                        route = Route(
                            id=route_db.id,
                            cluster=None,
                            assigned_to_telegram_id=route_db.assigned_to_telegram_id,
                            assigned_to_name=route_db.assigned_to_name,
                            color=route_db.color,
                            optimized_order=optimized,
                            delivered_packages=route_db.delivered_packages or [],
                            map_file=route_db.map_file
                        )
                        routes.append(route)
                    
                    return DailySession(
                        session_id=session_db.session_id,
                        session_name=session_db.session_name or '',
                        date=session_db.date,
                        period=session_db.period or '',
                        created_at=session_db.created_at,
                        base_address=session_db.base_address,
                        base_lat=session_db.base_lat,
                        base_lng=session_db.base_lng,
                        romaneios=romaneios,
                        routes=routes,
                        is_finalized=session_db.is_finalized,
                        finalized_at=session_db.finalized_at
                    )
            except Exception as e:
                print(f"⚠️ Erro ao carregar sessão do PostgreSQL: {e}, tentando JSON")
        
        # Fallback: JSON
        file_path = self._session_file(session_id)
        
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reconstrói objetos
        romaneios = []
        for r_data in data.get('romaneios', []):
            points = [
                DeliveryPoint(
                    package_id=p['package_id'],
                    romaneio_id=p['romaneio_id'],
                    address=p['address'],
                    lat=p['lat'],
                    lng=p['lng'],
                    priority=p.get('priority', 'normal')
                ) for p in r_data['points']
            ]
            romaneios.append(Romaneio(
                id=r_data['id'],
                uploaded_at=datetime.fromisoformat(r_data['uploaded_at']),
                points=points
            ))
        
        routes = []
        for r_data in data.get('routes', []):
            optimized = [
                DeliveryPoint(
                    package_id=p['package_id'],
                    romaneio_id=p['romaneio_id'],
                    address=p['address'],
                    lat=p['lat'],
                    lng=p['lng'],
                    priority=p.get('priority', 'normal')
                ) for p in r_data['optimized_order']
            ]
            
            route = Route(
                id=r_data['id'],
                cluster=None,  # Cluster não precisa ser reconstruído
                assigned_to_telegram_id=r_data.get('assigned_to_telegram_id'),
                assigned_to_name=r_data.get('assigned_to_name'),
                color=r_data.get('color', '#667eea'),
                optimized_order=optimized,
                delivered_packages=r_data.get('delivered_packages', []),
                map_file=r_data.get('map_file')
            )
            routes.append(route)
        
        session = DailySession(
            session_id=data['session_id'],
            session_name=data.get('session_name', ''),
            date=data['date'],
            period=data.get('period', ''),
            created_at=datetime.fromisoformat(data['created_at']),
            base_address=data['base_address'],
            base_lat=data['base_lat'],
            base_lng=data['base_lng'],
            romaneios=romaneios,
            routes=routes,
            is_finalized=data.get('is_finalized', False),
            finalized_at=datetime.fromisoformat(data['finalized_at']) if data.get('finalized_at') else None
        )
        
        return session
    
    def list_sessions(self, limit: int = 20) -> List[Dict]:
        """Lista todas as sessões (mais recentes primeiro)"""
        sessions = []
        
        try:
            # Garante que diretório existe
            if not self.sessions_dir.exists():
                return []
            
            for file_path in self.sessions_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    sessions.append({
                        'session_id': data['session_id'],
                        'date': data['date'],
                        'created_at': datetime.fromisoformat(data['created_at']),
                        'is_finalized': data.get('is_finalized', False),
                        'total_packages': sum(len(r['points']) for r in data.get('romaneios', [])),
                        'num_routes': len(data.get('routes', []))
                    })
                except Exception as e:
                    print(f"⚠️ Erro ao carregar {file_path}: {e}")
                    continue
            
            # Ordena por data de criação (mais recente primeiro)
            sessions.sort(key=lambda x: x['created_at'], reverse=True)
            
            return sessions[:limit]
        except Exception as e:
            print(f"⚠️ Erro ao listar sessões: {e}")
            return []
    
    def delete_session(self, session_id: str) -> bool:
        """Deleta sessão do disco"""
        file_path = self._session_file(session_id)
        
        if file_path.exists():
            file_path.unlink()
            return True
        return False


# Instância global
session_store = SessionStore()
