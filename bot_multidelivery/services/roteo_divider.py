"""
ROTEO DIVIDER - Divide romaneio entre N entregadores
Balanceia por: distancia, numero de pacotes, densidade geografica
"""
import math
from typing import List, Dict, Tuple
from dataclasses import dataclass
import sys
from pathlib import Path

# Fix imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from bot_multidelivery.parsers.shopee_parser import ShopeeDelivery, ShopeeRomaneioParser
from bot_multidelivery.services.scooter_optimizer import ScooterRouteOptimizer


@dataclass
class EntregadorRoute:
    """Rota otimizada de um entregador"""
    entregador_id: str
    entregador_nome: str
    stops: List[Tuple[float, float, List[ShopeeDelivery]]]  # (lat, lon, [deliveries])
    optimized_order: List[int]  # Ordem otimizada dos stops
    total_distance_km: float
    total_time_minutes: float
    total_packages: int
    start_point: Tuple[float, float, str]  # lat, lon, address
    end_point: Tuple[float, float, str]
    shortcuts: int
    color: str = None  # ⚡ COR DA ROTA (vermelho, azul, verde, etc)


class RoteoDivider:
    """
    Divide romaneio entre entregadores de forma inteligente
    
    Estrategia:
    1. Agrupa entregas por stop (mesmo endereco)
    2. Clusteriza stops geograficamente
    3. Balanceia clusters entre entregadores
    4. Otimiza rota de cada um
    """
    
    def __init__(self):
        self.optimizer = ScooterRouteOptimizer()
    
    def divide_romaneio(
        self, 
        deliveries: List[ShopeeDelivery],
        num_entregadores: int,
        entregadores_info: Dict[str, str],  # {id: nome}
        colors: List[str] = None  # ⚡ CORES SELECIONADAS
    ) -> List[EntregadorRoute]:
        """
        Divide romaneio entre N entregadores
        
        Args:
            deliveries: Lista de entregas parseadas do Excel
            num_entregadores: Quantos entregadores vao trabalhar
            entregadores_info: Dicionario com ID e nome dos entregadores
            colors: Lista de cores selecionadas (ex: ['vermelho', 'azul'])
            
        Returns:
            Lista de rotas otimizadas (uma por entregador)
        """
        # Agrupa por stop
        stop_groups = self._group_by_stop(deliveries)
        
        # Clusteriza geograficamente
        clusters = self._geo_cluster(stop_groups, num_entregadores)
        
        # Cria rota para cada entregador
        routes = []
        entregador_ids = list(entregadores_info.keys())
        
        for i, cluster in enumerate(clusters):
            if i >= len(entregador_ids):
                break
                
            entregador_id = entregador_ids[i]
            entregador_nome = entregadores_info[entregador_id]
            
            # ⚡ Atribui cor do array (cicla se tiver menos cores que entregadores)
            route_color = None
            if colors and len(colors) > 0:
                route_color = colors[i % len(colors)]
            
            route = self._optimize_cluster(
                cluster, 
                entregador_id, 
                entregador_nome,
                color=route_color  # ⚡ PASSA A COR
            )
            routes.append(route)
        
        return routes
    
    def _group_by_stop(
        self, 
        deliveries: List[ShopeeDelivery]
    ) -> Dict[int, List[ShopeeDelivery]]:
        """Agrupa entregas por stop"""
        groups = {}
        for d in deliveries:
            if d.stop not in groups:
                groups[d.stop] = []
            groups[d.stop].append(d)
        return groups
    
    def _geo_cluster(
        self, 
        stop_groups: Dict[int, List[ShopeeDelivery]],
        num_clusters: int
    ) -> List[List[Tuple[int, List[ShopeeDelivery]]]]:
        """
        Clusteriza stops geograficamente
        
        Usa K-means simples baseado em lat/lon
        """
        if num_clusters >= len(stop_groups):
            # Cada entregador pega 1 stop
            return [[(stop_id, items)] for stop_id, items in stop_groups.items()]
        
        # Extrai centroids dos stops
        stops_list = list(stop_groups.items())
        centroids = []
        
        for stop_id, items in stops_list:
            lat = items[0].latitude
            lon = items[0].longitude
            centroids.append((lat, lon))
        
        # K-means simples
        clusters = [[] for _ in range(num_clusters)]
        
        # Inicializa centroids dos clusters (pega stops mais distantes)
        cluster_centers = self._init_kmeans_centers(centroids, num_clusters)
        
        # Atribui cada stop ao cluster mais proximo
        for idx, (stop_id, items) in enumerate(stops_list):
            stop_lat, stop_lon = centroids[idx]
            
            # Acha cluster mais proximo
            min_dist = float('inf')
            min_cluster = 0
            
            for c_idx, (c_lat, c_lon) in enumerate(cluster_centers):
                dist = self._haversine(stop_lat, stop_lon, c_lat, c_lon)
                if dist < min_dist:
                    min_dist = dist
                    min_cluster = c_idx
            
            clusters[min_cluster].append((stop_id, items))
        
        # Remove clusters vazios
        clusters = [c for c in clusters if c]
        
        return clusters
    
    def _init_kmeans_centers(
        self, 
        points: List[Tuple[float, float]], 
        k: int
    ) -> List[Tuple[float, float]]:
        """Inicializa centroids do K-means (K-means++)"""
        if k >= len(points):
            return points[:k]
        
        centers = [points[0]]
        
        for _ in range(k - 1):
            # Acha ponto mais distante dos centroids existentes
            max_min_dist = 0
            farthest = None
            
            for point in points:
                min_dist = min(
                    self._haversine(point[0], point[1], c[0], c[1])
                    for c in centers
                )
                if min_dist > max_min_dist:
                    max_min_dist = min_dist
                    farthest = point
            
            if farthest:
                centers.append(farthest)
        
        return centers
    
    def _optimize_cluster(
        self, 
        cluster: List[Tuple[int, List[ShopeeDelivery]]],
        entregador_id: str,
        entregador_nome: str,
        color: str = None  # ⚡ COR DA ROTA
    ) -> EntregadorRoute:
        """Otimiza rota de um cluster (entregador)"""
        
        # Converte stops para pontos
        points = []
        stop_data = []
        
        for stop_id, items in cluster:
            lat = items[0].latitude
            lon = items[0].longitude
            points.append((lat, lon))
            stop_data.append((lat, lon, items))
        
        # Otimiza rota
        base = points[0] if points else (0, 0)
        route = self.optimizer.optimize(points, base)
        
        # Reordena stops
        ordered_stops = [stop_data[i] for i in route.points_order]
        
        # Calcula totais
        total_packages = sum(len(items) for _, _, items in stop_data)
        
        # Pontos inicio/fim
        start_lat, start_lon, start_items = ordered_stops[0]
        start_address = start_items[0].address
        
        end_lat, end_lon, end_items = ordered_stops[-1]
        end_address = end_items[0].address
        
        return EntregadorRoute(
            entregador_id=entregador_id,
            entregador_nome=entregador_nome,
            stops=ordered_stops,
            optimized_order=route.points_order,
            total_distance_km=route.total_distance_km,
            total_time_minutes=route.estimated_time_minutes,
            total_packages=total_packages,
            start_point=(start_lat, start_lon, start_address),
            end_point=(end_lat, end_lon, end_address),
            shortcuts=route.shortcuts,
            color=color  # ⚡ ADICIONA COR NA ROTA
        )
    
    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula distancia haversine entre dois pontos"""
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
    
    def print_division_summary(self, routes: List[EntregadorRoute]):
        """Imprime resumo da divisao"""
        print("=" * 60)
        print("DIVISAO DE ROTA - RESUMO")
        print("=" * 60)
        
        total_packages = sum(r.total_packages for r in routes)
        total_distance = sum(r.total_distance_km for r in routes)
        total_time = sum(r.total_time_minutes for r in routes)
        
        print(f"\nTotal: {total_packages} pacotes | {total_distance:.2f} km | {total_time:.0f} min")
        print(f"Entregadores: {len(routes)}\n")
        
        for i, route in enumerate(routes, 1):
            print(f"{i}. {route.entregador_nome} (ID: {route.entregador_id})")
            print(f"   Pacotes: {route.total_packages}")
            print(f"   Paradas: {len(route.stops)}")
            print(f"   Distancia: {route.total_distance_km:.2f} km")
            print(f"   Tempo: {route.total_time_minutes:.0f} min")
            print(f"   Atalhos: {route.shortcuts}")
            print(f"   Inicio: {route.start_point[2][:50]}...")
            print(f"   Fim: {route.end_point[2][:50]}...")
            print()


# CLI
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Uso: python roteo_divider.py <arquivo.xlsx> <num_entregadores>")
        sys.exit(1)
    
    excel_path = sys.argv[1]
    num_entregadores = int(sys.argv[2])
    
    # Parse
    deliveries = ShopeeRomaneioParser.parse(excel_path)
    print(f"[OK] {len(deliveries)} entregas parseadas\n")
    
    # Cria entregadores fake para teste
    entregadores = {
        f"E{i+1}": f"Entregador {i+1}"
        for i in range(num_entregadores)
    }
    
    # Divide
    divider = RoteoDivider()
    routes = divider.divide_romaneio(deliveries, num_entregadores, entregadores)
    
    # Mostra resultado
    divider.print_division_summary(routes)
