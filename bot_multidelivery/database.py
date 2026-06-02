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
    payments = relationship("PaymentRecordDB", back_populates="deliverer")
    performance_metrics = relationship("PerformanceMetricDB", back_populates="deliverer")


class SessionDB(Base):
    """Tabela de sessões diárias com nomenclatura automática"""
    __tablename__ = 'sessions'
    
    session_id = Column(String(20), primary_key=True)
    session_name = Column(String(200), nullable=False, index=True)  # Aumentado para 200 para suportar nomes de arquivo longos
    date = Column(String(10), nullable=False, index=True)
    period = Column(String(10))  # 🆕 "manhã" ou "tarde"
    created_at = Column(DateTime, default=datetime.now)
    base_address = Column(String(300))
    base_lat = Column(Float)
    base_lng = Column(Float)
    is_finalized = Column(Boolean, default=False)
    finalized_at = Column(DateTime, nullable=True)
    
    # JSON fields para dados complexos
    romaneios_data = Column(JSON, nullable=True)  # Lista de romaneios serializados
    
    # Relacionamentos
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
    
    # JSON fields
    optimized_order = Column(JSON, nullable=True)  # Lista de DeliveryPoints serializados
    delivered_packages = Column(JSON, default=list)
    
    # Relacionamentos
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
    priority = Column(String(20), default='normal')  # low, normal, high, urgent
    status = Column(String(20), default='pending')  # pending, in_transit, delivered, failed
    assigned_to_telegram_id = Column(BigInteger, ForeignKey('deliverers.telegram_id'), nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    delivery_time_minutes = Column(Integer, nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relacionamentos
    session = relationship("SessionDB", back_populates="packages")
    route = relationship("RouteDB", back_populates="packages")
    deliverer = relationship("DelivererDB", back_populates="packages")


# ==================== TABELAS FINANCEIRAS ====================

class DailyFinancialReportDB(Base):
    """Tabela de relatórios financeiros diários"""
    __tablename__ = 'daily_financial_reports'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False, unique=True, index=True)
    revenue = Column(Float, nullable=False)
    delivery_costs = Column(Float, nullable=False)
    other_costs = Column(Float, default=0.0)
    net_profit = Column(Float, nullable=False)
    total_packages = Column(Integer, nullable=False)
    total_deliveries = Column(Integer, nullable=False)
    deliverer_breakdown = Column(JSON)  # {nome: custo}
    created_at = Column(DateTime, default=datetime.now)


class WeeklyFinancialReportDB(Base):
    """Tabela de relatórios financeiros semanais"""
    __tablename__ = 'weekly_financial_reports'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    week_start = Column(String(10), nullable=False, index=True)
    week_end = Column(String(10), nullable=False)
    total_revenue = Column(Float, nullable=False)
    total_delivery_costs = Column(Float, nullable=False)
    total_operational_costs = Column(Float, nullable=False)
    gross_profit = Column(Float, nullable=False)
    reserve_amount = Column(Float, nullable=False)  # 10% reserva
    distributable_profit = Column(Float, nullable=False)  # 90% para distribuir
    partner_1_share = Column(Float, nullable=False)  # 70% do distribuível
    partner_2_share = Column(Float, nullable=False)  # 30% do distribuível
    daily_reports = Column(JSON)  # Lista de datas
    created_at = Column(DateTime, default=datetime.now)


class PartnerConfigDB(Base):
    """Tabela de configuração dos sócios (singleton)"""
    __tablename__ = 'partner_config'
    
    id = Column(Integer, primary_key=True, default=1)
    partner_1_name = Column(String(100), nullable=False)
    partner_1_share = Column(Float, nullable=False)  # 0.70 = 70%
    partner_2_name = Column(String(100), nullable=False)
    partner_2_share = Column(Float, nullable=False)  # 0.30 = 30%
    reserve_percentage = Column(Float, nullable=False)  # 0.10 = 10%
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PaymentRecordDB(Base):
    """Tabela de registros de pagamento"""
    __tablename__ = 'payment_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    deliverer_id = Column(BigInteger, ForeignKey('deliverers.telegram_id'), nullable=False)
    deliverer_name = Column(String(100))
    period_start = Column(String(10), nullable=False)
    period_end = Column(String(10), nullable=False)
    packages_delivered = Column(Integer, nullable=False)
    amount_due = Column(Float, nullable=False)
    paid = Column(Boolean, default=False)
    paid_at = Column(DateTime, nullable=True)
    payment_method = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)
    
    # Relacionamento
    deliverer = relationship("DelivererDB", back_populates="payments")


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
    value_type = Column(String(20))  # string, int, float, bool, json
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PerformanceMetricDB(Base):
    """Tabela de métricas de performance"""
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    deliverer_id = Column(BigInteger, ForeignKey('deliverers.telegram_id'), nullable=False)
    deliverer_name = Column(String(100))
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    total_assigned = Column(Integer, nullable=False)
    total_delivered = Column(Integer, nullable=False)
    total_failed = Column(Integer, nullable=False)
    success_rate = Column(Float, nullable=False)
    average_time_minutes = Column(Float, nullable=False)
    fastest_delivery_minutes = Column(Integer)
    slowest_delivery_minutes = Column(Integer)
    total_distance_km = Column(Float, nullable=False)
    complaints = Column(Integer, default=0)
    rating = Column(Float, default=5.0)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relacionamento
    deliverer = relationship("DelivererDB", back_populates="performance_metrics")


class BankCredentialDB(Base):
    """Tabela de credenciais bancárias (singleton, encrypted)"""
    __tablename__ = 'bank_credentials'
    
    id = Column(Integer, primary_key=True, default=1)
    bank_name = Column(String(50), nullable=False)
    account_number = Column(String(50))
    certificate_data = Column(Text)  # Base64 encoded
    key_data = Column(Text)  # Base64 encoded (encrypted)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class NeighborhoodStatsDB(Base):
    """
    🧠 Tabela do Cérebro Geográfico
    Armazena inteligência acumulada sobre cada bairro
    """
    __tablename__ = 'neighborhood_stats'
    
    name = Column(String(100), primary_key=True)  # Nome do bairro
    total_deliveries = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    success_rate = Column(Float, default=0.0, nullable=False)  # Percentual
    avg_delivery_time = Column(Float, default=0.0)  # Minutos
    best_deliverer = Column(String(100))  # Nome do melhor entregador
    best_deliverer_rate = Column(Float, default=0.0)  # Taxa de sucesso dele
    common_failure_reasons = Column(Text)  # CSV de motivos
    peak_hours = Column(Text)  # CSV de horas (0-23)
    difficulty_score = Column(Float, default=0.0)  # 0-10
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        Index('idx_neighborhood_success_rate', 'success_rate'),
        Index('idx_neighborhood_difficulty', 'difficulty_score'),
    )


# ==================== HELPER FUNCTIONS ====================

def generate_session_name(date: datetime, period: str) -> str:
    """
    Gera nome automático da sessão no formato "Dia Período"
    
    Args:
        date: Data da sessão
        period: 'manhã' ou 'tarde'
    
    Returns:
        Nome formatado: "Segunda Manhã", "Terça Tarde", etc.
    """
    days = {
        0: "Segunda",
        1: "Terça",
        2: "Quarta",
        3: "Quinta",
        4: "Sexta",
        5: "Sábado",
        6: "Domingo"
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
        
        print("\n" + "="*50)
        print("🔍 INICIANDO CONEXÃO COM BANCO DE DADOS")
        print("="*50)
        
        if self.database_url:
            print(f"✅ DATABASE_URL encontrada: {self.database_url[:30]}...")
            
            # Railway/Heroku usam postgres:// mas SQLAlchemy 1.4+ precisa postgresql://
            if self.database_url.startswith('postgres://'):
                self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
                print("🔄 Convertido postgres:// → postgresql://")
            
            try:
                print("🔌 Conectando ao PostgreSQL...")
                self.engine = create_engine(
                    self.database_url,
                    pool_size=5,
                    max_overflow=10,
                    pool_pre_ping=True,  # Verifica conexão antes de usar
                    echo=False,
                    connect_args={
                        'connect_timeout': 10,  # Timeout de 10 segundos
                    }
                )
                self.SessionLocal = sessionmaker(bind=self.engine)
                
                # Testa conexão com retry
                print("📊 Criando tabelas se não existirem...")
                max_retries = 3
                for attempt in range(1, max_retries + 1):
                    try:
                        # Cria tabelas apenas se não existirem (não apaga dados!)
                        Base.metadata.create_all(self.engine)
                        
                        # Testa conexão
                        with self.get_session() as session:
                            session.execute(text('SELECT 1'))
                        
                        print(f"✅ PostgreSQL conectado com sucesso! (tentativa {attempt}/{max_retries})")
                        
                        # --- AUTO-MIGRATION (Schema Fix) ---
                        try:
                            with self.engine.connect() as conn:
                                # Adiciona colunas faltantes se necessário
                                # Usa bloco try/catch para cada uma caso IF NOT EXISTS falhe ou já exista
                                try:
                                    conn.execute(text("ALTER TABLE sessions ADD COLUMN session_name VARCHAR(50)"))
                                    conn.commit()
                                    print("🛠️ Schema fix: Coluna 'session_name' adicionada.")
                                except Exception:
                                    pass # Ignora se já existe
                                    
                                try:
                                    conn.execute(text("ALTER TABLE sessions ADD COLUMN period VARCHAR(10)"))
                                    conn.commit()
                                    print("🛠️ Schema fix: Coluna 'period' adicionada.")
                                except Exception:
                                    pass # Ignora se já existe
                        except Exception as e:
                            print(f"⚠️ Erro ao verificar schema: {e}")
                        # -----------------------------------
                        print("💾 Dados serão persistidos permanentemente")
                        print(f"📋 Total de tabelas no schema: {len(Base.metadata.tables)}")
                        print(f"🗂️  Tabelas: {', '.join(Base.metadata.tables.keys())}")
                        break
                    except Exception as retry_error:
                        if attempt < max_retries:
                            print(f"⚠️ Tentativa {attempt}/{max_retries} falhou: {retry_error}")
                            print(f"🔄 Tentando novamente em 2 segundos...")
                            import time
                            time.sleep(2)
                        else:
                            raise retry_error
                
            except Exception as e:
                print(f"❌ ERRO ao conectar PostgreSQL: {e}")
                print(f"❌ Tipo do erro: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                print("📁 FALLBACK: Usando arquivos JSON locais")
                self.engine = None
        else:
            print("❌ DATABASE_URL NÃO CONFIGURADA!")
            print("📁 Usando arquivos JSON locais")
            print("⚠️ DADOS SERÃO PERDIDOS AO REINICIAR!")
            print("\n💡 Configure DATABASE_URL no Railway:")
            print("   1. Crie PostgreSQL Database")
            print("   2. Copie DATABASE_PUBLIC_URL")
            print("   3. Cole nas Variables do bot")
        
        print("="*50 + "\n")
    
    @property
    def is_connected(self) -> bool:
        """Verifica se está conectado ao PostgreSQL"""
        return self.engine is not None
    
    @contextmanager
    def get_session(self):
        """Context manager para sessões SQLAlchemy"""
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


# Singleton global
db_manager = DatabaseManager()

# ==================== DEPENDENCY FOR FASTAPI ====================

def get_db():
    """Generator para usar em FastAPI dependencies"""
    db = db_manager.SessionLocal()
    try:
        yield db
    finally:
        db.close()