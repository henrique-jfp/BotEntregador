"""
🔥 CONFIG MALUCA - Bot Multi-Entregador
Centraliza configs sensíveis e constantes do sistema
"""
import os
from dataclasses import dataclass
from typing import List

@dataclass
class DeliveryPartner:
    """Entregador cadastrado"""
    telegram_id: int
    name: str
    is_partner: bool  # True = sócio (não recebe por pacote)
    
    @property
    def cost_per_package(self) -> float:
        return 0.0 if self.is_partner else 1.0


class BotConfig:
    """Configuração central"""
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
    
    # Admin que controla tudo
    ADMIN_TELEGRAM_ID = int(os.getenv('ADMIN_TELEGRAM_ID', '0'))
    
    # Entregadores cadastrados (LEGADO - usar deliverer_service agora)
    DELIVERY_PARTNERS: List[DeliveryPartner] = []
    
    # Constantes
    MAX_ROMANEIOS_PER_BATCH = 10
    CLUSTER_COUNT = 2  # Divide em 2 territórios
    
    @classmethod
    def get_partner_by_id(cls, telegram_id: int) -> DeliveryPartner | None:
        """LEGADO - Usa deliverer_service internamente"""
        from .services import deliverer_service
        
        deliverer = deliverer_service.get_deliverer(telegram_id)
        if deliverer:
            # Converte Deliverer para DeliveryPartner (compatibilidade)
            return DeliveryPartner(
                telegram_id=deliverer.telegram_id,
                name=deliverer.name,
                is_partner=deliverer.is_partner
            )
        return None
    
    @classmethod
    def get_partner_name(cls, telegram_id: int) -> str:
        partner = cls.get_partner_by_id(telegram_id)
        return partner.name if partner else "Desconhecido"
