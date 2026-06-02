"""
🧬 OTIMIZAÇÃO DE ROTAS COM ALGORITMO GENÉTICO
Muito mais foda que K-means - resolve TSP de forma criativa
"""
import random
import math
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class GeneticConfig:
    population_size: int = 50
    generations: int = 100
    mutation_rate: float = 0.15
    elite_size: int = 10
    tournament_size: int = 5


class GeneticRouteOptimizer:
    """Otimizador genético para rotas de entrega"""
    
    def __init__(self, config: GeneticConfig = None):
        self.config = config or GeneticConfig()
    
    def optimize(self, points: List[Tuple[float, float]], 
                base_coords: Tuple[float, float]) -> List[int]:
        """
        Otimiza ordem de visita aos pontos.
        
        Args:
            points: Lista de (lat, lng)
            base_coords: Coordenadas da base (lat, lng)
        
        Returns:
            Lista de índices na ordem otimizada
        """
        if len(points) <= 3:
            # Pra poucos pontos, força bruta é melhor
            return self._brute_force_optimize(points, base_coords)
        
        # Algoritmo genético
        population = self._create_initial_population(len(points))
        
        for generation in range(self.config.generations):
            # Avalia fitness de cada indivíduo
            fitness_scores = [
                self._calculate_fitness(individual, points, base_coords)
                for individual in population
            ]
            
            # Seleciona elite
            elite_indices = sorted(range(len(fitness_scores)), 
                                 key=lambda i: fitness_scores[i])[:self.config.elite_size]
            elite = [population[i] for i in elite_indices]
            
            # Cria nova geração
            new_population = elite.copy()
            
            while len(new_population) < self.config.population_size:
                # Seleção por torneio
                parent1 = self._tournament_selection(population, fitness_scores)
                parent2 = self._tournament_selection(population, fitness_scores)
                
                # Crossover
                child = self._crossover(parent1, parent2)
                
                # Mutação
                if random.random() < self.config.mutation_rate:
                    child = self._mutate(child)
                
                new_population.append(child)
            
            population = new_population
        
        # Retorna melhor solução
        fitness_scores = [
            self._calculate_fitness(ind, points, base_coords)
            for ind in population
        ]
        best_index = fitness_scores.index(min(fitness_scores))
        
        return population[best_index]
    
    def _create_initial_population(self, size: int) -> List[List[int]]:
        """Cria população inicial"""
        population = []
        base_route = list(range(size))
        
        for _ in range(self.config.population_size):
            route = base_route.copy()
            random.shuffle(route)
            population.append(route)
        
        return population
    
    def _calculate_fitness(self, route: List[int], 
                          points: List[Tuple[float, float]],
                          base: Tuple[float, float]) -> float:
        """
        Calcula fitness (menor = melhor).
        Fitness = distância total da rota
        """
        total_distance = 0.0
        
        # Base → primeiro ponto
        total_distance += self._haversine(base, points[route[0]])
        
        # Pontos intermediários
        for i in range(len(route) - 1):
            p1 = points[route[i]]
            p2 = points[route[i + 1]]
            total_distance += self._haversine(p1, p2)
        
        # Último ponto → base
        total_distance += self._haversine(points[route[-1]], base)
        
        return total_distance
    
    def _tournament_selection(self, population: List[List[int]], 
                             fitness_scores: List[float]) -> List[int]:
        """Seleção por torneio"""
        tournament_indices = random.sample(range(len(population)), 
                                         self.config.tournament_size)
        tournament_fitness = [fitness_scores[i] for i in tournament_indices]
        winner_index = tournament_indices[tournament_fitness.index(min(tournament_fitness))]
        
        return population[winner_index]
    
    def _crossover(self, parent1: List[int], parent2: List[int]) -> List[int]:
        """
        Crossover ordenado (Order Crossover - OX)
        Preserva ordem relativa dos genes
        """
        size = len(parent1)
        start, end = sorted(random.sample(range(size), 2))
        
        # Copia segmento do parent1
        child = [-1] * size
        child[start:end] = parent1[start:end]
        
        # Preenche resto com genes do parent2 na ordem
        p2_genes = [gene for gene in parent2 if gene not in child]
        
        j = 0
        for i in range(size):
            if child[i] == -1:
                child[i] = p2_genes[j]
                j += 1
        
        return child
    
    def _mutate(self, route: List[int]) -> List[int]:
        """
        Mutação por swap (troca 2 posições aleatórias)
        """
        mutated = route.copy()
        i, j = random.sample(range(len(route)), 2)
        mutated[i], mutated[j] = mutated[j], mutated[i]
        
        return mutated
    
    def _brute_force_optimize(self, points: List[Tuple[float, float]], 
                             base: Tuple[float, float]) -> List[int]:
        """Força bruta para poucos pontos"""
        from itertools import permutations
        
        indices = list(range(len(points)))
        best_route = indices
        best_distance = float('inf')
        
        for perm in permutations(indices):
            distance = self._calculate_fitness(list(perm), points, base)
            if distance < best_distance:
                best_distance = distance
                best_route = list(perm)
        
        return best_route
    
    @staticmethod
    def _haversine(coord1: Tuple[float, float], 
                  coord2: Tuple[float, float]) -> float:
        """Distância haversine em km"""
        R = 6371
        lat1, lng1 = map(math.radians, coord1)
        lat2, lng2 = map(math.radians, coord2)
        
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c


# Singleton
genetic_optimizer = GeneticRouteOptimizer()
