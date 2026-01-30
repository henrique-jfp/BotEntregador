"""
📦 MODELOS DE DADOS - Sistema Multi-Entregador
Define estruturas de dados escaláveis
"""

from dataclasses import dataclass, field
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
