# -*- coding: utf-8 -*-
"""
📱 TELEGRAM NOTIFIER SERVICE
Serviço para enviar notificações via Telegram Bot API
"""
import os
import logging
import aiohttp
from typing import Optional, List, Tuple
from io import BytesIO

from bot_multidelivery.services.static_map_generator import StaticMapGenerator
from bot_multidelivery.config import BotConfig

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Envia mensagens via Telegram Bot API (HTTP direto)"""
    
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.geoapify_key = os.getenv('GEOAPIFY_API_KEY', '')
        self.mapbox_token = os.getenv('MAPBOX_TOKEN', '')
        
        # Log status das APIs de mapa
        if self.geoapify_key:
            logger.info("🗺️ Geoapify API configurada - mapas estáticos habilitados")
        elif self.mapbox_token:
            logger.info("🗺️ Mapbox API configurada - mapas estáticos habilitados")
        else:
            logger.warning("⚠️ Nenhuma API de mapa configurada! Notificações serão enviadas SEM imagem do mapa")
            logger.warning("   Configure GEOAPIFY_API_KEY (grátis: https://myprojects.geoapify.com)")
        
    async def send_message(
        self, 
        chat_id: int, 
        text: str, 
        parse_mode: str = "HTML",
        reply_markup: Optional[dict] = None
    ) -> bool:
        """
        Envia uma mensagem de texto para um chat/usuário
        
        Args:
            chat_id: ID do Telegram do destinatário
            text: Texto da mensagem (suporta HTML)
            parse_mode: 'HTML' ou 'Markdown'
            reply_markup: Botões inline (opcional)
            
        Returns:
            True se enviou com sucesso, False caso contrário
        """
        if not self.token:
            logger.error("❌ Token do Telegram não configurado!")
            return False
            
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_markup:
            payload["reply_markup"] = reply_markup
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            logger.info(f"✅ Mensagem enviada para {chat_id}")
                            return True
                        else:
                            # Log detalhado do erro da API
                            error_desc = result.get('description', 'No description provided.')
                            logger.error(f"❌ Telegram API Error (Chat ID: {chat_id}): {error_desc}")
                            logger.debug(f"Full Telegram error response: {result}")
                            return False
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Telegram HTTP Error (Chat ID: {chat_id}): Status {response.status} - Response: {error_text}")
                        return False
                        
        except aiohttp.ClientError as e:
            logger.error(f"❌ Erro de conexão com Telegram: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao enviar mensagem: {e}")
            return False
    
    async def send_photo(
        self,
        chat_id: int,
        photo_url: str = None,
        photo_bytes: bytes = None,
        photo_path: str = None,
        caption: str = None,
        parse_mode: str = "HTML",
        reply_markup: Optional[dict] = None
    ) -> bool:
        """
        Envia uma foto para um chat/usuário
        
        Args:
            chat_id: ID do Telegram do destinatário
            photo_url: URL da imagem (ou photo_bytes)
            photo_bytes: Bytes da imagem (alternativa ao URL)
            photo_path: Caminho do arquivo (alternativa ao URL/bytes)
            caption: Legenda da foto
            reply_markup: Botões inline (opcional)
        """
        if not self.token:
            logger.error("❌ Token do Telegram não configurado!")
            return False
            
        url = f"{self.base_url}/sendPhoto"
        
        try:
            async with aiohttp.ClientSession() as session:
                # ✅ Caso 1: Enviar por arquivo local (mais confiável)
                if photo_path and os.path.exists(photo_path):
                    data = aiohttp.FormData()
                    data.add_field('chat_id', str(chat_id))
                    
                    with open(photo_path, 'rb') as f:
                        data.add_field('photo', f, filename='map.png', content_type='image/png')
                    
                    if caption:
                        data.add_field('caption', caption)
                        data.add_field('parse_mode', parse_mode)
                    if reply_markup:
                        import json
                        data.add_field('reply_markup', json.dumps(reply_markup))
                    
                    async with session.post(url, data=data, timeout=30) as response:
                        result = await response.json()
                        if response.status == 200 and result.get("ok"):
                            logger.info(f"✅ Foto (arquivo) enviada para {chat_id}")
                            return True
                        else:
                            error_desc = result.get('description', 'No description provided.')
                            logger.error(f"❌ Telegram API Error on send_photo (file): {error_desc}")
                            logger.debug(f"Full Telegram error response: {result}")
                            return False
                
                # ✅ Caso 2: Enviar bytes diretamente
                elif photo_bytes:
                    data = aiohttp.FormData()
                    data.add_field('chat_id', str(chat_id))
                    data.add_field('photo', photo_bytes, filename='map.png', content_type='image/png')
                    
                    if caption:
                        data.add_field('caption', caption)
                        data.add_field('parse_mode', parse_mode)
                    if reply_markup:
                        import json
                        data.add_field('reply_markup', json.dumps(reply_markup))
                    
                    async with session.post(url, data=data, timeout=30) as response:
                        result = await response.json()
                        if response.status == 200 and result.get("ok"):
                            logger.info(f"✅ Foto (bytes) enviada para {chat_id}")
                            return True
                        else:
                            error_desc = result.get('description', 'No description provided.')
                            logger.error(f"❌ Telegram API Error on send_photo (bytes): {error_desc}")
                            logger.debug(f"Full Telegram error response: {result}")
                            return False
                
                # ✅ Caso 3: Enviar por URL (mais rápido, Telegram baixa)
                else:
                    payload = {
                        "chat_id": chat_id,
                        "photo": photo_url,
                    }
                    if caption:
                        payload["caption"] = caption
                        payload["parse_mode"] = parse_mode
                    if reply_markup:
                        payload["reply_markup"] = reply_markup
                        
                    async with session.post(url, json=payload, timeout=30) as response:
                        result = await response.json()
                        if response.status == 200 and result.get("ok"):
                            logger.info(f"✅ Foto (URL) enviada para {chat_id}")
                            return True
                        else:
                            error_desc = result.get('description', 'No description provided.')
                            logger.error(f"❌ Telegram API Error on send_photo (url): {error_desc}")
                            logger.debug(f"Full Telegram error response: {result}")
                            return False
                        
        except Exception as e:
            logger.error(f"❌ Erro ao enviar foto: {e}")
            return False
    
    async def generate_static_map_url(
        self,
        points: List[Tuple[float, float]],
        route_color: str = "#FF4444",
        width: int = 600,
        height: int = 400
    ) -> str:
        """
        Gera URL para mapa estático usando Geoapify ou alternativas
        
        Args:
            points: Lista de (lat, lng) coordenadas
            route_color: Cor da rota em hex
            width: Largura da imagem
            height: Altura da imagem
            
        Returns:
            URL do mapa estático ou None se falhar
        """
        if not points or len(points) < 2:
            return None
            
        try:
            # Calcular centro e zoom do mapa
            lats = [p[0] for p in points]
            lngs = [p[1] for p in points]
            
            center_lat = (min(lats) + max(lats)) / 2
            center_lng = (min(lngs) + max(lngs)) / 2
            
            # Calcular zoom baseado no bounding box
            lat_diff = max(lats) - min(lats)
            lng_diff = max(lngs) - min(lngs)
            max_diff = max(lat_diff, lng_diff)
            
            # Zoom aproximado
            if max_diff > 0.5:
                zoom = 10
            elif max_diff > 0.1:
                zoom = 12
            elif max_diff > 0.05:
                zoom = 13
            elif max_diff > 0.01:
                zoom = 14
            else:
                zoom = 15
            
            # Tentar Geoapify primeiro (3000 requests/dia grátis)
            if self.geoapify_key:
                # Gerar markers para cada ponto no formato Geoapify
                markers = []
                
                # Primeiro ponto (início) - Verde
                markers.append(f"lonlat:{lngs[0]},{lats[0]};type:awesome;color:green;size:medium;icon:home")
                
                # Último ponto (fim) - Vermelho
                if len(points) > 1:
                    markers.append(f"lonlat:{lngs[-1]},{lats[-1]};type:awesome;color:red;size:medium;icon:flag")
                
                # Pontos intermediários (máximo 10 para não sobrecarregar)
                step = max(1, len(points) // 8)
                for i in range(1, len(points) - 1, step):
                    markers.append(f"lonlat:{lngs[i]},{lats[i]};type:circle;color:%23{route_color.replace('#', '')};size:small")
                
                markers_str = "|".join(markers[:12])  # Limite de markers
                
                map_url = f"https://maps.geoapify.com/v1/staticmap?style=osm-carto&width={width}&height={height}&center=lonlat:{center_lng},{center_lat}&zoom={zoom}&marker={markers_str}&apiKey={self.geoapify_key}"
                
                logger.info(f"🗺️ URL do mapa gerada: Geoapify com {len(points)} pontos")
                return map_url
            
            # Alternativa: Mapbox (tem tier gratuito)
            if self.mapbox_token:
                # Gerar marcadores no formato Mapbox
                pins = []
                for i, (lat, lng) in enumerate(points[:5]):
                    color = "22c55e" if i == 0 else ("ef4444" if i == len(points)-1 else "3b82f6")
                    pins.append(f"pin-s+{color}({lng},{lat})")
                
                pins_str = ",".join(pins)
                map_url = f"https://api.mapbox.com/styles/v1/mapbox/streets-v12/static/{pins_str}/{center_lng},{center_lat},{zoom}/{width}x{height}?access_token={self.mapbox_token}"
                logger.info(f"🗺️ URL do mapa gerada: Mapbox")
                return map_url
            
            logger.warning(f"⚠️ Nenhuma API de mapa configurada")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar URL do mapa: {e}")
            return None
    
    async def send_route_notification(
        self, 
        chat_id: int, 
        route_color: str,
        total_packages: int,
        distance_km: float,
        addresses: list,
        webapp_url: str = None,
        coordinates: List[Tuple[float, float]] = None
    ) -> bool:
        """
        Envia notificação de nova rota para o entregador COM MAPA
        
        Args:
            chat_id: ID Telegram do entregador
            route_color: Cor da rota (ex: "#FF4444")
            total_packages: Total de pacotes na rota
            distance_km: Distância total em km
            addresses: Lista de endereços (primeiros 5 serão mostrados)
            webapp_url: URL do WebApp para abrir mapa
            coordinates: Lista de (lat, lng) para gerar mapa estático
        """
        # Mapear cor hex para nome
        color_names = {
            '#FF4444': '🔴 VERMELHO',
            '#44FF44': '🟢 VERDE', 
            '#4444FF': '🔵 AZUL',
            '#FFD700': '🟡 AMARELO',
            '#FF69B4': '🩷 ROSA',
            '#9370DB': '🟣 ROXO',
            '#FF8C00': '🟠 LARANJA',
            '#00CED1': '🩵 CIANO',
            '#EF4444': '🔴 VERMELHO',
            '#22C55E': '🟢 VERDE',
            '#3B82F6': '🔵 AZUL',
            '#EAB308': '🟡 AMARELO',
            '#EC4899': '🩷 ROSA',
            '#A855F7': '🟣 ROXO',
            '#F97316': '🟠 LARANJA',
            '#06B6D4': '🩵 CIANO',
        }
        
        color_name = color_names.get(route_color.upper(), route_color)
        
        # Formatar endereços (pegar ruas únicas e limpas)
        clean_addresses = []
        for addr in addresses:
            # Pega só a parte da rua antes da vírgula ou traço para o resumo
            clean = addr.split('-')[0].split(',')[0].strip()
            if clean and clean not in clean_addresses:
                clean_addresses.append(clean)
            if len(clean_addresses) >= 5:
                break
                
        address_list = ""
        for clean in clean_addresses:
            address_list += f"▫️ <i>{clean}</i>\n"
        
        remaining = max(0, len(addresses) - len(clean_addresses))
        if remaining > 0:
            address_list += f"▫️ <i>... e mais {remaining} entregas na região.</i>"
            
        # Calcular tempo estimado (Base: 15 km/h + 3 min por pacote de tempo parado)
        tempo_deslocamento_min = (distance_km / 15.0) * 60
        tempo_parado_min = total_packages * 3
        tempo_total_min = int(tempo_deslocamento_min + tempo_parado_min)
        
        horas = tempo_total_min // 60
        minutos = tempo_total_min % 60
        tempo_str = f"{horas}h {minutos}m" if horas > 0 else f"{minutos} minutos"
        
        # Montar mensagem/caption (Card Bonitinho)
        message = f"""📦 <b>NOVA ROTA ATRIBUÍDA A VOCÊ!</b>

<b>Cor de Separação:</b> {color_name}

📊 <b>Resumo da Rota:</b>
📦 <b>Pacotes:</b> {total_packages} volumes
🛣️ <b>Distância:</b> {distance_km:.1f} km
⏱️ <b>Tempo Est.:</b> ~{tempo_str}

📍 <b>Principais Destinos:</b>
{address_list}

👇 <b>CLIQUE ABAIXO PARA VER O MAPA E DAR BAIXA:</b>"""

        # Garantir que SEMPRE teremos o botão do app, gerando o fallback se `webapp_url` for nulo
        try:
            fallback_url = f"{BotConfig.WEBAPP_URL}?user_id={chat_id}&tab=myroute"
        except Exception:
            fallback_url = "https://t.me/" # URL dummy para não quebrar se algo der muito errado
            
        final_url = webapp_url if webapp_url else fallback_url

        buttons = [
            {"text": "📱 ABRIR APP DE ENTREGAS", "url": final_url}
        ]
        
        reply_markup = {"inline_keyboard": [buttons]}
        
        # Se temos coordenadas, tentar enviar mapa estático PREMIUM
        map_sent = False
        # Permite desativar gerador pesado via variável de ambiente (útil em containers com pouca memória)
        if os.getenv('DISABLE_STATIC_MAPS', '0') == '1':
            logger.info("⚠️ DISABLE_STATIC_MAPS ativo: pulando geração de mapa estático")
            map_sent = False
        elif coordinates and len(coordinates) >= 2:
            try:
                # NOVO: Usar gerador de mapa profissional
                logger.info(f"🗺️ Gerando mapa premium para {len(coordinates)} coordenadas...")
                map_path = StaticMapGenerator.generate_route_map(
                    coordinates=coordinates,
                    route_number=1,
                    deliverer_name="Entregador",
                    total_packages=total_packages
                )
                
                if map_path and os.path.exists(map_path):
                    # Se o gerador retornou um HTML (quando Selenium/Chrome ausente ou conversão falhou),
                    # NÃO devemos enviar o HTML como "photo" — isso causa erro 400 do Telegram.
                    if map_path.lower().endswith('.html'):
                        logger.warning(f"⚠️ Map generator returned HTML ({map_path}) - skipping file send and using URL fallback")
                    else:
                        # Enviar arquivo como foto (PNG esperado)
                        logger.info(f"📸 Enviando mapa de {map_path}")
                        map_sent = await self.send_photo(
                            chat_id=chat_id,
                            photo_path=map_path,
                            caption=message,
                            reply_markup=reply_markup
                        )

                        # Limpar arquivo temporário
                        try:
                            os.remove(map_path)
                        except:
                            pass

                        if map_sent:
                            return True

                # Fallback: tentar Geoapify/Mapbox
                logger.info("⚠️ Fallback para Geoapify/Mapbox")
                map_url = await self.generate_static_map_url(
                    points=coordinates,
                    route_color=route_color
                )

                if map_url:
                    # Enviar foto com o mapa (via URL) - Telegram aceita JSON com 'photo' URL
                    map_sent = await self.send_photo(
                        chat_id=chat_id,
                        photo_url=map_url,
                        caption=message.strip(),
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )

                    if map_sent:
                        logger.info(f"📍 Mapa estático enviado para {chat_id}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao enviar mapa estático: {e}")
        
        # Fallback: se não conseguiu enviar mapa, envia só texto
        if not map_sent:
            return await self.send_message(
                chat_id=chat_id,
                text=message.strip(),
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        
        return map_sent


# Instância global
notifier = TelegramNotifier()


async def notify_route_assigned(
    telegram_id: int,
    route_color: str,
    total_packages: int,
    distance_km: float,
    addresses: list,
    webapp_url: str = None,
    coordinates: List[Tuple[float, float]] = None
) -> bool:
    """
    Função de conveniência para enviar notificação de rota COM MAPA
    
    Args:
        telegram_id: ID do Telegram do entregador
        route_color: Cor da rota em hex
        total_packages: Total de pacotes
        distance_km: Distância em km
        addresses: Lista de endereços
        webapp_url: URL do webapp
        coordinates: Lista de (lat, lng) para gerar mapa estático
    """
    return await notifier.send_route_notification(
        chat_id=telegram_id,
        route_color=route_color,
        total_packages=total_packages,
        distance_km=distance_km,
        addresses=addresses,
        webapp_url=webapp_url,
        coordinates=coordinates
    )
