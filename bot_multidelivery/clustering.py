"""
🧠 IA DE DIVISÃO TERRITORIAL
Usa K-Means para dividir entregas em clusters geográficos otimizados
"""
from dataclasses import dataclass
from typing import List, Tuple
import math


@dataclass
class DeliveryPoint:
    """Ponto de entrega"""
    address: str
    lat: float
    lng: float
    romaneio_id: str
    package_id: str
    priority: str = "normal"  # low, normal, high, urgent


@dataclass
class Cluster:
    """Cluster geográfico de entregas"""
    id: int
    center_lat: float
    center_lng: float
    points: List[DeliveryPoint]
    
    @property
    def total_packages(self) -> int:
        return len(self.points)
    
    def distance_to_base(self, base_lat: float, base_lng: float) -> float:
        return haversine_distance(self.center_lat, self.center_lng, base_lat, base_lng)


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


class TerritoryDivider:
    """Divide entregas em territórios otimizados"""
    
    def __init__(self, base_lat: float, base_lng: float):
        self.base_lat = base_lat
        self.base_lng = base_lng
    
    def divide_into_clusters(self, points: List[DeliveryPoint], k: int = 2, max_iterations: int = 50) -> List[Cluster]:
        """
        K-Means geográfico simplificado
        k=2 significa dividir em 2 territórios
        """
        if len(points) < k:
            # Se tem menos pontos que clusters, cada ponto vira um cluster
            return [Cluster(id=i, center_lat=p.lat, center_lng=p.lng, points=[p]) for i, p in enumerate(points)]
        
        # 1. Inicializa centroides: pontos mais distantes da base
        centroids = self._initialize_centroids(points, k)
        
        # 2. Iteração K-Means
        for iteration in range(max_iterations):
            # Atribui cada ponto ao centroide mais próximo
            clusters_dict = {i: [] for i in range(k)}
            
            for point in points:
                closest_cluster = min(
                    range(k),
                    key=lambda c: haversine_distance(point.lat, point.lng, centroids[c][0], centroids[c][1])
                )
                clusters_dict[closest_cluster].append(point)
            
            # Recalcula centroides
            new_centroids = []
            for i in range(k):
                if clusters_dict[i]:
                    avg_lat = sum(p.lat for p in clusters_dict[i]) / len(clusters_dict[i])
                    avg_lng = sum(p.lng for p in clusters_dict[i]) / len(clusters_dict[i])
                    new_centroids.append((avg_lat, avg_lng))
                else:
                    new_centroids.append(centroids[i])  # Mantém centroide vazio
            
            # Convergiu?
            if new_centroids == centroids:
                break
            
            centroids = new_centroids
        
        # 3. Monta objetos Cluster
        clusters = []
        for i in range(k):
            if clusters_dict[i]:
                clusters.append(Cluster(
                    id=i,
                    center_lat=centroids[i][0],
                    center_lng=centroids[i][1],
                    points=clusters_dict[i]
                ))
        
        # 4. Ordena clusters por distância da base (mais próximo primeiro)
        clusters.sort(key=lambda c: c.distance_to_base(self.base_lat, self.base_lng))
        
        # Renumera IDs após ordenação
        for i, cluster in enumerate(clusters):
            cluster.id = i
        
        return clusters
    
    def _initialize_centroids(self, points: List[DeliveryPoint], k: int) -> List[Tuple[float, float]]:
        """
        Inicialização inteligente: pega os k pontos mais distantes entre si
        Estratégia: K-Means++
        """
        centroids = []
        
        # Primeiro centroide: ponto mais distante da base
        first = max(points, key=lambda p: haversine_distance(p.lat, p.lng, self.base_lat, self.base_lng))
        centroids.append((first.lat, first.lng))
        
        # Próximos centroides: pontos mais distantes dos centroides já escolhidos
        for _ in range(k - 1):
            distances = []
            for point in points:
                min_dist_to_centroid = min(
                    haversine_distance(point.lat, point.lng, c[0], c[1]) for c in centroids
                )
                distances.append((point, min_dist_to_centroid))
            
            # Escolhe o ponto com maior distância mínima
            next_point = max(distances, key=lambda x: x[1])[0]
            centroids.append((next_point.lat, next_point.lng))
        
        return centroids
    
    def optimize_cluster_route(self, cluster: Cluster) -> List[DeliveryPoint]:
        """
        Otimiza ordem de entrega dentro do cluster
        Greedy nearest neighbor a partir da base
        """
        if not cluster.points:
            return []
        
        # Começa da base
        current_lat, current_lng = self.base_lat, self.base_lng
        remaining = cluster.points.copy()
        route = []
        
        while remaining:
            # Próximo ponto = mais próximo do atual
            closest = min(
                remaining,
                key=lambda p: haversine_distance(current_lat, current_lng, p.lat, p.lng)
            )
            route.append(closest)
            remaining.remove(closest)
            current_lat, current_lng = closest.lat, closest.lng
        
        return route
