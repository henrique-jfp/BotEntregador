"""
Router para Aba Separação - Bipagem de Pacotes com Integração de Rotas
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from bot_multidelivery.session import session_manager
from bot_multidelivery.persistence import data_store
from bot_multidelivery.services.barcode_separator import barcode_separator

# Logger DEVE ser definido antes do try-except
logger = logging.getLogger(__name__)

# Import opcional para pyzbar (requer libzbar nativo)
try:
    from pyzbar.pyzbar import decode as decode_barcode
    BARCODE_SCANNER_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ pyzbar não disponível - scanner de código de barras desabilitado")
    BARCODE_SCANNER_AVAILABLE = False
    decode_barcode = None

from PIL import Image
import io

router = APIRouter(prefix="/separation", tags=["Separation"])


@router.post("/start")
async def start_separation_session():
    """
    Inicia uma sessão de separação global.
    Retorna dados da sessão atual ativa.
    """
    try:
        # Usar sessão ativa atual
        active_session = session_manager.get_active_session()
        
        if not active_session:
            # Retornar estado vazio se não há sessão
            return {
                "success": True,
                "session": {
                    "id": None,
                    "total_packages": 0,
                    "scanned_packages": 0,
                    "progress": 0
                }
            }
        
        # Inicializa modo separação com assignments reais
        barcode_separator.start_separation_mode(active_session)
        total_points = len(barcode_separator.assignments)
        scanned_points = len(barcode_separator.scanned)
        progress = int((scanned_points / total_points) * 100) if total_points > 0 else 0

        return {
            "success": True,
            "session": {
                "id": active_session.session_id,
                "total_packages": total_points,
                "scanned_packages": scanned_points,
                "progress": progress
            }
        }
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar separação: {str(e)}")
        return {
            "success": False,
            "session": None,
            "error": str(e)
        }


class ScanRequest(BaseModel):
    barcode: str


@router.post("/scan")
async def scan_barcode(request: ScanRequest):
    """
    Processa um código de barras bipado.
    Endpoint simplificado que usa a sessão ativa.
    """
    barcode = request.barcode.strip() if request.barcode else ""
    
    try:
        active_session = session_manager.get_active_session()
        
        if not active_session:
            raise HTTPException(status_code=404, detail="Nenhuma sessão ativa")
        
        if not active_session.routes:
            raise HTTPException(status_code=400, detail="Nenhuma rota importada")
        
        if not barcode:
            raise HTTPException(status_code=400, detail="Código de barras não informado")
        
        # Garante que o modo separação está ativo e alinhado com a sessão atual
        if (not barcode_separator.active) or (barcode_separator.session_id != active_session.session_id):
            barcode_separator.start_separation_mode(active_session)

        # Busca assignment direto
        assignment = barcode_separator.assignments.get(barcode.strip().upper())
        if assignment:
            barcode_separator.scanned.add(assignment.package_id)

            total_points = len(barcode_separator.assignments)
            scanned_points = len(barcode_separator.scanned)
            progress = int((scanned_points / total_points) * 100) if total_points > 0 else 0

            return {
                "status": "found",
                "message": "✅ Pacote encontrado!",
                "route_color": assignment.color,
                "route_name": assignment.color_name,
                "deliverer": assignment.deliverer_name,
                "sequence": assignment.position,
                "total_in_route": assignment.total_in_route,
                "address": assignment.address,
                "progress": {
                    "scanned": scanned_points,
                    "total": total_points,
                    "percentage": progress
                }
            }
        
        # Não encontrado
        logger.warning(f"⚠️ Código {barcode} não encontrado")
        return {
            "status": "not_found",
            "message": f"❌ Pacote '{barcode}' não encontrado nas rotas",
            "barcode": barcode
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao processar scan: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/barcode-lookup")
async def lookup_barcode(
    session_id: str = Query(...),
    barcode: str = Query(...),
    image_base64: str = Query(None)
):
    """
    Quando um pacote é bipado:
    1. Procura o código de barras nos romaneios importados
    2. Identifica em qual rota ele está
    3. Retorna: "Este pacote é da ROTA AZUL PARADA 2"
    """
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")
        
        if not session.routes:
            raise HTTPException(status_code=400, detail="Nenhuma rota iniciada")
        
        # Procurar o pacote em todas as rotas
        for route in session.routes:
            for sequence_idx, point in enumerate(route.optimized_order):
                # Comparar código de barras (pode estar no address ou ter sido parseado)
                if barcode.lower() in str(point.address).lower() or barcode == point.id:
                    
                    response = {
                        "status": "found",
                        "message": f"✅ Pacote encontrado",
                        "details": {
                            "route_color": route.color,
                            "deliverer": route.assigned_to_name or "Não atribuído",
                            "sequence": sequence_idx + 1,
                            "total_sequence": route.total_packages,
                            "address": point.address,
                            "lat": point.lat,
                            "lng": point.lng
                        },
                        "formatted_message": f"🎯 Rota {route.color} | Parada {sequence_idx + 1} de {route.total_packages}\n📍 {point.address}"
                    }
                    
                    logger.info(f"✅ Código encontrado: {barcode} → {route.color} Parada {sequence_idx + 1}")
                    return response
        
        # Não encontrado
        logger.warning(f"⚠️ Código {barcode} não encontrado nas rotas")
        return {
            "status": "not_found",
            "message": "❌ Pacote não encontrado nas rotas importadas",
            "barcode": barcode
        }
    
    except Exception as e:
        logger.error(f"❌ Erro ao procurar código: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/barcode-image")
async def lookup_barcode_from_image(
    session_id: str = Query(...),
    image_base64: str = Query(...)
):
    """
    Decodifica código de barras de uma imagem
    """
    if not BARCODE_SCANNER_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Scanner de código de barras não disponível (libzbar ausente)"
        )
    
    try:
        # Decodificar base64 → imagem
        import base64
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        
        # Ler código de barras
        barcodes = decode_barcode(image)
        
        if not barcodes:
            return {
                "status": "no_barcode",
                "message": "Nenhum código de barras detectado na imagem"
            }
        
        barcode_str = barcodes[0].data.decode('utf-8')
        
        # Procurar como acima
        return await lookup_barcode(session_id=session_id, barcode=barcode_str)
    
    except Exception as e:
        logger.error(f"❌ Erro ao decodificar imagem: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Erro ao processar imagem: {str(e)}")


@router.get("/progress/{session_id}")
async def get_separation_progress(session_id: str):
    """
    Retorna progresso geral de separação
    """
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")
        
        total_points = sum(len(r.optimized_order) for r in session.routes)
        total_separated = sum(len(r.delivered_packages) for r in session.routes)
        
        return {
            "session_id": session_id,
            "total_packages": total_points,
            "separated": total_separated,
            "pending": total_points - total_separated,
            "percentage": (total_separated / total_points * 100) if total_points > 0 else 0,
            "routes_status": [
                {
                    "route_id": r.id,
                    "color": r.color,
                    "deliverer": r.assigned_to_name,
                    "total": r.total_packages,
                    "separated": r.delivered_count,
                    "pending": r.pending_count,
                    "completion": f"{r.completion_rate:.1f}%"
                }
                for r in session.routes
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
