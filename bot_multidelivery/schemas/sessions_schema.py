"""
SESSÕES COM PERMAPERSISTÊNCIA - Zero friction, máximo power
Sessão = Contenedor vivo que cresce com os dados
"""

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, 
    JSON, ForeignKey, UniqueConstraint, Index, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()


class SessionStatus(str, enum.Enum):
    OPEN = "open"  # Aberta, aguardando distribuição
    ACTIVE = "active"  # Em execução, entregadores trabalhando
    COMPLETED = "completed"  # Finalizada, histórico only
    PAUSED = "paused"  # Em pausa
    ARCHIVED = "archived"  # Arquivada (>30 dias)


class DeliverySession(Base):
    """
    A ALMA DO SISTEMA: Uma sessão é um universo paralelo
    que contém TUDO linkado: endereços, pacotes, entregadores, finanças, rotas
    """
    __tablename__ = "delivery_sessions"
    
    # Identidade
    session_id = Column(String(36), primary_key=True, index=True)  # UUID
    user_id = Column(Integer, index=True)
    
    # Timeline
    created_at = Column(DateTime, default=func.now(), index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    
    # Status & Tipo
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.OPEN, index=True)
    session_type = Column(String(50))  # "manual", "import_file", "api"
    
    # Metadados
    file_name = Column(String(255), nullable=True)  # Nome do arquivo importado
    total_packages = Column(Integer, default=0)
    total_deliverers = Column(Integer, default=0)
    
    # MONEY TRACKER
    total_cost = Column(Float, default=0.0)  # Custo total da rota
    total_revenue = Column(Float, default=0.0)  # Faturamento
    total_profit = Column(Float, default=0.0)  # Lucro bruto
    
    # DATA SNAPSHOT (congelado no final)
    financial_snapshot = Column(JSON, nullable=True)  # Snapshot final
    route_optimization_data = Column(JSON, nullable=True)  # Dados da otimização
    
    # FLAGS
    is_readonly = Column(Boolean, default=False)  # True depois de completo
    was_reused = Column(Boolean, default=False)  # Se foi reutilizada antes de iniciar
    reuse_count = Column(Integer, default=0)  # Quantas vezes foi reutilizada
    
    __table_args__ = (
        Index("idx_session_user_status", "user_id", "status"),
        Index("idx_session_created", "created_at"),
        UniqueConstraint("session_id", name="uq_session_id"),
    )


class SessionPackage(Base):
    """
    Pacotes LINKADOS à sessão - imutável uma vez criado
    """
    __tablename__ = "session_packages"
    
    package_id = Column(String(36), primary_key=True)  # UUID
    session_id = Column(String(36), ForeignKey("delivery_sessions.session_id"), index=True)
    
    # Dados do pacote
    barcode = Column(String(100), index=True)
    address_id = Column(String(36), nullable=True)
    recipient_name = Column(String(255))
    recipient_phone = Column(String(20))
    address_full = Column(String(500))
    
    # Entrega
    assigned_deliverer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    delivery_status = Column(String(50), default="pending")  # pending, picked_up, delivered, failed
    delivery_time = Column(DateTime, nullable=True)
    delivery_notes = Column(String(500), nullable=True)
    
    # Financeiro
    package_value = Column(Float)
    delivery_fee = Column(Float, nullable=True)
    
    # OCR Barcode (para scanner quebrado)
    barcode_ocr_attempt = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_package_session_barcode", "session_id", "barcode"),
        Index("idx_package_deliverer", "assigned_deliverer_id"),
    )


class SessionDeliverer(Base):
    """
    Entregadores LINKADOS à sessão com salário in-session
    """
    __tablename__ = "session_deliverers"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), ForeignKey("delivery_sessions.session_id"), index=True)
    deliverer_id = Column(Integer, ForeignKey("users.id"))
    
    # Performance in-session
    packages_assigned = Column(Integer, default=0)
    packages_delivered = Column(Integer, default=0)
    
    # Financeiro in-session
    base_salary = Column(Float)
    commission_per_delivery = Column(Float)
    total_earned = Column(Float, default=0.0)  # Auto-calculado
    total_cost_assigned = Column(Float, default=0.0)  # Custo das rotas
    
    # Rotas otimizadas
    route_optimization = Column(JSON, nullable=True)  # Dados de otimização genética
    total_distance = Column(Float, default=0.0)
    estimated_time = Column(Float, default=0.0)  # em minutos
    
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index("idx_session_deliverer_deliverer", "session_id", "deliverer_id"),
    )


class SessionAddress(Base):
    """
    Endereços da sessão com geocoding em cache
    """
    __tablename__ = "session_addresses"
    
    address_id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("delivery_sessions.session_id"), index=True)
    
    address = Column(String(500))
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Cache de geocoding
    geocoding_cache = Column(JSON, nullable=True)
    geocoded_at = Column(DateTime, nullable=True)
    
    package_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index("idx_address_session", "session_id"),
    )


class SessionAudit(Base):
    """
    Log imutável de tudo que acontece na sessão
    """
    __tablename__ = "session_audit"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), ForeignKey("delivery_sessions.session_id"), index=True)
    
    action = Column(String(100))  # "session_created", "package_delivered", "deliverer_assigned"
    actor_id = Column(Integer, nullable=True)
    details = Column(JSON)
    
    created_at = Column(DateTime, default=func.now(), index=True)
    
    __table_args__ = (
        Index("idx_audit_session", "session_id", "created_at"),
    )
