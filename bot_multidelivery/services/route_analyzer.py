"""
ROUTE ANALYZER - Análise inteligente de rotas com suporte a endereços brutos
Avalia viabilidade, qualidade, prós/contras com detecção automática de tipo
"""
import math
from .osrm_service import get_route_distance_km
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from .address_parser import AddressParser, ParsedAddress


@dataclass
class RouteAnalysis:
    """Resultado completo da análise de uma rota"""
    # Básicas
    total_packages: int
    total_stops: int  # Endereços únicos (paradas reais)
    unique_addresses: int  # Endereços únicos
    
    # Geográficas
    unique_neighborhoods: int  # Bairros únicos
    neighborhood_list: List[str] = field(default_factory=list)
    neighborhood_counts: Dict[str, int] = field(default_factory=dict)
    
    # Distâncias
    distance_to_first_km: float = 0.0
    route_distance_km: float = 0.0
    total_distance_km: float = 0.0
    area_coverage_km2: float = 0.0
    
    # Scores
    density_score: float = 0.0  # Pacotes por km²
    concentration_score: float = 0.0  # 0-10: quão concentrado
    overall_score: float = 0.0  # 0-10: score geral
    
    # Timing
    estimated_time_minutes: float = 0.0
    
    # Análise Qualitativa
    recommendation: str = "Média"
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    ai_comment: str = ""
    
    # ⭐ NOVOS CAMPOS - FINANCEIRO E PERFIL
    route_value: float = 0.0  # Valor total informado pelo usuário
    hourly_earnings: float = 0.0  # R$ por hora
    package_earnings: float = 0.0  # R$ por pacote
    
    # Perfil da Rota
    commercial_count: int = 0  # Quantidade de endereços comerciais
    vertical_count: int = 0  # Quantidade de apartamentos/condomínios
    route_type: str = "Mista"  # 🏠 Residencial / 🏢 Comercial / 🏘️ Mista
    commercial_percentage: float = 0.0  # % de endereços comerciais
    
    # Top Drops
    top_drops: List[Tuple[str, int]] = field(default_factory=list)  # [(rua, count), ...]
    
    # Formatado
    formatted: Dict = field(default_factory=dict)  # Para exibir no frontend


class RouteAnalyzer:
    """Analisa rotas com detecção inteligente de tipos de endereço"""
    
    def __init__(self):
        self.avg_speed_kmh = 20  # Velocidade média de moto/bike
        self.avg_stop_minutes = 3  # Tempo médio por parada
        self.parser = AddressParser()
    
    def analyze_addresses_from_text(
        self,
        addresses_text: str,
        route_value: float = 0.0,
        base_location: Tuple[float, float] = None
    ) -> RouteAnalysis:
        """
        Analisa lista de endereços em formato texto puro
        Cada endereço em uma linha
        """
        lines = [l.strip() for l in addresses_text.strip().split('\n') if l.strip()]
        
        # Converte em formato de delivery para usar analyze_route
        deliveries = []
        for i, addr in enumerate(lines):
            deliveries.append({
                'id': str(i),
                'address': addr,
                'original_address': addr,
                'lat': 0.0,  # Será geocodificado depois se necessário
                'lon': 0.0,
                'bairro': ''
            })
        
        # Usa a análise de rotas (sem coordenadas geográficas)
        return self.analyze_route(
            deliveries=deliveries,
            base_location=base_location,
            route_value=route_value,
            skip_geo=True  # Pula geocodificação
        )
    
    def analyze_route(
        self, 
        deliveries: List[Dict],
        base_location: Tuple[float, float] = None,
        route_value: float = 0.0,
        skip_geo: bool = False
    ) -> RouteAnalysis:
        """
        Analisa uma rota completa com detecção automática de tipo de endereço
        
        Args:
            deliveries: Lista de entregas com endereço + opcionalmente lat/lon
            base_location: (lat, lon) da base (opcional)
            route_value: Valor total da rota informado pelo usuário
            skip_geo: Se True, não usa coordenadas (análise apenas textual)
        
        Returns:
            RouteAnalysis com métricas, score e insights IA
        """
        if not deliveries:
            return self._empty_analysis()
        
        # ====== PARSING DE ENDEREÇOS ======
        parsed_addresses: List[ParsedAddress] = []
        commercial_count = 0
        vertical_count = 0
        street_counts = {}  # Para Top Drops
        unique_addresses_set = set()
        
        for delivery in deliveries:
            raw_addr = delivery.get('address', '')
            if not raw_addr:
                continue
            
            # Parse do endereço
            parsed = self.parser.parse(raw_addr)
            parsed_addresses.append(parsed)
            
            # Contadores
            if parsed.is_commercial:
                commercial_count += 1
            if parsed.is_vertical:
                vertical_count += 1
            
            # Top Drops (por rua)
            street_key = parsed.street.lower()
            street_counts[street_key] = street_counts.get(street_key, 0) + 1
            
            # Endereços únicos
            unique_addresses_set.add(raw_addr.lower())
        
        total_packages = len(deliveries)
        if total_packages == 0:
            return self._empty_analysis()
        
        unique_addresses = len(unique_addresses_set)
        commercial_percentage = (commercial_count / total_packages) * 100 if total_packages > 0 else 0
        
        # Top 3 Drops
        top_drops = sorted(street_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        top_drops_list = [(street.title(), count) for street, count in top_drops]
        
        # ====== TIPO DE ROTA ======
        if commercial_percentage > 40:
            route_type = "🏢 Comercial"
        elif commercial_percentage > 15:
            route_type = "🏘️ Mista"
        else:
            route_type = "🏠 Residencial"
        
        # ====== MÉTRICAS ESPACIAIS ======
        coords = []
        for d in deliveries:
            lat = d.get('lat')
            lon = d.get('lon')
            if lat and lon and not skip_geo:
                coords.append((float(lat), float(lon)))
        
        route_distance = 0.0
        area_coverage = 0.1  # Valor padrão
        density_score = 0.0
        
        if coords and len(coords) > 1:
            route_distance = self._calculate_total_distance(coords)
            area_coverage = self._calculate_coverage_area(coords)
            area_coverage = max(0.1, area_coverage)
            density_score = total_packages / area_coverage
        else:
            # Sem coordenadas: estimativa baseada em paradas únicas
            # Assume ~2km por parada como média conservadora
            est_distance = unique_addresses * 2
            area_coverage = (est_distance ** 2) / 10  # Estimativa de cobertura
            area_coverage = max(0.5, area_coverage)
            density_score = total_packages / area_coverage
        
        dist_to_first = 0.0
        if base_location and coords:
            dist_to_first = self._haversine(
                base_location[0], base_location[1],
                coords[0][0], coords[0][1]
            )
        
        total_distance = dist_to_first + route_distance
        
        # Score de concentração (0-10)
        # Mais pacotes em menos paradas = melhor concentração
        avg_packages_per_stop = total_packages / unique_addresses if unique_addresses > 0 else 1
        concentration_score = min(10, (avg_packages_per_stop / 2) * 10)  # 2 pacotes/parada = nota 10
        
        # ====== TIMING ======
        # Base: 3 min por parada + deslocamento
        travel_time = (total_distance / self.avg_speed_kmh) * 60 if total_distance > 0 else 0
        stop_time = unique_addresses * self.avg_stop_minutes
        
        # Penalty por verticalização (+1.5 min por apto)
        vertical_penalty = vertical_count * 1.5
        
        # Penalty por comercial (mais burocra, menos horas úteis)
        commercial_penalty = (commercial_count * 1.0) if commercial_percentage > 40 else 0
        
        total_time_minutes = travel_time + stop_time + vertical_penalty + commercial_penalty
        total_time_minutes = max(30, total_time_minutes)  # Mínimo 30 min
        
        # ====== FINANCEIRO ======
        hourly_earnings = 0.0
        package_earnings = 0.0
        
        if route_value > 0 and total_time_minutes > 0:
            hourly_earnings = route_value / (total_time_minutes / 60)
            package_earnings = route_value / total_packages
        
        # ====== SCORE FINAL ======
        # Pesos: Concentração (40%), Quantidade (35%), Tipo (25%)
        qty_score = min(10, (total_packages / 80) * 10)  # 80 pacotes = nota 10
        
        # Ajuste por tipo de rota
        type_adjustment = 0
        if "Comercial" in route_type:
            type_adjustment = -1.5  # Mais complicado
        elif "Residencial" in route_type:
            type_adjustment = 0.5  # Um pouco melhor
        
        overall_score = (
            (concentration_score * 0.4) +
            (qty_score * 0.35) +
            (min(10, (density_score / 5)) * 0.25)  # Densidade
        ) + type_adjustment
        
        overall_score = round(min(10, max(0, overall_score)), 1)
        
        # ====== RECOMENDAÇÃO ======
        recommendation = self._get_recommendation(overall_score)
        
        # ====== PROS E CONTRAS ======
        pros = []
        cons = []
        
        # === PRÓS ===
        # Concentração
        if avg_packages_per_stop >= 1.5:
            pros.append(f"📦 Boa concentração: {avg_packages_per_stop:.1f} pacotes por parada")
        if len(top_drops_list) > 0 and top_drops_list[0][1] >= 5:
            pros.append(f"🎯 Hot spot: {top_drops_list[0][1]} entregas na {top_drops_list[0][0]}")
        
        # Volume
        if total_packages >= 100:
            pros.append(f"📈 Volume excelente: {total_packages} pacotes")
        elif total_packages >= 70:
            pros.append(f"📊 Bom volume: {total_packages} pacotes")
        
        # Paradas
        if unique_addresses <= 40 and total_packages >= 50:
            pros.append(f"⚡ Poucas paradas ({unique_addresses}) para muitos pacotes")
        
        # Financeiro
        if hourly_earnings >= 40 and route_value > 0:
            pros.append(f"💰 Ganho excelente: R$ {hourly_earnings:.0f}/hora")
        elif hourly_earnings >= 30 and route_value > 0:
            pros.append(f"💵 Boa média: R$ {hourly_earnings:.0f}/hora")
        
        # Tipo
        if "Residencial" in route_type:
            pros.append("🏠 Residencial: horário flexível")
        
        # Se não tem prós, adiciona genérico
        if not pros:
            if total_packages >= 30:
                pros.append(f"📦 {total_packages} pacotes para entrega")
            if unique_addresses > 0:
                pros.append(f"🗺️ {unique_addresses} pontos de parada mapeados")
        
        # === CONTRAS ===
        # Paradas
        if unique_addresses > 80:
            cons.append(f"⚠️ Muitas paradas ({unique_addresses}): dia cansativo")
        elif unique_addresses > 60:
            cons.append(f"📍 {unique_addresses} paradas: prepare-se para rodar")
        
        # Comercial
        if commercial_percentage > 50:
            cons.append(f"🏢 {commercial_percentage:.0f}% comercial: cuidado com horário (12h-14h fecha)")
        elif commercial_percentage > 30:
            cons.append(f"🏬 Parte comercial ({commercial_percentage:.0f}%): atenção ao horário")
        
        # Vertical
        if vertical_count > (total_packages * 0.6):
            cons.append(f"🏢 Muitos apartamentos ({vertical_count}): subir/descer eleva tempo")
        elif vertical_count > (total_packages * 0.3):
            cons.append(f"🔼 {vertical_count} apartamentos: fator tempo extra")
        
        # Distância estimada
        if unique_addresses > 50 and total_packages < 80:
            cons.append("🛣️ Rota espalhada: muita parada para pouco volume")
        
        # Financeiro
        if hourly_earnings < 20 and route_value > 0:
            cons.append(f"💸 Ganho baixo: apenas R$ {hourly_earnings:.0f}/hora")
        
        # Volume baixo
        if total_packages < 30:
            cons.append(f"📉 Volume baixo ({total_packages} pacotes): pode não compensar")
        
        # Se não tem contras, adiciona algo neutro
        if not cons:
            cons.append("✅ Sem pontos negativos significativos identificados")
        
        # ====== COMENTÁRIO IA DINÂMICO ======
        ai_comment = self._generate_ai_comment(
            score=overall_score,
            route_type=route_type,
            route_value=route_value,
            hourly_earnings=hourly_earnings,
            commercial_pct=commercial_percentage,
            total_packages=total_packages,
            unique_stops=unique_addresses,
            top_drops=top_drops_list
        )
        
        # ====== MONTAGEM DO RESULTADO ======
        analysis = RouteAnalysis(
            total_packages=total_packages,
            total_stops=unique_addresses,
            unique_addresses=unique_addresses,
            unique_neighborhoods=0,  # Pulando isso por enquanto
            neighborhood_list=[],
            neighborhood_counts={},
            distance_to_first_km=dist_to_first,
            route_distance_km=route_distance,
            total_distance_km=total_distance,
            area_coverage_km2=area_coverage,
            density_score=density_score,
            concentration_score=concentration_score,
            estimated_time_minutes=total_time_minutes,
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
            commercial_percentage=commercial_percentage,
            top_drops=top_drops_list
        )
        
        # Monta dict formatado para frontend
        analysis.formatted = self._format_for_display(analysis)
        
        return analysis

    def _generate_ai_comment(
        self,
        score: float,
        route_type: str,
        route_value: float,
        hourly_earnings: float,
        commercial_pct: float,
        total_packages: int,
        unique_stops: int,
        top_drops: List[Tuple[str, int]]
    ) -> str:
        """Gera comentário dinâmico da IA com insights contextuais"""
        import random
        
        # Abertura contextualizada
        if score >= 8.5:
            opener = random.choice([
                "🎯 **ROTA DE OURO!** A famosa 'mata num tapa'.",
                "🔥 **EXCELENTE ESCOLHA!** Pega logo antes que alguém veja!",
                "💰 **PERFEITA PARA LUCRO!** Rápido, concentrado, lucrativo.",
                "👑 **TOP TIER!** Vai contar dinheiro bem feliz no final.",
            ])
        elif score >= 7:
            opener = random.choice([
                "✅ **BOA ROTA.** Volume legal + área compacta.",
                "👍 **RECOMENDADA.** Paga bem e não tira seu dia.",
                "💵 **HONESTA.** Não é perfeita, mas vale a pena.",
                "🎯 **CONSISTENTE.** Dia produtivo à vista.",
            ])
        elif score >= 5:
            opener = random.choice([
                "⚠️ **ROTA MÉDIA.** Vai ser um dia 'osso'.",
                "😐 **PACIÊNCIA OBRIGATÓRIA.** Muita parada, pouca concentração.",
                "🤔 **AVALIE ANTES.** Só se não tiver algo melhor.",
                "📊 **ACEITÁVEL.** Dentro da média, mas nada especial.",
            ])
        else:
            opener = random.choice([
                "💣 **BOMBA!** Evite se possível.",
                "🚫 **NÃO RECOMENDADO.** Vai rodar demais.",
                "❌ **RISCO DE PREJUÍZO.** Cuidado.",
                "⛔ **ESPALHADA DEMAIS.** Vai cansador.",
            ])
        
        parts = [opener]
        
        # Financeiro
        if route_value > 0:
            if hourly_earnings > 40:
                parts.append(f"💸 **Financeiro brutal:** R$ {hourly_earnings:.0f}/hora! Esse é o tipo que faz a diferença no mês.")
            elif hourly_earnings > 30:
                parts.append(f"💰 **Ótima média:** R$ {hourly_earnings:.0f}/hora. Tá na faixa VIP de lucratividade.")
            elif hourly_earnings > 22:
                parts.append(f"💵 **Valor ok:** R$ {hourly_earnings:.0f}/hora. Paga as contas tranquilo.")
            elif hourly_earnings > 15:
                parts.append(f"📊 **Ganho baixo:** R$ {hourly_earnings:.0f}/hora. Só pega se não tiver opção.")
            else:
                parts.append(f"⚠️ **Ganho MUITO baixo:** R$ {hourly_earnings:.0f}/hora. Melhor recusar.")
        
        # Tipo de Rota
        if "Comercial" in route_type:
            parts.append(f"🏢 **{commercial_pct:.0f}% COMERCIAL:** Muita loja/escritório. Dica de ouro: saia cedo pra não pegar 12h-14h (almoço) ou 18h+ (fechado).")
            if top_drops:
                top_street = top_drops[0][0]
                parts.append(f"📍 **TOP CONCENTRAÇÃO:** Rua {top_street} tem {top_drops[0][1]} pontos. Ali é o 'mata' principal.")
        elif "Mista" in route_type:
            parts.append(f"🏘️ **MISTA ({commercial_pct:.0f}% comercial):** Mix de residencial + loja. Cuidado com horário comercial (12h-14h).")
        else:
            parts.append(f"🏠 **RESIDENCIAL PURO:** Apartamentos e casas. Tranquilo de horário.")
        
        # Volume
        if total_packages >= 100:
            parts.append(f"📦 **VOLUME PESADO:** {total_packages} pacotes! Mas em apenas {unique_stops} paradas (ótima concentração).")
        elif total_packages >= 70:
            parts.append(f"📈 **BOM VOLUME:** {total_packages} pacotes para fazer a diferença.")
        elif total_packages < 30:
            parts.append(f"⚠️ **VOLUME BAIXO:** Só {total_packages} pacotes. Não compensa muito rodar.")
        
        # Resumo final
        if score >= 8:
            parts.append("**Veredicto:** 🚀 **PEGUE JÁ!** Essa não dura muito no painel.")
        elif score >= 6:
            parts.append("**Veredicto:** ✅ **RECOMENDADA.** Dia normal, nada anormal.")
        else:
            parts.append("**Veredicto:** ⚠️ **PENSE BEM** antes de confirmar.")
        
        return "\n\n".join(parts)
    
    def _format_for_display(self, analysis: RouteAnalysis) -> Dict:
        """Formata análise para exibir no frontend com destaques"""
        # Score numérico para comparações
        score_num = analysis.overall_score
        
        # Emojis para Top Drops
        drop_emojis = ["🥇", "🥈", "🥉", "📍", "📍"]
        
        return {
            # HEADER - formato que o frontend espera
            "header": {
                "💰 VALOR": f"R$ {analysis.route_value:.2f}" if analysis.route_value > 0 else "---",
                "⭐ TIPO": analysis.route_type,
                "📊 SCORE": score_num,
                "✅ RECOMENDAÇÃO": analysis.recommendation
            },
            
            # FINANCIAL
            "financial": {
                "hourly": f"R$ {analysis.hourly_earnings:.2f}/h" if analysis.hourly_earnings > 0 else "---",
                "per_package": f"R$ {analysis.package_earnings:.2f}" if analysis.package_earnings > 0 else "---",
                "total": f"R$ {analysis.route_value:.2f}" if analysis.route_value > 0 else "---"
            },
            
            # PROFILE - Perfil da Rota
            "profile": {
                "type": analysis.route_type,
                "commercial_pct": f"{analysis.commercial_percentage:.0f}%",
                "total_packages": analysis.total_packages,
                "unique_stops": analysis.total_stops
            },
            
            # TOP DROPS - Ruas com maior concentração
            "top_drops": [
                {
                    "emoji": drop_emojis[i] if i < len(drop_emojis) else "📍",
                    "street": street,
                    "count": count,
                    "percentage": f"{(count/analysis.total_packages)*100:.1f}%" if analysis.total_packages > 0 else "0%"
                }
                for i, (street, count) in enumerate(analysis.top_drops[:5])
            ],
            
            # ANÁLISE QUALITATIVA
            "analysis": {
                "pros": analysis.pros if analysis.pros else ["Sem pontos positivos identificados"],
                "cons": analysis.cons if analysis.cons else ["Sem pontos negativos identificados"]
            },
            
            # COMENTÁRIO IA
            "ai_comment": analysis.ai_comment,
            
            # MÉTRICAS EXTRAS para mapa
            "metrics": {
                "estimated_time": f"{analysis.estimated_time_minutes:.0f} min",
                "distance_km": f"{analysis.total_distance_km:.1f} km" if analysis.total_distance_km > 0 else "Não calculado",
                "density": f"{analysis.density_score:.0f} pkg/km²" if analysis.density_score > 0 else "---",
                "vertical_count": analysis.vertical_count,
                "commercial_count": analysis.commercial_count
            }
        }
    
    def _calculate_total_distance(self, coords: List[Tuple[float, float]]) -> float:
        """Calcula distância total percorrendo todos os pontos (não otimizado)"""
        if len(coords) < 2:
            return 0.0

        osrm_distance = get_route_distance_km(coords)
        if osrm_distance is not None:
            return osrm_distance
        
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
    
    
    def _empty_analysis(self) -> RouteAnalysis:
        """Retorna análise vazia quando não há dados"""
        return RouteAnalysis(
            total_packages=0,
            total_stops=0,
            unique_addresses=0,
            unique_neighborhoods=0,
            neighborhood_list=[],
            neighborhood_counts={},
            distance_to_first_km=0.0,
            route_distance_km=0.0,
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
