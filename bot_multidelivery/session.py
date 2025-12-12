"""
📦 GERENCIADOR DE ESTADO - Sessões de Admin e Entregadores
Controla fluxo de importação de romaneios, divisão de rotas e tracking
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
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
    optimized_order: List[DeliveryPoint] = field(default_factory=list)
    delivered_packages: List[str] = field(default_factory=list)  # package_ids
    
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
    
    def mark_as_delivered(self, package_id: str):
        if package_id not in self.delivered_packages:
            self.delivered_packages.append(package_id)


@dataclass
class DailySession:
    """Sessão do dia (uma por dia de trabalho)"""
    date: str  # YYYY-MM-DD
    base_address: str
    base_lat: float
    base_lng: float
    romaneios: List[Romaneio] = field(default_factory=list)
    routes: List[Route] = field(default_factory=list)
    is_finalized: bool = False
    
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
    """Gerencia sessões ativas"""
    
    def __init__(self):
        self.active_session: Optional[DailySession] = None
        self.admin_state: Dict[int, str] = {}  # telegram_id -> estado do fluxo
        self.temp_data: Dict[int, Dict] = {}   # Dados temporários do admin
    
    def start_new_session(self, date: str) -> DailySession:
        """Inicia nova sessão do dia"""
        self.active_session = DailySession(
            date=date,
            base_address="",
            base_lat=0.0,
            base_lng=0.0
        )
        return self.active_session
    
    def get_active_session(self) -> Optional[DailySession]:
        return self.active_session
    
    def add_romaneio(self, romaneio: Romaneio):
        """Adiciona romaneio à sessão ativa"""
        if self.active_session:
            self.active_session.romaneios.append(romaneio)
    
    def set_base_location(self, address: str, lat: float, lng: float):
        """Define base do dia"""
        if self.active_session:
            self.active_session.base_address = address
            self.active_session.base_lat = lat
            self.active_session.base_lng = lng
    
    def set_routes(self, routes: List[Route]):
        """Define rotas divididas"""
        if self.active_session:
            self.active_session.routes = routes
    
    def finalize_session(self):
        """Fecha sessão (não pode adicionar mais romaneios)"""
        if self.active_session:
            self.active_session.is_finalized = True
    
    def get_route_for_deliverer(self, telegram_id: int) -> Optional[Route]:
        """Retorna rota atribuída a um entregador"""
        if not self.active_session:
            return None
        
        return next((r for r in self.active_session.routes if r.assigned_to_telegram_id == telegram_id), None)
    
    def mark_package_delivered(self, telegram_id: int, package_id: str) -> bool:
        """Marca pacote como entregue"""
        route = self.get_route_for_deliverer(telegram_id)
        if route:
            route.mark_as_delivered(package_id)
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
