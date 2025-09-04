import json
from pathlib import Path
import httpx
import os
from typing import Dict, Tuple, Optional
from bot.config import logger

class Geocoder:
    cache: Dict[str, Tuple[float, float]] = {}
    cache_path = Path('geocode_cache.json')

    @classmethod
    def load_cache(cls):
        if cls.cache_path.exists():
            try:
                cls.cache.update(json.loads(cls.cache_path.read_text(encoding='utf-8')))
            except Exception:
                pass

    @classmethod
    def save_cache(cls):
        try:
            cls.cache_path.write_text(json.dumps(cls.cache, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass

    @classmethod
    async def geocode(cls, address: str) -> Optional[Tuple[float, float]]:
        key = address.lower()
        if key in cls.cache:
            return cls.cache[key]
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get('https://maps.googleapis.com/maps/api/geocode/json', params={'address': address, 'language': 'pt-BR', 'key': api_key})
                data = r.json()
                if data.get('status') == 'OK' and data.get('results'):
                    loc = data['results'][0]['geometry']['location']
                    latlng = (loc['lat'], loc['lng'])
                    cls.cache[key] = latlng
                    return latlng
        except Exception as e:
            logger.warning(f'Geocode falhou para {address}: {e}')
        return None
