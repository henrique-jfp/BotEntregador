"""
⚡ API ENDPOINTS - Sistema de Sessões Completo
Gerencia: criar, reutilizar, distribuir, monitorar, finalizar
"""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from .services.session_engine import SessionEngine
from .services.barcode_ocr_service import scan_barcode_from_image
from .database import get_db
from .security import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"], dependencies=[Depends(verify_api_key)])


# ============================================
# CRIAR NOVA SESSÃO
# ============================================
@router.post("/create")
async def create_session(
    user_id: int,
    session_type: str = "manual",
    file_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Cria uma nova sessão vazia
    Retorna: session_id
    """
    engine = SessionEngine(db)
    session_id = engine.create_session(user_id, session_type, file_name)
    
    return {
        "success": True,
        "session_id": session_id,
        "message": f"Sessão criada. Pronto para receber {session_id}"
    }


# ============================================
# ADICIONAR PACOTES À SESSÃO
# ============================================
@router.post("/{session_id}/packages")
async def add_packages(
    session_id: str,
    packages: List[dict],
    db: Session = Depends(get_db)
):
    """
    Adiciona múltiplos pacotes à sessão
    Smart: Evita duplicatas automaticamente
    
    Esperado:
    {
        "packages": [
            {"barcode": "1234567890123", "recipient_name": "João", "address": "Rua X", "value": 50.0},
            ...
        ]
    }
    """
    engine = SessionEngine(db)
    result = engine.add_packages_to_session(session_id, packages)
    
    return {
        "success": True,
        "added": result["added"],
        "duplicates_skipped": result["duplicates"],
        "total_in_session": result["total_in_session"]
    }


# ============================================
# REUTILIZAR SESSÃO NÃO INICIADA
# ============================================
@router.post("/{session_id}/reuse")
async def reuse_session(
    session_id: str,
    new_packages: Optional[List[dict]] = None,
    db: Session = Depends(get_db)
):
    """
    Reutiliza uma sessão em estado OPEN (não iniciada)
    Permite redistribuir pacotes sem re-import
    """
    engine = SessionEngine(db)
    result = engine.reuse_session_before_start(session_id, new_packages)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {
        "success": True,
        "message": f"Sessão reutilizada {result['reuse_count']}x",
        "result": result
    }


# ============================================
# INICIAR SESSÃO COM DISTRIBUIÇÃO
# ============================================
@router.post("/{session_id}/start")
async def start_session(
    session_id: str,
    deliverer_ids: List[int],
    db: Session = Depends(get_db)
):
    """
    Inicia a sessão: muda status OPEN → ACTIVE
    Registra entregadores que vão fazer as entregas
    """
    engine = SessionEngine(db)
    result = engine.start_session(session_id, deliverer_ids)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {
        "success": True,
        "message": "Sessão iniciada! Entregas em andamento",
        "result": result
    }


# ============================================
# MARCAR ENTREGA COMO COMPLETA
# ============================================
@router.post("/{session_id}/delivery/complete")
async def mark_delivery_complete(
    session_id: str,
    package_id: str,
    deliverer_id: int,
    delivery_notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Marca um pacote como entregue
    Auto-calcula comissão e lucro em tempo real
    """
    engine = SessionEngine(db)
    result = engine.mark_delivery_complete(
        session_id, package_id, deliverer_id, delivery_notes
    )
    
    return {
        "success": True,
        "message": "Entrega registrada!",
        "result": result
    }


# ============================================
# FINALIZAR SESSÃO → HISTÓRICO
# ============================================
@router.post("/{session_id}/complete")
async def complete_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Finaliza a sessão: ACTIVE → COMPLETED
    - Gera snapshot financeiro
    - Torna read-only
    - Arquivo como histórico
    - 🧠 APRENDE com a sessão (Cérebro Geográfico)
    """
    engine = SessionEngine(db)
    result = engine.complete_session(session_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # 🧠 Ativar aprendizado geográfico
    try:
        from bot_multidelivery.services.geographic_brain import geographic_brain
        geographic_brain.learn_from_session(session_id)
        logger.info(f"🎓 Cérebro Geográfico aprendeu com sessão {session_id}")
    except Exception as e:
        logger.error(f"⚠️ Erro ao aprender com sessão: {e}")
    
    return {
        "success": True,
        "message": "Sessão finalizada e arquivada!"
    }


# ============================================
# OBTER SESSÃO COM TODOS OS LINKS (Real-time)
# ============================================
@router.get("/{session_id}")
async def get_session_complete(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna TUDO linkedado em tempo real:
    - Informações da sessão
    - Todos os pacotes
    - Todos os entregadores
    - Financeiro
    - Histórico de auditoria
    """
    engine = SessionEngine(db)
    result = engine.get_session_with_links(session_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return {
        "success": True,
        "data": result
    }


# ============================================
# LISTAR TODAS AS SESSÕES DO USUÁRIO
# ============================================
@router.get("/user/{user_id}")
async def list_user_sessions(
    user_id: int,
    status: Optional[str] = None,  # open, active, completed
    db: Session = Depends(get_db)
):
    """
    Lista todas as sessões do usuário
    Opcional: filtra por status (open/active/completed)
    """
    from schemas.sessions_schema import DeliverySession
    
    query = db.query(DeliverySession).filter_by(user_id=user_id)
    
    if status:
        query = query.filter_by(status=status)
    
    sessions = query.all()
    
    return {
        "success": True,
        "total": len(sessions),
        "sessions": [
            {
                "id": s.session_id,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
                "total_packages": s.total_packages,
                "total_profit": s.total_profit
            }
            for s in sessions
        ]
    }


# ============================================
# SCANNER OCR: Quando a câmera falha
# ============================================
@router.post("/{session_id}/scan-barcode")
async def scan_barcode_endpoint(
    session_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint para scanner de código de barras com OCR
    Quando a câmera falha, envia foto e deixa a IA decodificar
    
    - Tenta: ZBar → Tesseract OCR → ML Template Matching
    - Retorna: barcode encontrado + confiança
    """
    try:
        # Lê arquivo
        image_bytes = await file.read()
        
        # Escaneia
        result = await scan_barcode_from_image(image_bytes)
        
        if result["success"]:
            barcode = result["barcode"]
            
            # Auto-vincula o pacote se encontrado na sessão
            from schemas.sessions_schema import SessionPackage
            
            package = db.query(SessionPackage).filter(
                SessionPackage.barcode == barcode,
                SessionPackage.session_id == session_id
            ).first()
            
            if package:
                package.barcode_ocr_attempt = True
                db.commit()
                return {
                    "success": True,
                    "barcode": barcode,
                    "package_found": True,
                    "package_id": package.package_id,
                    "metadata": result["metadata"]
                }
            else:
                return {
                    "success": True,
                    "barcode": barcode,
                    "package_found": False,
                    "message": "Código encontrado mas não existe nesta sessão",
                    "metadata": result["metadata"]
                }
        else:
            return {
                "success": False,
                "error": "Não consegui decodificar o código de barras",
                "metadata": result["metadata"]
            }
    
    except Exception as e:
        logger.error(f"❌ Erro no scanner: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar imagem: {e}")


# ============================================
# DASHBOARD REAL-TIME (WebSocket seria melhor, mas isso é REST)
# ============================================
@router.get("/{session_id}/dashboard")
async def get_session_dashboard(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Dashboard em tempo real de uma sessão ativa
    Mostra: progresso, ganhos, entregas, entregadores
    """
    engine = SessionEngine(db)
    session_data = engine.get_session_with_links(session_id)
    
    if "error" in session_data:
        raise HTTPException(status_code=404, detail=session_data["error"])
    
    packages = session_data["packages"]
    deliverers = session_data["deliverers"]
    financial = session_data["financial"]
    
    # Calcula stats
    delivered = len([p for p in packages if p["status"] == "delivered"])
    pending = len([p for p in packages if p["status"] == "pending"])
    progress = (delivered / len(packages) * 100) if packages else 0
    
    return {
        "success": True,
        "session_id": session_id,
        "status": session_data["session"]["status"],
        "progress": {
            "delivered": delivered,
            "pending": pending,
            "total": len(packages),
            "percentage": round(progress, 2)
        },
        "deliverers_count": len(deliverers),
        "is_readonly": session_data["session"]["is_readonly"],
        "was_reused": session_data["session"]["was_reused"],
        "reuse_count": session_data["session"]["reuse_count"]
    }
