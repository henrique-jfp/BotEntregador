"""
📦 GERENCIADOR DE ESTADO - Sessões de Admin e Entregadores
Controla fluxo de importação de romaneios, divisão de rotas e tracking
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import uuid
from .clustering import DeliveryPoint, Cluster


@dataclass
class Romaneio:
    """Romaneio importado"""
    id: str
    uploaded_at: datetime
    points: List[DeliveryPoint]
    
    @property
    def total_packages(self) -> int:
        return len(self.points)


@dataclass
class Route:
    """Rota atribuída a um entregador"""
    id: str
    cluster: Cluster
    assigned_to_telegram_id: Optional[int] = None
    assigned_to_name: Optional[str] = None
    color: str = '#667eea'  # Cor única do entregador
    optimized_order: List[DeliveryPoint] = field(default_factory=list)
    delivered_packages: List[str] = field(default_factory=list)  # package_ids
    map_file: Optional[str] = None  # Caminho do mapa HTML gerado
    
    @property
    def total_packages(self) -> int:
        return len(self.optimized_order)
    
    @property
    def delivered_count(self) -> int:
        return len(self.delivered_packages)
    
    @property
    def pending_count(self) -> int:
        return self.total_packages - self.delivered_count
    
    @property
    def completion_rate(self) -> float:
        return (self.delivered_count / self.total_packages * 100) if self.total_packages > 0 else 0

    @property
    def total_distance_km(self) -> float:
        """Distância estimada somando hops da rota (fallback quando não há valor calculado)."""
        try:
            from .clustering import haversine_distance
        except Exception:
            return 0.0

        if not self.optimized_order:
            return 0.0

        distance = 0.0
        hops = self.optimized_order
        for prev, curr in zip(hops, hops[1:]):
            distance += haversine_distance(prev.lat, prev.lng, curr.lat, curr.lng)
        return round(distance, 2)
    
    def mark_as_delivered(self, package_id: str):
        if package_id not in self.delivered_packages:
            self.delivered_packages.append(package_id)


@dataclass
class DailySession:
    """Sessão do dia (uma por dia de trabalho)"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])  # ID único
    date: str = ''  # YYYY-MM-DD
    created_at: datetime = field(default_factory=datetime.now)
    base_address: str = ''
    base_lat: float = 0.0
    base_lng: float = 0.0
    romaneios: List[Romaneio] = field(default_factory=list)
    routes: List[Route] = field(default_factory=list)
    is_finalized: bool = False
    finalized_at: Optional[datetime] = None
    
    @property
    def total_packages(self) -> int:
        return sum(r.total_packages for r in self.romaneios)
    
    @property
    def total_delivered(self) -> int:
        return sum(r.delivered_count for r in self.routes)
    
    @property
    def total_pending(self) -> int:
        return sum(r.pending_count for r in self.routes)


class SessionManager:
    """Gerencia múltiplas sessões com auto-save"""
    
    def __init__(self):
        self.active_sessions: Dict[str, DailySession] = {}  # session_id -> DailySession
        self.current_session_id: Optional[str] = None  # Sessão em foco
        self.admin_state: Dict[int, str] = {}  # telegram_id -> estado do fluxo
        self.temp_data: Dict[int, Dict] = {}   # Dados temporários do admin
        self._load_all_sessions()
    
    def _load_all_sessions(self):
        """Carrega todas as sessões do disco na inicialização"""
        try:
            from .session_persistence import session_store
            sessions = session_store.list_sessions(limit=100)
            
            for s_info in sessions:
                try:
                    session = session_store.load_session(s_info['session_id'])
                    if session:
                        self.active_sessions[session.session_id] = session
                except Exception as load_err:
                    print(f"⚠️ Erro ao carregar sessão {s_info.get('session_id', '?')}: {load_err}")
                    continue
                    
            print(f"✅ {len(self.active_sessions)} sessões carregadas do disco")
        except ImportError as e:
            print(f"⚠️ session_persistence não disponível: {e}")
        except Exception as e:
            print(f"⚠️ Erro ao carregar sessões (continuando sem histórico): {e}")
            import traceback
            traceback.print_exc()
    
    def _auto_save(self, session: DailySession):
        """Auto-save da sessão"""
        try:
            from .session_persistence import session_store
            session_store.save_session(session)
        except Exception as e:
            print(f"⚠️ Erro ao salvar sessão: {e}")
    
    def create_new_session(self, date: str) -> DailySession:
        """Cria nova sessão (permite múltiplas sessões simultâneas)"""
        session = DailySession(date=date)
        self.active_sessions[session.session_id] = session
        self.current_session_id = session.session_id
        self._auto_save(session)
        return session
    
    def get_session(self, session_id: str) -> Optional[DailySession]:
        """Retorna sessão específica por ID"""
        return self.active_sessions.get(session_id)
    
    def get_current_session(self) -> Optional[DailySession]:
        """Retorna sessão atual em foco"""
        if self.current_session_id:
            return self.active_sessions.get(self.current_session_id)
        return None
    
    def set_current_session(self, session_id: str):
        """Define qual sessão está em foco"""
        if session_id in self.active_sessions:
            self.current_session_id = session_id
    
    def list_sessions(self, finalized_only: bool = False) -> List[DailySession]:
        """Lista todas as sessões carregadas"""
        sessions = list(self.active_sessions.values())
        
        if finalized_only:
            sessions = [s for s in sessions if s.is_finalized]
        
        # Ordena por data de criação (mais recente primeiro)
        sessions.sort(key=lambda x: x.created_at, reverse=True)
        return sessions
    
    def add_romaneio(self, romaneio: Romaneio, session_id: Optional[str] = None):
        """Adiciona romaneio à sessão"""
        session = self.get_session(session_id) if session_id else self.get_current_session()
        if session:
            session.romaneios.append(romaneio)
            self._auto_save(session)
    
    def set_base_location(self, address: str, lat: float, lng: float, session_id: Optional[str] = None):
        """Define base do dia"""
        session = self.get_session(session_id) if session_id else self.get_current_session()
        if session:
            session.base_address = address
            session.base_lat = lat
            session.base_lng = lng
            self._auto_save(session)
    
    def set_routes(self, routes: List[Route], session_id: Optional[str] = None):
        """Define rotas divididas"""
        session = self.get_session(session_id) if session_id else self.get_current_session()
        if session:
            session.routes = routes
            self._auto_save(session)
    
    def finalize_session(self, session_id: Optional[str] = None):
        """Fecha sessão (não pode adicionar mais romaneios)"""
        session = self.get_session(session_id) if session_id else self.get_current_session()
        if session:
            session.is_finalized = True
            session.finalized_at = datetime.now()
            self._auto_save(session)
    
    def get_route_for_deliverer(self, telegram_id: int, session_id: Optional[str] = None) -> Optional[Route]:
        """Retorna rota atribuída a um entregador"""
        session = self.get_session(session_id) if session_id else self.get_current_session()
        if not session:
            return None
        
        return next((r for r in session.routes if r.assigned_to_telegram_id == telegram_id), None)
    
    def mark_package_delivered(self, telegram_id: int, package_id: str, session_id: Optional[str] = None) -> bool:
        """Marca pacote como entregue"""
        route = self.get_route_for_deliverer(telegram_id, session_id)
        if route:
            route.mark_as_delivered(package_id)
            session = self.get_session(session_id) if session_id else self.get_current_session()
            if session:
                self._auto_save(session)
            return True
        return False
    
    # Estados de admin
    def set_admin_state(self, telegram_id: int, state: str):
        self.admin_state[telegram_id] = state
    
    def get_admin_state(self, telegram_id: int) -> Optional[str]:
        return self.admin_state.get(telegram_id)
    
    def clear_admin_state(self, telegram_id: int):
        self.admin_state.pop(telegram_id, None)
        self.temp_data.pop(telegram_id, None)
    
    def save_temp_data(self, telegram_id: int, key: str, value):
        if telegram_id not in self.temp_data:
            self.temp_data[telegram_id] = {}
        self.temp_data[telegram_id][key] = value
    
    def get_temp_data(self, telegram_id: int, key: str):
        return self.temp_data.get(telegram_id, {}).get(key)


# Instância global (singleton)
session_manager = SessionManager()
