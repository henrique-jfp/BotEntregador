"""
🛵 BIKE/SCOOTER OPTIMIZER - Otimização específica para entregas de 2 rodas
Considera: linha reta, contramão, calçadas, atalhos
"""
import math
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class ScooterRoute:
    """Rota otimizada para scooter"""
    points_order: List[int]
    total_distance_km: float
    estimated_time_minutes: float
    shortcuts: int  # Número de atalhos usados


class ScooterRouteOptimizer:
    """Otimizador de rotas para scooter elétrica"""
    
    # Parâmetros de scooter
    AVG_SPEED_KMH = 25  # Velocidade média scooter elétrica
    SPEED_PENALTY_TRAFFIC = 0.85  # Menos afetado por tráfego que carro
    SHORTCUT_BONUS = 1.15  # 15% mais rápido usando atalhos
    
    def __init__(self):
        self.mode = 'euclidean'  # Sempre linha reta
    
    def optimize(self, points: List[Tuple[float, float]], 
                base: Tuple[float, float]) -> ScooterRoute:
        """
        Otimiza rota para scooter usando distância euclidiana pura.
        
        Diferenças vs carro:
        - Distância = linha reta (haversine)
        - Pode contramão, calçada, atalhos
        - Menos afetado por tráfego
        - Mais rápido em distâncias curtas
        """
        if len(points) <= 1:
            order = list(range(len(points)))
            return self._build_route(order, points, base)
        
        # Usa algoritmo guloso: sempre vai pro mais próximo
        # (para scooter, isso é melhor que genético)
        order = self._greedy_nearest_neighbor(points, base)
        
        return self._build_route(order, points, base)
    
    def _greedy_nearest_neighbor(self, points: List[Tuple[float, float]], 
                                 base: Tuple[float, float]) -> List[int]:
        """
        Algoritmo guloso: sempre vai pro ponto mais próximo.
        Para scooter, isso é ótimo porque pode ir em linha reta!
        """
        unvisited = set(range(len(points)))
        order = []
        current = base
        
        while unvisited:
            # Encontra ponto mais próximo
            nearest = min(unvisited, 
                         key=lambda i: self._euclidean_distance(current, points[i]))
            
            order.append(nearest)
            current = points[nearest]
            unvisited.remove(nearest)
        
        return order
    
    def _build_route(self, order: List[int], 
                    points: List[Tuple[float, float]],
                    base: Tuple[float, float]) -> ScooterRoute:
        """Constrói objeto de rota"""
        total_distance = 0.0
        shortcuts = 0
        
        # Base → primeiro ponto
        if order:
            total_distance += self._euclidean_distance(base, points[order[0]])
            shortcuts += 1
        
        # Pontos intermediários
        for i in range(len(order) - 1):
            dist = self._euclidean_distance(points[order[i]], points[order[i+1]])
            total_distance += dist
            
            # Considera atalho se distância < 500m
            if dist < 0.5:
                shortcuts += 1
        
        # Último → base
        if order:
            total_distance += self._euclidean_distance(points[order[-1]], base)
        
        # Calcula tempo (scooter é mais rápido em curtas distâncias)
        time = self._estimate_time(total_distance, shortcuts)
        
        return ScooterRoute(
            points_order=order,
            total_distance_km=round(total_distance, 2),
            estimated_time_minutes=round(time, 1),
            shortcuts=shortcuts
        )
    
    def _estimate_time(self, distance_km: float, shortcuts: int) -> float:
        """
        Estima tempo considerando características de scooter.
        
        Scooter é:
        - Mais rápido que carro em < 2km (não espera sinal)
        - Menos afetado por tráfego
        - Bônus por usar atalhos
        """
        # Tempo base
        time_hours = distance_km / self.AVG_SPEED_KMH
        time_minutes = time_hours * 60
        
        # Bônus por atalhos (scooter usa calçadas, contramão)
        if shortcuts > 0:
            time_minutes *= (2.0 - self.SHORTCUT_BONUS)  # Reduz tempo
        
        # Menos afetado por tráfego
        time_minutes *= self.SPEED_PENALTY_TRAFFIC
        
        # Tempo mínimo por parada (3 min)
        time_minutes += 3
        
        return time_minutes
    
    @staticmethod
    def _euclidean_distance(p1: Tuple[float, float], 
                           p2: Tuple[float, float]) -> float:
        """
        Distância euclidiana real entre dois pontos (haversine).
        Para scooter, isso é a distância real viajada!
        """
        lat1, lng1 = p1
        lat2, lng2 = p2
        
        # Haversine
        R = 6371  # Raio da Terra em km
        
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlng/2)**2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def calculate_savings_vs_car(self, scooter_route: ScooterRoute, 
                                car_distance: float) -> dict:
        """
        Calcula economia de scooter vs carro.
        Scooter economiza por poder ir em linha reta!
        """
        distance_saved = car_distance - scooter_route.total_distance_km
        percent_saved = (distance_saved / car_distance * 100) if car_distance > 0 else 0
        
        # Scooter também é mais rápido em cidade
        car_time = (car_distance / 20) * 60  # Carro a 20km/h em cidade
        time_saved = car_time - scooter_route.estimated_time_minutes
        
        return {
            'distance_saved_km': round(distance_saved, 2),
            'distance_saved_percent': round(percent_saved, 1),
            'time_saved_minutes': round(time_saved, 1),
            'shortcuts_used': scooter_route.shortcuts
        }


# Singleton
scooter_optimizer = ScooterRouteOptimizer()
