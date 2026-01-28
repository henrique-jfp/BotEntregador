"""
ROUTE ANALYZER - Análise inteligente de rotas da Shopee
Avalia viabilidade, qualidade, prós/contras de romaneios externos
"""
import math
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class RouteAnalysis:
    """Resultado da análise de uma rota"""
    total_packages: int
    total_stops: int
    total_distance_km: float
    area_coverage_km2: float
    density_score: float  # Pacotes por km²
    concentration_score: float  # 0-10: quão concentrado está
    estimated_time_minutes: float
    overall_score: float  # 0-10: score geral
    recommendation: str  # "Excelente", "Boa", "Média", "Ruim"
    pros: List[str]
    cons: List[str]
    ai_comment: str


class RouteAnalyzer:
    """Analisa rotas da Shopee antes de aceitar"""
    
    def __init__(self):
        self.avg_speed_kmh = 20  # Velocidade média de moto
        self.avg_stop_minutes = 3  # Tempo médio por parada
    
    def analyze_route(
        self, 
        deliveries: List[Dict],
        base_location: Tuple[float, float] = None
    ) -> RouteAnalysis:
        """
        Analisa uma rota e retorna métricas + IA comment
        
        Args:
            deliveries: Lista de entregas com lat/lon
            base_location: (lat, lon) da base (opcional)
        
        Returns:
            RouteAnalysis com score, pros/cons e comentário IA
        """
        if not deliveries:
            return self._empty_analysis()
        
        # Extrai coordenadas
        coords = []
        for d in deliveries:
            lat = d.get('lat')
            lon = d.get('lon')
            if lat and lon:
                coords.append((lat, lon))
        
        if not coords:
            return self._empty_analysis()
        
        # Métricas básicas
        total_packages = len(deliveries)
        total_stops = len(coords)
        
        # Calcula distância total (rota não otimizada, worst-case)
        total_distance = self._calculate_total_distance(coords)
        
        # Calcula área de cobertura (bounding box)
        area_km2 = self._calculate_coverage_area(coords)
        
        # Densidade: pacotes por km²
        density = total_packages / area_km2 if area_km2 > 0 else 0
        
        # Concentração: quão próximos estão os pontos (0-10)
        concentration = self._calculate_concentration_score(coords)
        
        # Tempo estimado
        travel_time = (total_distance / self.avg_speed_kmh) * 60
        stop_time = total_stops * self.avg_stop_minutes
        total_time = travel_time + stop_time
        
        # Score geral (0-10)
        overall_score = self._calculate_overall_score(
            concentration, density, total_distance, total_packages
        )
        
        # Recomendação
        recommendation = self._get_recommendation(overall_score)
        
        # Prós e contras
        pros, cons = self._generate_pros_cons(
            concentration, density, total_distance, total_packages, area_km2
        )
        
        # Comentário da IA
        ai_comment = self._generate_ai_comment(
            total_packages, total_distance, concentration, 
            density, overall_score, recommendation
        )
        
        return RouteAnalysis(
            total_packages=total_packages,
            total_stops=total_stops,
            total_distance_km=total_distance,
            area_coverage_km2=area_km2,
            density_score=density,
            concentration_score=concentration,
            estimated_time_minutes=total_time,
            overall_score=overall_score,
            recommendation=recommendation,
            pros=pros,
            cons=cons,
            ai_comment=ai_comment
        )
    
    def _calculate_total_distance(self, coords: List[Tuple[float, float]]) -> float:
        """Calcula distância total percorrendo todos os pontos (não otimizado)"""
        if len(coords) < 2:
            return 0.0
        
        total = 0.0
        for i in range(len(coords) - 1):
            dist = self._haversine(coords[i][0], coords[i][1], 
                                   coords[i+1][0], coords[i+1][1])
            total += dist
        
        return total
    
    def _calculate_coverage_area(self, coords: List[Tuple[float, float]]) -> float:
        """Calcula área do bounding box em km²"""
        if not coords:
            return 0.0
        
        lats = [c[0] for c in coords]
        lons = [c[1] for c in coords]
        
        lat_min, lat_max = min(lats), max(lats)
        lon_min, lon_max = min(lons), max(lons)
        
        # Largura e altura em km
        width = self._haversine(lat_min, lon_min, lat_min, lon_max)
        height = self._haversine(lat_min, lon_min, lat_max, lon_min)
        
        return width * height
    
    def _calculate_concentration_score(self, coords: List[Tuple[float, float]]) -> float:
        """
        Score de concentração (0-10)
        10 = super concentrado (área pequena)
        0 = muito disperso (área gigante)
        """
        if len(coords) < 2:
            return 10.0
        
        # Calcula desvio padrão das distâncias ao centroid
        center_lat = sum(c[0] for c in coords) / len(coords)
        center_lon = sum(c[1] for c in coords) / len(coords)
        
        distances = [
            self._haversine(c[0], c[1], center_lat, center_lon)
            for c in coords
        ]
        
        avg_dist = sum(distances) / len(distances)
        
        # Mapeia distância média para score (0-10)
        # 0-2km = score 10
        # 2-5km = score 7
        # 5-10km = score 4
        # >10km = score 0
        if avg_dist <= 2:
            score = 10
        elif avg_dist <= 5:
            score = 10 - ((avg_dist - 2) / 3) * 3
        elif avg_dist <= 10:
            score = 7 - ((avg_dist - 5) / 5) * 3
        else:
            score = max(0, 4 - ((avg_dist - 10) / 10) * 4)
        
        return round(score, 1)
    
    def _calculate_overall_score(
        self, 
        concentration: float, 
        density: float, 
        total_distance: float,
        total_packages: int
    ) -> float:
        """
        Score geral da rota (0-10)
        
        Fatores:
        - Concentração (peso 40%)
        - Densidade (peso 30%)
        - Distância vs pacotes (peso 30%)
        """
        # Normaliza densidade (0-10)
        # >50 pacotes/km² = excelente
        # 20-50 = bom
        # 10-20 = ok
        # <10 = ruim
        if density >= 50:
            density_score = 10
        elif density >= 20:
            density_score = 7 + ((density - 20) / 30) * 3
        elif density >= 10:
            density_score = 4 + ((density - 10) / 10) * 3
        else:
            density_score = max(0, (density / 10) * 4)
        
        # Normaliza distância/pacote (0-10)
        # <0.5km/pacote = excelente
        # 0.5-1km = bom
        # 1-2km = ok
        # >2km = ruim
        km_per_package = total_distance / total_packages if total_packages > 0 else 10
        if km_per_package <= 0.5:
            distance_score = 10
        elif km_per_package <= 1:
            distance_score = 7 + ((1 - km_per_package) / 0.5) * 3
        elif km_per_package <= 2:
            distance_score = 4 + ((2 - km_per_package) / 1) * 3
        else:
            distance_score = max(0, 4 - ((km_per_package - 2) / 2) * 4)
        
        # Score ponderado
        overall = (
            concentration * 0.4 +
            density_score * 0.3 +
            distance_score * 0.3
        )
        
        return round(overall, 1)
    
    def _get_recommendation(self, score: float) -> str:
        """Converte score em recomendação"""
        if score >= 8:
            return "🔥 EXCELENTE"
        elif score >= 6:
            return "✅ BOA"
        elif score >= 4:
            return "⚠️ MÉDIA"
        else:
            return "❌ RUIM"
    
    def _generate_pros_cons(
        self,
        concentration: float,
        density: float,
        total_distance: float,
        total_packages: int,
        area_km2: float
    ) -> Tuple[List[str], List[str]]:
        """Gera lista de prós e contras"""
        pros = []
        cons = []
        
        # Concentração
        if concentration >= 7:
            pros.append("📍 Alta concentração geográfica")
        elif concentration <= 4:
            cons.append("🗺️ Pontos muito dispersos")
        
        # Densidade
        if density >= 30:
            pros.append("📦 Densidade alta (muitos pacotes/km²)")
        elif density <= 10:
            cons.append("📉 Densidade baixa (poucos pacotes por área)")
        
        # Distância
        km_per_package = total_distance / total_packages if total_packages > 0 else 10
        if km_per_package <= 0.7:
            pros.append("🛣️ Distância curta entre paradas")
        elif km_per_package >= 2:
            cons.append("🚗 Muita distância entre entregas")
        
        # Número de pacotes
        if total_packages >= 40:
            pros.append(f"💰 Volume alto ({total_packages} pacotes)")
        elif total_packages <= 15:
            cons.append(f"📉 Volume baixo ({total_packages} pacotes)")
        
        # Área
        if area_km2 <= 5:
            pros.append("🎯 Área compacta (fácil de completar)")
        elif area_km2 >= 20:
            cons.append("🌍 Área muito extensa")
        
        return pros, cons
    
    def _generate_ai_comment(
        self,
        total_packages: int,
        total_distance: float,
        concentration: float,
        density: float,
        overall_score: float,
        recommendation: str
    ) -> str:
        """Gera comentário inteligente da IA"""
        
        if overall_score >= 8:
            comment = (
                f"🎯 <b>ROTA EXCELENTE!</b>\n\n"
                f"Essa é uma rota muito boa pra pegar. Com {total_packages} pacotes "
                f"concentrados em uma área compacta, você vai ter alta produtividade. "
                f"A densidade de {density:.1f} pacotes/km² indica que não vai perder tempo "
                f"rodando à toa. Provavelmente consegue finalizar rápido e ainda pegar outra!"
            )
        
        elif overall_score >= 6:
            comment = (
                f"✅ <b>ROTA BOA</b>\n\n"
                f"Rota válida com {total_packages} pacotes. A concentração de {concentration:.1f}/10 "
                f"é razoável. Você vai rodar uns {total_distance:.1f}km, mas é factível. "
                f"Não é a melhor rota, mas compensa se não tiver muita opção no momento."
            )
        
        elif overall_score >= 4:
            comment = (
                f"⚠️ <b>ROTA MÉDIA</b>\n\n"
                f"Essa rota tá meio dispersa. {total_packages} pacotes espalhados em "
                f"~{total_distance:.1f}km pode cansar. A concentração de {concentration:.1f}/10 "
                f"indica que vai ter bastante deslocamento entre paradas. "
                f"Só vale se tiver urgência de faturar ou se o valor por pacote compensar."
            )
        
        else:
            comment = (
                f"❌ <b>ROTA RUIM</b>\n\n"
                f"Não recomendo pegar essa rota. Com apenas {total_packages} pacotes "
                f"espalhados por {total_distance:.1f}km, a relação custo-benefício é péssima. "
                f"Densidade baixa ({density:.1f} pacotes/km²) = muito tempo rodando, pouco faturando. "
                f"Melhor esperar uma rota mais concentrada aparecer!"
            )
        
        return comment
    
    def _empty_analysis(self) -> RouteAnalysis:
        """Retorna análise vazia quando não há dados"""
        return RouteAnalysis(
            total_packages=0,
            total_stops=0,
            total_distance_km=0,
            area_coverage_km2=0,
            density_score=0,
            concentration_score=0,
            estimated_time_minutes=0,
            overall_score=0,
            recommendation="❌ SEM DADOS",
            pros=[],
            cons=[],
            ai_comment="Nenhum dado válido encontrado para análise."
        )
    
    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula distância haversine entre dois pontos"""
        R = 6371  # Raio da Terra em km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(dlon / 2) ** 2)
        
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c


# Instância global
route_analyzer = RouteAnalyzer()
