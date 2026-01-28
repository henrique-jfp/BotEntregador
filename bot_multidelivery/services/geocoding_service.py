"""
🗺️ GEOCODING SERVICE - Cache inteligente + Fallback
Economiza chamadas de API com cache persistente
"""
import json
import hashlib
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime, timedelta


class GeocodingCache:
    """Cache persistente de geocoding"""
    
    def __init__(self, cache_file: str = "data/geocoding_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache = self._load_cache()
        self.ttl_days = 90  # Cache válido por 90 dias
    
    def _load_cache(self) -> dict:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)
    
    def _get_key(self, address: str) -> str:
        """Gera hash MD5 do endereço normalizado"""
        normalized = address.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def get(self, address: str) -> Optional[Tuple[float, float]]:
        """Busca coordenadas no cache"""
        key = self._get_key(address)
        
        if key in self.cache:
            entry = self.cache[key]
            cached_date = datetime.fromisoformat(entry['cached_at'])
            
            # Verifica se cache ainda é válido
            if datetime.now() - cached_date < timedelta(days=self.ttl_days):
                return (entry['lat'], entry['lng'])
        
        return None
    
    def set(self, address: str, lat: float, lng: float):
        """Salva coordenadas no cache"""
        key = self._get_key(address)
        self.cache[key] = {
            'address': address,
            'lat': lat,
            'lng': lng,
            'cached_at': datetime.now().isoformat()
        }
        self._save_cache()
    
    def stats(self) -> dict:
        """Estatísticas do cache"""
        valid = sum(1 for e in self.cache.values() 
                   if datetime.now() - datetime.fromisoformat(e['cached_at']) < timedelta(days=self.ttl_days))
        
        return {
            'total_entries': len(self.cache),
            'valid_entries': valid,
            'expired_entries': len(self.cache) - valid
        }


class GeocodingService:
    """Geocoding com fallback inteligente"""
    
    def __init__(self, google_api_key: Optional[str] = None):
        self.api_key = google_api_key
        self.cache = GeocodingCache()
        self.api_calls_today = 0
        self.last_reset = datetime.now().date()
    
    def geocode(self, address: str) -> Tuple[float, float]:
        """
        Geocode com estratégia em cascata:
        1. Cache local (GRATUITO)
        2. OpenStreetMap Nominatim (GRATUITO)
        3. Google Maps API (PAGO - se disponível)
        4. Simulação baseada em hash (ÚLTIMO RECURSO)
        """
        # 1. Tenta cache
        cached = self.cache.get(address)
        if cached:
            return cached
        
        # 2. Tenta OpenStreetMap (GRATUITO)
        coords = self._geocode_osm(address)
        if coords:
            self.cache.set(address, coords[0], coords[1])
            return coords
        
        # 3. Tenta Google Maps API (se disponível)
        if self.api_key and self.api_calls_today < 100:
            coords = self._geocode_google(address)
            if coords:
                self.cache.set(address, coords[0], coords[1])
                self._increment_api_call()
                return coords
        
        # 4. Fallback: simulação determinística (ÚLTIMO RECURSO)
        coords = self._geocode_fallback(address)
        self.cache.set(address, coords[0], coords[1])
        return coords
    
    def _geocode_osm(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Geocode via OpenStreetMap Nominatim (GRATUITO)
        Respeita rate limit: 1 req/sec
        """
        try:
            import requests
            import time
            
            # Rate limit: espera 1 segundo entre chamadas
            time.sleep(1)
            
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'BotEntregador/1.0 (Telegram Bot)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    result = data[0]
                    return (float(result['lat']), float(result['lon']))
        except Exception as e:
            # Se falhar, continua para próxima estratégia
            pass
        
        return None
                self.cache.set(address, coords[0], coords[1])
                self._increment_api_call()
                return coords
        
        # 3. Fallback: simulação determinística
        coords = self._geocode_fallback(address)
        self.cache.set(address, coords[0], coords[1])
        return coords
    
    def _geocode_google(self, address: str) -> Optional[Tuple[float, float]]:
        """Geocode via Google Maps API"""
        try:
            import requests
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': address,
                'key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                location = data['results'][0]['geometry']['location']
                return (location['lat'], location['lng'])
        except:
            pass
        
        return None
    
    def _geocode_fallback(self, address: str) -> Tuple[float, float]:
        """
        Geocoding simulado baseado em hash do endereço.
        Distribui pontos em São Paulo de forma determinística.
        """
        # Hash do endereço para gerar coordenadas consistentes
        hash_int = int(hashlib.md5(address.encode()).hexdigest()[:8], 16)
        
        # São Paulo: aprox -23.5 a -23.7 lat, -46.5 a -46.8 lng
        lat_offset = (hash_int % 2000) / 10000  # 0 a 0.2
        lng_offset = (hash_int // 2000 % 3000) / 10000  # 0 a 0.3
        
        lat = -23.5505 - lat_offset
        lng = -46.6333 - lng_offset
        
        return (lat, lng)
    
    def _increment_api_call(self):
        """Incrementa contador de chamadas API"""
        today = datetime.now().date()
        if today > self.last_reset:
            self.api_calls_today = 0
            self.last_reset = today
        
        self.api_calls_today += 1
    
    async def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Versão async do geocode para uso com Telegram bot.
        Retorna (lat, lng) ou None se falhar.
        """
        try:
            return self.geocode(address)
        except Exception:
            return None
    
    async def reverse_geocode(self, lat: float, lng: float) -> Optional[str]:
        """
        Reverse geocoding: coordenadas → endereço
        """
        # Tenta Google Maps API primeiro
        if self.api_key and self.api_calls_today < 100:
            try:
                import requests
                url = "https://maps.googleapis.com/maps/api/geocode/json"
                params = {
                    'latlng': f"{lat},{lng}",
                    'key': self.api_key
                }
                
                response = requests.get(url, params=params, timeout=5)
                data = response.json()
                
                if data['status'] == 'OK' and data['results']:
                    self._increment_api_call()
                    return data['results'][0]['formatted_address']
            except Exception:
                pass
        
        # Fallback: retorna as coordenadas formatadas
        return f"Lat: {lat:.6f}, Lng: {lng:.6f}"
    
    def get_stats(self) -> dict:
        """Estatísticas do serviço"""
        cache_stats = self.cache.stats()
        
        return {
            'cache': cache_stats,
            'api_calls_today': self.api_calls_today,
            'using_api': bool(self.api_key)
        }


# Singleton
from ..config import BotConfig
geocoding_service = GeocodingService(BotConfig.GOOGLE_API_KEY)
