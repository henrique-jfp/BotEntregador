from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict
from bot.config import Config

class BotStates(Enum):
    WAITING_PHOTOS = 1
    PROCESSING = 2
    CONFIRMING_ROUTE = 3
    NAVIGATING = 4
    REVIEWING_ADDRESSES = 5
    EDITING_ADDRESS = 6
    ADDING_ADDRESS = 7
    GAINS_MENU = 20
    GAINS_DATE = 21
    GAINS_APP = 22
    GAINS_VALUE = 23

@dataclass
class DeliveryAddress:
    original_text: str
    cleaned_address: str
    confidence: float = 0.7
    lat: Optional[float] = None
    lng: Optional[float] = None

@dataclass
class UserSession:
    user_id: int
    photos: List[str]
    raw_text: str = ""
    addresses: List[DeliveryAddress] = None
    optimized_route: List[str] = None
    current_delivery_index: int = 0
    start_time: datetime = None
    completed_deliveries: List[str] = None
    state: BotStates = BotStates.WAITING_PHOTOS
    processed: bool = False
    pending_edit_index: Optional[int] = None
    config: Dict[str, float] = None
    gains_temp: Dict[str, str] = None

    def ensure_config(self):
        if self.config is None:
            self.config = {
                'valor_entrega': 0.0,
                'custo_km': 0.0,
                'service_time_min': Config.SERVICE_TIME_PER_STOP_MIN
            }

    def __post_init__(self):
        if self.photos is None:
            self.photos = []
        if self.addresses is None:
            self.addresses = []
        if self.optimized_route is None:
            self.optimized_route = []
        if self.completed_deliveries is None:
            self.completed_deliveries = []
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.gains_temp is None:
            self.gains_temp = {}
        self.ensure_config()
