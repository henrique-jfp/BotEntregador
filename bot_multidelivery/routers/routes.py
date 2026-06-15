"""
Router para Gestão Completa de Rotas
Divisão por entregadores, coloração, sequenciação e envio
"""
import logging
from fastapi import APIRouter, HTTPException, Query, Body, Form, status, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional
from pydantic import BaseModel
from bot_multidelivery.session import session_manager, Route, RouteStatus
import uuid
import time
from bot_multidelivery.clustering import DeliveryPoint, haversine_distance
from bot_multidelivery.services.zone_utils import ZoneUtils
from bot_multidelivery.services.vertical_grouping import group_by_cep_condominio
from bot_multidelivery.services.microzoner import MicroZoner
from bot_multidelivery.services.pedestrian_router import PedestrianRouter
from bot_multidelivery.colors import get_color_for_index

from bot_multidelivery.services.deliverer_service import deliverer_service
from bot_multidelivery.services.route_analyzer import route_analyzer
from bot_multidelivery.services.geocoding_service import geocoding_service
from bot_multidelivery.persistence import data_store
from bot_multidelivery.services.static_map_generator import StaticMapGenerator
import asyncio

router = APIRouter(prefix="/routes", tags=["Routes"])
logger = logging.getLogger(__name__)

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
            
            addresses = [p.address for p in route.points] if hasattr(route, 'points') else []

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
# ENDPOINT BATCH: ATRIBUIR MULTIPLAS ROTAS
# ============================================
@router.post("/assign-multiple", status_code=200)
async def assign_multiple_routes(background_tasks: BackgroundTasks, request: AssignRoutesRequest = Body(...)):
    """
    Atribui múltiplas rotas a entregadores de uma vez (batch).
    Agora usa BackgroundTasks para notificações, tornando a resposta instantânea.
    """
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    if not session.routes:
        raise HTTPException(status_code=400, detail="Nenhuma rota criada ainda para esta sessão")

    results = {}
    
    try:
        # Etapa 1: Validar e atribuir rotas na memória
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
            logger.info(f"✅ Rota {route.id} atribuída a {deliverer.name}")

        # Persistir as atribuições
        session_manager.save_session(session)

        # Etapa 2: Agendar notificações em background
        background_tasks.add_task(process_notifications, request.session_id, request.assignments)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "message": "Atribuições salvas. Notificações sendo enviadas em background.",
                "assignments": results
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🚨 Erro crítico em assign_multiple_routes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

        
    except HTTPException as http_exc:
        # Rollback em caso de erro de validação/atribuição
        logger.warning(f"Rollback de atribuições devido a erro: {http_exc.detail}")
        for r in session.routes:
            if r.id in original_assignments:
                r.assigned_to_telegram_id, r.assigned_to_name = original_assignments[r.id]
        raise http_exc
        
    except Exception as e:
        # Rollback para exceções inesperadas
        logger.error(f"Erro inesperado na atribuição batch, fazendo rollback: {e}", exc_info=True)
        for r in session.routes:
            if r.id in original_assignments:
                r.assigned_to_telegram_id, r.assigned_to_name = original_assignments[r.id]
        raise HTTPException(status_code=500, detail=f"Erro interno no servidor: {e}")
"""
Router para Gestão Completa de Rotas
Divisão por entregadores, coloração, sequenciação e envio
"""
import logging
from fastapi import APIRouter, HTTPException, Query, Body, Form
from typing import List, Dict, Optional
from pydantic import BaseModel
from bot_multidelivery.session import session_manager, Route, RouteStatus
import uuid
import time
from bot_multidelivery.clustering import DeliveryPoint, haversine_distance
from bot_multidelivery.services.zone_utils import ZoneUtils
from bot_multidelivery.services.vertical_grouping import group_by_cep_condominio
from bot_multidelivery.services.microzoner import MicroZoner
from bot_multidelivery.services.pedestrian_router import PedestrianRouter
from bot_multidelivery.colors import get_color_for_index

from bot_multidelivery.services.deliverer_service import deliverer_service
from bot_multidelivery.services.route_analyzer import route_analyzer
from bot_multidelivery.services.geocoding_service import geocoding_service
from bot_multidelivery.persistence import data_store
import asyncio

router = APIRouter(prefix="/routes", tags=["Routes"])
logger = logging.getLogger(__name__)

# ============================================
# PYDANTIC MODELS
# ============================================

class DivideRoutesRequest(BaseModel):
    session_id: str
    num_deliverers: int
    deliverer_ids: Optional[List[int]] = []
    base_lat: Optional[float] = None  # Localização da base (partida das rotas)
    base_lng: Optional[float] = None

class AssignRoutesRequest(BaseModel):
    session_id: str
    assignments: Dict[str, int]  # {route_id: deliverer_telegram_id}

class AssignSingleRouteRequest(BaseModel):
    route_id: str
    deliverer_id: int

# ============================================
# ENDPOINTS
# ============================================

@router.post("/assign")
async def assign_single_route(request: AssignSingleRouteRequest = Body(...)):
    """
    Atribui uma rota específica a um entregador (UI de dropdown)
    Atualiza localmente sem enviar notificação ainda
    """
    try:
        # Buscar sessão ativa
        session = session_manager.get_active_session()
        if not session:
            raise HTTPException(status_code=404, detail="Nenhuma sessão ativa")
        
        if not session.routes:
            raise HTTPException(status_code=400, detail="Nenhuma rota criada ainda")
        
        # Encontrar a rota
        route = next((r for r in session.routes if r.id == request.route_id), None)
        if not route:
            raise HTTPException(status_code=404, detail=f"Rota {request.route_id} não encontrada")
        
        # Buscar entregador
        deliverer = data_store.get_deliverer(request.deliverer_id)
        if not deliverer:
            raise HTTPException(status_code=404, detail=f"Entregador {request.deliverer_id} não encontrado")
        
        # Atribuir
        route.assigned_to_telegram_id = request.deliverer_id
        route.assigned_to_name = deliverer.name
        session_manager.save_session(session)
        
        logger.info(f"✅ Rota {route.id} atribuída a {deliverer.name}")
        
        return {
            "status": "success",
            "route_id": route.id,
            "deliverer_id": request.deliverer_id,
            "deliverer_name": deliverer.name
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao atribuir rota: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/analyze-addresses")
async def analyze_addresses(
    addresses_text: str = Form(...),
    route_value: float = Form(...)
):
    """
    Analisa lista de endereços (texto) e retorna stats + recomendação
    Usado na "Analise Manual" (sem romaneio)
    """
    try:
        # Usa o serviço de análise
        analysis = route_analyzer.analyze_addresses_from_text(
            addresses_text, 
            route_value
        )
        
        # O serviço já retorna os dados formatados para o frontend no campo .formatted
        return analysis.formatted
        
    except Exception as e:
        logger.error(f"Erro na análise manual: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/divide-and-assign")
async def divide_and_assign(request: DivideRoutesRequest = Body(...)):
    """
    1️⃣ Geocodifica endereços que ainda não têm coordenadas
    2️⃣ Divide romaneios entre entregadores
    3️⃣ Gera cores únicas para cada rota
    4️⃣ Ordena pontos de entrega (otimização)
    5️⃣ Gera mapas por rota
    6️⃣ Retorna preview com cores para seleção
    """
    try:
        session = session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")
        
        # Coletar todos os pontos de todos os romaneios
        all_points = []
        for romaneio in session.romaneios:
            all_points.extend(romaneio.points)
        
        if not all_points:
            raise HTTPException(status_code=400, detail="Nenhum ponto de entrega importado")
        
        # Usar localização base do request, ou da sessão, ou padrão (Rio de Janeiro)
        base_lat = request.base_lat if request.base_lat else (session.base_lat if session.base_lat else -22.9068)
        base_lng = request.base_lng if request.base_lng else (session.base_lng if session.base_lng else -43.1729)
        
        # Salvar base na sessão para uso futuro
        session.base_lat = base_lat
        session.base_lng = base_lng
        
        # ===== GEOCODIFICAR PONTOS SEM COORDENADAS =====
        # Paraleliza geocoding com ThreadPool para acelerar quando múltiplas APIs rápidas estiverem disponíveis
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import random

        points_to_geocode = [p for p in all_points if p.lat == 0.0 and p.lng == 0.0]
        geocoded_count = 0
        failed_count = 0

        if points_to_geocode:
            # Se temos keys de API (LocationIQ/Geoapify/Google) podemos paralelizar.
            stats = geocoding_service.get_stats()
            if stats.get('using_api'):
                logger.info(f"🔎 Geocoding paralelo de {len(points_to_geocode)} pontos (workers=6) — APIs configuradas")
                with ThreadPoolExecutor(max_workers=6) as executor:
                    # Passa expected_bairro para melhorar acurácia do geocoding
                    future_map = {executor.submit(geocoding_service.geocode, p.address, getattr(p, 'bairro', None)): p for p in points_to_geocode}
                    for fut in as_completed(future_map):
                        point = future_map[fut]
                        try:
                            coords = fut.result()
                            point.lat = coords[0]
                            point.lng = coords[1]
                            geocoded_count += 1
                            logger.info(f"📍 Geocoded: {point.address[:40]}... -> ({point.lat:.4f}, {point.lng:.4f})")
                        except Exception as e:
                            # fallback aleatório próximo à base
                            point.lat = base_lat + random.uniform(-0.01, 0.01)
                            point.lng = base_lng + random.uniform(-0.01, 0.01)
                            failed_count += 1
                            logger.warning(f"⚠️ Geocoding falhou para: {point.address[:40]}... usando fallback")
            else:
                # Sem keys configuradas — Nominatim é sensível a paralelismo. Geocode sequencialmente respeitando delays.
                logger.info(f"🔎 Geocoding SEQUENCIAL de {len(points_to_geocode)} pontos (Nominatim público)")
                for point in points_to_geocode:
                    try:
                        coords = geocoding_service.geocode(point.address, getattr(point, 'bairro', None))
                        point.lat = coords[0]
                        point.lng = coords[1]
                        geocoded_count += 1
                        logger.info(f"📍 Geocoded: {point.address[:60]} -> ({point.lat:.4f}, {point.lng:.4f})")
                    except Exception as e:
                        point.lat = base_lat + random.uniform(-0.01, 0.01)
                        point.lng = base_lng + random.uniform(-0.01, 0.01)
                        failed_count += 1
                        logger.warning(f"⚠️ Geocoding falhou para: {point.address[:60]}... usando fallback")

        logger.info(f"✅ Geocoding: {geocoded_count} sucesso, {failed_count} fallback de {len(all_points)} pontos")
        

        # 1. Agrupamento vertical (CEP/Condomínio)
        logger.info("🏢 Agrupando pacotes por CEP/Condomínio...")
        superpoints = group_by_cep_condominio([{
            'lat': p.lat, 'lng': p.lng, 'cep': getattr(p, 'cep', None), 'condominio': getattr(p, 'condominio', None), 'building': getattr(p, 'building', None), 'address': p.address, 'obj': p
        } for p in all_points])

        # 2. Identificação de bairros/polígonos
        logger.info("🗺️ Identificando bairros/polígonos...")
        # Usar GeoJSON detalhado da Zona Sul
        zone_utils = ZoneUtils('data/geojson/zona_sul_rio.json')
        for group in superpoints:
            for p in group:
                p['bairro'] = zone_utils.get_zone(p['lat'], p['lng'])

        # 3. Microzonamento dinâmico (clusters balanceados por tempo/distância)
        logger.info("🔬 Microzonamento dinâmico (K-means com restrições)...")
        # Flatten superpoints para clusterização
        flat_points = [p for group in superpoints for p in group]

        # 3.1. Balanceamento por tempo estimado (pedestre)
        logger.info("⏱️ Calculando tempo estimado de cada cluster para balanceamento...")
        # pedestrian_router removido: balanceamento agora só usa geopy
        # Inicialmente, clusterizar normalmente
        microzoner = MicroZoner(n_clusters=request.num_deliverers)
        labels = microzoner.fit(flat_points)
        clusters = [[] for _ in range(request.num_deliverers)]
        for idx, p in zip(labels, flat_points):
            clusters[idx].append(p)

        # Iterativamente rebalancear clusters para igualar tempo estimado
        def estimate_time(cluster_points):
            coords = [(p['lat'], p['lng']) for p in cluster_points]
            if len(coords) < 2:
                return 0
            # Usa ordem original para estimar distância total
            from geopy.distance import geodesic
            dist_km = sum(geodesic(coords[i], coords[i+1]).km for i in range(len(coords)-1))
            return dist_km / 4 * 60  # tempo em minutos

        max_iters = 10
        for _ in range(max_iters):
            times = [estimate_time(c) for c in clusters]
            max_time = max(times)
            min_time = min(times)
            if max_time - min_time < 10:  # tolerância de 10min
                break
            # Move ponto da borda do cluster mais lento para o mais rápido
            slow_idx = times.index(max_time)
            fast_idx = times.index(min_time)
            if not clusters[slow_idx]:
                break
            # Move o ponto mais distante do centroide do cluster lento
            import numpy as np
            slow_coords = np.array([[p['lat'], p['lng']] for p in clusters[slow_idx]])
            centroid = slow_coords.mean(axis=0)
            dists = np.linalg.norm(slow_coords - centroid, axis=1)
            move_idx = int(np.argmax(dists))
            move_point = clusters[slow_idx].pop(move_idx)
            clusters[fast_idx].append(move_point)

        # 4. Roteirização pedestre para cada cluster
        logger.info("🚶 Roteirizando cada cluster com API pedestre...")
        routes = []
        route_previews = []
        for idx, cluster_points in enumerate(clusters):
            color = get_color_for_index(idx)
            # Adiciona índice original para garantir mapeamento correto
            for i, p in enumerate(cluster_points):
                p['idx'] = i
            coords = [[p['lng'], p['lat']] for p in cluster_points]  # ORS espera [lng, lat]
            if len(coords) >= 2:
                from bot_multidelivery.services.ors_router import optimize_route
                ordered_coords = optimize_route(coords, profile="foot-walking")
            else:
                ordered_coords = coords
            # Mapeamento robusto: usa índice original
            idx_map = {i: p['obj'] for i, p in enumerate(cluster_points)}
            # ORS mantém o ponto inicial, depois jobs na ordem ótima
            optimized_points = []
            for coord in ordered_coords:
                # Busca pelo índice original
                for i, p in enumerate(cluster_points):
                    if abs(p['lng'] - coord[0]) < 1e-6 and abs(p['lat'] - coord[1]) < 1e-6:
                        if idx_map[i] not in optimized_points:
                            optimized_points.append(idx_map[i])
                        break
            # Garante que todos os pontos estejam presentes
            for p in cluster_points:
                if p['obj'] not in optimized_points:
                    optimized_points.append(p['obj'])
            route = Route(
                id=f"rota_{request.session_id}_{idx}",
                cluster=None,
                color=color,
                status=RouteStatus.PENDING,
                optimized_order=optimized_points
            )
            routes.append(route)
            # Gerar geometria da rota: base -> pontos otimizados -> base
            geometry = []
            if len(optimized_points) > 0:
                geometry.append([base_lat, base_lng])
                geometry.extend([[p.lat, p.lng] for p in optimized_points])
                geometry.append([base_lat, base_lng])
            route_previews.append({
                "route_id": route.id,
                "route_index": idx,
                "color": color,
                "total_stops": len(optimized_points),
                "total_packages": len(optimized_points),
                "estimated_distance_km": None,
                "map_url": None,
                "base_lat": base_lat,
                "base_lng": base_lng,
                "geometry": geometry,
                "points_sample": [
                    {
                        "address": p.address,
                        "lat": p.lat,
                        "lng": p.lng
                    }
                    for p in optimized_points[:10]
                ]
            })

        # Salvar temporariamente na sessão
        session.routes = routes
        session.current_step = "routes_created"
        session_manager.save_session(session)
        logger.info(f"✅ {len(routes)} rotas criadas com cores únicas (nova lógica)")
        return {
            "status": "success",
            "session_id": request.session_id,
            "total_routes": len(routes),
            "routes": route_previews,
            "next_step": "assign_deliverers"
        }
    
    except HTTPException as http_exc:
        # Tratamento manual de parsing do body caso erro de validação
        import json
        from fastapi import Request
        session_id = None
        num_deliverers = None
        base_lat = None
        base_lng = None
        deliverer_ids = []
        if isinstance(request, Request):
            body_bytes = await request.body()
            logger.info(f"[DEBUG] BODY CRU RECEBIDO: {body_bytes}")
            try:
                data = await request.json()
            except Exception as e:
                logger.error(f"[DEBUG] Falha ao parsear JSON: {e}")
                raise HTTPException(status_code=400, detail="Body não é JSON válido")
            logger.info(f"[DEBUG] JSON PARSED: {data}")
            session_id = data.get("session_id")
            num_deliverers = data.get("num_deliverers")
            base_lat = data.get("base_lat")
            base_lng = data.get("base_lng")
            deliverer_ids = data.get("deliverer_ids", [])
        else:
            logger.info(f"[DEBUG] Payload recebido: {request}")
            session_id = getattr(request, "session_id", None)
            num_deliverers = getattr(request, "num_deliverers", None)
            base_lat = getattr(request, "base_lat", None)
            base_lng = getattr(request, "base_lng", None)
            deliverer_ids = getattr(request, "deliverer_ids", [])

        # Validação explícita do payload
        if not session_id:
            logger.error("❌ Payload vazio ou malformado: session_id ausente")
            raise HTTPException(status_code=400, detail="Payload vazio ou malformado: session_id obrigatório")
        if not num_deliverers:
            logger.error("❌ Payload malformado: num_deliverers ausente")
            raise HTTPException(status_code=400, detail="Payload malformado: num_deliverers obrigatório")
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")
        all_points = []
        for romaneio in session.romaneios:
            all_points.extend(romaneio.points)
        if not all_points:
            raise HTTPException(status_code=400, detail="Nenhum ponto de entrega importado")
        base_lat = base_lat if base_lat else (session.base_lat if session.base_lat else -22.9068)
        base_lng = base_lng if base_lng else (session.base_lng if session.base_lng else -43.1729)
        session.base_lat = base_lat
        session.base_lng = base_lng
        logger.info("[DEBUG] Parsing manual concluído, pronto para dividir rotas.")
        raise http_exc  # Re-raise para FastAPI tratar corretamente


@router.get("/map/{session_id}")
async def get_route_map(session_id: str):
    """
    Gera e retorna mapa interativo com todas as rotas coloridas
    """
    try:
        session = session_manager.get_session(session_id)
        if not session or not session.routes:
            raise HTTPException(status_code=404, detail="Rotas não encontradas")
        

        # Gerar mapa com cores (MapGenerator removido - legado)
        all_points_with_colors = []
        
        for route in session.routes:
            for idx, point in enumerate(route.optimized_order):
                all_points_with_colors.append({
                    "point": point,
                    "color": route.color,
                    "route_id": route.id,
                    "sequence": idx + 1,
                    "deliverer": route.assigned_to_name or "Não atribuído"
                })
        
        # Gera mapa multi-rota usando StaticMapGenerator (substitui o legado `map_gen`)
        try:
            routes_data = []
            for r in session.routes:
                coords = [[p.lat, p.lng] for p in getattr(r, 'optimized_order', []) if hasattr(p, 'lat') and hasattr(p, 'lng') and p.lat and p.lng]
                routes_data.append({
                    'coordinates': coords,
                    'name': r.assigned_to_name or 'Não atribuído',
                    'color': r.color,
                    'deliverer': r.assigned_to_name or 'Não atribuído'
                })
            map_html = StaticMapGenerator.generate_multi_route_map(routes_data, session_name=session.session_name or 'Entregas')
        except Exception as _e:
            map_html = None
        
        return {
            "status": "success",
            "map_html": map_html,
            "total_routes": len(session.routes),
            "routes_info": [
                {
                    "route_id": r.id,
                    "color": r.color,
                    "deliverer": r.assigned_to_name,
                    "total_points": r.total_packages
                }
                for r in session.routes
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Erro ao gerar mapa: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/start")
async def start_routes(session_id: str = Query(...)):
    """
    Marca as rotas como iniciadas
    """
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")
        
        for route in session.routes:
            route.status = RouteStatus.IN_TRANSIT
        
        session.current_step = "separating"
        session_manager.save_session(session)
        
        return {
            "status": "success",
            "message": f"{len(session.routes)} rotas iniciadas"
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Helper para enviar via Telegram
async def send_route_to_telegram(tg_id: int, session, route: Route):
    """Envia a rota para o entregador via Telegram Bot API COM MAPA ESTÁTICO"""
    try:
        from bot_multidelivery.services.telegram_notifier import notify_route_assigned
        from bot_multidelivery.config import BotConfig

        # Extrair endereços da rota
        addresses = [p.address for p in route.optimized_order if hasattr(p, 'address')]

        # Extrair coordenadas para gerar mapa estático
        coordinates = []
        for p in route.optimized_order:
            if hasattr(p, 'lat') and hasattr(p, 'lng') and p.lat and p.lng:
                coordinates.append((p.lat, p.lng))

        logger.info(f"🗺️ Rota {route.color} tem {len(coordinates)} coordenadas para o mapa (tg_id={tg_id})")

        # Preferir link público minimalista: /public/deliverer/{token}
        try:
            from bot_multidelivery.routers.deliverer import public_links
            token = uuid.uuid4().hex
            expires_at = int(time.time()) + 3600  # 1 hora
            public_links[token] = {"route_id": str(route.id), "expires_at": expires_at}
            webapp_url = f"{BotConfig.WEBAPP_URL}/public/deliverer/{token}"
        except Exception as e:
            logger.warning(f"[Telegram] Fallback legacy link para rota: {e}")
            webapp_url = f"{BotConfig.WEBAPP_URL}?user_id={tg_id}&tab=myroute"

        # Enviar notificação COM MAPA
        try:
            success = await notify_route_assigned(
                telegram_id=tg_id,
                route_color=route.color,
                total_packages=route.total_packages,
                distance_km=route.total_distance_km or 0,
                addresses=addresses,
                webapp_url=webapp_url,
                coordinates=coordinates if len(coordinates) >= 2 else None
            )
            if success:
                logger.info(f"📱 ✅ Rota {route.color} enviada para {tg_id} {'com mapa' if coordinates else 'sem mapa'}")
            else:
                logger.warning(f"📱 ⚠️ Falha ao enviar rota {route.color} para {tg_id}")
        except Exception as e:
            logger.error(f"❌ Erro ao enviar rota {route.color} para {tg_id}: {e}")
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao preparar envio para Telegram: {e}")
