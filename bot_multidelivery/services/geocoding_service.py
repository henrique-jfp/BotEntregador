"""
🗺️ GEOCODING SERVICE - Cache inteligente + Fallback
Economiza chamadas de API com cache persistente
"""
import json
import hashlib
import os
import re
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime, timedelta
import math
import logging


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
        # Contexto padrao para enderecos sem cidade/UF
        self.default_city = os.getenv("DEFAULT_CITY", "Rio de Janeiro")
        self.default_state = os.getenv("DEFAULT_STATE", "RJ")
        self.default_country = os.getenv("DEFAULT_COUNTRY", "Brasil")
        self.fallback_center = (
            float(os.getenv("FALLBACK_LAT", "-22.9068")),
            float(os.getenv("FALLBACK_LNG", "-43.1729")),
        )
        self.fallback_radius_km = float(os.getenv("FALLBACK_RADIUS_KM", "8"))
        self.osm_delay = float(os.getenv("OSM_GEOCODE_DELAY_SEC", "0.15"))
        viewbox_env = os.getenv("DEFAULT_VIEWBOX")  # "lon_left,lat_top,lon_right,lat_bottom"
        self.viewbox = None
        if viewbox_env:
            try:
                parts = [float(p) for p in viewbox_env.split(",")]
                if len(parts) == 4:
                    self.viewbox = parts
            except ValueError:
                self.viewbox = None
        else:
            # Rio de Janeiro metro bounding box (lon_left, lat_top, lon_right, lat_bottom)
            self.viewbox = [-43.8, -22.7, -43.0, -23.1]
        self.max_valid_distance_km = float(os.getenv("MAX_GEOCODE_DISTANCE_KM", "25"))
    
    def _prepare_query(self, address: str) -> str:
        """Enriquece endereco com cidade/UF se faltar contexto."""
        addr = self._sanitize_address(address)
        if not addr:
            return addr
        has_uf = re.search(r"\b(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MG|MS|MT|PA|PB|PE|PI|PR|RJ|RN|RO|RR|RS|SC|SE|SP|TO)\b", addr, re.IGNORECASE)
        has_city = self.default_city.lower() in addr.lower()
        has_country = any(c in addr.lower() for c in ["brasil", "brazil"])
        parts = [addr]
        if not has_city:
            parts.append(self.default_city)
        if not has_uf:
            parts.append(self.default_state)
        if not has_country:
            parts.append(self.default_country)
        return ", ".join(parts)

    def _sanitize_address(self, address: str) -> str:
        """Limpa observacoes excessivas para melhorar match no OSM."""
        addr = address or ""
        addr = re.sub(r"\(.*?\)", "", addr)  # remove parenteses
        addr = re.sub(r"\b(portaria|recepcao|entrada|bloco [a-z0-9]+|bl\.?\s?[a-z0-9]+)\b", "", addr, flags=re.IGNORECASE)
        addr = re.sub(r"\s+", " ", addr)
        return addr.strip(", ")

    def geocode(self, address: str) -> Tuple[float, float]:
        """
        Geocode com estratégia em cascata:
        1. Cache local (GRATUITO)
        2. OpenStreetMap Nominatim (GRATUITO)
        3. Google Maps API (PAGO - se disponível)
        4. Simulação baseada em hash (ÚLTIMO RECURSO)
        """
        query = self._prepare_query(address)
        if not query:
            raise ValueError("Endereco vazio para geocodificacao")

        # 1. Tenta cache
        cached = self.cache.get(query)
        if cached:
            return cached
        
        # 2. Tenta OpenStreetMap (GRATUITO)
        coords = self._geocode_osm(query)
        if coords:
            self.cache.set(query, coords[0], coords[1])
            return coords
        
        # 3. Tenta Google Maps API (se disponível)
        if self.api_key and self.api_calls_today < 100:
            coords = self._geocode_google(query)
            if coords:
                self.cache.set(query, coords[0], coords[1])
                self._increment_api_call()
                return coords
        
        # 4. Fallback: simulação determinística (ÚLTIMO RECURSO)
        coords = self._geocode_fallback(query)
        self.cache.set(query, coords[0], coords[1])
        return coords
    
    def _geocode_osm(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Geocode via OpenStreetMap Nominatim (GRATUITO)
        Respeita rate limit: 1 req/sec
        """
        try:
            import requests
            import time
            
            # Rate limit (ajustavel). Default 150ms para acelerar sem abusar.
            time.sleep(self.osm_delay)
            
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'addressdetails': 0,
                'countrycodes': 'br'
            }
            if self.viewbox:
                params['viewbox'] = ','.join(str(v) for v in self.viewbox)
                params['bounded'] = 1
            headers = {
                'User-Agent': 'BotEntregador/1.0 (Telegram Bot)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    result = data[0]
                    latlng = (float(result['lat']), float(result['lon']))
                    if self._distance_km(latlng, self.fallback_center) <= self.max_valid_distance_km:
                        return latlng
                    logging.warning("OSM geocode descartado: longe do centro (%skm): %s", round(self._distance_km(latlng, self.fallback_center), 1), address)
        except Exception as e:
            # Se falhar, continua para próxima estratégia
            pass
        
        return None
    
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
        Geocoding simulado baseado em hash do endereço, restrito ao centro padrão.
        Mantém consistência determinística para o mesmo input.
        """
        hash_int = int(hashlib.md5(address.encode()).hexdigest()[:8], 16)
        lat, lng = self.fallback_center
        # Converte hash em deslocamentos pequenos dentro do raio configurado
        delta_deg = self.fallback_radius_km / 111  # km -> graus aproximados
        lat_offset = ((hash_int % 1000) / 1000 - 0.5) * 2 * delta_deg
        lng_offset = (((hash_int // 1000) % 1000) / 1000 - 0.5) * 2 * delta_deg
        return (lat + lat_offset, lng + lng_offset)

    def _distance_km(self, a: Tuple[float, float], b: Tuple[float, float]) -> float:
        """Haversine rapida; suficiente para filtro local."""
        lat1, lon1 = a
        lat2, lon2 = b
        p = math.pi / 180
        d = 0.5 - math.cos((lat2 - lat1) * p) / 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2
        return 12742 * math.asin(math.sqrt(d))
    
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
