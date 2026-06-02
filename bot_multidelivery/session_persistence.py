"""
💾 PERSISTÊNCIA DE SESSÕES - Auto-save em PostgreSQL ou JSON
Salva sessões automaticamente com histórico completo
"""
import json
import os
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from .session import DailySession, Route, Romaneio, DeliveryPoint

# Import database - verificação de conexão será feita dinamicamente
try:
    from .database import db_manager, SessionDB, RouteDB
    HAS_DATABASE_MODULE = True
except Exception as e:
    print(f"⚠️ Database import failed: {e}")
    HAS_DATABASE_MODULE = False
    db_manager = None


class SessionStore:
    """Gerencia persistência de sessões em disco ou PostgreSQL"""
    
    def __init__(self, data_dir: str = "data"):
        self.sessions_dir = Path(data_dir) / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._last_db_check = None
        self._check_database_connection()
    
    def _check_database_connection(self) -> bool:
        """Verifica conexão com banco dinamicamente (não apenas no import)"""
        if not HAS_DATABASE_MODULE or db_manager is None:
            self.using_database = False
            return False
        
        # Re-verifica conexão real
        self.using_database = db_manager.is_connected
        
        if self.using_database:
            print("✅ SessionStore: PostgreSQL conectado")
        else:
            print("⚠️ SessionStore: PostgreSQL não disponível, usando JSON local")
            if os.getenv("RAILWAY_ENVIRONMENT"):
                print("🚨 ALERTA: Rodando em RAILWAY sem PostgreSQL!")
                print("   Os dados serão PERDIDOS ao reiniciar!")
                print("   Configure DATABASE_URL nas variáveis de ambiente")
        
        return self.using_database
    
    def _session_file(self, session_id: str) -> Path:
        """Path do arquivo da sessão"""
        return self.sessions_dir / f"{session_id}.json"
    
    def delete_session(self, session_id: str) -> bool:
        """Exclui sessão do PostgreSQL e/ou Disco"""
        success = True
        
        # 1. Tenta remover do PostgreSQL
        if self.using_database:
            try:
                with db_manager.get_session() as db_session:
                    # Cascata deve remover rotas automaticamente se configurado no DB,
                    # mas vamos garantir removendo manual primeiro
                    db_session.query(RouteDB).filter_by(session_id=session_id).delete()
                    
                    rows = db_session.query(SessionDB).filter_by(session_id=session_id).delete()
                    if rows == 0:
                        print(f"⚠️ Sessão {session_id} não encontrada no DB para exclusão")
                    else:
                        print(f"🗑️ Sessão {session_id} removida do PostgreSQL")
            except Exception as e:
                print(f"⚠️ Erro ao excluir sessão {session_id} do DB: {e}")
                success = False

        # 2. Sempre tenta remover arquivo JSON local (backup ou modo arquivo)
        try:
            file_path = self._session_file(session_id)
            if file_path.exists():
                file_path.unlink()
                print(f"🗑️ Arquivo de sessão {session_id}.json removido")
            elif not self.using_database:
                # Se não está no DB e não tem arquivo, falhou
                success = False
        except Exception as e:
            print(f"⚠️ Erro ao excluir arquivo da sessão {session_id}: {e}")
            success = False
            
        return success

    def save_session(self, session: DailySession):
        """Salva sessão em disco ou PostgreSQL (auto-save)"""
        # Re-verifica conexão antes de salvar (pode ter reconectado)
        if not self.using_database:
            self._check_database_connection()
        
        if self.using_database:
            # Salva no PostgreSQL
            try:
                with db_manager.get_session() as db_session:
                    # Serializa romaneios para JSON
                    romaneios_data = [
                        {
                            'id': r.id,
                            'filename': r.filename,
                            'uploaded_at': r.uploaded_at.isoformat(),
                            'points': [
                                {
                                    'package_id': p.package_id,
                                    'romaneio_id': p.romaneio_id,
                                    'address': p.address,
                                    'lat': p.lat,
                                    'lng': p.lng,
                                    'priority': p.priority,
                                    'bairro': getattr(p, 'bairro', '')
                                } for p in r.points
                            ]
                        } for r in session.romaneios
                    ]
                    
                    # Verifica se sessão já existe
                    session_db = db_session.query(SessionDB).filter_by(session_id=session.session_id).first()
                    
                    if session_db:
                        # Atualiza existente
                        session_db.session_name = session.session_name
                        session_db.date = session.date
                        session_db.period = session.period
                        session_db.base_address = session.base_address
                        session_db.base_lat = session.base_lat
                        session_db.base_lng = session.base_lng
                        session_db.is_finalized = session.is_finalized
                        session_db.finalized_at = session.finalized_at
                        session_db.romaneios_data = romaneios_data
                        
                        # Remove rotas antigas
                        db_session.query(RouteDB).filter_by(session_id=session.session_id).delete()
                    else:
                        # Cria nova
                        session_db = SessionDB(
                            session_id=session.session_id,
                            session_name=session.session_name,
                            date=session.date,
                            period=session.period,
                            created_at=session.created_at,
                            base_address=session.base_address,
                            base_lat=session.base_lat,
                            base_lng=session.base_lng,
                            is_finalized=session.is_finalized,
                            finalized_at=session.finalized_at,
                            romaneios_data=romaneios_data
                        )
                        db_session.add(session_db)
                    
                    # Salva rotas
                    for route in session.routes:
                        route_db = RouteDB(
                            id=route.id,
                            session_id=session.session_id,
                            assigned_to_telegram_id=route.assigned_to_telegram_id,
                            assigned_to_name=route.assigned_to_name,
                            color=route.color,
                            map_file=route.map_file,
                            optimized_order=[
                                {
                                    'package_id': p.package_id,
                                    'romaneio_id': p.romaneio_id,
                                    'address': p.address,
                                    'lat': p.lat,
                                    'lng': p.lng,
                                    'priority': p.priority,
                                    'bairro': getattr(p, 'bairro', '')
                                } for p in route.optimized_order
                            ],
                            delivered_packages=route.delivered_packages
                        )
                        db_session.add(route_db)
                    
                print(f"💾 Sessão {session.session_name} salva no PostgreSQL")
                return
            except Exception as e:
                print(f"⚠️ Erro ao salvar sessão no PostgreSQL: {e}, usando fallback JSON")
                self.using_database = False  # Marca para usar JSON
        
        # Fallback: JSON
        try:
            # Garante que diretório existe
            self.sessions_dir.mkdir(parents=True, exist_ok=True)
            
            # AVISO em produção
            if os.getenv("RAILWAY_ENVIRONMENT"):
                print(f"🚨 SALVANDO EM JSON LOCAL: {session.session_name}")
                print("   Isso será PERDIDO no próximo deploy!")
            
            data = {
                'session_id': session.session_id,
                'session_name': session.session_name,
                'date': session.date,
                'period': session.period,
                'created_at': session.created_at.isoformat(),
                'base_address': session.base_address,
                'base_lat': session.base_lat,
                'base_lng': session.base_lng,
                'is_finalized': session.is_finalized,
                'finalized_at': session.finalized_at.isoformat() if session.finalized_at else None,
                'romaneios': [
                    {
                        'id': r.id,
                        'filename': r.filename,
                        'uploaded_at': r.uploaded_at.isoformat(),
                        'points': [
                            {
                                'package_id': p.package_id,
                                'romaneio_id': p.romaneio_id,
                                'address': p.address,
                                'lat': p.lat,
                                'lng': p.lng,
                                'priority': p.priority
                            } for p in r.points
                        ]
                    } for r in session.romaneios
                ],
                'routes': [
                    {
                        'id': r.id,
                        'assigned_to_telegram_id': r.assigned_to_telegram_id,
                        'assigned_to_name': r.assigned_to_name,
                        'color': r.color,
                        'optimized_order': [
                            {
                                'package_id': p.package_id,
                                'romaneio_id': p.romaneio_id,
                                'address': p.address,
                                'lat': p.lat,
                                'lng': p.lng,
                                'priority': p.priority
                            } for p in r.optimized_order
                        ],
                        'delivered_packages': r.delivered_packages,
                        'map_file': r.map_file
                    } for r in session.routes
                ]
            }
            
            file_path = self._session_file(session.session_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Erro ao salvar sessão {session.session_id}: {e}")
            import traceback
            traceback.print_exc()
    
    def load_session(self, session_id: str) -> Optional[DailySession]:
        """Carrega sessão do PostgreSQL ou disco"""
        if self.using_database:
            # Carrega do PostgreSQL
            try:
                with db_manager.get_session() as db_session:
                    session_db = db_session.query(SessionDB).filter_by(session_id=session_id).first()
                    
                    if not session_db:
                        return None
                    
                    # Reconstrói romaneios
                    romaneios = []
                    for r_data in (session_db.romaneios_data or []):
                        points = [
                            DeliveryPoint(
                                package_id=p['package_id'],
                                romaneio_id=p['romaneio_id'],
                                address=p['address'],
                                lat=p['lat'],
                                lng=p['lng'],
                                priority=p.get('priority', 'normal'),
                                bairro=p.get('bairro', '')
                            ) for p in r_data['points']
                        ]
                        romaneios.append(Romaneio(
                            id=r_data['id'],
                            filename=r_data.get('filename', ''),
                            uploaded_at=datetime.fromisoformat(r_data['uploaded_at']),
                            points=points
                        ))
                    
                    # Reconstrói rotas
                    routes = []
                    for route_db in session_db.routes:
                        optimized = [
                            DeliveryPoint(
                                package_id=p['package_id'],
                                romaneio_id=p['romaneio_id'],
                                address=p['address'],
                                lat=p['lat'],
                                lng=p['lng'],
                                priority=p.get('priority', 'normal'),
                                bairro=p.get('bairro', '')
                            ) for p in (route_db.optimized_order or [])
                        ]
                        
                        route = Route(
                            id=route_db.id,
                            cluster=None,
                            assigned_to_telegram_id=route_db.assigned_to_telegram_id,
                            assigned_to_name=route_db.assigned_to_name,
                            color=route_db.color,
                            optimized_order=optimized,
                            delivered_packages=route_db.delivered_packages or [],
                            map_file=route_db.map_file
                        )
                        routes.append(route)
                    
                    return DailySession(
                        session_id=session_db.session_id,
                        session_name=session_db.session_name or '',
                        date=session_db.date,
                        period=session_db.period or '',
                        created_at=session_db.created_at,
                        base_address=session_db.base_address,
                        base_lat=session_db.base_lat,
                        base_lng=session_db.base_lng,
                        romaneios=romaneios,
                        routes=routes,
                        is_finalized=session_db.is_finalized,
                        finalized_at=session_db.finalized_at
                    )
            except Exception as e:
                print(f"⚠️ Erro ao carregar sessão do PostgreSQL: {e}, tentando JSON")
        
        # Fallback: JSON
        file_path = self._session_file(session_id)
        
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reconstrói objetos
        romaneios = []
        for r_data in data.get('romaneios', []):
            points = [
                DeliveryPoint(
                    package_id=p['package_id'],
                    romaneio_id=p['romaneio_id'],
                    address=p['address'],
                    lat=p['lat'],
                    lng=p['lng'],
                    priority=p.get('priority', 'normal'),
                    bairro=p.get('bairro', '')
                ) for p in r_data['points']
            ]
            romaneios.append(Romaneio(
                id=r_data['id'],
                filename=r_data.get('filename', ''),
                uploaded_at=datetime.fromisoformat(r_data['uploaded_at']),
                points=points
            ))
        
        routes = []
        for r_data in data.get('routes', []):
            optimized = [
                DeliveryPoint(
                    package_id=p['package_id'],
                    romaneio_id=p['romaneio_id'],
                    address=p['address'],
                    lat=p['lat'],
                    lng=p['lng'],
                    priority=p.get('priority', 'normal'),
                    bairro=p.get('bairro', '')
                ) for p in r_data['optimized_order']
            ]
            
            route = Route(
                id=r_data['id'],
                cluster=None,  # Cluster não precisa ser reconstruído
                assigned_to_telegram_id=r_data.get('assigned_to_telegram_id'),
                assigned_to_name=r_data.get('assigned_to_name'),
                color=r_data.get('color', '#667eea'),
                optimized_order=optimized,
                delivered_packages=r_data.get('delivered_packages', []),
                map_file=r_data.get('map_file')
            )
            routes.append(route)
        
        session = DailySession(
            session_id=data['session_id'],
            session_name=data.get('session_name', ''),
            date=data['date'],
            period=data.get('period', ''),
            created_at=datetime.fromisoformat(data['created_at']),
            base_address=data['base_address'],
            base_lat=data['base_lat'],
            base_lng=data['base_lng'],
            romaneios=romaneios,
            routes=routes,
            is_finalized=data.get('is_finalized', False),
            finalized_at=datetime.fromisoformat(data['finalized_at']) if data.get('finalized_at') else None
        )
        
        return session
    
    def list_sessions(self, limit: int = 20) -> List[Dict]:
        """Lista todas as sessões (mais recentes primeiro)"""
        sessions = []
        
        # Tenta carregar do PostgreSQL primeiro
        if self.using_database:
            try:
                with db_manager.get_session() as db_session:
                    sessions_db = db_session.query(SessionDB).order_by(SessionDB.created_at.desc()).limit(limit).all()
                    
                    for s in sessions_db:
                        sessions.append({
                            'session_id': s.session_id,
                            'session_name': s.session_name or '',
                            'date': s.date,
                            'period': s.period or '',
                            'created_at': s.created_at,
                            'is_finalized': s.is_finalized,
                            'base_address': s.base_address,
                            'total_packages': sum(len(r['points']) for r in (s.romaneios_data or [])),
                            'num_routes': db_session.query(RouteDB).filter_by(session_id=s.session_id).count()
                        })
                    
                    if sessions:
                        return sessions
            except Exception as e:
                print(f"⚠️ Erro ao listar sessões do PostgreSQL: {e}")
        
        # Fallback: JSON
        try:
            if not self.sessions_dir.exists():
                return []
            
            for file_path in self.sessions_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    sessions.append({
                        'session_id': data['session_id'],
                        'session_name': data.get('session_name', ''),
                        'date': data['date'],
                        'period': data.get('period', ''),
                        'created_at': datetime.fromisoformat(data['created_at']),
                        'is_finalized': data.get('is_finalized', False),
                        'base_address': data.get('base_address'),
                        'total_packages': sum(len(r['points']) for r in data.get('romaneios', [])),
                        'num_routes': len(data.get('routes', []))
                    })
                except Exception as e:
                    print(f"⚠️ Erro ao carregar {file_path}: {e}")
                    continue
            
            sessions.sort(key=lambda x: x['created_at'], reverse=True)
            
            return sessions[:limit]
        except Exception as e:
            print(f"⚠️ Erro ao listar sessões: {e}")
            return []
    
    def load_all_sessions(self) -> List['DailySession']:
        """Carrega TODAS as sessões completas do PostgreSQL ou JSON"""
        sessions = []
        
        # Tenta carregar do PostgreSQL
        if self.using_database:
            try:
                with db_manager.get_session() as db_session:
                    sessions_db = db_session.query(SessionDB).order_by(SessionDB.created_at.desc()).limit(50).all()
                    
                    for s_db in sessions_db:
                        session = self.load_session(s_db.session_id)
                        if session:
                            sessions.append(session)
                    
                    if sessions:
                        print(f"✅ {len(sessions)} sessões carregadas do PostgreSQL")
                        return sessions
            except Exception as e:
                print(f"⚠️ Erro ao carregar sessões do PostgreSQL: {e}")
        
        # Fallback: JSON
        try:
            if not self.sessions_dir.exists():
                return []
            
            for file_path in self.sessions_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    session = self.load_session(data['session_id'])
                    if session:
                        sessions.append(session)
                except Exception as e:
                    print(f"⚠️ Erro ao carregar {file_path}: {e}")
                    continue
            
            print(f"✅ {len(sessions)} sessões carregadas do JSON")
            return sessions
        except Exception as e:
            print(f"⚠️ Erro ao carregar sessões: {e}")
            return []
    
    def delete_session(self, session_id: str) -> bool:
        """Deleta sessão do PostgreSQL e/ou disco"""
        deleted = False
        
        # Tenta deletar do PostgreSQL
        if self.using_database:
            try:
                with db_manager.get_session() as db_session:
                    # Deleta rotas primeiro (foreign key)
                    db_session.query(RouteDB).filter_by(session_id=session_id).delete()
                    # Deleta sessão
                    result = db_session.query(SessionDB).filter_by(session_id=session_id).delete()
                    if result > 0:
                        deleted = True
                        print(f"✅ Sessão {session_id} deletada do PostgreSQL")
            except Exception as e:
                print(f"⚠️ Erro ao deletar sessão do PostgreSQL: {e}")
        
        # Deleta do JSON também (se existir)
        file_path = self._session_file(session_id)
        if file_path.exists():
            file_path.unlink()
            deleted = True
            print(f"✅ Sessão {session_id} deletada do JSON")
        
        return deleted


# Instância global
session_store = SessionStore()


# ========================================================================
# 🆕 SESSION MANAGER AVANÇADO - NOVO SISTEMA DE PERSISTÊNCIA E REUSO
# ========================================================================

from enum import Enum
from datetime import timedelta
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, JSON, Float, Boolean
from sqlalchemy.orm import Session as DBSession
from bot_multidelivery.database import Base
import logging

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Estados da sessão: ciclo de vida completo"""
    CREATED = "created"           # Sessão criada, não iniciada
    OPENED = "opened"             # Usuário abriu, pronto para finalizar romaneio
    STARTED = "started"           # Começou distribuição de entregas
    IN_PROGRESS = "in_progress"   # Entregas em andamento
    COMPLETED = "completed"       # Todas entregas finalizadas
    READ_ONLY = "read_only"       # Histórico congelado, sem alterações


class AdvancedSessionModel(Base):
    """Tabela de Sessões Avançada - núcleo da persistência com reuso"""
    __tablename__ = "sessions_advanced"
    
    id = Column(String(36), primary_key=True)
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.CREATED)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(String(100))
    
    # Dados da sessão (JSON para flexibilidade)
    manifest_data = Column(JSON)  # Dados originais do romaneio importado
    addresses = Column(JSON)      # Lista de endereços processados
    deliverers = Column(JSON)     # Entregadores envolvidos
    route_assignments = Column(JSON)  # Atribuições de rota
    financials = Column(JSON)     # Dados financeiros da sessão
    statistics = Column(JSON)     # Estatísticas gerais
    
    # Rastreabilidade
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(String(1000), nullable=True)
    reused = Column(Boolean, default=False)  # Flag se foi reutilizada


class SessionManager:
    """Gerenciador de persistência com reusabilidade SEM re-import"""
    
    def __init__(self, db: DBSession):
        self.db = db
    
    # ==================== CRIAR/RECUPERAR SESSÃO ====================
    
    def create_session(
        self,
        session_id: str,
        created_by: str,
        manifest_data: Dict = None
    ) -> AdvancedSessionModel:
        """Criar nova sessão vazia, estado CREATED"""
        try:
            session = AdvancedSessionModel(
                id=session_id,
                status=SessionStatus.CREATED,
                created_by=created_by,
                manifest_data=manifest_data or {},
                addresses=[],
                deliverers=[],
                route_assignments=[],
                financials={"total_profit": 0, "total_cost": 0, "total_salary": 0},
                statistics={}
            )
            self.db.add(session)
            self.db.commit()
            logger.info(f"✅ Sessão criada: {session_id}")
            return session
        except Exception as e:
            logger.error(f"❌ Erro ao criar sessão: {e}")
            self.db.rollback()
            raise
    
    def get_session(self, session_id: str) -> Optional[AdvancedSessionModel]:
        """Recuperar sessão existente (SEM re-import!)"""
        session = self.db.query(AdvancedSessionModel).filter(
            AdvancedSessionModel.id == session_id
        ).first()
        
        if session:
            logger.info(f"🔍 Sessão encontrada: {session_id} (status: {session.status})")
        return session
    
    def list_sessions(
        self,
        status: Optional[SessionStatus] = None,
        created_by: Optional[str] = None,
        limit: int = 50
    ) -> List[AdvancedSessionModel]:
        """Listar sessões com filtros"""
        query = self.db.query(AdvancedSessionModel)
        
        if status:
            query = query.filter(AdvancedSessionModel.status == status)
        if created_by:
            query = query.filter(AdvancedSessionModel.created_by == created_by)
        
        return query.order_by(AdvancedSessionModel.created_at.desc()).limit(limit).all()
    
    # ==================== TRANSIÇÕES DE ESTADO ====================
    
    def open_session(self, session_id: str) -> AdvancedSessionModel:
        """Transição: CREATED → OPENED (usuário quer finalizar romaneio SEM re-import)"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Sessão não encontrada: {session_id}")
        
        if session.status not in [SessionStatus.CREATED, SessionStatus.OPENED]:
            raise ValueError(
                f"❌ Não pode abrir sessão em status '{session.status.value}'. "
                f"Use histórico para sessões COMPLETED."
            )
        
        session.status = SessionStatus.OPENED
        session.last_updated = datetime.utcnow()
        self.db.commit()
        logger.info(f"📂 Sessão aberta (SEM re-import): {session_id}")
        return session
    
    def start_session(self, session_id: str) -> AdvancedSessionModel:
        """Transição: OPENED → STARTED (iniciou distribuição)"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Sessão não encontrada: {session_id}")
        
        if session.status != SessionStatus.OPENED:
            raise ValueError(f"❌ Sessão deve estar em OPENED para iniciar")
        
        session.status = SessionStatus.STARTED
        session.started_at = datetime.utcnow()
        session.last_updated = datetime.utcnow()
        self.db.commit()
        logger.info(f"🚀 Sessão iniciada: {session_id}")
        return session
    
    def update_progress(
        self,
        session_id: str,
        route_assignments: List[Dict] = None,
        statistics: Dict = None,
        financials: Dict = None
    ) -> AdvancedSessionModel:
        """Atualizar sessão IN_PROGRESS (salva tudo em tempo real)"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Sessão não encontrada: {session_id}")
        
        session.status = SessionStatus.IN_PROGRESS
        if route_assignments is not None:
            session.route_assignments = route_assignments
        if statistics is not None:
            session.statistics = statistics
        if financials is not None:
            session.financials = financials
        session.last_updated = datetime.utcnow()
        self.db.commit()
        logger.info(f"⏳ Sessão atualizada: {session_id}")
        return session
    
    def complete_session(self, session_id: str) -> AdvancedSessionModel:
        """Transição: IN_PROGRESS → COMPLETED → READ_ONLY"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Sessão não encontrada: {session_id}")
        
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.utcnow()
        session.last_updated = datetime.utcnow()
        self.db.commit()
        
        # Transição automática para READ_ONLY
        self._archive_session(session_id)
        logger.info(f"✅ Sessão completada: {session_id}")
        return session
    
    def _archive_session(self, session_id: str):
        """Mover para READ_ONLY (histórico)"""
        session = self.get_session(session_id)
        if session:
            session.status = SessionStatus.READ_ONLY
            self.db.commit()
            logger.info(f"📚 Sessão arquivada (READ_ONLY): {session_id}")
    
    # ==================== PERSISTÊNCIA DE DADOS ====================
    
    def save_all_data(
        self,
        session_id: str,
        addresses: List[Dict] = None,
        deliverers: List[Dict] = None,
        route_assignments: List[Dict] = None,
        financials: Dict = None,
        statistics: Dict = None
    ) -> AdvancedSessionModel:
        """SALVA TUDO: addresses, deliverers, rotas, financeiro, estatísticas"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Sessão não encontrada: {session_id}")
        
        if addresses is not None:
            session.addresses = addresses
        if deliverers is not None:
            session.deliverers = deliverers
        if route_assignments is not None:
            session.route_assignments = route_assignments
        if financials is not None:
            session.financials = financials
        if statistics is not None:
            session.statistics = statistics
        
        session.last_updated = datetime.utcnow()
        self.db.commit()
        logger.info(f"💾 Todos os dados salvos: {session_id}")
        return session
    
    # ==================== REUSO E CONSULTAS ====================
    
    def can_reuse_session(self, session_id: str) -> bool:
        """Verificar se pode reutilizar SEM re-import"""
        session = self.get_session(session_id)
        if not session:
            return False
        return session.status in [SessionStatus.CREATED, SessionStatus.OPENED]
    
    def get_session_summary(self, session_id: str) -> Dict:
        """Resumo completo para exibição"""
        session = self.get_session(session_id)
        if not session:
            return {}
        
        return {
            "id": session.id,
            "status": session.status.value,
            "created_at": session.created_at.isoformat(),
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "created_by": session.created_by,
            "addresses_count": len(session.addresses or []),
            "deliverers_count": len(session.deliverers or []),
            "financials": session.financials or {},
            "statistics": session.statistics or {},
            "reused": session.reused,
            "last_updated": session.last_updated.isoformat()
        }
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """Obter histórico (READ_ONLY)"""
        sessions = self.list_sessions(
            status=SessionStatus.READ_ONLY,
            limit=limit
        )
        return [self.get_session_summary(s.id) for s in sessions]
