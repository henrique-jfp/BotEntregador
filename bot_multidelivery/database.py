"""
💾 DATABASE - PostgreSQL com SQLAlchemy
Persistência permanente para Railway
"""
import os
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from contextlib import contextmanager

Base = declarative_base()


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
    
    # Relacionamento com sessões
    routes = relationship("RouteDB", back_populates="deliverer")


class SessionDB(Base):
    """Tabela de sessões diárias"""
    __tablename__ = 'sessions'
    
    session_id = Column(String(20), primary_key=True)
    date = Column(String(10), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)
    base_address = Column(String(300))
    base_lat = Column(Float)
    base_lng = Column(Float)
    is_finalized = Column(Boolean, default=False)
    finalized_at = Column(DateTime, nullable=True)
    
    # JSON fields para dados complexos
    romaneios_data = Column(JSON, nullable=True)  # Lista de romaneios serializados
    
    # Relacionamento com rotas
    routes = relationship("RouteDB", back_populates="session", cascade="all, delete-orphan")


class RouteDB(Base):
    """Tabela de rotas"""
    __tablename__ = 'routes'
    
    id = Column(String(50), primary_key=True)
    session_id = Column(String(20), ForeignKey('sessions.session_id'), nullable=False)
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
                print("📊 Criando/atualizando tabelas...")
                max_retries = 3
                for attempt in range(1, max_retries + 1):
                    try:
                        # IMPORTANTE: Drop e recriar para corrigir tipo telegram_id (Integer → BigInteger)
                        # Só executará se as tabelas já existirem com tipo errado
                        print("🔄 Recriando tabelas para suportar Telegram IDs grandes...")
                        Base.metadata.drop_all(self.engine)
                        Base.metadata.create_all(self.engine)
                        
                        # Testa conexão
                        with self.get_session() as session:
                            session.execute(text('SELECT 1'))
                        
                        print(f"✅ PostgreSQL conectado com sucesso! (tentativa {attempt}/{max_retries})")
                        print("💾 Dados serão persistidos permanentemente")
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
            print("   2. Copie DATABASE_URL")
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
