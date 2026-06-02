"""
📦 MODELOS DE DADOS - Sistema Multi-Entregador
Define estruturas de dados escaláveis
"""

from dataclasses import dataclass, field
from typing import List, Tuple

# --- MODELOS DE ENTREGA E CLUSTERIZAÇÃO ---
@dataclass
class DeliveryPoint:
    """Ponto de entrega individual (um pacote)"""
    address: str
    lat: float
    lng: float
    romaneio_id: str
    package_id: str
    priority: str = "normal"  # low, normal, high, urgent
    bairro: str = ""  # bairro/colonia opcional (melhora o geocoding)

@dataclass
class DeliveryStop:
    """
    Uma PARADA na rota (pode ter múltiplos pacotes no mesmo endereço)
    Exemplo: 5 pacotes para "Rua X, 123" = 1 parada com 5 pacotes
    Numeração sequencial: 1, 2, 3... SEM PULAR NÚMEROS
    """
    stop_number: int  # Número sequencial da parada: 1, 2, 3...
    address: str
    lat: float
    lng: float
    packages: List[DeliveryPoint] = field(default_factory=list)

    @property
    def package_count(self) -> int:
        return len(self.packages)

    @property
    def package_ids(self) -> List[str]:
        return [p.package_id for p in self.packages]

    def __repr__(self):
        return f"Stop#{self.stop_number} ({self.package_count} pkgs) - {self.address[:40]}"

@dataclass
class Cluster:
    """Cluster geográfico de entregas (território de um entregador)"""
    id: int
    center_lat: float
    center_lng: float
    points: List[DeliveryPoint]
    stops: List[DeliveryStop] = field(default_factory=list)

    @property
    def total_packages(self) -> int:
        return len(self.points)

    @property
    def total_stops(self) -> int:
        return len(self.stops) if self.stops else len(self._unique_locations())

    @property
    def centroid(self) -> Tuple[float, float]:
        return (self.center_lat, self.center_lng)

    def _unique_locations(self) -> set:
        return set((round(p.lat, 4), round(p.lng, 4)) for p in self.points)

    def distance_to_base(self, base_lat: float, base_lng: float) -> float:
        # Função dummy, implemente a real se necessário
        from math import radians, cos, sin, asin, sqrt
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371  # km
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
            c = 2 * asin(sqrt(a))
            return R * c
        return haversine(self.center_lat, self.center_lng, base_lat, base_lng)
from datetime import datetime
from typing import Optional, List
from enum import Enum


class PackagePriority(Enum):
    """Prioridade de entrega"""
    LOW = "baixa"
    NORMAL = "normal"
    HIGH = "alta"
    URGENT = "urgente"


class PackageStatus(Enum):
    """Status do pacote"""
    PENDING = "pendente"
    IN_TRANSIT = "em_transito"
    DELIVERED = "entregue"
    FAILED = "falhou"
    TRANSFER_REQUEST = "solicitacao_transferencia"


@dataclass
class Package:
    """Pacote individual com todos os metadados"""
    id: str
    address: str
    lat: float
    lng: float
    priority: PackagePriority = PackagePriority.NORMAL
    status: PackageStatus = PackageStatus.PENDING
    assigned_to: Optional[str] = None
    delivered_at: Optional[datetime] = None
    delivery_time_minutes: Optional[int] = None
    notes: str = ""
    barcode: Optional[str] = None  # Código de barras do pacote
    scanned_at: Optional[datetime] = None  # Quando foi bipado na separação
    sequence_in_route: Optional[int] = None  # Ordem de entrega na rota
    
    @property
    def priority_weight(self) -> float:
        """Peso numérico da prioridade (para algoritmo)"""
        weights = {
            PackagePriority.LOW: 0.5,
            PackagePriority.NORMAL: 1.0,
            PackagePriority.HIGH: 1.5,
            PackagePriority.URGENT: 2.0
        }
        return weights[self.priority]


@dataclass
class Deliverer:
    """Entregador com capacidade e configurações"""
    telegram_id: int
    name: str
    is_partner: bool = False
    max_capacity: int = 50  # Máximo de pacotes por dia
    cost_per_package: float = 1.0  # R$ por pacote (0 para sócios)
    is_active: bool = True
    total_deliveries: int = 0
    total_earnings: float = 0.0
    success_rate: float = 100.0
    average_delivery_time: float = 0.0
    joined_date: datetime = field(default_factory=datetime.now)
    
    def can_accept_packages(self, count: int) -> bool:
        """Verifica se pode aceitar N pacotes"""
        return self.is_active and count <= self.max_capacity
    
    def calculate_earnings(self, delivered_count: int) -> float:
        """Calcula ganho por entregas"""
        return 0.0 if self.is_partner else delivered_count * self.cost_per_package


@dataclass
class FinancialReport:
    """Relatório financeiro completo"""
    date: datetime
    total_packages: int
    total_delivered: int
    total_pending: int
    total_cost: float  # Custo com entregadores
    revenue: float  # Receita bruta (se houver)
    net_profit: float  # Lucro líquido
    deliverer_costs: dict  # {deliverer_id: cost}
    deliverer_stats: dict  # {deliverer_id: {packages, cost, rate}}
    expenses: List[dict] = field(default_factory=list)  # Lista de custos extras [{type, value, desc}]
    
    def to_dict(self) -> dict:
        """Exporta para dicionário"""
        return {
            'date': self.date.isoformat(),
            'total_packages': self.total_packages,
            'total_delivered': self.total_delivered,
            'total_pending': self.total_pending,
            'total_cost': self.total_cost,
            'revenue': self.revenue,
            'net_profit': self.net_profit,
            'deliverer_costs': self.deliverer_costs,
            'deliverer_stats': self.deliverer_stats,
            'expenses': self.expenses
        }


@dataclass
class PerformanceMetrics:
    """Métricas de desempenho do entregador"""
    deliverer_id: int
    deliverer_name: str
    period_start: datetime
    period_end: datetime
    total_assigned: int
    total_delivered: int
    total_failed: int
    success_rate: float
    average_time_minutes: float
    fastest_delivery_minutes: Optional[int]
    slowest_delivery_minutes: Optional[int]
    total_distance_km: float
    complaints: int = 0
    rating: float = 5.0
    
    def to_dict(self) -> dict:
        """Exporta para dicionário"""
        return {
            'deliverer_id': self.deliverer_id,
            'deliverer_name': self.deliverer_name,
            'period': f"{self.period_start.date()} a {self.period_end.date()}",
            'assigned': self.total_assigned,
            'delivered': self.total_delivered,
            'failed': self.total_failed,
            'success_rate': f"{self.success_rate:.1f}%",
            'avg_time': f"{self.average_time_minutes:.1f} min",
            'fastest': f"{self.fastest_delivery_minutes} min" if self.fastest_delivery_minutes else "N/A",
            'slowest': f"{self.slowest_delivery_minutes} min" if self.slowest_delivery_minutes else "N/A",
            'distance': f"{self.total_distance_km:.1f} km",
            'complaints': self.complaints,
            'rating': f"{self.rating:.1f}/5.0"
        }


@dataclass
class PaymentRecord:
    """Registro de pagamento para entregador"""
    deliverer_id: int
    deliverer_name: str
    period_start: datetime
    period_end: datetime
    packages_delivered: int
    amount_due: float
    paid: bool = False
    paid_at: Optional[datetime] = None
    payment_method: str = ""
    
    def to_payment_file_line(self) -> str:
        """Formata linha para arquivo de pagamento"""
        return (
            f"{self.deliverer_id},"
            f"{self.deliverer_name},"
            f"{self.packages_delivered},"
            f"{self.amount_due:.2f},"
            f"{self.period_start.date()},"
            f"{self.period_end.date()}"
        )
