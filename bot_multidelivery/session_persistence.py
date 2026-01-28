"""
💾 PERSISTÊNCIA DE SESSÕES - Auto-save em JSON
Salva sessões automaticamente com histórico completo
"""
import json
import os
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from .session import DailySession, Route, Romaneio, DeliveryPoint


class SessionStore:
    """Gerencia persistência de sessões em disco"""
    
    def __init__(self, data_dir: str = "data"):
        self.sessions_dir = Path(data_dir) / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def _session_file(self, session_id: str) -> Path:
        """Path do arquivo da sessão"""
        return self.sessions_dir / f"{session_id}.json"
    
    def save_session(self, session: DailySession):
        """Salva sessão em disco (auto-save)"""
        try:
            # Garante que diretório existe
            self.sessions_dir.mkdir(parents=True, exist_ok=True)
            
            data = {
                'session_id': session.session_id,
                'date': session.date,
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
                                'id': p.id,
                                'address': p.address,
                                'lat': p.lat,
                                'lng': p.lng,
                                'weight': p.weight,
                                'notes': p.notes
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
                                'id': p.id,
                                'address': p.address,
                                'lat': p.lat,
                                'lng': p.lng,
                                'weight': p.weight,
                                'notes': p.notes
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
        """Carrega sessão do disco"""
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
                    id=p['id'],
                    address=p['address'],
                    lat=p['lat'],
                    lng=p['lng'],
                    weight=p.get('weight', 1.0),
                    notes=p.get('notes', '')
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
                    id=p['id'],
                    address=p['address'],
                    lat=p['lat'],
                    lng=p['lng'],
                    weight=p.get('weight', 1.0),
                    notes=p.get('notes', '')
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
            date=data['date'],
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
