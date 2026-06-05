# -*- coding: utf-8 -*-
"""
🧠 CÉREBRO GEOGRÁFICO
Sistema de auto-aprendizado que analisa padrões de entregas e otimiza rotas futuras

Funcionalidades:
- Aprende taxa de sucesso por bairro
- Identifica melhor entregador por região
- Detecta horários problemáticos
- Sugere divisão inteligente de rotas
- Prevê tempo de entrega por área
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict
from dataclasses import dataclass
from bot_multidelivery.database import db_manager
from sqlalchemy import text

logger = logging.getLogger(__name__)


@dataclass
class NeighborhoodIntelligence:
    """Inteligência acumulada sobre um bairro"""
    name: str
    total_deliveries: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_delivery_time: float  # minutos
    best_deliverer: str
    best_deliverer_rate: float
    common_failure_reasons: List[str]
    peak_hours: List[int]  # Horas com mais entregas (0-23)
    difficulty_score: float  # 0-10, quanto maior, mais difícil


class GeographicBrain:
    """Cérebro Geográfico - Sistema de Inteligência de Entregas"""
    
    def __init__(self):
        self.intelligence_cache: Dict[str, NeighborhoodIntelligence] = {}
        self.last_update = None
    
    def get_neighborhood_from_coords(self, lat: float, lng: float) -> str:
        """
        Identifica bairro baseado em coordenadas
        TODO: Integrar com GeoJSON para precisão real
        """
        # Heurística para Zona Sul do Rio (expandir futuramente)
        if -22.98 <= lat <= -22.96 and -43.19 <= lng <= -43.17:
            return "Copacabana"
        elif -23.00 <= lat <= -22.98 and -43.21 <= lng <= -43.19:
            return "Ipanema"
        elif -23.01 <= lat <= -22.98 and -43.23 <= lng <= -43.21:
            return "Leblon"
        elif -22.95 <= lat <= -22.93 and -43.19 <= lng <= -43.17:
            return "Botafogo"
        elif -22.93 <= lat <= -22.91 and -43.21 <= lng <= -43.19:
            return "Lagoa"
        elif -23.03 <= lat <= -23.01 and -43.25 <= lng <= -43.23:
            return "São Conrado"
        else:
            return "Zona Sul"
    
    def learn_from_session(self, session_id: str):
        """
        Aprende com uma sessão finalizada
        Extrai padrões e atualiza inteligência de bairros
        """
        try:
            if not db_manager.is_connected:
                logger.warning("⚠️ Banco não conectado, pulando aprendizado")
                return
            
            logger.info(f"🧠 Aprendendo com sessão {session_id}...")
            
            # Buscar todos os pacotes dessa sessão
            query = text("""
                SELECT 
                    p.lat, p.lng, p.status, p.delivered_at, p.created_at,
                    p.failure_reason, p.assigned_to_telegram_id,
                    d.name as deliverer_name
                FROM packages p
                LEFT JOIN deliverers d ON p.assigned_to_telegram_id = d.telegram_id
                WHERE p.session_id = :session_id
                  AND p.lat IS NOT NULL AND p.lng IS NOT NULL
            """)
            
            with db_manager.get_session() as db_session:
                packages = db_session.execute(query, {"session_id": session_id}).fetchall()
            
            if not packages:
                logger.info(f"🤷 Nenhum pacote encontrado para sessão {session_id}")
                return
            
            # Agrupar por bairro
            neighborhood_data = defaultdict(lambda: {
                'total': 0,
                'success': 0,
                'failure': 0,
                'deliverers': defaultdict(lambda: {'total': 0, 'success': 0}),
                'delivery_times': [],
                'failure_reasons': defaultdict(int),
                'hours': defaultdict(int)
            })
            
            for pkg in packages:
                lat, lng, status, delivered_at, created_at, failure_reason, tg_id, deliverer_name = pkg
                
                neighborhood = self.get_neighborhood_from_coords(lat, lng)
                data = neighborhood_data[neighborhood]
                
                data['total'] += 1
                
                if status == 'delivered':
                    data['success'] += 1
                    
                    # Calcular tempo de entrega
                    if delivered_at and created_at:
                        delta = delivered_at - created_at
                        data['delivery_times'].append(delta.total_seconds() / 60)
                    
                    # Registrar entregador bem-sucedido
                    if deliverer_name:
                        data['deliverers'][deliverer_name]['total'] += 1
                        data['deliverers'][deliverer_name]['success'] += 1
                else:
                    data['failure'] += 1
                    
                    # Registrar motivo de falha
                    reason_key = failure_reason or "Não especificado"
                    data['failure_reasons'][reason_key] += 1
                    
                    # Registrar entregador com falha
                    if deliverer_name:
                        data['deliverers'][deliverer_name]['total'] += 1
                
                # Registrar hora de entrega/tentativa
                if delivered_at:
                    hour = delivered_at.hour
                    data['hours'][hour] += 1
            
            # Processar e salvar inteligência
            for neighborhood, data in neighborhood_data.items():
                success_rate = (data['success'] / data['total'] * 100) if data['total'] > 0 else 0
                avg_time = sum(data['delivery_times']) / len(data['delivery_times']) if data['delivery_times'] else 0
                
                # Identificar melhor entregador
                best_deliverer = "N/A"
                best_rate = 0
                for name, stats in data['deliverers'].items():
                    rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
                    if rate > best_rate:
                        best_rate = rate
                        best_deliverer = name
                
                # Top 3 motivos de falha
                top_failures = sorted(
                    data['failure_reasons'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3]
                common_failures = [reason for reason, _ in top_failures]
                
                # Identificar horários de pico
                peak_hours = sorted(
                    data['hours'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3]
                peak_hours_list = [hour for hour, _ in peak_hours]
                
                # Calcular score de dificuldade (0-10)
                # Fatores: taxa de falha, tempo médio, variação de entregadores
                difficulty = (
                    (100 - success_rate) / 10 +  # Taxa de falha
                    min(avg_time / 30, 5) +       # Tempo (cap 5 pontos)
                    min(len(data['deliverers']) / 2, 2)  # Muitos entregadores = complexo
                )
                
                # Criar/atualizar inteligência
                intelligence = NeighborhoodIntelligence(
                    name=neighborhood,
                    total_deliveries=data['total'],
                    success_count=data['success'],
                    failure_count=data['failure'],
                    success_rate=round(success_rate, 1),
                    avg_delivery_time=round(avg_time, 1),
                    best_deliverer=best_deliverer,
                    best_deliverer_rate=round(best_rate, 1),
                    common_failure_reasons=common_failures,
                    peak_hours=peak_hours_list,
                    difficulty_score=round(difficulty, 1)
                )
                
                self.intelligence_cache[neighborhood] = intelligence
                
                # Salvar no banco (tabela neighborhood_stats)
                self._save_to_database(intelligence)
                
                logger.info(f"✅ {neighborhood}: {data['total']} entregas, {success_rate:.1f}% sucesso, melhor: {best_deliverer}")
            
            self.last_update = datetime.now()
            logger.info(f"🎓 Aprendizado concluído! {len(neighborhood_data)} bairros analisados")
        
        except Exception as e:
            logger.error(f"❌ Erro ao aprender com sessão: {e}")
    
    def _save_to_database(self, intel: NeighborhoodIntelligence):
        """Salva inteligência no PostgreSQL"""
        try:
            if not db_manager.is_connected:
                return
            
            query = text("""
                INSERT INTO neighborhood_stats 
                (name, total_deliveries, success_count, failure_count, success_rate,
                 avg_delivery_time, best_deliverer, best_deliverer_rate, 
                 common_failure_reasons, peak_hours, difficulty_score, updated_at)
                VALUES 
                (:name, :total, :success, :failure, :rate, :time, :deliverer, :del_rate,
                 :failures, :hours, :difficulty, :updated)
                ON CONFLICT (name) DO UPDATE SET
                    total_deliveries = neighborhood_stats.total_deliveries + EXCLUDED.total_deliveries,
                    success_count = neighborhood_stats.success_count + EXCLUDED.success_count,
                    failure_count = neighborhood_stats.failure_count + EXCLUDED.failure_count,
                    success_rate = ((neighborhood_stats.success_count + EXCLUDED.success_count) * 100.0 / 
                                   NULLIF(neighborhood_stats.total_deliveries + EXCLUDED.total_deliveries, 0)),
                    avg_delivery_time = ((neighborhood_stats.avg_delivery_time + EXCLUDED.avg_delivery_time) / 2),
                    best_deliverer = EXCLUDED.best_deliverer,
                    best_deliverer_rate = EXCLUDED.best_deliverer_rate,
                    common_failure_reasons = EXCLUDED.common_failure_reasons,
                    peak_hours = EXCLUDED.peak_hours,
                    difficulty_score = EXCLUDED.difficulty_score,
                    updated_at = EXCLUDED.updated_at
            """)
            
            with db_manager.get_session() as session:
                session.execute(query, {
                    "name": intel.name,
                    "total": intel.total_deliveries,
                    "success": intel.success_count,
                    "failure": intel.failure_count,
                    "rate": intel.success_rate,
                    "time": intel.avg_delivery_time,
                    "deliverer": intel.best_deliverer,
                    "del_rate": intel.best_deliverer_rate,
                    "failures": ','.join(intel.common_failure_reasons),
                    "hours": ','.join(map(str, intel.peak_hours)),
                    "difficulty": intel.difficulty_score,
                    "updated": datetime.now()
                })
                session.commit()
        
        except Exception as e:
            logger.error(f"❌ Erro ao salvar stats no banco: {e}")
    
    def suggest_route_division(self, packages: List[Tuple[float, float]], num_deliverers: int) -> Dict:
        """
        Sugere divisão inteligente de rotas baseado em aprendizado
        """
        # TODO: Usar inteligência acumulada para sugerir divisões
        # Por enquanto, retorna sugestão genérica
        return {
            "strategy": "learning_based",
            "confidence": 0.7,
            "suggestions": [
                f"Bairro {name}: Enviar {intel.best_deliverer} (taxa {intel.best_deliverer_rate}%)"
                for name, intel in self.intelligence_cache.items()
                if intel.best_deliverer != "N/A"
            ]
        }


# Instância global
geographic_brain = GeographicBrain()
