# -*- coding: utf-8 -*-
"""
🗺️ GERADOR DE MAPA ESTÁTICO PREMIUM PARA TELEGRAM
Gera imagem PNG com:
- Sequência numérica clara (1, 2, 3, 4...)
- Rota traçada conectando os pontos
- Cores vibrantes e legíveis
- Visual profissional (tipo o bot original do usuário)
"""
import logging
from typing import List, Tuple, Optional
import tempfile
import os

logger = logging.getLogger(__name__)

try:
    import folium
    from folium.plugins import PolyLineTextPath
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    logger.warning("⚠️ Folium não instalado. Mapas estáticos desabilitados.")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("⚠️ Selenium não instalado.")


class StaticMapGenerator:
    """
    Gera mapas estáticos PNG de rotas de entrega com estilo premium
    """
    
    # Paleta de cores vibrantes para os marcadores
    MARKER_COLORS = [
        '#FF4444',  # Vermelho vibrante
        '#4CAF50',  # Verde
        '#2196F3',  # Azul
        '#FF9800',  # Laranja
        '#9C27B0',  # Roxo
        '#E91E63',  # Rosa
        '#00BCD4',  # Ciano
        '#FFC107',  # Amarelo
        '#FF6F00',  # Deep Orange
        '#7B1FA2',  # Deep Purple
    ]
    
    @staticmethod
    def generate_route_map(
        coordinates: List[Tuple[float, float]],
        route_number: int = 1,
        deliverer_name: str = "Entregador",
        total_packages: int = 0
    ) -> Optional[str]:
        """
        Gera mapa estático PNG com rota numerada
        
        Args:
            coordinates: Lista de (lat, lng) em ORDEM DE ENTREGA
            route_number: Número da rota (1, 2, 3...)
            deliverer_name: Nome do entregador
            total_packages: Total de pacotes na rota
        
        Returns:
            Caminho para arquivo PNG ou None se falhar
        """
        if not coordinates or len(coordinates) < 2:
            logger.error("❌ Mapa: menos de 2 coordenadas")
            return None
        
        if not FOLIUM_AVAILABLE:
            logger.warning("⚠️ Folium não disponível - não pode gerar mapa")
            return None
        
        try:
            # Calcular centro e zoom
            lats = [c[0] for c in coordinates]
            lngs = [c[1] for c in coordinates]
            
            center_lat = (min(lats) + max(lats)) / 2
            center_lng = (min(lngs) + max(lngs)) / 2
            
            # Calcular zoom baseado na dispersão
            lat_range = max(lats) - min(lats)
            lng_range = max(lngs) - min(lngs)
            max_range = max(lat_range, lng_range)
            
            if max_range < 0.01:
                zoom = 16
            elif max_range < 0.03:
                zoom = 15
            elif max_range < 0.05:
                zoom = 14
            elif max_range < 0.1:
                zoom = 13
            else:
                zoom = 12
            
            logger.info(f"🗺️ Gerando mapa: {len(coordinates)} pontos, zoom={zoom}")
            
            # Criar mapa base
            m = folium.Map(
                location=[center_lat, center_lng],
                zoom_start=zoom,
                tiles='OpenStreetMap'
            )
            
            # Adicionar polyline da rota
            route_color = StaticMapGenerator.MARKER_COLORS[route_number % len(StaticMapGenerator.MARKER_COLORS)]
            folium.PolyLine(
                coordinates,
                color=route_color,
                weight=4,
                opacity=0.8,
                popup='Rota'
            ).add_to(m)
            
            # Adicionar marcadores numerados
            for idx, (lat, lng) in enumerate(coordinates):
                stop_num = idx + 1
                
                # Determinar cor e ícone
                if idx == 0:
                    # Ponto inicial - verde
                    icon_color = '#10b981'
                    popup_text = f"<b>INÍCIO - Parada {stop_num}</b>"
                elif idx == len(coordinates) - 1:
                    # Ponto final - vermelho
                    icon_color = '#ef4444'
                    popup_text = f"<b>FIM - Parada {stop_num}</b>"
                else:
                    # Paradas intermediárias - roxo
                    icon_color = '#a855f7'
                    popup_text = f"<b>Parada {stop_num}</b>"
                
                # Criar marcador customizado
                folium.CircleMarker(
                    location=[lat, lng],
                    radius=20,
                    popup=popup_text,
                    color=icon_color,
                    fill=True,
                    fillColor=icon_color,
                    fillOpacity=0.9,
                    weight=3,
                    opacity=1.0
                ).add_to(m)
                
                # Adicionar número no marcador
                folium.Marker(
                    location=[lat, lng],
                    icon=folium.DivIcon(
                        html=f'''
                        <div style=\"
                            font-size: 14px; 
                            font-weight: bold; 
                            color: white; 
                            background-color: {icon_color}; 
                            border-radius: 50%; 
                            width: 30px; 
                            height: 30px; 
                            display: flex; 
                            align-items: center; 
                            justify-content: center;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                            border: 2px solid white;
                        \">{stop_num}</div>
                        '''
                    )
                ).add_to(m)
            
            # Adicionar título do mapa
            title_html = f'''
            <div style=\"
                position: fixed; 
                top: 10px; 
                left: 10px; 
                width: 300px;
                background-color: white; 
                border-radius: 10px; 
                padding: 12px; 
                font-size: 14px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                z-index: 999;
                font-family: Arial, sans-serif;
            \">
                <div style=\"font-weight: bold; font-size: 16px; margin-bottom: 5px;\">
                    🚚 ROTA {route_number}
                </div>
                <div style=\"color: #666; font-size: 12px; margin-bottom: 3px;\">
                    <strong>Entregador:</strong> {deliverer_name}
                </div>
                <div style=\"color: #666; font-size: 12px;\">
                    <strong>Paradas:</strong> {len(coordinates)} | <strong>Pacotes:</strong> {total_packages}
                </div>
            </div>
            '''
            m.get_root().html.add_child(folium.Element(title_html))
            
            # Salvar em arquivo temporário
            with tempfile.NamedTemporaryFile(
                suffix='.html',
                delete=False,
                mode='w',
                encoding='utf-8'
            ) as tmp:
                m.save(tmp.name)
                html_path = tmp.name
            
            logger.info(f"✅ Mapa HTML gerado: {html_path}")
            
            # Converter HTML para PNG (requer screenshot)
            png_path = StaticMapGenerator._html_to_png(html_path)
            
            # Limpar HTML temporário
            try:
                os.remove(html_path)
            except:
                pass
            
            return png_path
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar mapa: {e}")
            logger.exception(e)
            return None
    
    @staticmethod
    def _html_to_png(html_path: str) -> Optional[str]:
        """
        Converte HTML map para PNG usando Selenium + Chrome
        
        Args:
            html_path: Caminho para arquivo HTML
            
        Returns:
            Caminho para PNG ou None
        """
        if not SELENIUM_AVAILABLE:
            logger.warning("⚠️ Selenium não disponível - retornando HTML")
            return html_path  # Fallback: retornar HTML
        
        try:
            # Configurar Chrome headless
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=800,600")
            
            # Tenta encontrar Chrome/Chromium
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(f"file://{html_path}")
            
            # Screenshot
            png_path = html_path.replace('.html', '.png')
            driver.save_screenshot(png_path)
            driver.quit()
            
            logger.info(f"✅ PNG gerado: {png_path}")
            return png_path
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao converter para PNG: {e} - usando HTML")
            return html_path  # Fallback

    @staticmethod
    def generate_multi_route_map(
        routes_data: List[dict],
        session_name: str = "Entregas"
    ) -> Optional[str]:
        """
        Gera mapa com múltiplas rotas coloridas
        
        Args:
            routes_data: Lista de dicts com:
                - coordinates: [(lat,lng), ...]
                - name: Nome da rota
                - color: Cor hex
                - deliverer: Nome entregador
                
        Returns:
            Caminho PNG ou None
        """
        if not routes_data:
            return None
        
        if not FOLIUM_AVAILABLE:
            logger.warning("⚠️ Folium não disponível")
            return None
        
        try:
            # Coletar todos os pontos para calcular bounds
            all_lats = []
            all_lngs = []
            
            for route in routes_data:
                coords = route.get('coordinates', [])
                all_lats.extend([c[0] for c in coords])
                all_lngs.extend([c[1] for c in coords])
            
            if not all_lats or not all_lngs:
                return None
            
            center_lat = (min(all_lats) + max(all_lats)) / 2
            center_lng = (min(all_lngs) + max(all_lngs)) / 2
            
            lat_range = max(all_lats) - min(all_lats)
            lng_range = max(all_lngs) - min(all_lngs)
            max_range = max(lat_range, lng_range)
            
            zoom = 12
            if max_range < 0.1:
                zoom = 13
            if max_range < 0.05:
                zoom = 14
            
            # Criar mapa
            m = folium.Map(
                location=[center_lat, center_lng],
                zoom_start=zoom,
                tiles='OpenStreetMap'
            )
            
            # Adicionar cada rota
            for route_idx, route in enumerate(routes_data):
                coordinates = route.get('coordinates', [])
                color = route.get('color', '#7C3AED')
                name = route.get('name', f'Rota {route_idx + 1}')
                deliverer = route.get('deliverer', 'Entregador')
                
                if len(coordinates) < 2:
                    continue
                
                # Polyline
                folium.PolyLine(
                    coordinates,
                    color=color,
                    weight=3,
                    opacity=0.7,
                    popup=name
                ).add_to(m)
                
                # Marcadores
                for idx, (lat, lng) in enumerate(coordinates):
                    marker_color = '#10b981' if idx == 0 else ('#ef4444' if idx == len(coordinates)-1 else color)
                    
                    folium.CircleMarker(
                        location=[lat, lng],
                        radius=15,
                        color=marker_color,
                        fill=True,
                        fillColor=marker_color,
                        fillOpacity=0.8,
                        weight=2
                    ).add_to(m)
            
            # Salvar
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w') as tmp:
                m.save(tmp.name)
                return tmp.name
            
        except Exception as e:
            logger.error(f"❌ Erro mapa multi-rota: {e}")
            return None
