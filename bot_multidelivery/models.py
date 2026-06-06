"""
📦 MODELOS DE DADOS - Sistema Multi-Entregador
Define estruturas de dados escaláveis
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from datetime import datetime
from enum import Enum

# --- ENUMS ---

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
    status: str = "pending"  # pending, delivered, failed, returned
    failure_reason: Optional[str] = None
    status_detail: Optional[str] = None

@dataclass
class DeliveryStop:
    """
    Uma PARADA na rota (pode ter múltiplos pacotes no mesmo endereço)
    """
    stop_number: int
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
        return len(self.stops) if self.stops else 0

    @property
    def centroid(self) -> Tuple[float, float]:
        return (self.center_lat, self.center_lng)

@dataclass
class Package:
    """Pacote individual com todos os metadados (Model compatível com o banco)"""
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
    barcode: Optional[str] = None
    scanned_at: Optional[datetime] = None
    sequence_in_route: Optional[int] = None
    
    @property
    def priority_weight(self) -> float:
        weights = {
            PackagePriority.LOW: 0.5,
            PackagePriority.NORMAL: 1.0,
            PackagePriority.HIGH: 1.5,
            PackagePriority.URGENT: 2.0
        }
        return weights.get(self.priority, 1.0)

@dataclass
class Deliverer:
    """Entregador com capacidade e configurações"""
    telegram_id: int
    name: str
    is_partner: bool = False
    max_capacity: int = 50
    is_active: bool = True
    total_deliveries: int = 0
    success_rate: float = 100.0
    average_delivery_time: float = 0.0
    joined_date: datetime = field(default_factory=datetime.now)
    
    def can_accept_packages(self, count: int) -> bool:
        return self.is_active and count <= self.max_capacity
