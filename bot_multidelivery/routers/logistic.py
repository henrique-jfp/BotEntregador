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


def build_route_preview(route: Route, idx: int) -> Dict:
    points = route.optimized_order or []
    total_packages = len(points)
    return {
        "route_id": route.id,
        "id": route.id,
        "name": f"Rota {idx + 1}",
        "total_stops": total_packages,
        "total_packages": total_packages,
        "total_points": total_packages,
        "packages_count": total_packages,
        "percentage_load": 0,
        "color": route.color,
        "map_url": None,
        "points_sample": [
            {
                "id": p.package_id,
                "address": p.address,
                "lat": p.lat,
                "lng": p.lng,
                "bairro": getattr(p, "bairro", ""),
                "cep": getattr(p, "cep", ""),
            }
            for p in points
            if getattr(p, "lat", None) and getattr(p, "lng", None)
        ],
        "assigned_to": route.assigned_to_name,
        "assigned_to_id": route.assigned_to_telegram_id,
    }

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

@router.post("/divide-and-assign")
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
        
        # ID Único: prefixado com session_id para evitar conflitos no DB
        route_id = f"{session.session_id}_ROTA_{cluster.id + 1}"
        
        route = Route(
            id=route_id,
            cluster=cluster,
            color=color,
            optimized_order=optimized
        )
        routes.append(route)

    session_manager.set_routes(routes, session.session_id)

    preview = []
    entregadores_lista = [{'name': d.name, 'id': str(d.telegram_id)} for d in deliverer_service.get_all_deliverers()]

    total_route_packages = sum(len(r.optimized_order or []) for r in routes) or 1
    for idx, r in enumerate(routes):
        center = r.cluster.centroid if r.cluster else (session.base_lat, session.base_lng)
        route_preview = build_route_preview(r, idx)
        route_preview.update({
            "route_id": r.id,  # Mapeamento para o frontend RouteAnalysisView.jsx
            "id": r.id,
            "name": f"Rota {r.id.split('_')[-1]}",
            "total_packages": len(r.optimized_order), # Mapeamento frontend
            "total_points": len(r.optimized_order),   # Mapeamento frontend
            "packages_count": len(r.optimized_order),
            "percentage_load": round(len(r.optimized_order or []) / total_route_packages * 100),
            "color": r.color,
            "center": {"lat": center[0], "lng": center[1]},
            "deliverer_id": None
        })
        preview.append(route_preview)

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
        # Busca flexível por ID (string ou objeto)
        route = next((r for r in session.routes if str(r.id) == str(route_id)), None)
        if not route:
            # Fallback: se o frontend mandou apenas o sufixo (ex: ROTA_1), tenta encontrar
            route = next((r for r in session.routes if r.id.endswith(str(route_id))), None)
            
        if not route:
            logger.error(f"❌ Rota {route_id} não encontrada na sessão {session.session_id}. Disponíveis: {[r.id for r in session.routes]}")
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
    """Atribuir rota individual."""
    # Busca por session_id se fornecido, senão usa atual
    session = session_manager.get_session(data.session_id) if data.session_id else session_manager.get_current_session()
    
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
        
    success = session_manager.assign_route(data.route_id, data.deliverer_id, session_id=session.session_id)
    
    if not success:
        # Tenta busca flexível se falhou (compatibilidade com prefixos)
        for r in session.routes:
            if r.id.endswith(data.route_id):
                success = session_manager.assign_route(r.id, data.deliverer_id, session_id=session.session_id)
                break
                
    if not success:
         raise HTTPException(status_code=404, detail=f"Rota {data.route_id} não encontrada na sessão")
         
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
        
        # ID Único prefixado
        creative_id = f"{session.session_id}_{c_route.id}"
        
        new_route = Route(
            id=creative_id,
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

    total_route_packages = sum(len(r.optimized_order or []) for r in new_routes) or 1
    routes_preview = []
    for idx, route in enumerate(new_routes):
        route_preview = build_route_preview(route, idx)
        route_preview["percentage_load"] = round(len(route.optimized_order or []) / total_route_packages * 100)
        routes_preview.append(route_preview)

    return {
        "status": "success",
        "session_id": session.session_id,
        "routes": routes_preview,
        "assignments": {
            r.id: r.assigned_to_telegram_id
            for r in new_routes
            if r.assigned_to_telegram_id
        }
    }

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
