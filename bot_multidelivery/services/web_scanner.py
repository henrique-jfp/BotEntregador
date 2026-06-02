"""
🎯 WEB SCANNER - Sistema de separação via câmera
Scan automático de barcodes usando câmera do celular
"""
import logging
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
from pathlib import Path
from .barcode_separator import barcode_separator

logger = logging.getLogger(__name__)

# FastAPI app para web scanner
scanner_app = FastAPI(title="Bot Multi-Entregador API")

# 🛡️ CONFIGURAÇÃO DE SEGURANÇA (CORS)
# Permite que o Frontend (React) converse com o Backend sem bloqueios
scanner_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, ideal restringir para seu domínio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ScanRequest(BaseModel):
    barcode: str
    
class ScanResponse(BaseModel):
    success: bool
    barcode: str
    color: Optional[str] = None
    color_name: Optional[str] = None
    deliverer_name: Optional[str] = None
    address: Optional[str] = None
    position: Optional[int] = None
    total: Optional[int] = None
    progress_count: Optional[int] = None
    progress_total: Optional[int] = None
    progress_percent: Optional[int] = None
    message: Optional[str] = None


@scanner_app.get("/scanner", response_class=HTMLResponse)
async def get_scanner_page():
    """Serve a página HTML do scanner"""
    html_path = Path(__file__).parent.parent / "templates" / "scanner.html"
    
    if not html_path.exists():
        return HTMLResponse(
            content="<h1>Scanner HTML não encontrado</h1>",
            status_code=404
        )
    
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@scanner_app.post("/api/scan", response_model=ScanResponse)
async def scan_barcode(request: ScanRequest):
    """
    Endpoint para processar scan de barcode
    Retorna informações da rota/cor do pacote
    """
    barcode = request.barcode.strip()
    
    if not barcode:
        raise HTTPException(status_code=400, detail="Barcode vazio")
    
    # Verifica se modo separação está ativo
    if not barcode_separator.active:
        return ScanResponse(
            success=False,
            barcode=barcode,
            message="❌ Modo separação não está ativo. Use /modo_separacao no bot."
        )
    
    # Busca assignment do pacote
    assignment = barcode_separator.assignments.get(barcode)
    
    if not assignment:
        return ScanResponse(
            success=False,
            barcode=barcode,
            message=f"❌ Código '{barcode}' não encontrado nas rotas atuais."
        )
    
    # Marca como escaneado
    barcode_separator.scanned.add(barcode)
    
    # Calcula progresso
    progress_count = len(barcode_separator.scanned)
    progress_total = len(barcode_separator.assignments)
    progress_percent = int((progress_count / progress_total) * 100) if progress_total > 0 else 0
    
    # Mapa de cores para hex
    # assignment.color já é string hex (ex: '#ef4444')
    # assignment.color_name já é string amigável (ex: '🔴 VERMELHO')
    
    return ScanResponse(
        success=True,
        barcode=barcode,
        color=assignment.color,
        color_name=assignment.color_name,
        deliverer_name=assignment.deliverer_name,
        address=assignment.address[:60],
        position=assignment.position,
        total=assignment.total_in_route,
        progress_count=progress_count,
        progress_total=progress_total,
        progress_percent=progress_percent,
        message="✅ Pacote escaneado com sucesso!"
    )


@scanner_app.get("/api/status")
async def get_status():
    """Retorna status atual da separação"""
    if not barcode_separator.active:
        return JSONResponse({
            "active": False,
            "message": "Modo separação não ativo"
        })
    
    progress_count = len(barcode_separator.scanned)
    progress_total = len(barcode_separator.assignments)
    progress_percent = int((progress_count / progress_total) * 100) if progress_total > 0 else 0
    
    return JSONResponse({
        "active": True,
        "progress_count": progress_count,
        "progress_total": progress_total,
        "progress_percent": progress_percent
    })


@scanner_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para updates em tempo real"""
    await websocket.accept()
    logger.info("🔌 WebSocket conectado")
    
    try:
        while True:
            # Mantém conexão viva
            await websocket.receive_text()
    except Exception as e:
        logger.info(f"🔌 WebSocket desconectado: {e}")
