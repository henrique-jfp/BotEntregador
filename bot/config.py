import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / 'bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("bot_delivery")

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    MAX_PHOTOS_PER_REQUEST = int(os.getenv('MAX_PHOTOS_PER_REQUEST', '8'))
    MAX_ADDRESSES_PER_ROUTE = int(os.getenv('MAX_ADDRESSES_PER_ROUTE', '20'))
    MAX_IMAGE_SIZE_MB = 20
    RATE_LIMIT_PER_HOUR = 50
    SERVICE_TIME_PER_STOP_MIN = float(os.getenv('SERVICE_TIME_PER_STOP_MIN', '1'))
    AVERAGE_SPEED_KMH = float(os.getenv('AVERAGE_SPEED_KMH', '25'))
    user_requests = {}

if not Config.TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN não configurado")
