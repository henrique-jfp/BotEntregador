"""
🗺️ GEOCODING SERVICE - Cache inteligente + Fallback
Economiza chamadas de API com cache persistente
"""
import json
import hashlib
import os
import re
from pathlib import Path
from typing import Tuple, Optional, List, Dict
from datetime import datetime, timedelta
import math
import logging


class GeocodingCache:
    """Cache persistente de geocoding (PostgreSQL com fallback JSON)"""
    
    def __init__(self, cache_file: str = "data/geocoding_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache = self._load_cache()
        self.ttl_days = 90  # Cache válido por 90 dias
        from ..database import db_manager
        self.db_manager = db_manager
    
    def _load_cache(self) -> dict:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Erro ao salvar cache JSON: {e}")
    
    def _get_key(self, address: str) -> str:
        """Gera hash MD5 do endereço normalizado"""
        normalized = address.lower().strip()
        # Para o DB usamos o próprio endereço como PK, para o JSON usamos hash
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def get(self, address: str) -> Optional[Tuple[float, float]]:
        """Busca coordenadas no cache (DB -> JSON)"""
        normalized = address.lower().strip()
        
        # 1. Tenta PostgreSQL
        if self.db_manager.is_connected:
            try:
                from ..database import GeocodingCacheDB
                with self.db_manager.get_session() as session:
                    cached = session.query(GeocodingCacheDB).filter(GeocodingCacheDB.address == normalized).first()
                    if cached:
                        # Verifica TTL
                        if datetime.now() - cached.cached_at < timedelta(days=self.ttl_days):
                            return (cached.lat, cached.lng)
            except Exception as e:
                logging.warning(f"Erro ao buscar cache no DB: {e}")
        
        # 2. Fallback JSON
        key = self._get_key(address)
        if key in self.cache:
            entry = self.cache[key]
            cached_date = datetime.fromisoformat(entry['cached_at'])
            if datetime.now() - cached_date < timedelta(days=self.ttl_days):
                return (entry['lat'], entry['lng'])
        
        return None
    
    def set(self, address: str, lat: float, lng: float, provider: str = None):
        """Salva coordenadas no cache (DB e JSON)"""
        normalized = address.lower().strip()
        
        # 1. Salva no PostgreSQL
        if self.db_manager.is_connected:
            try:
                from ..database import GeocodingCacheDB
                with self.db_manager.get_session() as session:
                    cached = session.query(GeocodingCacheDB).filter(GeocodingCacheDB.address == normalized).first()
                    if cached:
                        cached.lat = lat
                        cached.lng = lng
                        cached.provider = provider
                        cached.cached_at = datetime.now()
                    else:
                        new_entry = GeocodingCacheDB(
                            address=normalized,
                            lat=lat,
                            lng=lng,
                            provider=provider,
                            cached_at=datetime.now()
                        )
                        session.add(new_entry)
                    session.commit()
            except Exception as e:
                logging.error(f"Erro ao salvar cache no DB: {e}")
        
        # 2. Salva no JSON
        key = self._get_key(address)
        self.cache[key] = {
            'address': address,
            'lat': lat,
            'lng': lng,
            'provider': provider,
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
    """Geocoding com fallback inteligente - Múltiplas APIs GRATUITAS"""
    
    def __init__(self, google_api_key: Optional[str] = None, locationiq_key: Optional[str] = None, geoapify_key: Optional[str] = None):
        self.google_api_key = google_api_key
        self.api_key = google_api_key  # alias para compatibilidade
        self.locationiq_key = locationiq_key  # 5.000 req/dia GRÁTIS, sem cartão
        self.geoapify_key = geoapify_key      # 3.000 req/dia GRÁTIS, sem cartão
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
        # Verbose debug flag para registrar respostas de API
        self.debug = os.getenv("GEOCODING_DEBUG", "0") == "1"
    
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
        
        # 1. Remove texto entre parenteses (comum para ref)
        addr = re.sub(r"\(.*?\)", "", addr)
        
        # 2. Remove complementos comuns (regex case insensitive)
        # Ex: "Apt 101", "Sala 305", "Loja B", "Bloco 2", "Ao lado de..."
        # Remove do termo encontrado até o fim da string (assumindo que complemento vem no fim)
        # OU remove apenas o termo e o numero seguinte.
        
        # Lista de termos que indicam inicio de complemento que pode ser descartado
        stop_words = [
            r"apartamento", r"apto", r"apt", r"ap\.?", 
            r"sala", r"sl\.?", 
            r"loja", r"lj\.?", 
            r"sobreloja", r"subsolo", 
            r"cobertura", r"cob\.?", 
            r"bloco", r"bl\.?", 
            r"portaria", r"recepcao", r"entrada", 
            r"ao lado", r"perto", r"próximo", r"frente", r"fundos",
            r"condominio", r"edificio", r"ed\.?",
            r"shopping", r"galeria", r"posto", r"mercado"
        ]
        
        # \b no inicio garante que "sapato" nao seja pego por "ap"
        # Sem \b no fim para pegar "Apto104" (merged)
        pattern = r"\b(" + "|".join(stop_words) + r").*"
        addr = re.sub(pattern, "", addr, flags=re.IGNORECASE)

        # 3. Limpeza final de espaços e pontuação solta no fim
        # Ex: "Rua Gilberto, 123, " -> "Rua Gilberto, 123"
        addr = re.sub(r"\s+", " ", addr)
        addr = addr.strip(",. -")
        
        return addr

    def _extract_neighborhood(self, address: str) -> Optional[str]:
        tokens = [t.strip() for t in re.split(r"[,;]", address) if t.strip()]
        ignore = {self.default_city.lower(), self.default_state.lower(), self.default_country.lower(), "br"}
        for tok in reversed(tokens):
            if any(ch.isdigit() for ch in tok):
                continue
            low = tok.lower()
            if low in ignore or len(low) < 3:
                continue
            return tok
        return None

    def geocode(self, address: str, expected_bairro: Optional[str] = None) -> Tuple[float, float]:
        """
        Geocode com estratégia em cascata:
        1. Cache local (GRATUITO)
        2. LocationIQ (GRATUITO)
        3. Geoapify (GRATUITO)
        4. OpenStreetMap Nominatim (GRATUITO, mais lento)
        5. Google Maps API (PAGO - ÚLTIMO RECURSO)
        6. Simulação baseada em hash (ÚLTIMO RECURSO)
        """
        raw_addr = self._sanitize_address(address)
        bairro = self._extract_neighborhood(raw_addr)
        query = self._prepare_query(raw_addr)
        if not query:
            raise ValueError("Endereco vazio para geocodificacao")

        # 1. Tenta cache
        cached = self.cache.get(query)
        if cached:
            return cached
        
        # 2. Tenta LocationIQ (5.000/dia GRÁTIS, sem cartão, rápido)
        if self.locationiq_key and self.api_calls_today < 5000:
            coords = self._geocode_locationiq(query, expected_bairro)
            if coords:
                self.cache.set(query, coords[0], coords[1], "LocationIQ")
                self._increment_api_call()
                logging.info(f"✅ Geocoded via LocationIQ: {address[:60]} -> {coords}")
                return coords
        
        # 3. Tenta Geoapify (3.000/dia GRÁTIS, sem cartão)
        if self.geoapify_key and self.api_calls_today < 3000:
            coords = self._geocode_geoapify(query, expected_bairro)
            if coords:
                self.cache.set(query, coords[0], coords[1], "Geoapify")
                self._increment_api_call()
                logging.info(f"✅ Geocoded via Geoapify: {address[:60]} -> {coords}")
                return coords
        
        # 4. Fallback: OpenStreetMap Nominatim (GRÁTIS mas lento)
        coords = self._geocode_osm(query, raw_addr, bairro)
        if coords:
            self.cache.set(query, coords[0], coords[1], "OSM")
            logging.info(f"✅ Geocoded via OSM: {address[:60]} -> {coords}")
            return coords

        # 5. ÚLTIMO RECURSO: Google Maps (se configurado - exige cartão)
        if self.google_api_key and self.api_calls_today < 2500:
            coords = self._geocode_google(query, expected_bairro)
            if coords:
                self.cache.set(query, coords[0], coords[1], "Google")
                self._increment_api_call()
                logging.info(f"✅ Geocoded via Google Maps (último recurso): {address[:60]} -> {coords}")
                return coords
        
        # ERRO: Nenhuma API conseguiu geocodificar
        logging.error(f"❌ FALHA TOTAL no geocoding: {address[:80]}")
        logging.error(f"   APIs tentadas: LocationIQ={bool(self.locationiq_key)}, Geoapify={bool(self.geoapify_key)}, OSM=True, Google={bool(self.google_api_key)}")
        raise ValueError(f"Não foi possível geocodificar o endereço: {address}")
    
    def _geocode_osm(self, address: str, raw_addr: str, bairro: Optional[str]) -> Optional[Tuple[float, float]]:
        """
        Geocode via OpenStreetMap Nominatim (GRATUITO)
        Respeita rate limit: 1 req/sec
        """
        try:
            import requests
            import time
            
            # Rate limit OBRIGATÓRIO do OSM: 1 req/segundo
            time.sleep(1.0)  # Respeita rate limit oficial
            
            url = "https://nominatim.openstreetmap.org/search"
            base = {
                'format': 'json',
                'limit': 10,  # Aumenta limite para ter mais opções
                'addressdetails': 1,
                'countrycodes': 'br',
                'dedupe': 0  # Não remove duplicatas, queremos todas as opções
            }
            
            # Estratégia 1: pesquisa livre (`q`) — melhor para texto livre/descrições
            try:
                import requests
                headers = {
                    'User-Agent': 'BotEntregador/1.0 (Telegram Bot; contact@botentregador.com)'
                }

                if self.viewbox:
                    base['viewbox'] = ','.join(str(v) for v in self.viewbox)
                    base['bounded'] = 1

                free_q = ', '.join(filter(None, [raw_addr, bairro or '', self.default_city, self.default_state, self.default_country]))
                params = {**base, 'q': free_q}
                logging.debug(f"OSM free-text tentativa: {free_q[:80]}")
                response = requests.get(url, params=params, headers=headers, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        chosen = self._pick_best_osm(data, bairro)
                        if chosen:
                            latlng = (float(chosen['lat']), float(chosen['lon']))
                            dist_km = self._distance_km(latlng, self.fallback_center)
                            if dist_km <= self.max_valid_distance_km:
                                logging.info(f"✅ OSM (free) encontrou: {address[:60]} -> {latlng} (dist: {dist_km:.1f}km)")
                                if self.debug:
                                    try:
                                        import json as _json
                                        logging.debug(f"OSM free-text raw: {_json.dumps(data)[:2000]}")
                                    except Exception:
                                        pass
                                return latlng
                            logging.warning(f"⚠️ OSM (free) descartado (longe {dist_km:.1f}km): {address[:60]}")
            except Exception:
                pass

            # Estratégia 2: busca estruturada (fallback se free-text não retornar)
            attempts: List[dict] = []
            # Tentativa 1: Com bairro
            if bairro:
                attempts.append({
                    'street': raw_addr,
                    'city_district': bairro,
                    'city': self.default_city,
                    'state': self.default_state,
                    'country': self.default_country
                })
            # Tentativa 2: Sem bairro
            attempts.append({
                'street': raw_addr,
                'city': self.default_city,
                'state': self.default_state,
                'country': self.default_country
            })

            headers = {
                'User-Agent': 'BotEntregador/1.0 (Telegram Bot; contact@botentregador.com)'
            }

            for idx, attempt in enumerate(attempts, 1):
                params = {**base, **attempt}
                logging.debug(f"OSM tentativa {idx}/{len(attempts)}: {attempt.get('street', '')[:40]}")
                response = requests.get(url, params=params, headers=headers, timeout=15)
                if response.status_code != 200:
                    continue
                data = response.json()
                if not data:
                    continue
                chosen = self._pick_best_osm(data, bairro)
                if chosen:
                    latlng = (float(chosen['lat']), float(chosen['lon']))
                    dist_km = self._distance_km(latlng, self.fallback_center)
                    if dist_km <= self.max_valid_distance_km:
                        logging.info(f"✅ OSM encontrou: {address[:60]} -> {latlng} (dist: {dist_km:.1f}km)")
                        if self.debug:
                            try:
                                import json as _json
                                logging.debug(f"OSM structured raw: {_json.dumps(data)[:2000]}")
                            except Exception:
                                pass
                        return latlng
                    logging.warning(f"⚠️ OSM descartado (longe {dist_km:.1f}km): {address[:60]}")
        except Exception as e:
            # Se falhar, continua para próxima estratégia
            pass
        
        return None
    
    def _geocode_google(self, address: str, expected_bairro: Optional[str] = None) -> Optional[Tuple[float, float]]:
        """Geocode via Google Maps API com validação de bairro"""
        try:
            import requests
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': address,
                'key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                result = data['results'][0]
                location = result['geometry']['location']
                lat, lng = location['lat'], location['lng']
                
                # Validação 1: Verifica distância do centro
                if self._distance_km((lat, lng), self.fallback_center) > self.max_valid_distance_km:
                    logging.warning(f"Google Maps: resultado muito longe do centro: {address}")
                    return None
                
                # Validação 2: Verifica bairro se fornecido
                if expected_bairro:
                    address_components = result.get('address_components', [])
                    found_bairro = False
                    expected_lower = expected_bairro.lower().strip()
                    
                    for component in address_components:
                        types = component.get('types', [])
                        # Procura por bairro nas várias formas que o Google retorna
                        if any(t in types for t in ['sublocality', 'neighborhood', 'sublocality_level_1', 'political']):
                            component_name = component.get('long_name', '').lower().strip()
                            if expected_lower in component_name or component_name in expected_lower:
                                found_bairro = True
                                break
                    
                    if not found_bairro:
                        logging.warning(f"Google Maps: bairro não confere. Esperado: {expected_bairro}, Endereço: {address}")
                        return None
                
                return (lat, lng)
        except Exception as e:
            logging.error(f"Erro Google Maps API: {e}")
            pass
        
        return None
    
    def _geocode_locationiq(self, address: str, expected_bairro: Optional[str] = None) -> Optional[Tuple[float, float]]:
        """
        Geocode via LocationIQ (baseado em OSM mas MUITO mais rápido)
        FREE: 5.000 requests/dia SEM cartão de crédito
        Cadastro: https://locationiq.com/
        """
        try:
            import requests
            import time
            
            # Rate limit gentil
            time.sleep(0.1)
            
            url = "https://us1.locationiq.com/v1/search"
            params = {
                'key': self.locationiq_key,
                'q': address,
                'format': 'json',
                'limit': 5,
                'countrycodes': 'br',
                'addressdetails': 1
            }
            
            if self.viewbox:
                params['viewbox'] = ','.join(str(v) for v in self.viewbox)
                params['bounded'] = 1
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            if not data:
                return None
            
            # Pega melhor resultado com validação
            if self.debug:
                try:
                    import json as _json
                    logging.debug(f"LocationIQ raw: {_json.dumps(data)[:2000]}")
                except Exception:
                    pass
            for result in data:
                lat, lng = float(result['lat']), float(result['lon'])
                
                # Validação 1: Distância
                if self._distance_km((lat, lng), self.fallback_center) > self.max_valid_distance_km:
                    continue
                
                # Validação 2: Bairro (se fornecido)
                if expected_bairro:
                    addr = result.get('address', {})
                    bairro_fields = [
                        addr.get('neighbourhood', ''),
                        addr.get('suburb', ''),
                        addr.get('city_district', ''),
                        addr.get('quarter', '')
                    ]
                    
                    expected_lower = expected_bairro.lower().strip()
                    match = any(expected_lower in f.lower() or f.lower() in expected_lower 
                               for f in bairro_fields if f)
                    
                    if not match:
                        continue
                
                return (lat, lng)
            
        except Exception as e:
            logging.error(f"Erro LocationIQ API: {e}")
            if self.debug:
                import traceback
                logging.debug(traceback.format_exc())
        
        return None
    
    def _geocode_geoapify(self, address: str, expected_bairro: Optional[str] = None) -> Optional[Tuple[float, float]]:
        """
        Geocode via Geoapify
        FREE: 3.000 requests/dia SEM cartão de crédito
        Cadastro: https://www.geoapify.com/
        """
        try:
            import requests
            import time
            
            time.sleep(0.1)
            
            url = "https://api.geoapify.com/v1/geocode/search"
            params = {
                'apiKey': self.geoapify_key,
                'text': address,
                'limit': 5,
                'filter': f'countrycode:br'
            }
            
            # Adiciona bias para Rio de Janeiro
            if self.fallback_center:
                params['bias'] = f"proximity:{self.fallback_center[1]},{self.fallback_center[0]}"
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            features = data.get('features', [])

            if self.debug:
                try:
                    import json as _json
                    logging.debug(f"Geoapify raw: {_json.dumps(data)[:2000]}")
                except Exception:
                    pass
            
            if not features:
                return None
            
            # Pega melhor resultado
            for feature in features:
                props = feature.get('properties', {})
                lon = props.get('lon')
                lat = props.get('lat')
                
                if not lat or not lon:
                    continue
                
                # Validação 1: Distância
                if self._distance_km((lat, lon), self.fallback_center) > self.max_valid_distance_km:
                    continue
                
                # Validação 2: Bairro
                if expected_bairro:
                    bairro_fields = [
                        props.get('neighbourhood', ''),
                        props.get('suburb', ''),
                        props.get('district', ''),
                        props.get('quarter', '')
                    ]
                    
                    expected_lower = expected_bairro.lower().strip()
                    match = any(expected_lower in f.lower() or f.lower() in expected_lower 
                               for f in bairro_fields if f)
                    
                    if not match:
                        continue
                
                return (lat, lon)
            
        except Exception as e:
            logging.error(f"Erro Geoapify API: {e}")
        
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

    def _pick_best_osm(self, results: list, bairro: Optional[str]):
        best = None
        best_score = -1
        target_bairro = bairro.lower() if bairro else None
        for res in results:
            try:
                latlng = (float(res['lat']), float(res['lon']))
            except Exception:
                continue
            dist = self._distance_km(latlng, self.fallback_center)
            bairro_match = False
            if target_bairro and 'address' in res:
                addr_obj = res['address'] or {}
                for key in ['neighbourhood', 'suburb', 'city_district', 'quarter', 'residential']:
                    if addr_obj.get(key, '').lower() == target_bairro:
                        bairro_match = True
                        break
            score = 0
            if bairro_match:
                score += 5
            score += max(0, self.max_valid_distance_km - dist)
            if score > best_score:
                best_score = score
                best = res
        return best
    
    def _increment_api_call(self):
        """Incrementa contador de chamadas API"""
        today = datetime.now().date()
        if today > self.last_reset:
            self.api_calls_today = 0
            self.last_reset = today
        
        self.api_calls_today += 1
    
    async def geocode_address(self, address: str, expected_bairro: Optional[str] = None) -> Optional[Tuple[float, float]]:
        """
        Versão async do geocode para uso com Telegram bot.
        Retorna (lat, lng) ou None se falhar.
        """
        try:
            return self.geocode(address, expected_bairro)
        except Exception:
            return None
    
    async def geocode_batch(self, addresses_data: List[Dict]) -> List[Dict]:
        """
        Geocodifica múltiplos endereços em paralelo (async).
        
        Args:
            addresses_data: Lista de dicts com 'address' e 'bairro' (opcional)
        
        Returns:
            Lista de dicts com 'address', 'bairro', 'lat', 'lon'
        """
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        def geocode_single(item):
            """Geocodifica um único endereço"""
            try:
                address = item.get('address', '')
                bairro = item.get('bairro', '')
                
                if not address:
                    return {**item, 'lat': None, 'lon': None}
                
                coords = self.geocode(address, bairro)
                return {**item, 'lat': coords[0], 'lon': coords[1]}
            except Exception as e:
                logging.warning(f"Erro ao geocodificar {item.get('address', '')}: {e}")
                return {**item, 'lat': None, 'lon': None}
        
        # Executa geocoding em paralelo com ThreadPoolExecutor
        # Limita a 10 threads simultâneas para não sobrecarregar APIs
        with ThreadPoolExecutor(max_workers=10) as executor:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: list(executor.map(geocode_single, addresses_data))
            )
        
        return results
    
    async def reverse_geocode(self, lat: float, lng: float) -> Optional[str]:
        """
        Reverse geocoding: coordenadas → endereço
        """
        # Sem reverse gratuito configurado: retorna as coordenadas formatadas
        return f"Lat: {lat:.6f}, Lng: {lng:.6f}"
    
    def get_stats(self) -> dict:
        """Estatísticas do serviço"""
        cache_stats = self.cache.stats()
        
        return {
            'cache': cache_stats,
            'api_calls_today': self.api_calls_today,
            'using_api': bool(self.google_api_key or self.locationiq_key or self.geoapify_key),
            'apis_configured': {
                'google': bool(self.google_api_key),
                'locationiq': bool(self.locationiq_key),
                'geoapify': bool(self.geoapify_key)
            }
        }
    
    def batch_geocode_async(self, addresses: List[str]) -> List[Tuple[float, float]]:
        """
        🚀 Geocodifica lista de endereços em PARALELO
        - Usa ThreadPoolExecutor com 8 workers
        - Cache integrado (sem re-geocodificar)
        - Fallback com hash-seed (determinístico)
        - Retorna lista na MESMA ORDEM dos inputs
        """
        from concurrent.futures import ThreadPoolExecutor
        import hashlib
        import random as rand
        
        results = []
        
        def geocode_wrapper(addr):
            try:
                coords = self.geocode(addr)
                return coords if isinstance(coords, tuple) else None
            except:
                # Fallback determinístico com hash
                seed = int(hashlib.md5(addr.encode()).hexdigest()[:8], 16)
                rand.seed(seed)
                return (
                    -22.9570 + rand.uniform(-0.025, 0.025),
                    -43.1910 + rand.uniform(-0.025, 0.025)
                )
        
        # Executa até 8 requisições em paralelo
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(geocode_wrapper, addresses))
        
        return results


# Singleton
from ..config import BotConfig
geocoding_service = GeocodingService(
    google_api_key=BotConfig.GOOGLE_API_KEY,
    locationiq_key=os.getenv("LOCATIONIQ_API_KEY"),
    geoapify_key=os.getenv("GEOAPIFY_API_KEY")
)

