"""
📦 GERENCIADOR DE ESTADO - Sessões de Admin e Entregadores
Controla fluxo de importação de romaneios, divisão de rotas e tracking
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum
import uuid
from .clustering import DeliveryPoint, Cluster

class RouteStatus(str, Enum):
    PENDING = "pending"
    SEPARATING = "separating"
    READY = "ready"
    IN_TRANSIT = "in_transit"
    COMPLETED = "completed"

@dataclass
class Romaneio:
    """Romaneio importado"""
    id: str
    uploaded_at: datetime
    points: List[DeliveryPoint]
    filename: str = ""  # Nome do arquivo ou "Manual" se digitado
    
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
    status: RouteStatus = RouteStatus.PENDING
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
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
            from .services.osrm_service import get_route_distance_km
        except Exception:
            return 0.0

        if not self.optimized_order:
            return 0.0

        coords = [(p.lat, p.lng) for p in self.optimized_order]
        osrm_distance = get_route_distance_km(coords)
        if osrm_distance is not None:
            return round(osrm_distance, 2)

        distance = 0.0
        hops = self.optimized_order
        for prev, curr in zip(hops, hops[1:]):
            distance += haversine_distance(prev.lat, prev.lng, curr.lat, curr.lng)
        return round(distance, 2)
    
    def mark_as_delivered(self, package_id: str):
        if package_id not in self.delivered_packages:
            self.delivered_packages.append(package_id)
    
    def mark_as_failed(self, package_id: str):
        """Marca pacote como insucesso (não entregue)"""
        # Remove de delivered se estava lá
        if package_id in self.delivered_packages:
            self.delivered_packages.remove(package_id)
        # Atualiza status do ponto
        for point in self.optimized_order:
            if hasattr(point, 'package_id') and point.package_id == package_id:
                point.status = 'failed'
            elif hasattr(point, 'id') and point.id == package_id:
                point.status = 'failed'
    
    def mark_as_returned(self, package_id: str):
        """Marca pacote como devolvido"""
        if package_id in self.delivered_packages:
            self.delivered_packages.remove(package_id)
        for point in self.optimized_order:
            if hasattr(point, 'package_id') and point.package_id == package_id:
                point.status = 'returned'
            elif hasattr(point, 'id') and point.id == package_id:
                point.status = 'returned'


@dataclass
class DailySession:
    """Sessão do dia (uma por dia de trabalho)"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])  # ID único
    session_name: str = ''  # 🆕 "Segunda Manhã", "Terça Tarde"
    date: str = ''  # YYYY-MM-DD
    period: str = ''  # 🆕 "manhã" ou "tarde"
    created_at: datetime = field(default_factory=datetime.now)
    base_address: str = ''
    base_lat: float = 0.0
    base_lng: float = 0.0
    romaneios: List[Romaneio] = field(default_factory=list)
    routes: List[Route] = field(default_factory=list)
    is_finalized: bool = False
    finalized_at: Optional[datetime] = None
    current_step: str = 'idle'  # idle, importing, imported, optimizing, optimized, assigning, assigned, separating, completed
    route_value: float = 0.0  # Valor total da rota
    num_deliverers: int = 0  # Número de entregadores pra otimização
    
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
            
            latest_active_session = None
            for s_info in sessions:
                try:
                    session = session_store.load_session(s_info['session_id'])
                    if session:
                        self.active_sessions[session.session_id] = session
                        if not session.is_finalized:
                            if not latest_active_session or session.created_at > latest_active_session.created_at:
                                latest_active_session = session
                except Exception as load_err:
                    print(f"⚠️ Erro ao carregar sessão {s_info.get('session_id', '?')}: {load_err}")
                    continue
            
            if latest_active_session:
                self.current_session_id = latest_active_session.session_id
                print(f"📌 Sessão ativa restaurada: {latest_active_session.session_name} ({latest_active_session.session_id})")
                    
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
    
    def create_new_session(self, date: str, period: str = 'manhã') -> DailySession:
        """
        Cria nova sessão com nome automático
        
        Args:
            date: Data no formato YYYY-MM-DD
            period: 'manhã' ou 'tarde'
        
        Returns:
            DailySession criada
        """
        from datetime import datetime as dt
        from .database import generate_session_name
        
        # Converte string para datetime
        date_obj = dt.strptime(date, '%Y-%m-%d')
        
        # Gera nome automático
        session_name = generate_session_name(date_obj, period)
        
        session = DailySession(
            date=date,
            session_name=session_name,
            period=period
        )
        self.active_sessions[session.session_id] = session
        self.current_session_id = session.session_id
        self._auto_save(session)
        
        print(f"✅ Sessão criada: {session_name} ({session.session_id})")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[DailySession]:
        """Retorna sessão específica por ID"""
        return self.active_sessions.get(session_id)

    def save_session(self, session: DailySession, set_as_current: bool = True):
        """Salva explicitamente a sessão e opcionalmente define como atual"""
        if session:
            self.active_sessions[session.session_id] = session
            if set_as_current:
                self.current_session_id = session.session_id
            self._auto_save(session)
    
    def get_current_session(self) -> Optional[DailySession]:
        """Retorna sessão atual em foco"""
        if self.current_session_id:
            return self.active_sessions.get(self.current_session_id)
        return None

    def get_active_session(self) -> Optional[DailySession]:
        """Retorna a sessão ativa em foco.

        Comportamento estendido: se `current_session_id` não estiver setada,
        tenta retornar a última sessão não finalizada disponível. Isso evita
        que partes do sistema (entregadores, separação, mapa) falhem quando
        a aba de Análise for liberada (release_session_from_analysis).
        """
        # Se houver sessão explicitamente em foco, retorna ela
        if self.current_session_id:
            sess = self.active_sessions.get(self.current_session_id)
            if sess:
                return sess

        # Senão, buscar a última sessão não finalizada (mais recente)
        candidates = [s for s in self.active_sessions.values() if not s.is_finalized]
        if not candidates:
            return None
        candidates.sort(key=lambda x: x.created_at, reverse=True)
        return candidates[0]
    
    def set_current_session(self, session_id: str):
        """Define qual sessão está em foco"""
        if session_id in self.active_sessions:
            self.current_session_id = session_id
    
    def delete_session(self, session_id: str, force: bool = False) -> bool:
        """
        Exclui permanentemente uma sessão e seus dados.
        SEM restrição: permite deletar qualquer sessão, mesmo com rotas ativas ou não finalizadas.
        """
        try:
            from .session_persistence import session_store

            session = self.active_sessions.get(session_id)
            if not session:
                # Ainda tenta remover da persistência mesmo que não esteja na memória
                return session_store.delete_session(session_id)

            # Remove da memória
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]

            # Se era a sessão atual, limpa
            if self.current_session_id == session_id:
                self.current_session_id = None

            # Remove da persistência (DB/Disco)
            return session_store.delete_session(session_id)
        except Exception as e:
            print(f"⚠️ Erro ao excluir sessão {session_id}: {e}")
            raise

    def release_session_from_analysis(self, session_id: str) -> bool:
        """
        Libera a aba 'Análise' sem deletar a sessão.

        Apenas desassocia a sessão do foco atual (`current_session_id`) para que o
        frontend possa iniciar um novo romaneio/analise, mantendo a sessão
        ativa para mapa/separação/entregadores.
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return False

        if self.current_session_id == session_id:
            self.current_session_id = None
            # salva estado (não finaliza a sessão)
            try:
                self._auto_save(session)
            except Exception:
                pass
        return True

    def list_sessions(self, finalized_only: bool = False) -> List[DailySession]:
        """Lista todas as sessões carregadas"""
        sessions = list(self.active_sessions.values())
        
        if finalized_only:
            sessions = [s for s in sessions if s.is_finalized]
        
        # Ordena por data de criação (mais recente primeiro)
        sessions.sort(key=lambda x: x.created_at, reverse=True)
        return sessions
        def get_all_sessions(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[DailySession]:
            """
            Retorna todas as sessões, opcionalmente filtradas por data
        
            Args:
                start_date: Data inicial (YYYY-MM-DD), inclusive
                end_date: Data final (YYYY-MM-DD), inclusive
        
            Returns:
                Lista de DailySession ordenadas por data (mais recente primeiro)
            """
            from datetime import datetime as dt
        
            sessions = list(self.active_sessions.values())
        
            # Filtrar por data se especificada
            if start_date or end_date:
                try:
                    start_dt = dt.strptime(start_date, '%Y-%m-%d') if start_date else dt.min
                    end_dt = dt.strptime(end_date, '%Y-%m-%d') if end_date else dt.max
                
                    sessions = [
                        s for s in sessions
                        if start_dt <= dt.strptime(s.date, '%Y-%m-%d') <= end_dt
                    ]
                except ValueError as e:
                    print(f"⚠️ Erro ao parsear datas: {e}")
                    return []
        
            # Ordena por data de criação (mais recente primeiro)
            sessions.sort(key=lambda x: x.created_at, reverse=True)
            return sessions
    
    
    @property
    def sessions(self) -> List[DailySession]:
        """Alias para compatibilidade - retorna lista de sessões"""
        return list(self.active_sessions.values())
    
    @sessions.setter
    def sessions(self, value: List[DailySession]):
        """Permite setar sessions diretamente (usado ao deletar)"""
        self.active_sessions = {s.session_id: s for s in value}
    
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
    
    def assign_route(self, route_id: str, deliverer_id: int, session_id: Optional[str] = None) -> bool:
        """Atribui rota a entregador"""
        session = self.get_session(session_id) if session_id else self.get_current_session()
        if not session:
            return False
        
        for route in session.routes:
            if route.id == route_id:
                route.assigned_to_telegram_id = deliverer_id
                # Tenta carregar nome do entregador
                try:
                    from .services.deliverer_service import DelivererService
                    deliverer = DelivererService.get_deliverer(deliverer_id)
                    if deliverer:
                        route.assigned_to_name = deliverer.name
                except Exception:
                    pass
                
                self._auto_save(session)
                return True
        
        return False
    
    def get_route_for_deliverer(self, telegram_id: int, session_id: Optional[str] = None) -> Optional[Route]:
        """Retorna rota atribuída a um entregador"""
        session = self.get_session(session_id) if session_id else self.get_current_session()
        if not session:
            return None
        
        return next((r for r in session.routes if r.assigned_to_telegram_id == telegram_id), None)
    
    def mark_package_delivered(self, telegram_id: int, package_id: str, session_id: Optional[str] = None) -> bool:
        """Marca pacote como entregue e finaliza sessão automaticamente se todos os pacotes baixados"""
        route = self.get_route_for_deliverer(telegram_id, session_id)
        if route:
            route.mark_as_delivered(package_id)
            session = self.get_session(session_id) if session_id else self.get_current_session()
            if session:
                # Verifica se todos os pacotes de todas as rotas estão baixados (entregue, insucesso ou transferido)
                all_finalized = all(r.delivered_count >= r.total_packages for r in session.routes)
                if all_finalized and not session.is_finalized:
                    session.is_finalized = True
                    session.finalized_at = datetime.now()
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
