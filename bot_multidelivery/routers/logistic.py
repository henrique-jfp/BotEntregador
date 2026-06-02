# -*- coding: utf-8 -*-
import os
from fastapi import APIRouter, HTTPException
from typing import List, Dict
from bot_multidelivery.schemas_models import OptimizeInput, AssignRouteInput
from bot_multidelivery.session import session_manager, Route
from bot_multidelivery.models import DeliveryPoint
from bot_multidelivery.clustering import TerritoryDivider
from bot_multidelivery.services import deliverer_service

from bot_multidelivery.colors import get_color_for_index

router = APIRouter(prefix="/routes", tags=["Routes"])

@router.post("/optimize")
async def optimize_routes(data: OptimizeInput):
    """
    Divide e otimiza a rota pela quantidade de entregadores.
    Implementação REAL (Migrado de api_routes.py)
    """
    session = session_manager.get_session(data.session_id) if data.session_id else session_manager.get_current_session()
    
    if not session or not session.romaneios:
        raise HTTPException(status_code=400, detail="Nenhum romaneio importado na sessão.")

    # 1. Coletar todos os pontos
    all_points: List[DeliveryPoint] = []
    for rom in session.romaneios:
        all_points.extend(rom.points)

    # 2. Dividir Territórios (Clustering)
    divider = TerritoryDivider(session.base_lat, session.base_lng)
    clusters = divider.divide_into_clusters(all_points, k=data.num_deliverers)

    # 3. Criar Rotas
    routes: List[Route] = []
    for idx, cluster in enumerate(clusters):
        # Otimiza ordem de entrega (TSP)
        optimized = divider.optimize_cluster_route(cluster)
        color = get_color_for_index(idx)
        
        route = Route(
            id=f"ROTA_{cluster.id + 1}",
            cluster=cluster,
            color=color,
            optimized_order=optimized
        )
        routes.append(route)

    # 4. Salvar na Sessão
    session_manager.set_routes(routes, session.session_id)

    # 5. Gerar Preview para o Frontend
    preview = []
    base_loc = (session.base_lat, session.base_lng, session.base_address) if session.base_lat and session.base_lng else None
    
    # Gerar mini-mapa geral
    map_url = None  # MapGenerator removido (legado)

    entregadores_lista = [{'name': d.name, 'id': str(d.telegram_id)} for d in deliverer_service.get_all_deliverers()]

    for r in routes:
        center = r.cluster.centroid
        preview.append({
            "id": r.id,
            "name": f"Rota {r.id.split('_')[-1]}",
            "packages_count": len(r.optimized_order),
            "color": r.color,
            "center": {"lat": center[0], "lng": center[1]},
            "deliverer_id": None # Ainda não atribuído
        })

    return {
        "status": "success", 
        "optimized": True, 
        "routes": preview,
        "map_url": map_url,
        "server_clusters": len(clusters),
        "available_deliverers": entregadores_lista
    }

@router.post("/assign")
async def assign_route(data: AssignRouteInput):
    """Atribuir rota a entregador"""
    session = session_manager.get_current_session()
    if not session:
        raise HTTPException(status_code=400, detail="Sem sessão ativa")
        
    success = session_manager.assign_route(data.route_id, data.deliverer_id)
    if not success:
         raise HTTPException(status_code=404, detail="Rota não encontrada")
         
    return {"status": "success", "assigned_to": data.deliverer_id}

