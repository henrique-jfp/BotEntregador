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
    total_stops: int  # Endereços únicos (paradas reais)
    unique_addresses: int  # Endereços únicos
    unique_neighborhoods: int  # Bairros únicos
    neighborhood_list: List[str]  # Lista de bairros
    neighborhood_counts: Dict[str, int]  # Contagem por bairro
    distance_to_first_km: float  # Distância da base até o primeiro ponto
    route_distance_km: float  # Distância percorrendo a rota
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
    # Novos campos v5.0
    route_type: str = "Mista"  # Residencial, Comercial, Mista
    route_value: float = 0.0
    hourly_earnings: float = 0.0
    package_earnings: float = 0.0
    commercial_count: int = 0
    vertical_count: int = 0
    top_drops: List[Tuple[str, int]] = None


class RouteAnalyzer:
    """Analisa rotas da Shopee antes de aceitar"""
    
    def __init__(self):
        self.avg_speed_kmh = 20  # Velocidade média de moto
        self.avg_stop_minutes = 3  # Tempo médio por parada
    
    def analyze_route(
        self, 
        deliveries: List[Dict],
        base_location: Tuple[float, float] = None,
        route_value: float = 0.0  # Novo parâmetro
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
        full_addresses = []
        
        # Keywords para análise de perfil
        commercial_keywords = ['loja', 'ltda', 'me', 'eireli', 'comercio', 'sala', 'shopping', 'center', 'plaza', 'mall', 'edificio', 'ed.', 'empresarial', 'office', 'restaurante', 'farmacia', 'mercado']
        vertical_keywords = ['apto', 'apt', 'bloco', 'bl', 'cond', 'condominio', 'edificio', 'ed.', 'residencial']
        
        commercial_count = 0
        vertical_count = 0
        street_counts = {}  # Para Top Drops
        
        for d in deliveries:
            lat = d.get('lat')
            lon = d.get('lon')
            if lat and lon:
                coords.append((lat, lon))
            
            # Análise de texto
            raw_addr = str(d.get('address', '')).lower() + " " + str(d.get('original_address', '')).lower() + " " + str(d.get('customer', '')).lower()
            
            # Conta tipos
            if any(k in raw_addr for k in commercial_keywords):
                commercial_count += 1
            if any(k in raw_addr for k in vertical_keywords):
                vertical_count += 1
            
            # Top Drops - Simplificado para Rua
            # Pega o nome da rua até a primeira vírgula ou número
            simple_addr = d.get('address', '').split(',')[0].strip()
            if simple_addr:
                street_counts[simple_addr] = street_counts.get(simple_addr, 0) + 1
                
        # Top 3 Drops
        top_drops = sorted(street_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        if not coords:
            return self._empty_analysis()
        
        # Métricas básicas
        total_packages = len(deliveries)
        
        # Conta endereços e bairros únicos + contagem de pacotes por bairro
        unique_addresses_set = set()
        neighborhood_counts = {}
        
        for d in deliveries:
            addr = d.get('address', '').strip().lower()
            if addr:
                unique_addresses_set.add(addr)
            
            bairro = d.get('bairro', '').strip().title()  # Normaliza capitalização
            if bairro:
                neighborhood_counts[bairro] = neighborhood_counts.get(bairro, 0) + 1
        
        unique_addresses = len(unique_addresses_set)
        neighborhood_list = sorted(list(neighborhood_counts.keys()))
        unique_neighborhoods = len(neighborhood_list)
        total_stops = unique_addresses  # Paradas = endereços únicos
        
        # Determina Tipo de Rota
        comm_pct = (commercial_count / total_packages) * 100
        if comm_pct > 40:
            route_type = "🏢 Comercial"
        elif comm_pct > 15:
            route_type = "🏘️ Mista"
        else:
            route_type = "🏠 Residencial"
            
        # Calcula distância total (rota não otimizada, worst-case)
        route_distance = self._calculate_total_distance(coords)
        
        # Distância até o primeiro ponto (se tiver base)
        dist_to_first = 0.0
        if base_location and coords:
            dist_to_first = self._haversine(
                base_location[0], base_location[1],
                coords[0][0], coords[0][1]
            )
            
        total_distance = dist_to_first + route_distance
        
        # Densidade e Cobertura
        if len(coords) > 2:
            coverage = self._calculate_area_coverage(coords)
        else:
            coverage = 0.1
            
        coverage = max(0.1, coverage)  # Evita div por zero
        density = total_packages / coverage
        
        # Score de concentração (0-10)
        # Mais pacotes em menos área = melhor
        concentration_score = min(10, (density / 15))  # 150 pacotes/km2 = nota 10
        
        # Tempo estimado
        # Base: 3 min por parada + deslocamento (20km/h media cidade)
        travel_time = (total_distance / self.avg_speed_kmh) * 60
        stop_time = total_stops * self.avg_stop_minutes
        
        # Ajuste por verticalização (mais tempo em aptos)
        vertical_penalty = (vertical_count * 1.5) # +1.5 min por apto
        total_time = travel_time + stop_time + vertical_penalty
        
        # Cálculos Financeiros
        hourly_earnings = 0.0
        package_earnings = 0.0
        if route_value > 0 and total_time > 0:
            hourly_earnings = route_value / (total_time / 60)
            package_earnings = route_value / total_packages
            
        # Score final
        # Pesos: Densidade (40%), Distância média (30%), Qtd (30%)
        avg_dist_between_stops = route_distance / max(1, total_stops)
        dist_score = max(0, 10 - (avg_dist_between_stops * 5)) # 2km entre paradas = nota 0
        
        qty_score = min(10, total_packages / 8) # 80 pacotes = nota 10
        
        overall_score = (concentration_score * 0.4) + (dist_score * 0.3) + (qty_score * 0.3)
        overall_score = round(min(10, max(0, overall_score)), 1)
        
        # Recomendação
        recommendation = self._get_recommendation(overall_score)
            
        # Prós e Contras
        pros = []
        if density > 50: pros.append("Alta densidade (muitos pacotes/km²)")
        if avg_dist_between_stops < 0.5: pros.append("Paradas muito próximas (<500m)")
        if total_packages > 60: pros.append(f"Volume alto ({total_packages} pacotes)")
        if coverage < 2: pros.append("Área compacta (fácil de completar)")
        if hourly_earnings > 25: pros.append(f"Boa média/hora (R$ {hourly_earnings:.2f})")
        
        cons = []
        if density < 10: cons.append("Baixa densidade (muita rodagem)")
        if avg_dist_between_stops > 2: cons.append("Paradas distantes (>2km)")
        if total_packages < 20: cons.append("Poucos pacotes")
        if dist_to_first > 15: cons.append(f"Longe da base ({dist_to_first:.1f}km)")
        if "Comercial" in route_type: cons.append("Muitos endereços comerciais (atenção horário)")
        
        # Comentário IA Dinâmico
        ai_comment = self._generate_ai_comment(
            overall_score, 
            route_type, 
            route_value, 
            hourly_earnings, 
            neighborhood_list
        )
            
        return RouteAnalysis(
            total_packages=total_packages,
            total_stops=total_stops,
            unique_addresses=unique_addresses,
            unique_neighborhoods=unique_neighborhoods,
            neighborhood_list=neighborhood_list,
            neighborhood_counts=neighborhood_counts,
            distance_to_first_km=dist_to_first,
            route_distance_km=route_distance,
            total_distance_km=total_distance,
            area_coverage_km2=coverage,
            density_score=density,
            concentration_score=concentration_score,
            estimated_time_minutes=total_time,
            overall_score=overall_score,
            recommendation=recommendation,
            pros=pros,
            cons=cons,
            ai_comment=ai_comment,
            route_type=route_type,
            route_value=route_value,
            hourly_earnings=hourly_earnings,
            package_earnings=package_earnings,
            commercial_count=commercial_count,
            vertical_count=vertical_count,
            top_drops=top_drops
        )

    def _generate_ai_comment(self, score, r_type, value, hourly, bairros):
        """Gera texto natural com insights"""
        import random
        
        opener = ""
        if score >= 9:
            opener = random.choice([
                "Essa é filezionho! A famosa 'mata num tapa'.",
                "Rota de ouro. Pega logo antes que alguém veja!"
                "Excelente para fazer dinheiro rápido e voltar pra base."
            ])
        elif score >= 7:
            opener = random.choice([
                "Rota honesta. Tem volume e não roda tanto.",
                "Boa opção pro dia. Dá pra fazer um dinheiro legal.",
                "Não é perfeita, mas paga as contas tranquilo."
            ])
        elif score >= 5:
            opener = random.choice([
                "Rota meio 'osso'. Vai rodar um pouco mais que o ideal.",
                "Tem que ter paciência. Muita parada pingada.",
                "Avalie se o valor compensa o desgaste."
            ])
        else:
            opener = random.choice([
                "Bomba! Só pegue se não tiver outra opção.",
                "Vai gastar pneu e gasolina à toa. Evite.",
                "Essa tá com cara de prejuízo."
            ])
            
        # Contexto financeiro vs Tipo
        finance = ""
        if value > 0:
            if hourly > 30:
                finance = f"O financeiro tá TOP (R$ {hourly:.0f}/h). "
            elif hourly < 15:
                finance = f"O valor tá baixo pro tempo estimado (só R$ {hourly:.0f}/h). "
            else:
                finance = f"Paga a média do mercado. "
                
        # Alerta Comercial
        alert = ""
        if "Comercial" in r_type:
            alert = "⚠️ Atenção: Muita loja/sala. Tente sair cedo pra não pegar horário fechado. "
        elif "Mista" in r_type:
            alert = "👁️ Cuidado com entregas em horário de almoço nas áreas comerciais. "
            
        bairro_txt = f"Foco em {bairros[0]}." if bairros else ""
        
        return f"{opener} {finance}{alert}{bairro_txt}"
    
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
        recommendation: str,
        distance_to_first_km: float = 0.0,
        route_distance_km: float = 0.0
    ) -> str:
        """Gera comentário inteligente da IA"""
        
        # Aviso de deslocamento longo
        commute_warning = ""
        if distance_to_first_km > 15:
             commute_warning = f"\n\n⚠️ <b>ALERTA DE DESLOCAMENTO:</b> Você vai rodar {distance_to_first_km:.1f}km só pra chegar no primeiro ponto. Bota na ponta do lápis!"

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
        
        return comment + commute_warning
    
    def _empty_analysis(self) -> RouteAnalysis:
        """Retorna análise vazia quando não há dados"""
        return RouteAnalysis(
            total_packages=0,
            total_stops=0,
            unique_addresses=0,
            unique_neighborhoods=0,
            neighborhood_list=[],
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
