# -*- coding: utf-8 -*-
"""
🧠 IA DE DIVISÃO TERRITORIAL V2.0
Sistema inteligente de roteirização com:
- OSRM para rotas reais pelas vias (não linhas retas)
- Agrupamento de pacotes por endereço
- Divisão angular para evitar cruzamentos entre entregadores
- Otimização TSP com 2-opt
- Consideração da base como início e fim
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
import math
import logging
import random
import numpy as np
import os

from bot_multidelivery.services.osrm_service import osrm_client
from bot_multidelivery.proto_lookahead_router import lookahead_route
from bot_multidelivery.config import BotConfig
from bot_multidelivery.tsp_optimizer import TSPOptimizer, is_ortools_available

logger = logging.getLogger(__name__)


from bot_multidelivery.models import DeliveryPoint, DeliveryStop, Cluster


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calcula distância em km entre dois pontos (fórmula de Haversine)"""
    R = 6371  # Raio da Terra em km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


import math
import os
import random
from typing import List, Dict, Tuple, Optional
import numpy as np
from bot_multidelivery.models import DeliveryPoint, DeliveryStop, Cluster
from bot_multidelivery.config import BotConfig
from bot_multidelivery.services.osrm_service import osrm_client
from bot_multidelivery.tsp_optimizer import TSPOptimizer, is_ortools_available
from bot_multidelivery.proto_lookahead_router import lookahead_route

import logging

logger = logging.getLogger("bot_multidelivery.clustering")

class TerritoryDivider:
    """
    Divide entregas em territórios otimizados
    
    Características:
    - Divisão angular (setores de pizza) para evitar cruzamentos
    - Usa OSRM para distâncias reais quando disponível
    - Agrupa pacotes pelo mesmo endereço
    - Considera base como início e fim da rota
    """
    
    def __init__(self, base_lat: float, base_lng: float, mode: str = 'vehicle'):
        self.base_lat = base_lat
        self.base_lng = base_lng
        self.mode = mode
        logger.info(f"📍 TerritoryDivider inicializado com base em ({base_lat:.4f}, {base_lng:.4f}) e modo '{mode}'")
    
    # ==================== AGRUPAMENTO DE PACOTES ====================
    
    def group_packages_by_address(self, points: List[DeliveryPoint]) -> List[DeliveryStop]:
        """
        Agrupa pacotes pelo mesmo endereço em PARADAS
        
        Estratégia RIGOROSA:
        1. Tenta agrupar por endereço exato (string)
        2. Se não funcionar (endereços mal formatados), usa coordenadas (3 casas decimais = ~111m)
        3. Garante numeração sequencial SEM PULOS (1, 2, 3...)
        
        Isso evita:
        - Múltiplas paradas no mesmo local
        - Numeração pulando (1, 2, 5, 9...)
        
        Resultado:
        - Cada parada tem TODOS os pacotes daquele endereço
        - Numeração sequencial **garantida** (1, 2, 3...)
        """
        if not points:
            return []
        
        # Estratégia 1: Tenta agrupar por endereço exato (normalizado)
        address_groups: Dict[str, List[DeliveryPoint]] = {}
        has_valid_addresses = True
        
        for point in points:
            # Normaliza endereço: trim, lowercase, remove excesso de espaços
            normalized_addr = ' '.join(point.address.strip().lower().split())
            
            if not normalized_addr or normalized_addr == "unknown":
                has_valid_addresses = False
                break
            
            if normalized_addr not in address_groups:
                address_groups[normalized_addr] = []
            address_groups[normalized_addr].append(point)
        
        # Se for bem sucedido com endereços, usa isso
        if has_valid_addresses and len(address_groups) > 0:
            logger.info(f"✅ Agrupamento por ENDEREÇO EXATO: {len(points)} pacotes → {len(address_groups)} paradas")
            stops = []
            for addr, packages in address_groups.items():
                # Média ponderada das coordenadas dos pacotes do mesmo endereço
                avg_lat = sum(p.lat for p in packages) / len(packages)
                avg_lng = sum(p.lng for p in packages) / len(packages)
                
                stop = DeliveryStop(
                    stop_number=0,
                    address=packages[0].address,  # Usa address original (não normalizado)
                    lat=avg_lat,
                    lng=avg_lng,
                    packages=packages
                )
                stops.append(stop)
        else:
            # Fallback: Agrupa por coordenadas (3 casas decimais = ~111m de precisão)
            logger.warning(f"⚠️  Agrupamento por COORDENADAS (endereços inválidos)")
            coord_groups: Dict[Tuple[float, float], List[DeliveryPoint]] = {}
            
            for point in points:
                key = (round(point.lat, 3), round(point.lng, 3))  # 3 casas = mais rigoroso
                if key not in coord_groups:
                    coord_groups[key] = []
                coord_groups[key].append(point)
            
            stops = []
            for (lat, lng), packages in coord_groups.items():
                stop = DeliveryStop(
                    stop_number=0,
                    address=packages[0].address,
                    lat=lat,
                    lng=lng,
                    packages=packages
                )
                stops.append(stop)
            
            logger.info(f"📦 {len(points)} pacotes agrupados em {len(stops)} paradas por coordenadas")
        
        logger.info(f"📦 RESULTADO: {len(points)} pacotes → {len(stops)} paradas · numeração será {list(range(1, len(stops)+1))[:5]}...")
        return stops
    
    # ==================== DIVISÃO TERRITORIAL ====================
    
    def divide_into_clusters(self, points: List[DeliveryPoint], k: int) -> List[Cluster]:
        """
        Divide pontos em K territórios usando K-Means e rebalanceamento iterativo.
        Garante que as rotas sejam balanceadas (próximo de 50/50 para k=2).
        """
        if not points:
            return []
        if len(points) < k:
            return [Cluster(id=i, center_lat=p.lat, center_lng=p.lng, points=[p]) for i, p in enumerate(points)]

        # --- FASE 1: CLUSTERING INICIAL COM K-MEANS ---
        # Balanceamento é feito por paradas, não por pacotes individuais.
        stops = self.group_packages_by_address(points)
        if len(stops) < k:
            stops = points # Fallback para pontos individuais se o agrupamento for muito agressivo

        coords = np.array([[s.lat, s.lng] for s in stops])
        try:
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
            labels = kmeans.fit_predict(coords)
        except ImportError:
            logger.error("Scikit-learn não encontrado. Usando divisão angular como fallback.")
            return self._divide_by_angle(points, k)

        # Atribui paradas aos clusters
        stop_clusters = [[] for _ in range(k)]
        for i, stop in enumerate(stops):
            stop_clusters[labels[i]].append(stop)

        # --- FASE 2: REBALANCEAMENTO ITERATIVO ---
        for _ in range(len(stops) * 2): # Limita o número de iterações
            sizes = [len(c) for c in stop_clusters]
            if not any(s == 0 for s in sizes):
                min_cluster_idx, max_cluster_idx = np.argmin(sizes), np.argmax(sizes)

                # Para k=2, forçamos o mais próximo possível de 50/50
                is_balanced = (sizes[max_cluster_idx] - sizes[min_cluster_idx] <= 1)
                if k == 2 and len(stops) > 0:
                    is_balanced = (sizes[max_cluster_idx] - sizes[min_cluster_idx] <= 1)

                if is_balanced:
                    logger.info("✅ Clusters balanceados.")
                    break

                largest_cluster_stops = stop_clusters[max_cluster_idx]
                smallest_cluster_stops = stop_clusters[min_cluster_idx]

                if not smallest_cluster_stops:
                    smallest_centroid = kmeans.cluster_centers_[min_cluster_idx]
                else:
                    smallest_centroid = np.mean([[s.lat, s.lng] for s in smallest_cluster_stops], axis=0)

                # Encontra no cluster maior o ponto mais próximo do centroide do menor (Heurística de troca)
                # Se não balancear, relaxa a heurística para pegar qualquer ponto da borda
                best_stop_to_move = min(
                    largest_cluster_stops,
                    key=lambda s: haversine_distance(s.lat, s.lng, smallest_centroid[0], smallest_centroid[1])
                )

                # Move a parada
                if best_stop_to_move:
                    largest_cluster_stops.remove(best_stop_to_move)
                    smallest_cluster_stops.append(best_stop_to_move)
                else:
                    break
            else:
                break # Evita loop se um cluster ficar vazio

        # --- FASE 3: CONVERTE PARADAS EM PONTOS E CRIA OBJETOS CLUSTER ---
        final_clusters = []
        for i, sc in enumerate(stop_clusters):
            # Expande paradas de volta para pontos de entrega
            pts = [pkg for stop in sc for pkg in stop.packages] if sc and isinstance(sc[0], DeliveryStop) else sc
            
            if pts:
                center_lat = sum(pt.lat for pt in pts) / len(pts)
                center_lng = sum(pt.lng for pt in pts) / len(pts)
            else:
                center_lat = self.base_lat
                center_lng = self.base_lng
            final_clusters.append(Cluster(id=i, center_lat=center_lat, center_lng=center_lng, points=pts))

        logger.info(f"🗺️ K-Means+Balance: {len(points)} pts -> {k} clusters. Balance: {[len(c.points) for c in final_clusters]}")
        return final_clusters
    
    def _divide_by_angle(self, points: List[DeliveryPoint], k: int) -> List[Cluster]:
        """
        Divide pontos em setores angulares a partir da base
        
        Como funciona:
        1. Calcula ângulo de cada ponto em relação à base
        2. Ordena todos os pontos por ângulo
        3. Divide em K setores iguais
        
        Resultado: Cada entregador tem sua "fatia de pizza"
        """
        # Calcula ângulo de cada ponto
        point_angles = []
        for p in points:
            # atan2 retorna ângulo em radianos (-π a π)
            angle = math.atan2(p.lng - self.base_lng, p.lat - self.base_lat)
            angle_deg = math.degrees(angle) % 360  # Normaliza 0-360
            point_angles.append((p, angle_deg))
        
        # Ordena por ângulo (sentido horário a partir do norte)
        point_angles.sort(key=lambda x: x[1])

        # Cada ponto aqui é um REPRESENTANTE (parada). Para garantir que a
        # divisão 50/50 considere paradas (1 parada = 1), usamos peso = 1
        # por representante, ignorando `group_size` (nº de pacotes por parada).
        weights = [1 for _ in point_angles]
        total_weight = sum(weights)
        target_per_sector = float(total_weight) / max(1, k)

        # Particiona por quantis usando soma cumulativa de pesos.
        clusters = [[] for _ in range(k)]
        cum = 0.0
        for (p, angle), w in zip(point_angles, weights):
            # determina índice do cluster baseado no ponto cumulativo
            idx = int(min(math.floor(cum / max(1e-9, target_per_sector)), k - 1))
            clusters[idx].append(p)
            cum += w

        # Constrói objetos Cluster com centróides calculados
        result_clusters: List[Cluster] = []
        for i in range(k):
            pts = clusters[i]
            if pts:
                center_lat = sum(pt.lat for pt in pts) / len(pts)
                center_lng = sum(pt.lng for pt in pts) / len(pts)
            else:
                center_lat = self.base_lat
                center_lng = self.base_lng
            result_clusters.append(Cluster(id=i, center_lat=center_lat, center_lng=center_lng, points=pts))

        return result_clusters
    
    # ==================== OTIMIZAÇÃO DE ROTA ====================
    
    def optimize_cluster_route(self, cluster: Cluster) -> List[DeliveryPoint]:
        """
        Otimiza rota do cluster usando:
        1. Agrupamento por endereço
        2. Greedy nearest neighbor (vizinho mais próximo)
        3. 2-opt (remove cruzamentos)
        4. OSRM para distâncias reais (quando disponível)
        
        Retorna: Lista de DeliveryPoints na ordem otimizada
        """
        if not cluster.points:
            return []
        
        if len(cluster.points) == 1:
            return cluster.points
        
        # PASSO 1: Agrupa pacotes por endereço
        stops = self.group_packages_by_address(cluster.points)
        
        # PASSO 2: Otimiza ordem das paradas
        optimized_stops = self._optimize_stop_order(stops)
        
        # PASSO 2.5: Refina ordem dentro da mesma rua (ordena por numeração)
        # Apenas quando estratégia não for nearest (para manter regra "sempre o mais próximo")
        if BotConfig.ROUTE_STRATEGY != "nearest":
            optimized_stops = self._refine_same_street_order(optimized_stops)
        
        # PASSO 3: Numera paradas sequencialmente
        for i, stop in enumerate(optimized_stops):
            stop.stop_number = i + 1
        
        # Salva stops no cluster
        cluster.stops = optimized_stops
        
        # PASSO 4: Expande para lista de pontos na ordem correta
        result = []
        for stop in optimized_stops:
            result.extend(stop.packages)
        
        logger.info(f"🚀 Rota otimizada: {len(optimized_stops)} paradas, {len(result)} pacotes")
        return result
    
    def _optimize_stop_order(self, stops: List[DeliveryStop]) -> List[DeliveryStop]:
        """
        Otimiza ordem das paradas com MULTI-START:
        - Tenta 5 soluções iniciais (aleatórias)
        - Para cada: Cheaper Insertion + 2-opt + Or-opt
        - Retorna a melhor
        """
        if len(stops) <= 1:
            return stops
        
        logger.info(f"🔍 Otimizando {len(stops)} paradas (estratégia: {BotConfig.ROUTE_STRATEGY}, modo: {self.mode})...")
        
        # Para modo pedestre, usamos Haversine (linha reta) para a matriz de custo.
        if self.mode == 'pedestrian':
            logger.info("🚶 Modo pedestre: usando matriz de distância Haversine (linha reta).")
            coords = [(s.lat, s.lng) for s in stops]
            base_and_coords = [(self.base_lat, self.base_lng)] + coords
            
            # Construir matriz de custo com Haversine
            n = len(base_and_coords)
            cost_matrix = [[0.0] * n for _ in range(n)]
            for i in range(n):
                for j in range(i, n):
                    dist = haversine_distance(base_and_coords[i][0], base_and_coords[i][1], base_and_coords[j][0], base_and_coords[j][1])
                    cost_matrix[i][j] = dist
                    cost_matrix[j][i] = dist
            
            # Usa os otimizadores mais robustos com a matriz Haversine
            if len(stops) > 30 and is_ortools_available():
                logger.info(f"🚀 Rota GRANDE ({len(stops)} paradas) - usando OR-Tools TSP industrial (Haversine)")
                try:
                    optimized = self._ortools_tsp_with_matrix(stops, cost_matrix)
                    if optimized:
                        return optimized
                    logger.warning("⚠️ OR-Tools falhou, usando multi-start heurístico")
                except Exception as e:
                    logger.error(f"❌ Erro no OR-Tools: {e} - fallback para heurística")
            
            return self._multi_start_tsp_with_matrix(stops, cost_matrix)

        # Para modo 'vehicle', tenta usar OSRM para matriz de distâncias
        try:
            coords = [(s.lat, s.lng) for s in stops]
            base_and_coords = [(self.base_lat, self.base_lng)] + coords
            logger.debug(f"📡 Consultando OSRM para {len(base_and_coords)} pontos...")
            result = osrm_client.get_distance_matrix(base_and_coords)

            if not result.fallback_used and result.distances_km:
                logger.info("✅ OSRM respondeu com sucesso - usando distâncias reais (perfil 'foot')")
                # Matriz ajustada: sempre pega o menor entre OSRM e Haversine (com 10% de margem)
                coords_all = base_and_coords
                n = len(coords_all)
                adjusted_matrix = []
                for i in range(len(result.distances_km)):
                    row = []
                    for j in range(len(result.distances_km[i])):
                        osrm_val = result.distances_km[i][j]
                        hav_val = haversine_distance(coords_all[i][0], coords_all[i][1], coords_all[j][0], coords_all[j][1])
                        chosen = min(osrm_val, hav_val * 1.10)
                        row.append(chosen)
                    adjusted_matrix.append(row)

                cost_matrix = adjusted_matrix
                metric = "shortest_path_pedestrian"

                # Usa sempre o otimizador mais robusto
                if len(stops) > 30 and is_ortools_available():
                    logger.info(f"🚀 Rota GRANDE ({len(stops)} paradas) - usando OR-Tools TSP industrial ({metric})")
                    try:
                        optimized = self._ortools_tsp_with_matrix(stops, cost_matrix)
                        if optimized:
                            return optimized
                        logger.warning("⚠️ OR-Tools falhou, usando multi-start heurístico")
                    except Exception as e:
                        logger.error(f"❌ Erro no OR-Tools: {e} - fallback para heurística")
                optimized = self._multi_start_tsp_with_matrix(stops, cost_matrix)
                return optimized
            else:
                logger.warning("⚠️ OSRM retornou fallback - usando Haversine")
        except Exception as e:
            logger.warning(f"❌ OSRM falhou: {e} - usando Haversine")
        
        # Fallback: Greedy nearest neighbor com Haversine
        logger.info("📏 Usando algoritmo Haversine (linha reta)")
        return self._greedy_nearest_neighbor(stops)

    def _select_cost_matrix(
        self,
        distances_km: List[List[float]],
        durations_min: Optional[List[List[float]]],
        coords_all: Optional[List[Tuple[float, float]]] = None,
    ) -> Tuple[List[List[float]], str]:
        """
        Para roteirização a pé, sempre retorna matriz de distância pura.
        """
        return distances_km, "distance_pure"

    def _nearest_neighbor_with_matrix(
        self,
        stops: List[DeliveryStop],
        distances_km: List[List[float]],
        durations_min: Optional[List[List[float]]],
    ) -> List[DeliveryStop]:
        """
        Nearest Neighbor usando matriz OSRM (base -> mais próximo -> próximo ...)
        Respeita a regra: sempre ir para o ponto mais próximo do ponto atual.
        """
        n = len(stops)
        if n <= 1:
            return stops

        cost_matrix, metric = self._select_cost_matrix(distances_km, durations_min)
        logger.info(f"🧭 Nearest Neighbor OSRM ({metric}) com {n} paradas")

        remaining = set(range(n))
        route_indices: List[int] = []

        # Primeira parada: mais próxima da base
        first = min(remaining, key=lambda j: cost_matrix[0][j + 1])
        route_indices.append(first)
        remaining.remove(first)

        # Próximas: sempre a mais próxima do ponto atual
        while remaining:
            current = route_indices[-1]
            next_idx = min(remaining, key=lambda j: cost_matrix[current + 1][j + 1])
            route_indices.append(next_idx)
            remaining.remove(next_idx)

        return [stops[i] for i in route_indices]
    
    def _ortools_tsp_with_matrix(
        self,
        stops: List[DeliveryStop],
        distance_matrix: List[List[float]]
    ) -> Optional[List[DeliveryStop]]:
        """
        TSP INDUSTRIAL usando Google OR-Tools
        Otimização de nível mundial para 50-200+ pontos
        
        Args:
            stops: Lista de paradas
            distance_matrix: Matriz OSRM com distâncias reais (índice 0 = base)
        
        Returns:
            Lista otimizada de stops ou None se falhar
        """
        if not is_ortools_available():
            logger.warning("⚠️ OR-Tools não disponível")
            return None
        
        n = len(stops)
        if n < 2:
            return stops
        
        try:
            # Converte matriz para numpy
            np_matrix = np.array(distance_matrix, dtype=np.float64)
            
            # Cria optimizer com limite de tempo baseado no tamanho
            # 30s para até 100 pontos, 60s para 100-200, 90s para 200+
            if n <= 100:
                time_limit = 30
            elif n <= 200:
                time_limit = 60
            else:
                time_limit = 90
            
            logger.info(f"🧠 OR-Tools TSP: {n} paradas (tempo limite: {time_limit}s)")
            optimizer = TSPOptimizer(time_limit_seconds=time_limit)
            
            # Resolve TSP (índice 0 = base, retorna à base)
            route_order, total_distance = optimizer.optimize_route(
                distance_matrix=np_matrix,
                start_index=0,
                end_index=0  # Retorna à base
            )
            
            if route_order is None or total_distance == float('inf'):
                logger.error("❌ OR-Tools não encontrou solução válida")
                return None
            
            # Remove índice 0 (base) do início e fim
            # route_order = [0, 3, 1, 4, 2, 0] -> [3, 1, 4, 2]
            stop_indices = [idx - 1 for idx in route_order if idx > 0]  # -1 porque matriz tem base no índice 0
            
            # Valida índices
            if len(stop_indices) != n:
                logger.error(f"❌ OR-Tools retornou {len(stop_indices)} paradas, esperado {n}")
                return None
            
            optimized_stops = [stops[i] for i in stop_indices]
            
            logger.info(f"✅ OR-Tools TSP: {total_distance:.2f}km total")
            logger.info(f"   Ordem: {stop_indices[:10]}... (primeiros 10 índices)")
            
            return optimized_stops
            
        except Exception as e:
            logger.error(f"❌ Erro no OR-Tools TSP: {e}")
            logger.exception(e)
            return None
    
    def _refine_same_street_order(self, stops: List[DeliveryStop]) -> List[DeliveryStop]:
        """
        Refina ordem de paradas: quando tem paradas consecutivas na MESMA RUA,
        decide se ordena crescente ou decrescente baseado no caminho mais curto
        """
        if len(stops) < 2:
            return stops
        
        refined = []
        i = 0
        
        while i < len(stops):
            current_stop = stops[i]
            street_name = self._extract_street_name(current_stop.address)
            
            # Encontra todas as paradas consecutivas na mesma rua
            same_street_group = [current_stop]
            j = i + 1
            
            while j < len(stops) and self._extract_street_name(stops[j].address) == street_name:
                same_street_group.append(stops[j])
                j += 1
            
            # Se tem mais de 1 parada na mesma rua, ordena otimamente
            if len(same_street_group) > 1:
                # Considera o ponto anterior (de onde vem)
                prev_lat = refined[-1].lat if refined else self.base_lat
                prev_lng = refined[-1].lng if refined else self.base_lng
                
                # Considera o ponto próximo (para onde vai)
                next_lat = stops[j].lat if j < len(stops) else self.base_lat
                next_lng = stops[j].lng if j < len(stops) else self.base_lng
                
                # Testa ambas as ordenações
                ordered_asc = self._sort_by_street_number(same_street_group, reverse=False)
                ordered_desc = self._sort_by_street_number(same_street_group, reverse=True)
                
                # Calcula distância para cada uma
                dist_asc = self._calc_group_distance(prev_lat, prev_lng, ordered_asc, next_lat, next_lng)
                dist_desc = self._calc_group_distance(prev_lat, prev_lng, ordered_desc, next_lat, next_lng)
                
                # Escolhe a mais curta
                best_order = ordered_asc if dist_asc <= dist_desc else ordered_desc
                direction = "⬆️ crescente" if dist_asc <= dist_desc else "⬇️ decrescente"
                
                logger.debug(f"🏘️  {street_name}: {len(best_order)} paradas {direction} (asc:{dist_asc:.2f}km vs desc:{dist_desc:.2f}km)")
                refined.extend(best_order)
            else:
                refined.append(current_stop)
            
            i = j
        
        return refined
    
    def _calc_group_distance(self, prev_lat: float, prev_lng: float, 
                            group: List[DeliveryStop], 
                            next_lat: float, next_lng: float) -> float:
        """Calcula distância de: prev → grupo → next"""
        total = haversine_distance(prev_lat, prev_lng, group[0].lat, group[0].lng)
        
        for k in range(len(group) - 1):
            total += haversine_distance(group[k].lat, group[k].lng, 
                                       group[k+1].lat, group[k+1].lng)
        
        total += haversine_distance(group[-1].lat, group[-1].lng, next_lat, next_lng)
        
        return total
    
    def _extract_street_name(self, address: str) -> str:
        """Extrai nome da rua do endereço"""
        # Pega até a primeira vírgula (nome da rua + número)
        parts = address.split(',')
        if len(parts) >= 2:
            # Remove o número, fica só o nome da rua
            street_with_number = parts[0].strip()
            # Tenta extrair só o nome (remove o número do final)
            words = street_with_number.split()
            # Remove últimas palavras se forem números
            while words and words[-1].replace('-', '').isdigit():
                words.pop()
            return ' '.join(words)
        return address.split('-')[0].strip()
    
    def _sort_by_street_number(self, stops: List[DeliveryStop], reverse: bool = False) -> List[DeliveryStop]:
        """
        Ordena paradas da mesma rua por numeração
        reverse=False: crescente (63, 108, 116...)
        reverse=True: decrescente (330, 318, 291...)
        """
        # Extrai números dos endereços
        stops_with_numbers = []
        for stop in stops:
            number = self._extract_street_number(stop.address)
            stops_with_numbers.append((stop, number))
        
        # Ordena por número
        sorted_stops = sorted(stops_with_numbers, key=lambda x: x[1] if x[1] is not None else (999999 if not reverse else -1), reverse=reverse)
        
        return [s[0] for s in sorted_stops]
    
    def _extract_street_number(self, address: str) -> Optional[int]:
        """Extrai número do endereço"""
        try:
            # Formato: "Rua X, 123, ..."
            parts = address.split(',')
            if len(parts) >= 2:
                number_part = parts[1].strip().split()[0]
                return int(number_part)
        except:
            pass
        return None
    
    def _greedy_nearest_neighbor(self, stops: List[DeliveryStop]) -> List[DeliveryStop]:
        """Algoritmo guloso: sempre vai para a parada mais próxima"""
        current_lat, current_lng = self.base_lat, self.base_lng
        remaining = stops.copy()
        route = []
        
        while remaining:
            closest = min(
                remaining,
                key=lambda s: haversine_distance(current_lat, current_lng, s.lat, s.lng)
            )
            route.append(closest)
            remaining.remove(closest)
            current_lat, current_lng = closest.lat, closest.lng
        
        # Aplica 2-opt para remover cruzamentos
        route = self._two_opt_stops(route)
        
        return route
    
    def _multi_start_tsp_with_matrix(self, stops: List[DeliveryStop], distance_matrix: List[List[float]]) -> List[DeliveryStop]:
        """
        MULTI-START TSP TURBINADO: MUITO mais agressivo e inteligente!
        
        Estratégia NINJA 🥷:
        1. Tenta 15+ soluções iniciais (não apenas 5)
        2. Combina múltiplas estratégias:
           - Greedy (guloso puro)
           - Greedy customizado (próxima mais próxima)
           - Random (aleatório puro)
           - Nearest-Neighbor com diferentes pontos de partida
           - 2-opt + Or-opt em sequência
        3. Rastreia MELHOR solução de cada estratégia
        4. Retorna absoluta MELHOR com menor kg total
        
        Para BIKE ELÉTRICA: Isto mata! Reduz km significativamente.
        """
        n = len(stops)
        if n <= 2:
            return stops
        
        def route_cost(indices: List[int]) -> float:
            """Calcula custo total de uma rota (base ida + volta)"""
            if not indices:
                return 0
            total = distance_matrix[0][indices[0] + 1]  # base -> primeiro
            for a, b in zip(indices, indices[1:]):
                total += distance_matrix[a + 1][b + 1]
            total += distance_matrix[indices[-1] + 1][0]  # último -> base
            return total
        
        best_route_indices = None
        best_distance = float('inf')
        
        # Determina número de tentativas baseado no tamanho
        if n <= 10:
            num_attempts = 15
        elif n <= 30:
            num_attempts = 20
        else:
            num_attempts = 25
        
        logger.info(f"🚀 TURBINADO MULTI-START TSP: {num_attempts} tentativas para {n} paradas com {len(distance_matrix)}x{len(distance_matrix[0])} matrix")
        
        attempt = 0
        attempt_results = []  # Rastreia todas as tentativas
        
        # ==================== FASE 1: GREEDY PURO ====================
        # Próxima mais próxima do ponto atual
        route_indices = [-1] + list(range(n))
        random.shuffle(route_indices[1:])  # Embaralha começando com índice aleatório
        
        # Reconstrói como greedy a partir do ponto de partida aleatório
        start_idx = route_indices[1]
        ordered = [start_idx]
        remaining = set(range(n)) - {start_idx}
        
        while remaining:
            closest = min(remaining, key=lambda j: distance_matrix[ordered[-1] + 1][j + 1])
            ordered.append(closest)
            remaining.remove(closest)
        
        route_indices = ordered
        route_indices = self._two_opt_indices_with_matrix(route_indices, distance_matrix)
        route_indices = self._or_opt_indices_with_matrix(route_indices, distance_matrix)
        
        current_distance = route_cost(route_indices)
        if current_distance < best_distance:
            best_distance = current_distance
            best_route_indices = route_indices
        
        attempt_results.append(("Greedy Puro", current_distance))
        logger.debug(f"  ✓ Tentativa 1 (Greedy Puro): {current_distance:.2f}km")
        
        # ==================== FASE 2: GREEDY COM MÚLTIPLOS STARTS ====================
        # Tenta começar de cada ponto como ponto de partida
        for start_point in range(min(n, 5)):
            if n <= 20 or (n > 20 and start_point < 3):  # Limita para rotas grandes
                remaining = set(range(n)) - {start_point}
                route_indices = [start_point]
                
                while remaining:
                    closest = min(remaining, key=lambda j: distance_matrix[route_indices[-1] + 1][j + 1])
                    route_indices.append(closest)
                    remaining.remove(closest)
                
                route_indices = self._two_opt_indices_with_matrix(route_indices, distance_matrix)
                route_indices = self._or_opt_indices_with_matrix(route_indices, distance_matrix)
                
                current_distance = route_cost(route_indices)
                if current_distance < best_distance:
                    best_distance = current_distance
                    best_route_indices = route_indices
                
                attempt_results.append((f"Greedy start #{start_point}", current_distance))
                logger.debug(f"  ✓ Greedy start {start_point}: {current_distance:.2f}km")
        
        # ==================== FASE 3: RANDOM + OTIMIZAÇÕES ====================
        for attempt in range(5, num_attempts):
            route_indices = list(range(n))
            random.shuffle(route_indices)
            
            # Aplica 2-opt agressivamente
            route_indices = self._two_opt_indices_with_matrix(route_indices, distance_matrix)
            route_indices = self._or_opt_indices_with_matrix(route_indices, distance_matrix)
            
            current_distance = route_cost(route_indices)
            
            if current_distance < best_distance:
                best_distance = current_distance
                best_route_indices = route_indices
                logger.debug(f"  ✅ Tentativa {attempt + 1} (Random + 2opt): {current_distance:.2f}km NEW BEST!")
            else:
                attempt_results.append((f"Random #{attempt-4}", current_distance))
                logger.debug(f"  ❌ Tentativa {attempt + 1} (Random + 2opt): {current_distance:.2f}km")
        
        # Log resumido
        sorted_results = sorted(attempt_results, key=lambda x: x[1])
        logger.info(f"\n🎯 RESULTADO MULTI-START:")
        logger.info(f"   VENCEDOR: {best_distance:.2f}km")
        logger.info(f"   Diferença para 2º melhor: {sorted_results[0][1] - best_distance:.2f}km ({sorted_results[0][0]}) ")
        logger.info(f"   Total de tentativas: {num_attempts}")
        
        return [stops[i] for i in best_route_indices]
    
    def _tsp_with_matrix(self, stops: List[DeliveryStop], distance_matrix: List[List[float]]) -> List[DeliveryStop]:
        """
        TSP usando matriz OSRM com heurística de INSERÇÃO MAIS BARATA
        + 2-opt com matriz (distâncias reais)
        """
        n = len(stops)
        if n == 0:
            return []
        if n == 1:
            return stops
        
        # 1. Começa com a parada mais próxima da base
        best_first = -1
        best_dist = float('inf')
        for j in range(n):
            dist = distance_matrix[0][j + 1]  # 0 = base, j+1 = stops
            if dist < best_dist:
                best_dist = dist
                best_first = j
        
        if best_first < 0:
            logger.warning("⚠️ Nenhuma primeira parada encontrada")
            return stops
        
        # Rota começa com a primeira parada
        route_indices = [best_first]
        remaining = set(range(n)) - {best_first}
        
        logger.debug(f"🎯 Primeira parada: #{best_first} ({stops[best_first].address[:30]})")
        
        # 2. Para cada parada restante, insere na posição que aumenta MENOS a distância
        while remaining:
            best_insert_pos = -1
            best_insert_stop = -1
            best_insert_cost = float('inf')
            
            for stop_idx in remaining:
                # Testa inserir em cada posição da rota atual
                for insert_pos in range(len(route_indices) + 1):
                    cost = self._insertion_cost(route_indices, stop_idx, insert_pos, distance_matrix)
                    if cost < best_insert_cost:
                        best_insert_cost = cost
                        best_insert_pos = insert_pos
                        best_insert_stop = stop_idx
            
            if best_insert_stop >= 0:
                route_indices.insert(best_insert_pos, best_insert_stop)
                remaining.remove(best_insert_stop)
                logger.debug(f"  ↳ Inseriu parada #{best_insert_stop} na posição {best_insert_pos} (+{best_insert_cost:.2f}km)")
            else:
                break
        
        logger.info(f"🧭 TSP cheaper insertion: {len(route_indices)} paradas")
        
        # 3. 2-opt usando matriz OSRM (distâncias reais)
        route_indices = self._two_opt_indices_with_matrix(route_indices, distance_matrix)
        
        # 4. Or-opt para refinar ainda mais
        route_indices = self._or_opt_indices_with_matrix(route_indices, distance_matrix)
        
        return [stops[i] for i in route_indices]
    
    def _insertion_cost(self, route_indices: List[int], new_stop_idx: int, position: int, 
                       distance_matrix: List[List[float]]) -> float:
        """
        Calcula custo de inserir new_stop_idx na posição 'position' da rota
        Retorna: aumento na distância total
        """
        n = len(route_indices)
        
        if n == 0:
            # Primeira parada: distância da base
            return distance_matrix[0][new_stop_idx + 1]
        
        if position == 0:
            # Inserir no início: base -> new -> old_first
            old_first = route_indices[0]
            old_cost = distance_matrix[0][old_first + 1]
            new_cost = distance_matrix[0][new_stop_idx + 1] + distance_matrix[new_stop_idx + 1][old_first + 1]
            return new_cost - old_cost
        
        if position == n:
            # Inserir no final: old_last -> new -> base
            old_last = route_indices[-1]
            old_cost = distance_matrix[old_last + 1][0]
            new_cost = distance_matrix[old_last + 1][new_stop_idx + 1] + distance_matrix[new_stop_idx + 1][0]
            return new_cost - old_cost
        
        # Inserir no meio: prev -> new -> next
        prev = route_indices[position - 1]
        next_stop = route_indices[position]
        
        old_cost = distance_matrix[prev + 1][next_stop + 1]
        new_cost = distance_matrix[prev + 1][new_stop_idx + 1] + distance_matrix[new_stop_idx + 1][next_stop + 1]
        
        return new_cost - old_cost

    def _two_opt_indices_with_matrix(self, route_indices: List[int], distance_matrix: List[List[float]]) -> List[int]:
        """
        2-opt TURBINADO: Remove cruzamentos eficientemente com matriz OSRM (distâncias reais)
        
        Estratégia agressiva:
        1. Loop externo contínuo até nenhuma melhoria
        2. Testa TODAS as combinações i, j
        3. Se acha melhoria, reaplica até atingir ótimo local
        
        Resultado: Remove praticamente TODOS os cruzamentos
        """
        if len(route_indices) < 4:
            return route_indices

        best_route = route_indices.copy()
        improved = True
        iteration = 0
        max_iterations = 20  # Limita para evitar loop infinito

        def route_cost(indices: List[int]) -> float:
            # Base -> primeiro
            total = distance_matrix[0][indices[0] + 1]
            # Entre paradas
            for a, b in zip(indices, indices[1:]):
                total += distance_matrix[a + 1][b + 1]
            # Último -> base
            total += distance_matrix[indices[-1] + 1][0]
            return total

        best_distance = route_cost(best_route)
        initial_distance = best_distance

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            
            for i in range(len(best_route) - 2):
                for j in range(i + 2, len(best_route)):
                    # Inverte segmento [i:j]
                    new_route = best_route[:i] + best_route[i:j][::-1] + best_route[j:]
                    new_distance = route_cost(new_route)
                    
                    if new_distance < best_distance - 0.01:  # Tolerância 0.01km para flutuação
                        best_route = new_route
                        best_distance = new_distance
                        improved = True
                        logger.debug(f"    🔄 2-opt iter {iteration}: melhoria ({i},{j}) = {new_distance:.2f}km")
                        break  # Reacomça loop após melhoria
                
                if improved:
                    break  # Reacomça loop externo após melhoria
        
        if initial_distance - best_distance > 0.1:
            logger.debug(f"  ✅ 2-opt: redução de {initial_distance:.2f}km → {best_distance:.2f}km (economia {initial_distance - best_distance:.2f}km)")
            
        return best_route
    
    def _or_opt_indices_with_matrix(self, route_indices: List[int], distance_matrix: List[List[float]]) -> List[int]:
        """
        Or-opt TURBINADO: Move sequências de 1-3 paradas para otimizar ainda mais
        
        Complementa o 2-opt: enquanto 2-opt só inverte, Or-opt MOVE segmentos.
        Pode encontrar 10-20% de melhoria adicional em rotas complexas.
        
        Estratégia:
        1. Testa sequências de 1, 2, 3 paradas
        2. Tenta mover para cada posição possível
        3. Continua até nenhuma melhoria
        """
        if len(route_indices) < 4:
            return route_indices

        best_route = route_indices.copy()
        improved = True
        iteration = 0
        max_iterations = 15

        def route_cost(indices: List[int]) -> float:
            total = distance_matrix[0][indices[0] + 1]
            for a, b in zip(indices, indices[1:]):
                total += distance_matrix[a + 1][b + 1]
            total += distance_matrix[indices[-1] + 1][0]
            return total

        best_distance = route_cost(best_route)
        initial_distance = best_distance
        improvements_count = 0

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            
            # Testa mover sequências de 1, 2 ou 3 paradas
            for seq_len in [1, 2, 3]:
                if improved:
                    break
                    
                for i in range(len(best_route) - seq_len + 1):
                    if improved:
                        break
                        
                    # Sequência a mover: best_route[i:i+seq_len]
                    sequence = best_route[i:i+seq_len]
                    remaining = best_route[:i] + best_route[i+seq_len:]
                    
                    # Tenta inserir em cada posição do restante
                    for insert_pos in range(len(remaining) + 1):
                        # Skip trivial moves (volta para mesma posição)
                        if insert_pos == i or (insert_pos > i and insert_pos <= i + seq_len):
                            continue
                        
                        new_route = remaining[:insert_pos] + sequence + remaining[insert_pos:]
                        new_distance = route_cost(new_route)
                        
                        if new_distance < best_distance - 0.01:  # Tolerância
                            best_route = new_route
                            best_distance = new_distance
                            improved = True
                            improvements_count += 1
                            logger.debug(f"    🧩 Or-opt iter {iteration}: moveu {seq_len} parada(s) (pos {i}→{insert_pos}) = {new_distance:.2f}km")
                            break

        if improvements_count > 0:
            logger.debug(f"  ✅ Or-opt: {improvements_count} melhorias, redução {initial_distance:.2f}km → {best_distance:.2f}km (economia {initial_distance - best_distance:.2f}km)")

        return best_route
    
    def _two_opt_stops(self, route: List[DeliveryStop]) -> List[DeliveryStop]:
        """
        2-opt agressivo: elimina cruzamentos invertendo segmentos da rota
        Continua até não conseguir mais melhorias
        """
        if len(route) < 4:
            return route
        
        best_route = route.copy()
        improved = True
        max_no_improvement = 0
        
        while improved and max_no_improvement < 3:
            improved = False
            best_distance = self._calculate_stops_distance(best_route)
            
            # Testa TODAS as combinações possíveis de inversão
            for i in range(len(best_route) - 1):
                for j in range(i + 2, len(best_route) + 1):
                    # Inverte segmento [i:j]
                    new_route = best_route[:i] + best_route[i:j][::-1] + best_route[j:]
                    new_distance = self._calculate_stops_distance(new_route)
                    
                    # Se melhorou, adota a nova rota
                    if new_distance < best_distance:
                        best_route = new_route
                        best_distance = new_distance
                        improved = True
                        max_no_improvement = 0
                        logger.debug(f"🔄 2-opt: melhoria de {new_distance:.2f}km (inverteu {i}-{j})")
            
            if not improved:
                max_no_improvement += 1
        
        return best_route
    
    def _calculate_stops_distance(self, route: List[DeliveryStop]) -> float:
        """Calcula distância total da rota incluindo ida e volta da base"""
        if not route:
            return 0
        
        # Base → Primeira parada
        total = haversine_distance(self.base_lat, self.base_lng, route[0].lat, route[0].lng)
        
        # Entre paradas
        for i in range(len(route) - 1):
            total += haversine_distance(route[i].lat, route[i].lng, 
                                        route[i+1].lat, route[i+1].lng)
        
        # Última parada → Base
        total += haversine_distance(route[-1].lat, route[-1].lng, 
                                    self.base_lat, self.base_lng)
        
        return total
    
    def _calculate_route_distance(self, route: List[DeliveryPoint]) -> float:
        """Calcula distância total da rota (compatibilidade)"""
        if not route:
            return 0
        
        total = haversine_distance(self.base_lat, self.base_lng, route[0].lat, route[0].lng)
        
        for i in range(len(route) - 1):
            total += haversine_distance(route[i].lat, route[i].lng, 
                                        route[i+1].lat, route[i+1].lng)
        
        return total
    
    # ==================== MÉTODOS DE COMPATIBILIDADE ====================
    
    def _distance_matrix_points_to_centroids(
        self,
        points: List[DeliveryPoint],
        centroids: List[Tuple[float, float]],
    ) -> List[List[float]]:
        """Matriz de distâncias entre pontos e centroides (para K-means)"""
        if not points or not centroids:
            return []

        osrm_points = [(p.lat, p.lng) for p in points] + list(centroids)
        sources = list(range(len(points)))
        destinations = list(range(len(points), len(points) + len(centroids)))

        try:
            result = osrm_client.get_distance_matrix(osrm_points, sources, destinations)
            if not result.distances_km or len(result.distances_km) != len(points):
                return self._haversine_matrix_points_to_centroids(points, centroids)
            return result.distances_km
        except Exception as e:
            logger.error(f"Erro ao obter matriz de distância OSRM: {e}")
            return self._haversine_matrix_points_to_centroids(points, centroids)

    def enforce_disjoint_street_segments(self, clusters: List[Cluster], max_iterations: int = 3, round_decimals: int = 5, midpoint_thresh_m: float = 30.0):
        """
        Tenta alterar a atribuição de pontos entre clusters para evitar que duas rotas
        utilizem o MESMO trecho de via (segmento de geometria OSRM).

        Estratégia heurística:
        - Para cada cluster gera a geometria da rota (base -> pontos -> base) via OSRM
        - Extrai segmentos (pares de coordenadas consecutivas) e detecta conflitos
        - Para cada segmento conflitante, move paradas próximas ao segmento do cluster 'perdedor'
          para o cluster 'vencedor' (com critério simples: distância ao ponto médio do segmento)
        - Recalcula centróides e repete até convergir ou atingir max_iterations

        Esta é uma heurística prática (não é ótima), suficiente para reduzir sobreposição
        de trechos em cenários urbanos quando entregadores atuam a pé.
        """
        try:
            from bot_multidelivery.services.osrm_service import osrm_client
        except Exception:
            return clusters

        for iteration in range(max_iterations):
            segment_map = {}
            cluster_segments = {}
            conflicts = []

            # Construir segmentos para cada cluster usando rota otimizada atual
            for cluster in clusters:
                try:
                    # Otimiza rota temporariamente para extrair geometria
                    optimized_points = self.optimize_cluster_route(cluster)
                    coords = [(p.lat, p.lng) for p in optimized_points]
                except Exception:
                    coords = [(p.lat, p.lng) for p in cluster.points]

                if not coords:
                    cluster_segments[cluster.id] = set()
                    continue

                route_pts = [(self.base_lat, self.base_lng)] + coords + [(self.base_lat, self.base_lng)]
                geom_res = osrm_client.get_route_geometry(route_pts)
                coords_geom = []
                try:
                    coords_geom = geom_res.geometry.get('coordinates', []) if geom_res and geom_res.geometry else []
                except Exception:
                    coords_geom = []

                segs = set()
                for i in range(len(coords_geom) - 1):
                    a = coords_geom[i]
                    b = coords_geom[i + 1]
                    # a, b are [lng, lat]
                    lat1, lng1 = round(a[1], round_decimals), round(a[0], round_decimals)
                    lat2, lng2 = round(b[1], round_decimals), round(b[0], round_decimals)
                    key = tuple(sorted(((lat1, lng1), (lat2, lng2))))

                    # detecta conflito se já existir mapa com outro cluster
                    if key in segment_map and segment_map[key] != cluster.id:
                        conflicts.append((cluster.id, segment_map[key], key))
                    else:
                        segment_map[key] = cluster.id

                    segs.add(key)

                cluster_segments[cluster.id] = segs

            if not conflicts:
                # convergiu: sem conflitos
                break

            # Resolver conflitos por heurística simples
            for losing_id, winning_id, seg in conflicts:
                # segmento midpoint
                (lat1, lng1), (lat2, lng2) = seg
                mid_lat = (lat1 + lat2) / 2.0
                mid_lng = (lng1 + lng2) / 2.0

                losing_cluster = next((c for c in clusters if c.id == losing_id), None)
                winning_cluster = next((c for c in clusters if c.id == winning_id), None)
                if not losing_cluster or not winning_cluster:
                    continue

                # Limitar quantos pontos podemos mover por conflito para evitar
                # que um cluster fique desbalanceado (ex.: 38 vs 0 pacotes).
                total_points = sum(len(c.points) for c in clusters)
                avg_load = float(total_points) / max(1, len(clusters))
                # Permite uma tolerância (20%) sobre a média
                max_allowed_per_cluster = int(math.ceil(avg_load * 1.2))

                moved_any = False
                moves_this_conflict = 0
                max_moves_per_conflict = 3  # evita movimentos em massa num só segmento

                # encontra pontos do cluster perdedor próximos ao midpoint
                for p in losing_cluster.points[:]:
                    if moves_this_conflict >= max_moves_per_conflict:
                        break

                    # Não esvaziar completamente o cluster perdedor
                    if len(losing_cluster.points) <= 1:
                        break

                    # Não ultrapassar capacidade do cluster vencedor
                    if len(winning_cluster.points) >= max_allowed_per_cluster:
                        break

                    d_m = haversine_distance(p.lat, p.lng, mid_lat, mid_lng) * 1000.0
                    if d_m <= midpoint_thresh_m:
                        try:
                            losing_cluster.points.remove(p)
                            winning_cluster.points.append(p)
                            moved_any = True
                            moves_this_conflict += 1
                        except ValueError:
                            pass

                # Se nada movido, move o ponto mais próximo do midpoint como fallback
                if not moved_any and losing_cluster.points:
                    pmin = min(losing_cluster.points, key=lambda p: haversine_distance(p.lat, p.lng, mid_lat, mid_lng))
                    try:
                        losing_cluster.points.remove(pmin)
                        winning_cluster.points.append(pmin)
                    except ValueError:
                        pass

            # Recalcular centróides simples após reatribuições
            for c in clusters:
                if c.points:
                    c.center_lat = sum(p.lat for p in c.points) / len(c.points)
                    c.center_lng = sum(p.lng for p in c.points) / len(c.points)

        return clusters

    @staticmethod
    def _haversine_matrix_points_to_centroids(
        points: List[DeliveryPoint],
        centroids: List[Tuple[float, float]],
    ) -> List[List[float]]:
        """Fallback: matriz usando Haversine"""
        matrix: List[List[float]] = []
        for p in points:
            row = [haversine_distance(p.lat, p.lng, c[0], c[1]) for c in centroids]
            matrix.append(row)
        return matrix
