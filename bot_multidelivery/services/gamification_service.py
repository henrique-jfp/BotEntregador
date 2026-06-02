"""
🎮 GAMIFICAÇÃO - Ranking, Badges, Streaks
Engajamento dos entregadores através de mecânicas de jogo
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class BadgeType(Enum):
    """Tipos de badges"""
    FIRST_DELIVERY = "🎯 Primeira Entrega"
    SPEED_DEMON = "⚡ Demônio da Velocidade"
    PERFECT_DAY = "💯 Dia Perfeito"
    IRON_MAN = "🦾 Homem de Ferro"  # 7 dias seguidos
    LEGEND = "👑 Lendário"  # 100 entregas
    EFFICIENCY_MASTER = "🎓 Mestre da Eficiência"
    EARLY_BIRD = "🌅 Madrugador"
    NIGHT_OWL = "🦉 Coruja"


@dataclass
class Badge:
    """Badge conquistado"""
    type: BadgeType
    earned_at: datetime
    description: str


@dataclass
class LeaderboardEntry:
    """Entrada do ranking"""
    deliverer_id: int
    name: str
    score: int
    badges: List[Badge]
    streak_days: int
    rank: int


class GamificationService:
    """Sistema de gamificação"""
    
    def __init__(self, data_store):
        self.data_store = data_store
    
    def calculate_score(self, deliverer_id: int) -> int:
        """
        Calcula pontuação total do entregador.
        
        Pontos:
        - 10 pontos por entrega bem-sucedida
        - 50 pontos por dia perfeito (100% sucesso)
        - 20 pontos por entrega rápida (< tempo médio)
        - 100 pontos por streak de 7 dias
        """
        from .deliverer_service import deliverer_service
        
        deliverer = deliverer_service.get_deliverer(deliverer_id)
        if not deliverer:
            return 0
        
        score = 0
        
        # Pontos base
        score += deliverer.total_deliveries * 10
        
        # Bônus de taxa de sucesso
        if deliverer.success_rate >= 100:
            score += 200
        elif deliverer.success_rate >= 95:
            score += 100
        elif deliverer.success_rate >= 90:
            score += 50
        
        # Bônus de velocidade
        if deliverer.average_delivery_time < 15:  # < 15 min
            score += deliverer.total_deliveries * 5
        
        # Bônus de streaks
        streak = self._calculate_streak(deliverer_id)
        score += (streak // 7) * 100  # 100 pts a cada 7 dias
        
        return score
    
    def check_badges(self, deliverer_id: int) -> List[Badge]:
        """Verifica e retorna badges conquistados"""
        from .deliverer_service import deliverer_service
        
        deliverer = deliverer_service.get_deliverer(deliverer_id)
        if not deliverer:
            return []
        
        badges = []
        now = datetime.now()
        
        # 🎯 Primeira Entrega
        if deliverer.total_deliveries >= 1:
            badges.append(Badge(
                type=BadgeType.FIRST_DELIVERY,
                earned_at=deliverer.joined_date,
                description="Completou sua primeira entrega!"
            ))
        
        # ⚡ Demônio da Velocidade
        if deliverer.average_delivery_time < 10:
            badges.append(Badge(
                type=BadgeType.SPEED_DEMON,
                earned_at=now,
                description="Média < 10min por entrega"
            ))
        
        # 💯 Dia Perfeito
        if deliverer.success_rate == 100 and deliverer.total_deliveries >= 10:
            badges.append(Badge(
                type=BadgeType.PERFECT_DAY,
                earned_at=now,
                description="100% de taxa de sucesso!"
            ))
        
        # 🦾 Homem de Ferro
        streak = self._calculate_streak(deliverer_id)
        if streak >= 7:
            badges.append(Badge(
                type=BadgeType.IRON_MAN,
                earned_at=now,
                description=f"Streak de {streak} dias!"
            ))
        
        # 👑 Lendário
        if deliverer.total_deliveries >= 100:
            badges.append(Badge(
                type=BadgeType.LEGEND,
                earned_at=now,
                description="100+ entregas completadas!"
            ))
        
        # 🎓 Mestre da Eficiência
        if deliverer.success_rate >= 95 and deliverer.total_deliveries >= 50:
            badges.append(Badge(
                type=BadgeType.EFFICIENCY_MASTER,
                earned_at=now,
                description="95%+ sucesso com 50+ entregas"
            ))
        
        return badges
    
    def get_leaderboard(self, limit: int = 10) -> List[LeaderboardEntry]:
        """Retorna ranking dos top entregadores"""
        from .deliverer_service import deliverer_service
        
        deliverers = deliverer_service.get_active_deliverers()
        
        # Calcula scores
        entries = []
        for d in deliverers:
            score = self.calculate_score(d.telegram_id)
            badges = self.check_badges(d.telegram_id)
            streak = self._calculate_streak(d.telegram_id)
            
            entries.append(LeaderboardEntry(
                deliverer_id=d.telegram_id,
                name=d.name,
                score=score,
                badges=badges,
                streak_days=streak,
                rank=0  # Será preenchido depois
            ))
        
        # Ordena por score
        entries.sort(key=lambda e: e.score, reverse=True)
        
        # Define ranks
        for i, entry in enumerate(entries[:limit], start=1):
            entry.rank = i
        
        return entries[:limit]
    
    def get_deliverer_stats(self, deliverer_id: int) -> Dict:
        """Estatísticas detalhadas do entregador"""
        from .deliverer_service import deliverer_service
        
        deliverer = deliverer_service.get_deliverer(deliverer_id)
        if not deliverer:
            return {}
        
        score = self.calculate_score(deliverer_id)
        badges = self.check_badges(deliverer_id)
        streak = self._calculate_streak(deliverer_id)
        
        # Posição no ranking
        leaderboard = self.get_leaderboard(limit=100)
        rank = next((i for i, e in enumerate(leaderboard, 1) 
                    if e.deliverer_id == deliverer_id), None)
        
        return {
            'score': score,
            'badges': badges,
            'streak_days': streak,
            'rank': rank,
            'total_deliveries': deliverer.total_deliveries,
            'success_rate': deliverer.success_rate,
            'average_time': deliverer.average_delivery_time
        }
    
    def _calculate_streak(self, deliverer_id: int) -> int:
        """Calcula dias consecutivos de entregas"""
        packages = self.data_store.get_all_packages()
        
        # Filtra pacotes do entregador
        deliverer_packages = [
            p for p in packages 
            if p.get('assigned_to') == deliverer_id and p.get('status') == 'delivered'
        ]
        
        if not deliverer_packages:
            return 0
        
        # Ordena por data de entrega
        sorted_packages = sorted(
            deliverer_packages,
            key=lambda p: datetime.fromisoformat(p.get('delivered_at', '2000-01-01')),
            reverse=True
        )
        
        # Conta dias consecutivos
        streak = 0
        current_date = datetime.now().date()
        
        for pkg in sorted_packages:
            delivered_date = datetime.fromisoformat(pkg['delivered_at']).date()
            
            if delivered_date == current_date:
                streak += 1
                current_date -= timedelta(days=1)
            elif delivered_date < current_date:
                break
        
        return streak


# Singleton
from .deliverer_service import deliverer_service
from ..persistence import data_store
gamification_service = GamificationService(data_store)
