"""
💾 DATABASE - PostgreSQL com SQLAlchemy
Persistência permanente para Railway - SCHEMA COMPLETO v2.0
"""
import os
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, text, CheckConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from contextlib import contextmanager

Base = declarative_base()


# ==================== TABELAS PRINCIPAIS ====================

class DelivererDB(Base):
    """Tabela de entregadores"""
    __tablename__ = 'deliverers'
    
    telegram_id = Column(BigInteger, primary_key=True)
    name = Column(String(100), nullable=False)
    is_partner = Column(Boolean, default=False)
    max_capacity = Column(Integer, default=50)
    cost_per_package = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)
    total_deliveries = Column(Integer, default=0)
    total_earnings = Column(Float, default=0.0)
    success_rate = Column(Float, default=100.0)
    average_delivery_time = Column(Float, default=0.0)
    joined_date = Column(DateTime, default=datetime.now)
    
    # Relacionamentos
    routes = relationship("RouteDB", back_populates="deliverer")
    packages = relationship("PackageDB", back_populates="deliverer")


class SessionDB(Base):
    """Tabela de sessões diárias com nomenclatura automática"""
    __tablename__ = 'sessions'
    
    session_id = Column(String(20), primary_key=True)
    session_name = Column(String(200), nullable=False, index=True)
    date = Column(String(10), nullable=False, index=True)
    period = Column(String(10))
    created_at = Column(DateTime, default=datetime.now)
    base_address = Column(String(300))
    base_lat = Column(Float)
    base_lng = Column(Float)
    is_finalized = Column(Boolean, default=False)
    finalized_at = Column(DateTime, nullable=True)
    
    romaneios_data = Column(JSON, nullable=True)
    
    routes = relationship("RouteDB", back_populates="session", cascade="all, delete-orphan")
    packages = relationship("PackageDB", back_populates="session", cascade="all, delete-orphan")


class RouteDB(Base):
    """Tabela de rotas"""
    __tablename__ = 'routes'
    
    id = Column(String(50), primary_key=True)
    session_id = Column(String(20), ForeignKey('sessions.session_id', ondelete='CASCADE'), nullable=False)
    assigned_to_telegram_id = Column(BigInteger, ForeignKey('deliverers.telegram_id'), nullable=True)
    assigned_to_name = Column(String(100))
    color = Column(String(20))
    map_file = Column(String(200))
    
    optimized_order = Column(JSON, nullable=True)
    delivered_packages = Column(JSON, default=list)
    
    session = relationship("SessionDB", back_populates="routes")
    deliverer = relationship("DelivererDB", back_populates="routes")
    packages = relationship("PackageDB", back_populates="route")


# ==================== TABELAS DE PACOTES ====================

class PackageDB(Base):
    """Tabela de pacotes individuais"""
    __tablename__ = 'packages'
    
    id = Column(String(50), primary_key=True)
    session_id = Column(String(20), ForeignKey('sessions.session_id', ondelete='CASCADE'))
    romaneio_id = Column(String(50))
    route_id = Column(String(50), ForeignKey('routes.id', ondelete='SET NULL'), nullable=True)
    address = Column(Text, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    priority = Column(String(20), default='normal')
    status = Column(String(20), default='pending')
    assigned_to_telegram_id = Column(BigInteger, ForeignKey('deliverers.telegram_id'), nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    delivery_time_minutes = Column(Integer, nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    session = relationship("SessionDB", back_populates="packages")
    route = relationship("RouteDB", back_populates="packages")
    deliverer = relationship("DelivererDB", back_populates="packages")


# ==================== TABELAS DE CACHE E CONFIG ====================

class GeocodingCacheDB(Base):
    """Tabela de cache de geocodificação"""
    __tablename__ = 'geocoding_cache'
    
    address = Column(String(500), primary_key=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    formatted_address = Column(Text)
    cached_at = Column(DateTime, default=datetime.now)


class BotConfigDB(Base):
    """Tabela de configurações do bot"""
    __tablename__ = 'bot_config'
    
    key = Column(String(100), primary_key=True)
    value = Column(Text)
    value_type = Column(String(20))
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class BankCredentialDB(Base):
    """Tabela de credenciais bancárias (singleton, encrypted)"""
    __tablename__ = 'bank_credentials'
    
    id = Column(Integer, primary_key=True, default=1)
    bank_name = Column(String(50), nullable=False)
    account_number = Column(String(50))
    certificate_data = Column(Text)
    key_data = Column(Text)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class NeighborhoodStatsDB(Base):
    """
    🧠 Tabela do Cérebro Geográfico
    Armazena inteligência acumulada sobre cada bairro
    """
    __tablename__ = 'neighborhood_stats'
    
    name = Column(String(100), primary_key=True)
    total_deliveries = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    success_rate = Column(Float, default=0.0, nullable=False)
    avg_delivery_time = Column(Float, default=0.0)
    best_deliverer = Column(String(100))
    best_deliverer_rate = Column(Float, default=0.0)
    common_failure_reasons = Column(Text)
    peak_hours = Column(Text)
    difficulty_score = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        Index('idx_neighborhood_success_rate', 'success_rate'),
        Index('idx_neighborhood_difficulty', 'difficulty_score'),
    )


# ==================== HELPER FUNCTIONS ====================

def generate_session_name(date: datetime, period: str) -> str:
    """
    Gera nome automático da sessão no formato "Dia Período"
    """
    days = {
        0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta",
        4: "Sexta", 5: "Sábado", 6: "Domingo"
    }
    day_name = days[date.weekday()]
    return f"{day_name} {period.capitalize()}"


# ==================== DATABASE MANAGER ====================

class DatabaseManager:
    """Gerenciador de conexão com PostgreSQL"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', None)
        self.engine = None
        self.SessionLocal = None
        
        print("
" + "="*50)
        print("🔍 INICIANDO CONEXÃO COM BANCO DE DADOS")
        print("="*50)
        
        if self.database_url:
            print(f"✅ DATABASE_URL encontrada: {self.database_url[:30]}...")
            if self.database_url.startswith('postgres://'):
                self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
                print("🔄 Convertido postgres:// → postgresql://")
            
            try:
                print("🔌 Conectando ao PostgreSQL...")
                self.engine = create_engine(
                    self.database_url,
                    pool_size=5,
                    max_overflow=10,
                    pool_pre_ping=True,
                    echo=False,
                    connect_args={'connect_timeout': 10}
                )
                self.SessionLocal = sessionmaker(bind=self.engine)
                
                print("📊 Criando tabelas se não existirem...")
                max_retries = 3
                for attempt in range(1, max_retries + 1):
                    try:
                        Base.metadata.create_all(self.engine)
                        with self.get_session() as session:
                            session.execute(text('SELECT 1'))
                        print(f"✅ PostgreSQL conectado com sucesso! (tentativa {attempt}/{max_retries})")
                        print("💾 Dados serão persistidos permanentemente")
                        print(f"📋 Total de tabelas no schema: {len(Base.metadata.tables)}")
                        print(f"🗂️  Tabelas: {', '.join(Base.metadata.tables.keys())}")
                        break
                    except Exception as retry_error:
                        if attempt < max_retries:
                            print(f"⚠️ Tentativa {attempt}/{max_retries} falhou: {retry_error}")
                            import time
                            time.sleep(2)
                        else:
                            raise retry_error
            except Exception as e:
                print(f"❌ ERRO ao conectar PostgreSQL: {e}")
                print("📁 FALLBACK: Usando arquivos JSON locais")
                self.engine = None
        else:
            print("❌ DATABASE_URL NÃO CONFIGURADA!")
            print("📁 Usando arquivos JSON locais")
        
        print("="*50 + "
")
    
    @property
    def is_connected(self) -> bool:
        return self.engine is not None
    
    @contextmanager
    def get_session(self):
        if not self.is_connected:
            raise RuntimeError("Database não está conectado")
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

db_manager = DatabaseManager()

def get_db():
    db = db_manager.SessionLocal()
    try:
        yield db
    finally:
        db.close()
