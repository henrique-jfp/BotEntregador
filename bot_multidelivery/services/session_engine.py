"""
⚡ SESSION ENGINE - Sistema de Permapersistência
Sessões vivem, crescem, e podem ser reutilizadas
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

logger = logging.getLogger(__name__)


class SessionEngine:
    """Motor de sessões - gerencia o ciclo de vida completo"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ============================================
    # CRIAR NOVA SESSÃO
    # ============================================
    def create_session(
        self,
        user_id: int,
        session_type: str = "manual",
        file_name: Optional[str] = None
    ) -> str:
        """
        Cria uma nova sessão vazia pronta para receber dados
        Retorna: session_id (UUID)
        """
        from schemas.sessions_schema import DeliverySession, SessionAudit
        
        session_id = str(uuid.uuid4())
        
        new_session = DeliverySession(
            session_id=session_id,
            user_id=user_id,
            status="open",
            session_type=session_type,
            file_name=file_name,
            created_at=datetime.now()
        )
        
        self.db.add(new_session)
        
        # Audit log
        audit = SessionAudit(
            session_id=session_id,
            action="session_created",
            actor_id=user_id,
            details={
                "session_type": session_type,
                "file_name": file_name
            }
        )
        self.db.add(audit)
        self.db.commit()
        
        logger.info(f"✅ Sessão criada: {session_id}")
        return session_id
    
    # ============================================
    # ADICIONAR PACOTES (Sem duplicação)
    # ============================================
    def add_packages_to_session(
        self,
        session_id: str,
        packages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Adiciona pacotes à sessão.
        Smart: Detecta e evita duplicatas por barcode
        """
        from schemas.sessions_schema import SessionPackage, SessionAddress, SessionAudit
        
        added = 0
        duplicates = 0
        
        for pkg in packages:
            barcode = pkg.get("barcode")
            
            # Verifica duplicata NA MESMA SESSÃO
            existing = self.db.query(SessionPackage).filter(
                and_(
                    SessionPackage.session_id == session_id,
                    SessionPackage.barcode == barcode
                )
            ).first()
            
            if existing:
                duplicates += 1
                logger.warning(f"⚠️ Barcode duplicado em sessão: {barcode}")
                continue
            
            package_id = str(uuid.uuid4())
            address_id = str(uuid.uuid4())
            
            # Cria o endereço
            session_address = SessionAddress(
                address_id=address_id,
                session_id=session_id,
                address=pkg.get("address", ""),
                package_count=1
            )
            self.db.add(session_address)
            
            # Cria o pacote
            new_package = SessionPackage(
                package_id=package_id,
                session_id=session_id,
                barcode=barcode,
                address_id=address_id,
                recipient_name=pkg.get("recipient_name", ""),
                recipient_phone=pkg.get("recipient_phone", ""),
                address_full=pkg.get("address", ""),
                package_value=pkg.get("value", 0.0),
                created_at=datetime.now()
            )
            self.db.add(new_package)
            added += 1
        
        # Update session stats
        session = self.db.query(DeliverySession).filter_by(session_id=session_id).first()
        if session:
            session.total_packages += added
        
        self.db.commit()
        
        return {
            "added": added,
            "duplicates": duplicates,
            "total_in_session": session.total_packages if session else 0
        }
    
    # ============================================
    # REUTILIZAR SESSÃO NÃO INICIADA
    # ============================================
    def reuse_session_before_start(
        self,
        session_id: str,
        new_packages: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Se a sessão ainda está em OPEN (não iniciada),
        pode ser reutilizada sem duplicação de dados
        """
        from schemas.sessions_schema import DeliverySession
        
        session = self.db.query(DeliverySession).filter_by(session_id=session_id).first()
        
        if not session:
            return {"error": "Sessão não encontrada"}
        
        if session.status != "open":
            return {
                "error": f"Sessão não pode ser reutilizada - Status: {session.status}"
            }
        
        # Marca como reutilizada
        session.was_reused = True
        session.reuse_count += 1
        
        result = {
            "session_id": session_id,
            "reuse_count": session.reuse_count,
            "current_packages": session.total_packages
        }
        
        # Se houver novos pacotes, adiciona
        if new_packages:
            add_result = self.add_packages_to_session(session_id, new_packages)
            result["add_result"] = add_result
        
        self.db.commit()
        logger.info(f"♻️ Sessão reutilizada: {session_id} (uso #{session.reuse_count})")
        
        return result
    
    # ============================================
    # INICIAR SESSÃO (Distribuir para entregadores)
    # ============================================
    def start_session(
        self,
        session_id: str,
        deliverer_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Inicia a sessão: marca como ACTIVE, distribui pacotes, faz otimização
        """
        from schemas.sessions_schema import (
            DeliverySession, SessionDeliverer, SessionPackage, SessionAudit
        )
        
        session = self.db.query(DeliverySession).filter_by(session_id=session_id).first()
        
        if not session:
            return {"error": "Sessão não encontrada"}
        
        if session.status != "open":
            return {"error": f"Só sessões OPEN podem ser iniciadas. Status: {session.status}"}
        
        # Marca como ativa
        session.status = "active"
        session.started_at = datetime.now()
        
        # Registra entregadores
        session.total_deliverers = len(deliverer_ids)
        
        for deliverer_id in deliverer_ids:
            session_deliverer = SessionDeliverer(
                session_id=session_id,
                deliverer_id=deliverer_id,
                base_salary=3000.0,  # Default, pode mudar
                commission_per_delivery=5.0
            )
            self.db.add(session_deliverer)
        
        # Audit
        audit = SessionAudit(
            session_id=session_id,
            action="session_started",
            details={"deliverer_count": len(deliverer_ids), "total_packages": session.total_packages}
        )
        self.db.add(audit)
        
        self.db.commit()
        
        logger.info(f"🚀 Sessão iniciada: {session_id} com {len(deliverer_ids)} entregadores")
        
        return {
            "session_id": session_id,
            "status": "active",
            "deliverers": len(deliverer_ids),
            "packages": session.total_packages
        }
    
    # ============================================
    # MARCAR ENTREGA COMO COMPLETA
    # ============================================
    def mark_delivery_complete(
        self,
        session_id: str,
        package_id: str,
        deliverer_id: int,
        delivery_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Marca pacote como entregue e auto-calcula financeiro
        """
        from schemas.sessions_schema import (
            SessionPackage, SessionDeliverer, DeliverySession, SessionAudit
        )
        
        package = self.db.query(SessionPackage).filter_by(package_id=package_id).first()
        
        if not package:
            return {"error": "Pacote não encontrado"}
        
        package.delivery_status = "delivered"
        package.delivery_time = datetime.now()
        package.assigned_deliverer_id = deliverer_id
        package.delivery_notes = delivery_notes
        
        # Update entregador stats
        deliverer = self.db.query(SessionDeliverer).filter(
            and_(
                SessionDeliverer.session_id == session_id,
                SessionDeliverer.deliverer_id == deliverer_id
            )
        ).first()
        
        if deliverer:
            deliverer.packages_delivered += 1
            deliverer.total_earned = (
                deliverer.base_salary + 
                (deliverer.packages_delivered * deliverer.commission_per_delivery)
            )
        
        # Update session totals
        session = self.db.query(DeliverySession).filter_by(session_id=session_id).first()
        if session:
            session.total_revenue += package.package_value
            session.total_profit = session.total_revenue - session.total_cost
        
        # Audit
        audit = SessionAudit(
            session_id=session_id,
            action="package_delivered",
            actor_id=deliverer_id,
            details={
                "package_id": package_id,
                "value": package.package_value,
                "delivery_notes": delivery_notes
            }
        )
        self.db.add(audit)
        
        self.db.commit()
        
        return {
            "package_id": package_id,
            "status": "delivered",
            "deliverer_earning": deliverer.total_earned if deliverer else 0
        }
    
    # ============================================
    # FINALIZAR SESSÃO → HISTÓRICO
    # ============================================
    def complete_session(self, session_id: str) -> Dict[str, Any]:
        """
        Fecha a sessão, gera snapshot financeiro, fica read-only
        """
        from schemas.sessions_schema import (
            DeliverySession, SessionDeliverer, SessionAudit
        )
        
        session = self.db.query(DeliverySession).filter_by(session_id=session_id).first()
        
        if not session:
            return {"error": "Sessão não encontrada"}
        
        # Calcula snapshot
        deliverers = self.db.query(SessionDeliverer).filter_by(session_id=session_id).all()
        
        financial_snapshot = {
            "total_revenue": session.total_revenue,
            "total_cost": session.total_cost,
            "total_profit": session.total_profit,
            "deliverers_paid": sum(d.total_earned for d in deliverers),
            "net_profit": session.total_profit - sum(d.total_earned for d in deliverers)
        }
        
        session.financial_snapshot = financial_snapshot
        session.status = "completed"
        session.completed_at = datetime.now()
        session.is_readonly = True
        
        # Audit
        audit = SessionAudit(
            session_id=session_id,
            action="session_completed",
            details=financial_snapshot
        )
        self.db.add(audit)
        
        self.db.commit()
        
        logger.info(f"✅ Sessão finalizada e arquivada: {session_id}")
        logger.info(f"💰 Snapshot: {financial_snapshot}")
        
        return {
            "session_id": session_id,
            "status": "completed",
            "financial_snapshot": financial_snapshot
        }
    
    # ============================================
    # OBTER SESSÃO (Real-time ou Histórico)
    # ============================================
    def get_session_with_links(self, session_id: str) -> Dict[str, Any]:
        """
        Retorna TUDO linkedado: sessão + pacotes + entregadores + financeiro
        """
        from schemas.sessions_schema import (
            DeliverySession, SessionPackage, SessionDeliverer, SessionAddress
        )
        
        session = self.db.query(DeliverySession).filter_by(session_id=session_id).first()
        
        if not session:
            return {"error": "Sessão não encontrada"}
        
        packages = self.db.query(SessionPackage).filter_by(session_id=session_id).all()
        deliverers = self.db.query(SessionDeliverer).filter_by(session_id=session_id).all()
        addresses = self.db.query(SessionAddress).filter_by(session_id=session_id).all()
        
        return {
            "session": {
                "id": session.session_id,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "is_readonly": session.is_readonly,
                "was_reused": session.was_reused,
                "reuse_count": session.reuse_count
            },
            "financial": {
                "total_revenue": session.total_revenue,
                "total_cost": session.total_cost,
                "total_profit": session.total_profit,
                "snapshot": session.financial_snapshot
            },
            "packages": [
                {
                    "id": p.package_id,
                    "barcode": p.barcode,
                    "status": p.delivery_status,
                    "value": p.package_value,
                    "deliverer_id": p.assigned_deliverer_id,
                    "delivery_time": p.delivery_time.isoformat() if p.delivery_time else None
                }
                for p in packages
            ],
            "deliverers": [
                {
                    "id": d.deliverer_id,
                    "packages_delivered": d.packages_delivered,
                    "total_earned": d.total_earned,
                    "base_salary": d.base_salary
                }
                for d in deliverers
            ],
            "addresses": len(addresses),
            "total_packages": session.total_packages
        }
