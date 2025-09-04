from datetime import datetime, timedelta
from bot.config import Config
from PIL import Image
from io import BytesIO

class SecurityValidator:
    @staticmethod
    async def validate_image(image_bytes: bytes) -> bool:
        if len(image_bytes) > Config.MAX_IMAGE_SIZE_MB * 1024 * 1024:
            return False
        try:
            with Image.open(BytesIO(image_bytes)) as im:
                im.verify()
            return True
        except Exception:
            return False

    @staticmethod
    async def rate_limit(user_id: int) -> bool:
        now = datetime.now()
        one_hour = now - timedelta(hours=1)
        lst = Config.user_requests.setdefault(user_id, [])
        lst[:] = [t for t in lst if t > one_hour]
        if len(lst) >= Config.RATE_LIMIT_PER_HOUR:
            return False
        lst.append(now)
        return True
