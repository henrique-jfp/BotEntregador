"""
Router para Mapa Admin em Tempo Real
WebSocket para atualização de rotas quando entregador completa/falha entrega
"""
import logging
import os
import json
import asyncio
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from bot_multidelivery.session import session_manager
from bot_multidelivery.services import geocoding_service

_redis = None
_redis_pubsub_tasks = {}
try:
    import redis.asyncio as aioredis
except Exception:
    aioredis = None

router = APIRouter(prefix="/map", tags=["Map"])
logger = logging.getLogger(__name__)

# Armazenar conexões WebSocket ativas por session_id
active_connections: dict = {}


def get_redis_client():
    global _redis
    if _redis:
        return _redis
    red_url = os.environ.get('REDIS_URL')
    if not red_url or not aioredis:
        return None
    try:
        _redis = aioredis.from_url(red_url)
        return _redis
    except Exception:
        return None


@router.get("/realtime/active")
async def get_active_map_session():
    """
    Retorna a sessão ativa para o mapa em tempo real
    DEVE VIR ANTES de /realtime/{session_id}!
    """
    try:
        session = session_manager.get_active_session()
        if not session:
            # fallback: última sessão não finalizada
            candidates = [s for s in session_manager.sessions if not s.is_finalized]
            if candidates:
                candidates.sort(key=lambda s: s.created_at, reverse=True)
                session = candidates[0]
            else:
                raise HTTPException(status_code=404, detail="Nenhuma sessão ativa")

        return {
            "status": "success",
            "session_id": session.session_id,
            "session_name": session.session_name,
            "date": session.date,
            "routes_count": len(session.routes),
            "total_packages": session.total_packages
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao buscar sessão ativa do mapa: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/realtime/{session_id}")
async def get_map_realtime(session_id: str):
    """
    GET simples para iniciar carregamento do mapa
    Retorna estado atual de todas as rotas e pontos
    """
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")
        
        if not session.routes:
            # Se não houver rotas, mostrar pontos dos romaneios (pré-separação)
            # Tentativa leve de geocoding para permitir mapa antes da separação
            all_points = []
            geocoded_count = 0
            geocode_limit = 10
            pending_geocode = 0
            for romaneio in session.romaneios:
                for point in romaneio.points:
                    if (not getattr(point, 'lat', 0)) or (not getattr(point, 'lng', 0)):
                        pending_geocode += 1
                        if geocoded_count < geocode_limit:
                            try:
                                lat, lng = geocoding_service.geocode(point.address)
                                point.lat = float(lat)
                                point.lng = float(lng)
                                geocoded_count += 1
                            except Exception:
                                pass

                    if hasattr(point, 'lat') and hasattr(point, 'lng') and point.lat and point.lng:
                        all_points.append({
                            "id": getattr(point, "package_id", f"tmp_{point.lat}_{point.lng}"),
                            "address": point.address,
                            "lat": point.lat,
                            "lng": point.lng,
                            "color": "#9ca3af", # Cinza (pendente)
                            "route_color": "#e5e7eb",
                            "route_id": "unassigned",
                            "deliverer": "Aguardando Separação",
                            "sequence": 0,
                            "status": "pending"
                        })

            if geocoded_count > 0:
                session_manager.save_session(session)
            
            if not all_points:
                return {
                    "status": "empty",
                    "session_id": session_id,
                    "total_routes": 0,
                    "total_points": 0,
                    "points": [],
                    "routes_summary": [],
                    "message": "Nenhuma rota iniciada e nenhum ponto com coordenadas. Clique em 'Otimizar rotas' para geocodificar ou recarregue para tentar novamente."
                }
            
            return {
                "status": "planning",
                "session_id": session_id,
                "total_routes": 0,
                "total_points": len(all_points),
                "points": all_points,
                "routes_summary": [],
                "message": "Visualização pré-separação" + (f" • Geocodificados agora: {geocoded_count}" if geocoded_count else "")
            }
        
        # Montar payload com todos os pontos coloridos
        map_points = []
        for route in session.routes:
            for idx, point in enumerate(route.optimized_order):
                # Determinar cor do ponto:
                # Verde se entregue
                # Vermelha se falha
                # Cor da rota se pendente
                
                is_delivered = point.package_id in route.delivered_packages
                point_color = "#22c55e" if is_delivered else route.color  # Verde ou cor da rota
                
                map_points.append({
                    "id": point.package_id,
                    "address": point.address,
                    "lat": point.lat,
                    "lng": point.lng,
                    "color": point_color,
                    "route_color": route.color,
                    "route_id": route.id,
                    "deliverer": route.assigned_to_name or "Não atribuído",
                    "sequence": idx + 1,
                    "status": "delivered" if is_delivered else "pending"
                })
        
        return {
            "status": "success",
            "session_id": session_id,
            "total_routes": len(session.routes),
            "total_points": len(map_points),
            "points": map_points,
            "routes_summary": [
                {
                    "route_id": r.id,
                    "color": r.color,
                    "deliverer": r.assigned_to_name,
                    "total": r.total_packages,
                    "delivered": r.delivered_count,
                    "pending": r.pending_count,
                    "completion_rate": r.completion_rate
                }
                for r in session.routes
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao carregar mapa: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/realtime/active")
async def get_active_map_session():
    """
    Retorna a sessão ativa para o mapa em tempo real
    """
    try:
        session = session_manager.get_active_session()
        if not session:
            # fallback: última sessão não finalizada
            candidates = [s for s in session_manager.sessions if not s.is_finalized]
            if candidates:
                candidates.sort(key=lambda s: s.created_at, reverse=True)
                session = candidates[0]
            else:
                raise HTTPException(status_code=404, detail="Nenhuma sessão ativa")

        return {
            "status": "success",
            "session_id": session.session_id,
            "session_name": session.session_name,
            "date": session.date,
            "routes_count": len(session.routes),
            "total_packages": session.total_packages
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao buscar sessão ativa do mapa: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.websocket("/ws/{session_id}")
async def websocket_map_updates(websocket: WebSocket, session_id: str):
    """
    WebSocket para mapa em tempo real
    Envia updates quando:
    1. Entregador completa uma entrega
    2. Entregador marca como problema/falha
    3. Rota é finalizada
    """
    await websocket.accept()
    
    if session_id not in active_connections:
        active_connections[session_id] = []
    active_connections[session_id].append(websocket)
    
    logger.info(f"✅ Admin conectado ao WebSocket da sessão {session_id}")
    # Se houver REDIS configurado, inicia subscriber global para essa sessão (apenas 1 por sessão)
    redis_client = get_redis_client()
    if redis_client and session_id not in _redis_pubsub_tasks:
        task = asyncio.create_task(_redis_subscriber_forward(session_id, redis_client))
        _redis_pubsub_tasks[session_id] = task

    try:
        while True:
            # Receber keep-alive ou comandos do admin
            data = await websocket.receive_text()
            
            if data == "ping":
                # Enviar estado atual do mapa
                session = session_manager.get_session(session_id)
                if session:
                    map_state = {
                        "type": "state_update",
                        "routes": [
                            {
                                "route_id": r.id,
                                "color": r.color,
                                "delivered": r.delivered_count,
                                "total": r.total_packages,
                                "completion": r.completion_rate
                            }
                            for r in session.routes
                        ]
                    }
                    await websocket.send_json(map_state)
    
    except WebSocketDisconnect:
        active_connections[session_id].remove(websocket)
        logger.info(f"❌ Admin desconectado da sessão {session_id}")
        # Se não houver mais conexões para essa sessão, cancela subscriber
        if not active_connections.get(session_id):
            task = _redis_pubsub_tasks.pop(session_id, None)
            if task:
                task.cancel()


async def broadcast_delivery_update(session_id: str, point_id: str, status: str, route_id: str):
    """
    Chamado quando um entregador completa uma entrega
    Notifica todos os admins conectados ao WebSocket
    """
    if session_id not in active_connections:
        return
    
    session = session_manager.get_session(session_id)
    if not session:
        return
    
    # Encontrar rota e ponto
    route = None
    point = None
    for r in session.routes:
        if r.id == route_id:
            route = r
            for p in r.optimized_order:
                if p.id == point_id:
                    point = p
                    break
            break
    
    if not route or not point:
        return
    
    # Determinar nova cor
    new_color = "#22c55e" if status == "delivered" else "#ef4444"  # Verde ou vermelho
    
    update_payload = {
        "type": "point_update",
        "point_id": point_id,
        "route_id": route_id,
        "new_color": new_color,
        "status": status,
        "address": point.address,
        "sequence": route.optimized_order.index(point) + 1,
        "route_completion": route.completion_rate,
        "delivered": route.delivered_count,
        "total": route.total_packages
    }
    
    # Broadcast para todos os WebSockets dessa sessão
    for websocket in active_connections.get(session_id, []):
        try:
            await websocket.send_json(update_payload)
        except Exception as e:
            logger.error(f"❌ Erro ao enviar update: {e}")
    # Publicar em Redis para múltiplas réplicas, se configurado
    try:
        redis_client = get_redis_client()
        if redis_client:
            channel = f"map_updates:{session_id}"
            await redis_client.publish(channel, json.dumps(update_payload))
    except Exception:
        pass
    
    logger.info(f"📡 Broadcast enviado: {point.address} → {status}")


async def _redis_subscriber_forward(session_id: str, redis_client):
    """Subscreve canal Redis e encaminha mensagens recebidas para websockets locais."""
    try:
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"map_updates:{session_id}")

        async for message in pubsub.listen():
            if message is None:
                continue
            if message.get('type') != 'message':
                continue
            try:
                data = json.loads(message.get('data', b'{}'))
            except Exception:
                continue
            # Enviar para conexões locais
            for ws in active_connections.get(session_id, []):
                try:
                    await ws.send_json(data)
                except Exception as e:
                    logger.debug(f"Erro ao repassar msg Redis para WS: {e}")
    except asyncio.CancelledError:
        return
    except Exception as e:
        logger.error(f"Erro no subscriber Redis para session {session_id}: {e}")
