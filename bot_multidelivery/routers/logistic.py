# -*- coding: utf-8 -*-
import os
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, status, Query, Body
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional
from pydantic import BaseModel
from bot_multidelivery.schemas_models import OptimizeInput, AssignRouteInput, SaveCreativeRoutesInput
from bot_multidelivery.session import session_manager, Route, RouteStatus
from bot_multidelivery.models import DeliveryPoint, Cluster
from bot_multidelivery.clustering import TerritoryDivider
from bot_multidelivery.services.deliverer_service import deliverer_service
from bot_multidelivery.persistence import data_store
from bot_multidelivery.colors import get_color_for_index

router = APIRouter(prefix="/routes", tags=["Routes"])
logger = logging.getLogger(__name__)

# --- Pydantic Models ---
class AssignRoutesRequest(BaseModel):
    session_id: str
    assignments: Dict[str, int]  # {route_id: deliverer_telegram_id}

# ============================================
# FUNÇÃO AUXILIAR DE NOTIFICAÇÃO (BACKGROUND)
# ============================================
async def process_notifications(session_id: str, assignments: Dict[str, int]):
    """Processa o envio de notificações em segundo plano para não travar a UI"""
    from bot_multidelivery.services.telegram_notifier import notify_route_assigned
    
    session = session_manager.get_session(session_id)
    if not session:
        logger.error(f"❌ Sessão {session_id} não encontrada para notificações")
        return

    for route_id, deliverer_id in assignments.items():
        route = next((r for r in session.routes if str(r.id) == str(route_id)), None)
        if not route:
            continue

        logger.info(f"📱 Notificando entregador {deliverer_id} para rota {route.id}...")
        
        try:
            # Preparar dados
            coordinates = None
            if hasattr(route, 'optimized_order') and route.optimized_order:
                 coordinates = [(p.lat, p.lng) for p in route.optimized_order if hasattr(p, 'lat') and p.lat]
            
            # Usar pontos da rota para endereços (compatibilidade com manual e auto)
            pts = []
            if hasattr(route, 'cluster') and route.cluster and hasattr(route.cluster, 'points'):
                pts = route.cluster.points
            elif hasattr(route, 'optimized_order') and route.optimized_order:
                pts = route.optimized_order
                
            addresses = [p.address for p in pts] if pts else []

            await notify_route_assigned(
                telegram_id=deliverer_id,
                route_color=route.color,
                total_packages=route.total_packages,
                distance_km=route.total_distance_km or 0,
                addresses=addresses,
                webapp_url=None,
                coordinates=coordinates
            )
        except Exception as e:
            logger.error(f"🚨 Erro ao notificar rota {route_id}: {e}", exc_info=True)

# ============================================
# ENDPOINTS DE GESTÃO DE ROTAS
# ============================================

@router.post("/optimize")
async def optimize_routes(data: OptimizeInput):
    """Divide e otimiza a rota automaticamente."""
    session = session_manager.get_session(data.session_id) if data.session_id else session_manager.get_current_session()
    
    if not session or not session.romaneios:
        raise HTTPException(status_code=400, detail="Nenhum romaneio importado na sessão.")

    all_points: List[DeliveryPoint] = []
    for rom in session.romaneios:
        all_points.extend(rom.points)

    divider = TerritoryDivider(session.base_lat, session.base_lng)
    clusters = divider.divide_into_clusters(all_points, k=data.num_deliverers)

    routes: List[Route] = []
    for idx, cluster in enumerate(clusters):
        optimized = divider.optimize_cluster_route(cluster)
        color = get_color_for_index(idx)
        
        route = Route(
            id=f"ROTA_{cluster.id + 1}",
            cluster=cluster,
            color=color,
            optimized_order=optimized
        )
        routes.append(route)

    session_manager.set_routes(routes, session.session_id)

    preview = []
    entregadores_lista = [{'name': d.name, 'id': str(d.telegram_id)} for d in deliverer_service.get_all_deliverers()]

    for r in routes:
        center = r.cluster.centroid
        preview.append({
            "id": r.id,
            "name": f"Rota {r.id.split('_')[-1]}",
            "packages_count": len(r.optimized_order),
            "color": r.color,
            "center": {"lat": center[0], "lng": center[1]},
            "deliverer_id": None
        })

    return {
        "status": "success", 
        "routes": preview,
        "available_deliverers": entregadores_lista
    }

@router.post("/assign-multiple")
async def assign_multiple_routes(background_tasks: BackgroundTasks, request: AssignRoutesRequest = Body(...)):
    """Atribui múltiplas rotas e notifica em background."""
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    results = {}
    for route_id, deliverer_id in request.assignments.items():
        route = next((r for r in session.routes if str(r.id) == str(route_id)), None)
        if not route:
            raise HTTPException(status_code=404, detail=f"Rota {route_id} não encontrada")
        
        deliverer = data_store.get_deliverer(deliverer_id)
        if not deliverer:
            raise HTTPException(status_code=404, detail=f"Entregador {deliverer_id} não encontrado")

        route.assigned_to_telegram_id = deliverer_id
        route.assigned_to_name = deliverer.name
        results[route_id] = {"deliverer_id": deliverer_id, "deliverer_name": deliverer.name}

    session_manager.save_session(session)
    background_tasks.add_task(process_notifications, request.session_id, request.assignments)

    return {"status": "success", "assignments": results}

@router.post("/assign")
async def assign_route(data: AssignRouteInput):
    """Atribuir rota individual (legado/fallback)."""
    session = session_manager.get_current_session()
    if not session:
        raise HTTPException(status_code=400, detail="Sem sessão ativa")
    success = session_manager.assign_route(data.route_id, data.deliverer_id)
    if not success:
         raise HTTPException(status_code=404, detail="Rota não encontrada")
    return {"status": "success"}

@router.post("/creative/save")
async def save_creative_routes(data: SaveCreativeRoutesInput):
    """Salva rotas manuais e sequencia automaticamente."""
    session = session_manager.get_session(data.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    all_points_map = {p.package_id: p for rom in session.romaneios for p in rom.points}
    divider = TerritoryDivider(session.base_lat or -22.9068, session.base_lng or -43.1729)
    new_routes = []
    
    for c_route in data.routes:
        route_points = [all_points_map[pid] for pid in c_route.package_ids if pid in all_points_map]
        if not route_points: continue
            
        cluster = Cluster(
            id=len(new_routes),
            center_lat=sum(p.lat for p in route_points) / len(route_points),
            center_lng=sum(p.lng for p in route_points) / len(route_points),
            points=route_points
        )
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
    session_manager.save_session(session)
    return {"status": "success", "session_id": session.session_id}

@router.post("/start")
async def start_routes(session_id: str = Query(...)):
    """Inicia as rotas para entrega."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    for r in session.routes: r.status = RouteStatus.IN_TRANSIT
    session.current_step = "separating"
    session_manager.save_session(session)
    return {"status": "success"}
