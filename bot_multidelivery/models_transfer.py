"""
🔄 MODELOS DE TRANSFERÊNCIA - Sistema de Transferência de Pacotes
Define estruturas para solicitação e aprovação de transferências entre entregadores
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class TransferStatus(Enum):
    """Status da solicitação de transferência"""
    PENDING = "pendente"
    APPROVED = "aprovada"
    REJECTED = "rejeitada"
    CANCELLED = "cancelada"


@dataclass
class TransferRequest:
    """Solicitação de transferência de pacote entre entregadores"""
    id: str
    package_ids: list[str]  # Pode ser múltiplos pacotes
    from_deliverer_id: int
    from_deliverer_name: str
    to_deliverer_id: int
    to_deliverer_name: str
    reason: str
    status: TransferStatus = TransferStatus.PENDING
    requested_at: datetime = field(default_factory=datetime.now)
    approved_at: Optional[datetime] = None
    approved_by_admin_id: Optional[int] = None
    approved_by_admin_name: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Exporta para dicionário"""
        return {
            'id': self.id,
            'package_ids': self.package_ids,
            'package_count': len(self.package_ids),
            'from_deliverer': {
                'id': self.from_deliverer_id,
                'name': self.from_deliverer_name
            },
            'to_deliverer': {
                'id': self.to_deliverer_id,
                'name': self.to_deliverer_name
            },
            'reason': self.reason,
            'status': self.status.value,
            'requested_at': self.requested_at.isoformat(),
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approved_by': {
                'id': self.approved_by_admin_id,
                'name': self.approved_by_admin_name
            } if self.approved_by_admin_id else None,
            'rejection_reason': self.rejection_reason
        }


@dataclass
class SeparationSession:
    """Sessão de separação de pacotes para envio"""
    session_id: str
    route_ids: list[str]
    total_packages: int
    scanned_packages: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    is_complete: bool = False
    scan_mode: str = "barcode"  # "barcode" ou "camera"
    
    @property
    def progress_percentage(self) -> float:
        """Percentual de progresso"""
        if self.total_packages == 0:
            return 0.0
        return (self.scanned_packages / self.total_packages) * 100
    
    def to_dict(self) -> dict:
        """Exporta para dicionário"""
        return {
            'session_id': self.session_id,
            'route_ids': self.route_ids,
            'total_packages': self.total_packages,
            'scanned_packages': self.scanned_packages,
            'progress': f"{self.progress_percentage:.1f}%",
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'is_complete': self.is_complete,
            'scan_mode': self.scan_mode
        }
