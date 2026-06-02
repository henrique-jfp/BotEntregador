"""
Router para Entregadores - Rota do Dia e Confirmação de Entregas
"""
import asyncio
import logging
import os
from fastapi import APIRouter, HTTPException, Query, Body
import uuid
import time
from bot_multidelivery.session import session_manager
from bot_multidelivery.persistence import data_store
from bot_multidelivery.services.osrm_service import osrm_client

# Para broadcast de atualizações em tempo real
from bot_multidelivery.routers.map_realtime import broadcast_delivery_update
router = APIRouter(prefix="/deliverer", tags=["Deliverer"])
logger = logging.getLogger(__name__)

# Tokens públicos temporários para abrir a rota do entregador em página minimalista
# Estrutura: { token: { "route_id": <id>, "expires_at": <epoch_seconds> } }
public_links = {}


async def check_all_routes_completed(session):
    """
    Verifica se todas as rotas foram finalizadas (100% de conclusão)
    Se sim, notifica o admin via Telegram
    """
    all_completed = all(
        route.completion_rate >= 100.0 
        for route in session.routes
    )
    
    if all_completed:
        logger.info(f"🎉 TODAS as rotas foram finalizadas na sessão {session.session_id}")
        
        # Enviar notificação ao admin
        try:
            from bot_multidelivery.services.telegram_notifier import notifier
            admin_id = os.getenv('ADMIN_TELEGRAM_ID')
            
            if admin_id:
                message = f"""
🎉 <b>TODAS AS ROTAS FORAM FINALIZADAS!</b>

📦 Sessão: {session.session_name or session.session_id[:8]}
📅 Data: {session.date}

✅ <b>Estatísticas Finais:</b>
• Total de Pacotes: {session.total_packages}
• Entregadores: {session.num_deliverers}
• Rotas Completas: {len(session.routes)}/{len(session.routes)}

💰 <b>Próximo Passo:</b>
Venha fazer o fechamento diário no app! 👇
Acesse: Fechamento → Adicione custos → Finalize a sessão

<i>Não se esqueça de incluir: Combustível, Outros, Salários dos entregadores</i>
"""
                
                webapp_url = os.getenv('WEBAPP_URL', 'https://seu-app.railway.app')
                
                reply_markup = {
                    "inline_keyboard": [[
                        {
                            "text": "💰 Fazer Fechamento Agora",
                            "web_app": {"url": f"{webapp_url}?tab=closure"}
                        }
                    ]]
                }
                
                await notifier.send_message(
                    chat_id=int(admin_id),
                    text=message,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
                
                logger.info(f"📱 Notificação de finalização enviada ao admin {admin_id}")
        
        except Exception as e:
            logger.error(f"❌ Erro ao enviar notificação de finalização: {e}")


def _build_stops_from_route(user_route):
    """Agrupa pacotes por endereço/coordenadas em paradas únicas (ordem preservada)."""
    stops = []
    stop_index_by_key = {}

    for point in user_route.optimized_order:
        if not hasattr(point, 'lat') or not hasattr(point, 'lng'):
            continue
        if point.lat is None or point.lng is None:
            continue

        key = (round(point.lat, 4), round(point.lng, 4), (point.address or "").strip().lower())
        if key not in stop_index_by_key:
            stop_index_by_key[key] = len(stops)
            stops.append({
                "id": len(stops) + 1,
                "address": point.address,
                "lat": point.lat,
                "lng": point.lng,
                "packages": []
            })

        pkg_id = getattr(point, "package_id", None) or getattr(point, "id", None)
        if not pkg_id:
            pkg_id = f"pkg_{len(stops[stop_index_by_key[key]]['packages']) + 1}"
        stops[stop_index_by_key[key]]["packages"].append(pkg_id)

    return stops

@router.get("/route")
async def get_deliverer_route(user_id: int = Query(...)):
    """
    Retorna a rota do entregador para o dia
    Apenas sua rota, com mapa, sequência e próxima parada
    """
    try:
        # 1. Verificar se entregador existe
        deliverer = data_store.get_deliverer(user_id)
        if not deliverer:
            raise HTTPException(status_code=404, detail="Entregador não encontrado")
        
        # 2. Buscar sessão ativa
        session = session_manager.get_active_session()
        if not session or session.is_finalized:
            raise HTTPException(status_code=400, detail="Nenhuma sessão ativa")
        
        # 3. Procurar rota do entregador
        user_route = None
        for route in session.routes:
            if route.assigned_to_telegram_id == user_id:
                user_route = route
                break
        
        if not user_route:
            # Retornar objeto neutro em vez de erro para permitir que o frontend carregue
            return {
                "has_route": False, 
                "session_id": session.session_id,
                "message": "Sua rota será definida em breve."
            }

        # 4. Agrupar pacotes por parada
        stops = _build_stops_from_route(user_route)
        logger.info(f"🔎 Deliverer route debug: route_id={user_route.id} stops_count={len(stops)} base=({session.base_lat},{session.base_lng})")

        # Tentar obter geometria via OSRM para desenhar rota real nas apps
        try:
            # Sequência: base -> paradas (coords em (lat,lng))
            session_base = session.base_lat, session.base_lng
            coords = [session_base] + [(s['lat'], s['lng']) for s in stops]
            geom_result = osrm_client.get_route_geometry(coords)
            route_geometry = geom_result.geometry if geom_result else {}
            geometry_fallback = getattr(geom_result, 'fallback_used', True)
        except Exception:
            route_geometry = {}
            geometry_fallback = True

        return {
            "route_id": user_route.id,
            "color": user_route.color,
            "deliverer_name": user_route.assigned_to_name,
            "status": user_route.status,
            "total_distance_km": user_route.total_distance_km,
            "stops": stops,
            "route_geometry": route_geometry,
            "route_geometry_fallback": geometry_fallback,
            "completed": user_route.delivered_count,
            "total": user_route.total_packages,
            "completion_rate": user_route.completion_rate,
            "has_route": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao carregar rota: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/complete-stop")
async def complete_stop(
    route_id: str = Query(...),
    stop_index: int = Query(...),
    status: str = Query("delivered"),  # delivered, failed, returned
    lat: float = Query(None),
    lng: float = Query(None)
):
    """
    Marca uma parada com status: delivered, failed ou returned
    """
    try:
        # Procurar sessão e rota
        session = session_manager.get_active_session()
        if not session:
            raise HTTPException(status_code=400, detail="Sessão não ativa")
        
        route = None
        for r in session.routes:
            if r.id == route_id:
                route = r
                break
        
        if not route:
            raise HTTPException(status_code=404, detail="Rota não encontrada")
        
        # Recria paradas para mapear índice de parada -> pacotes
        stops = _build_stops_from_route(route)
        if stop_index >= len(stops):
            raise HTTPException(status_code=400, detail="Índice inválido")

        # Marcar TODOS os pacotes da parada com o status apropriado
        stop_packages = stops[stop_index].get("packages", [])
        for pkg_id in stop_packages:
            if pkg_id:
                if status == "delivered":
                    route.mark_as_delivered(pkg_id)
                elif status == "failed":
                    route.mark_as_failed(pkg_id)
                elif status == "returned":
                    route.mark_as_returned(pkg_id)
        
        logger.info(f"✅ Parada {stop_index + 1} marcada como {status} na rota {route.color}")
        
        # Salvar sessão
        session_manager.save_session(session)
        
        # 🔴 IMPORTANTE: Broadcast em tempo real para o mapa do admin
        if stop_packages:
            asyncio.create_task(broadcast_delivery_update(
                session_id=session.session_id,
                point_id=stop_packages[0],  # Usar primeiro pacote como referência
                status=status,
                route_id=route_id
            ))
        
        # 🚨 VERIFICAR SE TODAS AS ROTAS FORAM FINALIZADAS
        await check_all_routes_completed(session)
        
        return {
            "status": "success",
            "action": status,
            "completed": route.delivered_count,
            "total": route.total_packages,
            "completion_rate": route.completion_rate
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao confirmar parada: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transfer-stop")
async def transfer_stop(
    route_id: str = Query(...),
    stop_index: int = Query(...),
    target_deliverer: str = Query(...)
):
    """
    Transfere uma parada (e seus pacotes) para outro entregador
    """
    try:
        session = session_manager.get_active_session()
        if not session:
            raise HTTPException(status_code=400, detail="Sessão não ativa")
        
        # Encontrar rota de origem
        source_route = None
        for r in session.routes:
            if r.id == route_id:
                source_route = r
                break
        
        if not source_route:
            raise HTTPException(status_code=404, detail="Rota não encontrada")
        
        # Encontrar rota de destino (por nome ou telegram_id)
        target_route = None
        for r in session.routes:
            if (r.assigned_to_name and target_deliverer.lower() in r.assigned_to_name.lower()) or \
               (r.assigned_to_telegram_id and str(r.assigned_to_telegram_id) == target_deliverer):
                target_route = r
                break
        
        if not target_route:
            raise HTTPException(status_code=404, detail=f"Entregador '{target_deliverer}' não encontrado")
        
        # Reconstruir paradas
        stops = _build_stops_from_route(source_route)
        if stop_index >= len(stops):
            raise HTTPException(status_code=400, detail="Índice inválido")
        
        transfer_stop = stops[stop_index]
        
        # Remover pacotes da rota de origem e adicionar na de destino
        packages_to_transfer = []
        for point in source_route.optimized_order[:]:
            point_key = (round(point.lat, 4), round(point.lng, 4), (point.address or "").strip().lower())
            stop_key = (round(transfer_stop['lat'], 4), round(transfer_stop['lng'], 4), transfer_stop['address'].strip().lower())
            
            if point_key == stop_key:
                packages_to_transfer.append(point)
                source_route.optimized_order.remove(point)
        
        # Adicionar na rota de destino
        target_route.optimized_order.extend(packages_to_transfer)
        
        logger.info(f"📦 Transferidos {len(packages_to_transfer)} pacotes de {source_route.color} para {target_route.color}")
        
        # Salvar sessão
        session_manager.save_session(session)
        
        return {
            "status": "success",
            "transferred_packages": len(packages_to_transfer),
            "from_route": source_route.color,
            "to_route": target_route.color,
            "to_deliverer": target_route.assigned_to_name
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao transferir parada: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/link')
async def create_deliverer_link(route_id: str = Body(...), ttl_seconds: int = Body(3600)):
    """
    Gera um token público temporário que permite abrir a visualização minimalista
    da rota do entregador sem expor controles administrativos.
    Retorna { token, url, expires_at } (url é o caminho relativo que o frontend usa).
    """
    try:
        # Validar rota existe na sessão atual
        session = session_manager.get_active_session()
        if not session:
            raise HTTPException(status_code=400, detail="Sessão não ativa")

        found = None
        for r in session.routes:
            if str(r.id) == str(route_id):
                found = r
                break

        if not found:
            raise HTTPException(status_code=404, detail="Rota não encontrada")

        token = uuid.uuid4().hex
        expires_at = int(time.time()) + int(ttl_seconds)
        public_links[token] = {"route_id": str(route_id), "expires_at": expires_at}

        # URL relativa que o frontend conhece (rota React)
        url = f"/public/deliverer/{token}"
        return {"token": token, "url": url, "expires_at": expires_at}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao gerar link público: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/public-route/{token}')
async def get_public_route_json(token: str):
    """
    Retorna DADOS DA ROTA (JSON) para um token público.
    Usado pelo frontend React quando acessado via /public/deliverer/{token}
    """
    try:
        info = public_links.get(token)
        logger.info(f"🔍 Buscando rota pública para token: {token}")
        if not info:
            # Tenta buscar em cache persistente ou banco se necessário
            # Por enquanto, apenas memória
            raise HTTPException(status_code=404, detail="Link inválido ou expirado")

        if int(time.time()) > int(info['expires_at']):
            public_links.pop(token, None)
            raise HTTPException(status_code=404, detail="Link expirado")

        route_id = info['route_id']

        session = session_manager.get_active_session()
        if not session or session.is_finalized:
            raise HTTPException(status_code=400, detail="Sessão não ativa")

        user_route = None
        for route in session.routes:
            if str(route.id) == str(route_id):
                user_route = route
                break

        if not user_route:
            raise HTTPException(status_code=404, detail="Rota não encontrada")

        stops = _build_stops_from_route(user_route)
        
        try:
            session_base = session.base_lat, session.base_lng
            coords = [session_base] + [(s['lat'], s['lng']) for s in stops]
            geom_result = osrm_client.get_route_geometry(coords)
            route_geometry = geom_result.geometry if geom_result else {}
            geometry_fallback = getattr(geom_result, 'fallback_used', True)
        except Exception:
            route_geometry = {}
            geometry_fallback = True

        return {
            "route_id": user_route.id,
            "color": user_route.color,
            "deliverer_name": user_route.assigned_to_name,
            "status": user_route.status,
            "total_distance_km": user_route.total_distance_km,
            "stops": stops,
            "route_geometry": route_geometry,
            "route_geometry_fallback": geometry_fallback,
            "completed": user_route.delivered_count,
            "total": user_route.total_packages,
            "completion_rate": user_route.completion_rate,
            "has_route": True,
            "is_public_view": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao resolver token público JSON: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/config')
async def get_deliverer_config():
    """Retorna configurações públicas úteis para a UI do entregador (ex: GEOAPIFY key).
    Esta rota é segura para expor a chave de tiles para o cliente (somente leitura).
    """
    try:
        return {
            "geoapify_key": os.getenv('GEOAPIFY_API_KEY', '') or ''
        }
    except Exception:
        return {"geoapify_key": ''}
