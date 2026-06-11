# -*- coding: utf-8 -*-
import os
from fastapi import APIRouter, HTTPException
from typing import List, Dict
from bot_multidelivery.schemas_models import OptimizeInput, AssignRouteInput, SaveCreativeRoutesInput
from bot_multidelivery.session import session_manager, Route, RouteStatus
from bot_multidelivery.models import DeliveryPoint, Cluster
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

@router.post("/creative/save")
async def save_creative_routes(data: SaveCreativeRoutesInput):
    """
    Salva as rotas criadas manualmente no Modo Criativo.
    """
    session = session_manager.get_session(data.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    # Coletar todos os pontos disponíveis na sessão
    all_points_map = {}
    for rom in session.romaneios:
        for point in rom.points:
            all_points_map[point.package_id] = point

    divider = TerritoryDivider(session.base_lat or -22.9068, session.base_lng or -43.1729)
    
    new_routes = []
    
    for c_route in data.routes:
        route_points = []
        for pkg_id in c_route.package_ids:
            if pkg_id in all_points_map:
                route_points.append(all_points_map[pkg_id])
                
        if not route_points:
            continue
            
        # Cria um cluster dummy para a rota
        cluster = Cluster(
            id=len(new_routes),
            center_lat=sum(p.lat for p in route_points) / len(route_points) if route_points else 0.0,
            center_lng=sum(p.lng for p in route_points) / len(route_points) if route_points else 0.0,
            points=route_points
        )
        
        # Otimiza a ordem dos pontos dessa rota manual usando a mesma lógica do auto
        optimized_order = divider.optimize_cluster_route(cluster)
        
        new_route = Route(
            id=c_route.id,
            cluster=cluster,
            color=c_route.color,
            assigned_to_telegram_id=c_route.assigned_to_telegram_id,
            assigned_to_name=c_route.assigned_to_name,
            status=RouteStatus.PENDING,
            optimized_order=optimized_order
        )
        new_routes.append(new_route)

    session.routes = new_routes
    session.current_step = 'routes_created'
    session.num_deliverers = len(new_routes)
    session_manager.save_session(session)

    return {
        "status": "success",
        "message": f"{len(new_routes)} rotas salvas com sucesso.",
        "session_id": session.session_id
    }

