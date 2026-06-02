# -*- coding: utf-8 -*-
"""
🚀 TSP OPTIMIZER COM GOOGLE OR-TOOLS
Otimização industrial de rotas para 200+ entregas por dia
Resolve problema do caixeiro viajante com algoritmos de nível mundial
"""
import logging
from typing import List, Tuple, Optional
import numpy as np

try:
    from ortools.constraint_solver import routing_enums_pb2
    from ortools.constraint_solver import pywrapcp
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False
    logging.warning("⚠️ OR-Tools não instalado. TSP otimizado não disponível.")

logger = logging.getLogger(__name__)


class TSPOptimizer:
    """
    Otimizador de rotas usando Google OR-Tools
    Resolve TSP (Traveling Salesman Problem) para minimizar distância total
    """
    
    def __init__(self, time_limit_seconds: int = 30):
        """
        Args:
            time_limit_seconds: Tempo máximo para buscar solução (30s = ótimo para 200 pontos)
        """
        self.time_limit = time_limit_seconds
        
        if not ORTOOLS_AVAILABLE:
            raise RuntimeError("OR-Tools não está instalado. Execute: pip install ortools")
    
    def optimize_route(
        self,
        distance_matrix: np.ndarray,
        start_index: int = 0,
        end_index: Optional[int] = None
    ) -> Tuple[List[int], float]:
        """
        Otimiza rota usando OR-Tools TSP solver
        
        Args:
            distance_matrix: Matriz NxN de distâncias (km ou minutos)
            start_index: Índice do ponto inicial (base)
            end_index: Índice do ponto final (base ou None para retornar ao início)
        
        Returns:
            (order, total_distance): Ordem otimizada dos pontos e distância total
        """
        n = len(distance_matrix)
        
        if n < 2:
            logger.warning("TSP: Menos de 2 pontos, retornando ordem original")
            return list(range(n)), 0.0
        
        if n > 500:
            logger.warning(f"⚠️ TSP: {n} pontos é MUITO! Recomendo dividir em rotas menores.")
        
        try:
            # Converter para inteiros (OR-Tools trabalha com inteiros)
            # Multiplicar por 1000 para preservar precisão (km → metros)
            int_matrix = (distance_matrix * 1000).astype(np.int64)
            
            # Criar modelo de roteamento
            manager = pywrapcp.RoutingIndexManager(
                n,  # número de locais
                1,  # número de veículos (1 entregador)
                start_index  # depot (base)
            )
            routing = pywrapcp.RoutingModel(manager)
            
            # Callback de distância
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return int(int_matrix[from_node][to_node])
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            
            # Se end_index especificado, força retorno à base
            if end_index is not None:
                routing.AddDisjunction([manager.NodeToIndex(end_index)], 0)
            
            # Parâmetros de busca
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            )
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )
            search_parameters.time_limit.seconds = self.time_limit
            search_parameters.log_search = False
            
            logger.info(f"🧠 OR-Tools TSP: Otimizando {n} pontos (limite: {self.time_limit}s)...")
            
            # Resolver
            solution = routing.SolveWithParameters(search_parameters)
            
            if not solution:
                logger.error("❌ OR-Tools não encontrou solução! Usando fallback.")
                return list(range(n)), float('inf')
            
            # Extrair ordem otimizada
            route_order = []
            total_distance = 0
            index = routing.Start(0)
            
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                route_order.append(node)
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                total_distance += routing.GetArcCostForVehicle(previous_index, index, 0)
            
            # Adicionar último ponto
            route_order.append(manager.IndexToNode(index))
            
            # Converter distância de volta para km
            total_distance_km = total_distance / 1000.0
            
            logger.info(f"✅ OR-Tools TSP: Solução encontrada! Distância: {total_distance_km:.2f}km")
            logger.info(f"   Ordem: {route_order[:10]}... (primeiros 10 pontos)")
            
            return route_order, total_distance_km
            
        except Exception as e:
            logger.error(f"❌ Erro no OR-Tools TSP: {e}")
            logger.exception(e)
            return list(range(n)), float('inf')
    
    def optimize_with_time_windows(
        self,
        distance_matrix: np.ndarray,
        time_windows: List[Tuple[int, int]],
        start_index: int = 0
    ) -> Tuple[List[int], float]:
        """
        TSP com janelas de tempo (para entregas agendadas)
        
        Args:
            distance_matrix: Matriz de distâncias
            time_windows: Lista de (início, fim) em minutos para cada ponto
            start_index: Ponto inicial
        
        Returns:
            (order, total_distance)
        """
        n = len(distance_matrix)
        
        if len(time_windows) != n:
            logger.error("Janelas de tempo não correspondem ao número de pontos")
            return self.optimize_route(distance_matrix, start_index)
        
        try:
            int_matrix = (distance_matrix * 1000).astype(np.int64)
            
            manager = pywrapcp.RoutingIndexManager(n, 1, start_index)
            routing = pywrapcp.RoutingModel(manager)
            
            # Callback de distância
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return int(int_matrix[from_node][to_node])
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            
            # Adicionar dimensão de tempo
            time = 'Time'
            routing.AddDimension(
                transit_callback_index,
                30,  # slack de 30 min
                180,  # capacidade máxima de 3h
                False,  # não começa em zero
                time
            )
            time_dimension = routing.GetDimensionOrDie(time)
            
            # Adicionar janelas de tempo
            for location_idx, (start, end) in enumerate(time_windows):
                index = manager.NodeToIndex(location_idx)
                time_dimension.CumulVar(index).SetRange(start, end)
            
            # Parâmetros
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            )
            search_parameters.time_limit.seconds = self.time_limit
            
            logger.info(f"🧠 OR-Tools TSP com janelas de tempo: {n} pontos...")
            
            solution = routing.SolveWithParameters(search_parameters)
            
            if not solution:
                logger.warning("⚠️ Sem solução com janelas de tempo. Ignorando restrições.")
                return self.optimize_route(distance_matrix, start_index)
            
            # Extrair rota
            route_order = []
            total_distance = 0
            index = routing.Start(0)
            
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                route_order.append(node)
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                total_distance += routing.GetArcCostForVehicle(previous_index, index, 0)
            
            route_order.append(manager.IndexToNode(index))
            total_distance_km = total_distance / 1000.0
            
            logger.info(f"✅ TSP com time windows: {total_distance_km:.2f}km")
            return route_order, total_distance_km
            
        except Exception as e:
            logger.error(f"❌ Erro TSP com time windows: {e}")
            return self.optimize_route(distance_matrix, start_index)


def is_ortools_available() -> bool:
    """Verifica se OR-Tools está disponível"""
    return ORTOOLS_AVAILABLE
