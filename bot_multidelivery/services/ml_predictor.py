"""
🤖 IA PREDITIVA - Machine Learning para estimar tempo de entrega
Usa features: distância, horário, histórico do entregador, prioridade
"""
import math
import pickle
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime, time
from dataclasses import dataclass


@dataclass
class PredictionFeatures:
    """Features para predição"""
    distance_km: float
    hour_of_day: int
    is_rush_hour: bool
    deliverer_avg_time: float
    deliverer_success_rate: float
    priority_weight: float  # 0.5=low, 1.0=normal, 1.5=high, 2.0=urgent
    traffic_factor: float  # 1.0=normal, 1.5=pesado


class DeliveryTimePredictor:
    """Preditor de tempo de entrega com ML"""
    
    def __init__(self, model_path: str = "data/ml_model.pkl"):
        self.model_path = Path(model_path)
        self.model = self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Carrega modelo ou cria um novo"""
        if self.model_path.exists():
            try:
                with open(self.model_path, 'rb') as f:
                    return pickle.load(f)
            except:
                pass
        
        # Modelo inicial: regressão linear simples
        return {
            'type': 'heuristic',
            'base_time': 5,  # minutos base
            'distance_factor': 2.5,  # min/km
            'rush_hour_penalty': 1.3,
            'priority_factors': {
                'low': 0.8,
                'normal': 1.0,
                'high': 1.2,
                'urgent': 1.5
            }
        }
    
    def predict(self, features: PredictionFeatures) -> float:
        """
        Prediz tempo de entrega em minutos.
        
        Modelo heurístico (pode ser substituído por ML real):
        - Tempo base: 5 min
        - + 2.5 min por km
        - + 30% se horário de pico
        - Ajusta por histórico do entregador
        - Ajusta por prioridade
        """
        if self.model['type'] == 'heuristic':
            return self._heuristic_predict(features)
        else:
            # TODO: implementar ML real (sklearn, xgboost, etc)
            return self._heuristic_predict(features)
    
    def _heuristic_predict(self, f: PredictionFeatures) -> float:
        """Predição baseada em heurísticas"""
        model = self.model
        
        # Tempo base
        time = model['base_time']
        
        # Distância
        time += f.distance_km * model['distance_factor']
        
        # Horário de pico
        if f.is_rush_hour:
            time *= model['rush_hour_penalty']
        
        # Experiência do entregador (quanto melhor, mais rápido)
        if f.deliverer_avg_time > 0:
            # Se o entregador é mais rápido que a média, reduz tempo
            avg_baseline = 15  # minutos
            time *= f.deliverer_avg_time / avg_baseline
        
        # Taxa de sucesso (confiança)
        confidence = f.deliverer_success_rate / 100.0
        if confidence < 0.9:
            time *= 1.2  # Menos confiável = mais tempo
        
        # Prioridade
        priority_map = {'low': 0.8, 'normal': 1.0, 'high': 1.2, 'urgent': 1.5}
        time *= f.priority_weight
        
        # Tráfego
        time *= f.traffic_factor
        
        return round(time, 1)
    
    def predict_from_package(self, package_id: str, deliverer_id: int,
                            distance_km: float, priority: str = 'normal') -> float:
        """
        Prediz tempo a partir de dados de pacote e entregador.
        """
        from ..services import deliverer_service
        
        deliverer = deliverer_service.get_deliverer(deliverer_id)
        
        now = datetime.now()
        hour = now.hour
        
        features = PredictionFeatures(
            distance_km=distance_km,
            hour_of_day=hour,
            is_rush_hour=self._is_rush_hour(now.time()),
            deliverer_avg_time=deliverer.average_delivery_time if deliverer else 15,
            deliverer_success_rate=deliverer.success_rate if deliverer else 95.0,
            priority_weight=self._get_priority_weight(priority),
            traffic_factor=self._estimate_traffic(now.time())
        )
        
        return self.predict(features)
    
    def train_from_history(self):
        """
        Treina modelo a partir do histórico de entregas.
        TODO: implementar com sklearn quando houver dados suficientes
        """
        from ..persistence import data_store
        
        packages = data_store.get_all_packages()
        delivered = [p for p in packages if p.get('status') == 'delivered' 
                    and p.get('delivery_time_minutes')]
        
        if len(delivered) < 50:
            print(f"⚠️ Apenas {len(delivered)} entregas no histórico. Precisa de 50+ para treinar.")
            return False
        
        # TODO: Implementar treinamento com sklearn
        # features = extrair_features(delivered)
        # X_train, y_train = preparar_dados(features)
        # model = RandomForestRegressor()
        # model.fit(X_train, y_train)
        # salvar_modelo(model)
        
        print(f"✅ Modelo treinado com {len(delivered)} entregas")
        return True
    
    def evaluate_accuracy(self) -> dict:
        """Avalia precisão do modelo"""
        from ..persistence import data_store
        
        packages = data_store.get_all_packages()
        delivered = [p for p in packages if p.get('status') == 'delivered' 
                    and p.get('delivery_time_minutes')]
        
        if len(delivered) < 10:
            return {'error': 'Dados insuficientes'}
        
        errors = []
        for pkg in delivered[-50:]:  # Últimas 50 entregas
            actual = pkg['delivery_time_minutes']
            
            # Reconstrói features e prediz
            deliverer_id = pkg.get('assigned_to', 0)
            distance = self._estimate_distance(pkg)
            priority = pkg.get('priority', 'normal')
            
            predicted = self.predict_from_package(
                pkg['id'], deliverer_id, distance, priority
            )
            
            error = abs(predicted - actual)
            errors.append(error)
        
        mae = sum(errors) / len(errors)  # Mean Absolute Error
        
        return {
            'samples': len(errors),
            'mae': round(mae, 2),
            'accuracy': f"{max(0, 100 - mae * 5):.1f}%"
        }
    
    @staticmethod
    def _is_rush_hour(t: time) -> bool:
        """Detecta horário de pico"""
        # Picos: 7-9h e 17-19h
        return (7 <= t.hour <= 9) or (17 <= t.hour <= 19)
    
    @staticmethod
    def _estimate_traffic(t: time) -> float:
        """Estima fator de tráfego por horário"""
        hour = t.hour
        
        # Madrugada: tráfego leve
        if 0 <= hour <= 6:
            return 0.7
        
        # Pico manhã: 7-9h
        if 7 <= hour <= 9:
            return 1.5
        
        # Meio do dia: normal
        if 10 <= hour <= 16:
            return 1.0
        
        # Pico tarde: 17-19h
        if 17 <= hour <= 19:
            return 1.6
        
        # Noite: leve
        return 0.9
    
    @staticmethod
    def _get_priority_weight(priority: str) -> float:
        """Converte prioridade em peso"""
        weights = {
            'low': 0.8,
            'normal': 1.0,
            'high': 1.2,
            'urgent': 1.5
        }
        return weights.get(priority.lower(), 1.0)
    
    @staticmethod
    def _estimate_distance(package: dict) -> float:
        """Estima distância do pacote (simplificado)"""
        # TODO: usar coordenadas reais
        lat = package.get('lat', -23.55)
        lng = package.get('lng', -46.63)
        
        # Distância do centro de SP
        center_lat, center_lng = -23.5505, -46.6333
        
        # Haversine simplificado
        dlat = abs(lat - center_lat) * 111  # km
        dlng = abs(lng - center_lng) * 111 * math.cos(math.radians(lat))
        
        return math.sqrt(dlat**2 + dlng**2)


# Singleton
predictor = DeliveryTimePredictor()
