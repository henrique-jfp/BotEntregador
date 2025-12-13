"""
🎯 SERVIÇO DE GERENCIAMENTO DE ENTREGADORES
Cadastro, atualização e consulta de entregadores
"""

from typing import List, Optional
from datetime import datetime
from ..models import Deliverer
from ..persistence import data_store


class DelivererService:
    """Serviço para gerenciar entregadores"""
    
    @staticmethod
    def add_deliverer(
        telegram_id: int,
        name: str,
        is_partner: bool = False,
        max_capacity: int = 50
    ) -> Deliverer:
        """
        Adiciona novo entregador ao sistema.
        
        Args:
            telegram_id: ID do Telegram
            name: Nome do entregador
            is_partner: Se é sócio (não recebe por entrega)
            max_capacity: Máximo de pacotes por dia
            
        Returns:
            Deliverer criado
        """
        deliverer = Deliverer(
            telegram_id=telegram_id,
            name=name,
            is_partner=is_partner,
            max_capacity=max_capacity,
            cost_per_package=0.0 if is_partner else 1.0,
            is_active=True,
            joined_date=datetime.now()
        )
        
        data_store.add_deliverer(deliverer)
        return deliverer
    
    @staticmethod
    def get_deliverer(telegram_id: int) -> Optional[Deliverer]:
        """Busca entregador por ID"""
        return data_store.get_deliverer(telegram_id)
    
    @staticmethod
    def get_all_deliverers() -> List[Deliverer]:
        """Retorna todos os entregadores"""
        return data_store.load_deliverers()
    
    @staticmethod
    def get_active_deliverers() -> List[Deliverer]:
        """Retorna apenas entregadores ativos"""
        return [d for d in data_store.load_deliverers() if d.is_active]
    
    @staticmethod
    def update_deliverer(
        telegram_id: int,
        **kwargs
    ) -> bool:
        """
        Atualiza dados do entregador.
        
        Args:
            telegram_id: ID do entregador
            **kwargs: Campos a atualizar
            
        Returns:
            True se atualizou, False se não encontrou
        """
        deliverer = data_store.get_deliverer(telegram_id)
        if not deliverer:
            return False
        
        for key, value in kwargs.items():
            if hasattr(deliverer, key):
                setattr(deliverer, key, value)
        
        data_store.add_deliverer(deliverer)
        return True
    
    @staticmethod
    def deactivate_deliverer(telegram_id: int) -> bool:
        """Desativa entregador (soft delete)"""
        return DelivererService.update_deliverer(telegram_id, is_active=False)
    
    @staticmethod
    def activate_deliverer(telegram_id: int) -> bool:
        """Reativa entregador"""
        return DelivererService.update_deliverer(telegram_id, is_active=True)
    
    @staticmethod
    def update_stats_after_delivery(
        telegram_id: int,
        delivery_success: bool,
        delivery_time_minutes: int
    ):
        """
        Atualiza estatísticas após entrega.
        
        Args:
            telegram_id: ID do entregador
            delivery_success: Se entrega foi bem-sucedida
            delivery_time_minutes: Tempo da entrega em minutos
        """
        deliverer = data_store.get_deliverer(telegram_id)
        if not deliverer:
            return
        
        # Atualiza contadores
        if delivery_success:
            deliverer.total_deliveries += 1
            if not deliverer.is_partner:
                deliverer.total_earnings += deliverer.cost_per_package
        
        # Recalcula taxa de sucesso
        total_attempts = deliverer.total_deliveries + (0 if delivery_success else 1)
        deliverer.success_rate = (deliverer.total_deliveries / total_attempts) * 100
        
        # Atualiza tempo médio (média móvel simples)
        if deliverer.average_delivery_time == 0:
            deliverer.average_delivery_time = delivery_time_minutes
        else:
            deliverer.average_delivery_time = (
                (deliverer.average_delivery_time * (deliverer.total_deliveries - 1) + 
                 delivery_time_minutes) / deliverer.total_deliveries
            )
        
        data_store.add_deliverer(deliverer)
    
    @staticmethod
    def can_assign_packages(telegram_id: int, package_count: int) -> bool:
        """Verifica se entregador pode receber N pacotes"""
        deliverer = data_store.get_deliverer(telegram_id)
        if not deliverer:
            return False
        
        return deliverer.can_accept_packages(package_count)
    
    @staticmethod
    def get_deliverer_summary(telegram_id: int) -> Optional[dict]:
        """Retorna resumo completo do entregador"""
        deliverer = data_store.get_deliverer(telegram_id)
        if not deliverer:
            return None
        
        return {
            'id': deliverer.telegram_id,
            'name': deliverer.name,
            'tipo': 'Sócio' if deliverer.is_partner else 'Colaborador',
            'capacidade': deliverer.max_capacity,
            'custo_pacote': f'R$ {deliverer.cost_per_package:.2f}',
            'status': 'Ativo' if deliverer.is_active else 'Inativo',
            'total_entregas': deliverer.total_deliveries,
            'ganhos_totais': f'R$ {deliverer.total_earnings:.2f}',
            'taxa_sucesso': f'{deliverer.success_rate:.1f}%',
            'tempo_medio': f'{deliverer.average_delivery_time:.1f} min',
            'desde': deliverer.joined_date.strftime('%d/%m/%Y')
        }


# Singleton
deliverer_service = DelivererService()
