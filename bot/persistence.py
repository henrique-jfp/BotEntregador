import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from bot.models.core import UserSession, DeliveryAddress, BotStates
from bot.config import logger

class DataPersistence:
    DATA_DIR = Path("user_data")

    @classmethod
    def ensure(cls):
        cls.DATA_DIR.mkdir(exist_ok=True)

    @classmethod
    def path(cls, user_id: int) -> Path:
        return cls.DATA_DIR / f"user_{user_id}.json"

    @classmethod
    async def save(cls, session: UserSession):
        try:
            cls.ensure()
            data = session.__dict__.copy()
            data['state'] = session.state.name
            data['start_time'] = session.start_time.isoformat()
            with open(cls.path(session.user_id), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Falha ao salvar sessão {session.user_id}: {e}")

    @classmethod
    async def load(cls, user_id: int) -> Optional[UserSession]:
        try:
            p = cls.path(user_id)
            if not p.exists():
                return None
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
            start_time = datetime.now()
            if data.get('start_time'):
                try:
                    start_time = datetime.fromisoformat(data['start_time'])
                except Exception:
                    pass
            session = UserSession(
                user_id=user_id,
                photos=data.get('photos', []),
                raw_text=data.get('raw_text', ''),
                addresses=[DeliveryAddress(**a) for a in data.get('addresses', [])],
                optimized_route=data.get('optimized_route', []),
                current_delivery_index=data.get('current_delivery_index', 0),
                start_time=start_time,
                completed_deliveries=data.get('completed_deliveries', []),
                state=BotStates[data.get('state', 'WAITING_PHOTOS')],
                processed=data.get('processed', False),
                pending_edit_index=data.get('pending_edit_index'),
                config=data.get('config'),
                gains_temp=data.get('gains_temp'),
                apps=data.get('apps')  # garante persistência customizada de apps
            )
            return session
        except Exception as e:
            logger.warning(f"Falha ao carregar sessão {user_id}: {e}")
            return None
