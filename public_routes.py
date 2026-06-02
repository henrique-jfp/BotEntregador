import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/public", tags=["public"])

MAPS_DIR = os.path.join("data", "maps")
os.makedirs(MAPS_DIR, exist_ok=True)

def _safe_map_path(filename: str) -> str:
    safe_name = os.path.basename(filename)
    return os.path.join(MAPS_DIR, safe_name)

@router.get("/maps/{filename}")
async def get_map_file(filename: str):
    """
    Serve mapas HTML gerados (Acesso Público para WebApp/Links)
    """
    path = _safe_map_path(filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Mapa não encontrado")
    return FileResponse(path, media_type='text/html')
