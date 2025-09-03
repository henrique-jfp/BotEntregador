#!/usr/bin/env python3
"""
🚀 BOT DE OTIMIZAÇÃO DE ROTAS - TELEGRAM
Versão: 2.0 - Profissional

Desenvolvido para auxiliar entregadores a otimizar suas rotas diárias
através de inteligência artificial, OCR e navegação GPS integrada.

Author: Henrique de Jesus
Date: 2025-09-02
"""

import os
import re
import json
import logging
import threading
import base64
import errno
import math
import httpx
import urllib.parse
import uuid
import asyncio
import itertools
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from dotenv import load_dotenv
from google.cloud import vision
from google.oauth2 import service_account
import google.generativeai as genai
from PIL import Image

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

# OR-Tools (pode falhar em ambiente local sem instalação; fallback ativo)
try:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    ORTOOLS_AVAILABLE = True
except Exception:
    ORTOOLS_AVAILABLE = False

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

class BotStates(Enum):
    WAITING_PHOTOS = 1
    PROCESSING = 2
    CONFIRMING_ROUTE = 3
    NAVIGATING = 4

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

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    MAX_PHOTOS_PER_REQUEST = int(os.getenv('MAX_PHOTOS_PER_REQUEST', '8'))
    MAX_ADDRESSES_PER_ROUTE = int(os.getenv('MAX_ADDRESSES_PER_ROUTE', '20'))
    MAX_IMAGE_SIZE_MB = 20
    RATE_LIMIT_PER_HOUR = 50
    SERVICE_TIME_PER_STOP_MIN = float(os.getenv('SERVICE_TIME_PER_STOP_MIN', '1'))  # tempo médio para deixar pacote
    AVERAGE_SPEED_KMH = float(os.getenv('AVERAGE_SPEED_KMH', '25'))  # velocidade urbana média fallback
    user_requests: Dict[int, List[datetime]] = {}

if not Config.TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN não configurado")

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
            data = asdict(session)
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
            
            # Correção para parsing do datetime
            start_time = datetime.now()
            if data.get('start_time'):
                try:
                    start_time = datetime.fromisoformat(data['start_time'])
                except (ValueError, TypeError):
                    start_time = datetime.now()
            
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
                processed=data.get('processed', False)
            )
            return session
        except Exception as e:
            logger.warning(f"Falha ao carregar sessão {user_id}: {e}")
            return None

class SecurityValidator:
    @staticmethod
    async def validate_image(image_bytes: bytes) -> bool:
        if len(image_bytes) > Config.MAX_IMAGE_SIZE_MB * 1024 * 1024:
            return False
        try:
            from io import BytesIO
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

def setup_vision_client():
    try:
        # Tenta Base64 primeiro
        json_base64 = os.getenv('GOOGLE_VISION_CREDENTIALS_JSON_BASE64')
        if json_base64:
            try:
                # Remove espaços, quebras de linha e aspas acidentais
                json_base64 = json_base64.strip().strip('"').replace('\n', '').replace('\r', '').replace(' ', '')
                # Corrigir padding se necessário - Base64 deve ser múltiplo de 4
                missing_padding = len(json_base64) % 4
                if missing_padding:
                    json_base64 += '=' * (4 - missing_padding)
                
                # Valida se é Base64 válido antes de decodificar
                import string
                valid_chars = string.ascii_letters + string.digits + '+/='
                if not all(c in valid_chars for c in json_base64):
                    raise ValueError("Base64 contém caracteres inválidos")
                
                # Decodifica a string Base64
                decoded_json = base64.b64decode(json_base64).decode('utf-8')
                info = json.loads(decoded_json)
                credentials = service_account.Credentials.from_service_account_info(info)
                logger.info("Credenciais Vision carregadas via Base64")
                client = vision.ImageAnnotatorClient(credentials=credentials)
                logger.info("Vision client configurado com sucesso")
                return client
            except Exception as e:
                logger.error(f"Erro ao processar credenciais Base64: {e}")
        
        # Tenta JSON direto
        json_env = os.getenv('GOOGLE_VISION_CREDENTIALS_JSON')
        if json_env:
            try:
                info = json.loads(json_env)
                credentials = service_account.Credentials.from_service_account_info(info)
                logger.info("Credenciais Vision carregadas via JSON direto")
                client = vision.ImageAnnotatorClient(credentials=credentials)
                logger.info("Vision client configurado com sucesso")
                return client
            except Exception as e:
                logger.error(f"Erro ao processar credenciais JSON: {e}")
        
        # Tenta arquivo
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if creds_path and os.path.exists(creds_path):
            credentials = service_account.Credentials.from_service_account_file(creds_path)
            logger.info("Credenciais Vision carregadas via arquivo")
            client = vision.ImageAnnotatorClient(credentials=credentials)
            return client
            
        logger.warning("Credenciais do Vision não encontradas - OCR indisponível")
        logger.info("Variáveis disponíveis: GOOGLE_VISION_CREDENTIALS_JSON_BASE64, GOOGLE_VISION_CREDENTIALS_JSON, GOOGLE_APPLICATION_CREDENTIALS")
        return None
        
    except Exception as e:
        logger.error(f"Falha ao configurar Vision client: {e}")
        return None

vision_client = setup_vision_client()

def setup_gemini_model():
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        logger.info('GOOGLE_API_KEY não configurada - fallback Gemini indisponível')
        return None
    try:
        genai.configure(api_key=api_key)
        # Modelos possíveis: gemini-1.5-flash (rápido) ou gemini-1.5-pro (mais caro). Usamos flash.
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info('Modelo Gemini configurado para fallback OCR.')
        return model
    except Exception as e:
        logger.error(f'Falha ao configurar modelo Gemini: {e}')
        return None

gemini_model = setup_gemini_model()

ADDRESS_REGEX = re.compile(r'(rua|r\.|avenida|av\.|travessa|tv\.|alameda|praça|praca|rodovia|estrada|beco)\s+[^\n]{3,}', re.IGNORECASE)

# ===== Normalização de Abreviações de Logradouros =====
ABBREV_MAP = [
    (r'^(r)\b\.?:?', 'Rua'),
    (r'^(av)\b\.?:?', 'Avenida'),
    (r'^(tv|trav)\b\.?:?', 'Travessa'),
    (r'^(al)\b\.?:?', 'Alameda'),
    (r'^(pça|praca|praça)\b\.?:?', 'Praça'),
    (r'^(rod)\b\.?:?', 'Rodovia'),
    (r'^(estr|est)\b\.?:?', 'Estrada'),
    (r'^(bec)\b\.?:?', 'Beco'),
    (r'^(cond)\b\.?:?', 'Condomínio'),
    (r'^(jd)\b\.?:?', 'Jardim'),
    (r'^(lote)\b\.?:?', 'Loteamento'),
]

CEP_REGEX = re.compile(r'\b\d{5}-?\d{3}\b')

def normalize_address(original: str) -> str:
    """Expande somente a abreviação inicial (se houver) preservando todo o restante intacto
    (números, maiúsculas, CEP, acentos). Não reordena, não capitaliza o meio.
    """
    line = original.strip()
    if not line:
        return line
    # Remove caracteres de controle
    line = re.sub(r'[\u0000-\u001F]', '', line)
    # Divide primeira palavra para checar abreviação
    parts = line.split(maxsplit=1)
    first = parts[0]
    rest = parts[1] if len(parts) > 1 else ''
    replaced = False
    for pattern, repl in ABBREV_MAP:
        if re.match(pattern, first, flags=re.IGNORECASE):
            first = repl
            replaced = True
            break
    # Junta novamente mantendo resto exatamente
    rebuilt = (first + (' ' + rest if rest else '')).strip()
    # Garante que CEP (se existir no original) permaneça (já está preservado, apenas sanity)
    cep_match = CEP_REGEX.search(original)
    if cep_match and cep_match.group(0) not in rebuilt:
        rebuilt += f' CEP {cep_match.group(0)}'
    return rebuilt

class ImageProcessor:
    @staticmethod
    async def download(bot, file_id: str) -> Optional[bytes]:
        try:
            file = await bot.get_file(file_id)
            ba = await file.download_as_bytearray()
            return bytes(ba)
        except Exception as e:
            logger.error(f"Erro download imagem {file_id}: {e}")
            return None

    @staticmethod
    async def ocr(bot, photo_ids: List[str]) -> str:
        # 1) Tenta Google Vision
        if vision_client:
            texts = []
            for fid in photo_ids:
                img_bytes = await ImageProcessor.download(bot, fid)
                if not img_bytes:
                    continue
                if not await SecurityValidator.validate_image(img_bytes):
                    continue
                image = vision.Image(content=img_bytes)
                try:
                    resp = vision_client.text_detection(image=image)
                    if resp.error.message:
                        logger.warning(f"Vision erro: {resp.error.message}")
                        continue
                    if resp.text_annotations:
                        texts.append(resp.text_annotations[0].description)
                except Exception as e:
                    logger.error(f"OCR (Vision) falhou: {e}")
            if texts:
                return '\n'.join(texts)
            logger.info('Vision retornou vazio; tentando fallback Gemini se disponível.')
        else:
            logger.warning('Vision client não disponível - tentando fallback Gemini.')

        # 2) Fallback Gemini Vision
        if gemini_model:
            results = []
            for fid in photo_ids:
                img_bytes = await ImageProcessor.download(bot, fid)
                if not img_bytes:
                    continue
                if not await SecurityValidator.validate_image(img_bytes):
                    continue
                try:
                    b64 = base64.b64encode(img_bytes).decode('utf-8')
                    # Prompt para extrair somente texto
                    prompt = (
                        "Extraia exatamente o texto de endereços da imagem.\n"
                        "Regras IMPORTANTES:\n"
                        "1. NÃO traduza, NÃO corrija ortografia, NÃO invente nada.\n"
                        "2. Preserve números, hífens, vírgulas, barras, complementos, CEP (#####-###).\n"
                        "3. Uma linha por endereço como aparece.\n"
                        "4. NÃO expanda abreviações (R., Av., Tv.) – apenas copie como está.\n"
                        "5. Não agrupe ou reordene.\n"
                        "Saída: somente linhas de texto, sem comentários adicionais."
                    )
                    # API espera lista de partes: imagem e texto
                    resp = await asyncio.to_thread(
                        gemini_model.generate_content,
                        [
                            { 'mime_type': 'image/jpeg', 'data': b64 },
                            prompt
                        ]
                    )
                    if hasattr(resp, 'text') and resp.text:
                        results.append(resp.text.strip())
                except Exception as e:
                    logger.error(f"OCR (Gemini) falhou: {e}")
            if results:
                logger.info('OCR realizado via Gemini.')
                return '\n'.join(results)
            logger.warning('Fallback Gemini não retornou texto.')
        else:
            logger.warning('Modelo Gemini indisponível.')
        return ''

def extract_addresses(raw_text: str) -> List[DeliveryAddress]:
    """Extrai endereços preservando linhas e tentando unir fragmentos.

    Muitos comprovantes imprimem assim:
        R. Nossa Sra de Lourdes, 150
        São Francisco, Niterói - RJ, 24360-420

    Queremos juntar em uma única linha. Estratégia:
      1. Limpa linhas vazias / ruído curto (<3 chars sem dígitos ou letras)
      2. Detecta possível segunda linha se: não começa com tipo de logradouro
         e contém cidade/UF ou CEP e linha anterior tinha número.
      3. Junta com vírgula se não existir já.
      4. Aplica normalização apenas na primeira palavra (já existente).
    """
    lines = [l.strip() for l in raw_text.splitlines()]
    cleaned: List[str] = []
    for l in lines:
        if not l:
            continue
        if len(re.sub(r'[^\w]', '', l)) < 3:
            continue
        cleaned.append(l)

    merged: List[str] = []
    logradouro_start = re.compile(r'^(rua|r\.|avenida|av\.|travessa|tv\.|alameda|praça|praca|rodovia|estrada|beco)\b', re.IGNORECASE)
    city_or_cep = re.compile(r'(\b(rj|sp|mg|es|ba|rs|sc|pr|go|df|pe|ce)\b|\b\d{5}-?\d{3}\b)', re.IGNORECASE)

    i = 0
    while i < len(cleaned):
        cur = cleaned[i]
        nxt = cleaned[i+1] if i+1 < len(cleaned) else ''
        # Se a próxima linha parece complemento (cidade/UF/CEP) e a atual tem número de endereço
        if nxt and not logradouro_start.search(nxt) and city_or_cep.search(nxt) and re.search(r'\d', cur) and len(cur) < 120:
            combined = cur.rstrip(',') + ', ' + nxt
            merged.append(combined)
            i += 2
            continue
        merged.append(cur)
        i += 1

    # Remove duplicados mantendo ordem
    seen = set()
    results: List[DeliveryAddress] = []
    for line in merged:
        if re.search(r'\d', line) and re.search(r'[A-Za-zÀ-ÖØ-öø-ÿ]', line):
            norm = normalize_address(line)
            key = norm.lower()
            if key not in seen:
                seen.add(key)
                results.append(DeliveryAddress(original_text=line, cleaned_address=norm))
        if len(results) >= Config.MAX_ADDRESSES_PER_ROUTE:
            break
    return results

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

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

async def optimize_route(addresses: List[DeliveryAddress]) -> List[DeliveryAddress]:
    """Otimiza rota mantendo o primeiro endereço como origem fixa.

    Estratégia: geocoding + nearest neighbor + 2-opt simples.
    Se geocoding falhar para muitos pontos, mantém ordem original.
    """
    if len(addresses) <= 2:
        return addresses
    Geocoder.load_cache()
    # Geocode sequencial (poderia paralelizar, mas evita estourar quota)
    geocoded = 0
    for a in addresses:
        if a.lat is None or a.lng is None:
            coord = await Geocoder.geocode(a.cleaned_address)
            if coord:
                a.lat, a.lng = coord
                geocoded += 1
    if geocoded:
        Geocoder.save_cache()
    # Verifica se temos coordenadas suficientes
    if sum(1 for a in addresses if a.lat and a.lng) < max(3, len(addresses)//2):
        logger.warning('Poucos endereços geocodificados - mantendo ordem original.')
        return addresses
    origin = addresses[0]  # fixo
    remaining = addresses[1:]
    # Nearest neighbor a partir da origem
    route = [origin]
    current = origin
    rem = remaining.copy()
    while rem:
        # Escolhe próximo mais perto
        nxt = min(rem, key=lambda x: haversine(current.lat, current.lng, x.lat, x.lng) if x.lat and x.lng else 1e9)
        route.append(nxt)
        rem.remove(nxt)
        current = nxt
    # 2-opt simples para tentar melhorar
    improved = True
    def total_dist(seq):
        d=0
        for i in range(len(seq)-1):
            a,b=seq[i],seq[i+1]
            if a.lat and b.lat:
                d+=haversine(a.lat,a.lng,b.lat,b.lng)
        return d
    while improved:
        improved = False
        best = total_dist(route)
        for i in range(1, len(route)-2):
            for j in range(i+1, len(route)-1):
                if j - i == 1:
                    continue
                new_route = route[:]
                new_route[i:j] = reversed(new_route[i:j])
                dist = total_dist(new_route)
                if dist + 0.01 < best:  # tolerância
                    route = new_route
                    best = dist
                    improved = True
    logger.info('Rota otimizada (heurística) concluída.')
    return route

# ================= ROTAS COM MATRIZ DE DISTÂNCIA (Google Distance Matrix) =================
class DistanceMatrixBuilder:
    cache_file = Path('distance_cache.json')
    cache: Dict[str, Dict[str, Dict[str, float]]] = {}

    @classmethod
    def load(cls):
        if not cls.cache and cls.cache_file.exists():
            try:
                cls.cache = json.loads(cls.cache_file.read_text(encoding='utf-8'))
            except Exception:
                cls.cache = {}

    @classmethod
    def save(cls):
        try:
            cls.cache_file.write_text(json.dumps(cls.cache, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass

    @classmethod
    def get_cached(cls, o: str, d: str):
        okey = o.lower(); dkey = d.lower()
        if okey in cls.cache and dkey in cls.cache[okey]:
            return cls.cache[okey][dkey]
        return None

    @classmethod
    def set_cached(cls, o: str, d: str, dist: float, dur: float):
        okey = o.lower(); dkey = d.lower()
        cls.cache.setdefault(okey, {})[dkey] = {'distance': dist, 'duration': dur}

async def build_distance_duration_matrix(addresses: List[DeliveryAddress]) -> Tuple[List[List[float]], List[List[float]], bool, List[str]]:
    """Retorna (matriz_dist_m, matriz_dur_s, via_api, enderecos_falhos).

    Não aborta toda a matriz em caso de elemento NOT_FOUND; apenas marca distância grande.
    Considera a matriz utilizável se >=70% dos pares válidos.
    """
    api_key = os.getenv('GOOGLE_API_KEY')
    n = len(addresses)
    DistanceMatrixBuilder.load()
    if not api_key:
        return [], [], False, []
    dmat = [[0.0]*n for _ in range(n)]
    tmat = [[0.0]*n for _ in range(n)]
    failed: List[str] = []
    total_pairs = n*(n-1)
    ok_pairs = 0
    BIG = 5_000_000  # 5000 km penalidade
    async with httpx.AsyncClient(timeout=20) as client:
        for i, origin_obj in enumerate(addresses):
            origin = origin_obj.cleaned_address
            missing = []
            for j, dest_obj in enumerate(addresses):
                if i == j:
                    continue
                cached = DistanceMatrixBuilder.get_cached(origin, dest_obj.cleaned_address)
                if cached:
                    dmat[i][j] = cached['distance']
                    tmat[i][j] = cached['duration']
                    if cached['distance'] > 0:
                        ok_pairs += 1
                else:
                    missing.append((j, dest_obj.cleaned_address))
            if not missing:
                continue
            destinations_str = '|'.join(m[1] for m in missing)
            params = {
                'origins': origin,
                'destinations': destinations_str,
                'mode': 'driving',
                'language': 'pt-BR',
                'key': api_key
            }
            try:
                r = await client.get('https://maps.googleapis.com/maps/api/distancematrix/json', params=params)
                data = r.json()
                if data.get('status') != 'OK':
                    logger.warning(f"Distance Matrix status global {data.get('status')} - fallback total")
                    return [], [], False, [a.cleaned_address for a in addresses]
                elements = data['rows'][0]['elements']
                for idx, el in enumerate(elements):
                    j = missing[idx][0]
                    dest_addr = addresses[j].cleaned_address
                    st = el.get('status')
                    if st == 'OK':
                        dist = el['distance']['value']
                        dur = el['duration']['value']
                        dmat[i][j] = dist
                        tmat[i][j] = dur
                        DistanceMatrixBuilder.set_cached(origin, dest_addr, dist, dur)
                        ok_pairs += 1
                    else:
                        # Marca falho mas segue
                        dmat[i][j] = BIG
                        tmat[i][j] = dist = 0
                        if dest_addr not in failed:
                            failed.append(dest_addr)
                        logger.warning(f"Elemento DM não OK {origin} -> {dest_addr}: {st}")
            except Exception as e:
                logger.warning(f"Falha Distance Matrix origem {origin}: {e}")
                failed.extend([m[1] for m in missing if m[1] not in failed])
    DistanceMatrixBuilder.save()
    usable_ratio = ok_pairs/total_pairs if total_pairs else 0
    via_api = usable_ratio >= 0.7 and ok_pairs > 0
    return dmat, tmat, via_api, failed

def tsp_exact(distance_matrix: List[List[float]]) -> List[int]:
    """Held-Karp exato para n<=12."""
    n = len(distance_matrix)
    if n <= 2:
        return list(range(n))
    # DP: dict[(mask,last)] = (cost, prev)
    dp: Dict[Tuple[int,int], Tuple[float,int]] = {}
    for i in range(1, n):
        dp[(1<<i, i)] = (distance_matrix[0][i], 0)
    for mask in range(1, 1<<n):
        if not (mask & 1):
            # garantimos que bit 0 é origem fora das máscaras parciais
            for last in range(1, n):
                if mask & (1<<last):
                    prev_mask = mask ^ (1<<last)
                    if prev_mask == 0:
                        continue
                    best = dp.get((mask, last), (float('inf'), -1))[0]
                    for k in range(1, n):
                        if prev_mask & (1<<k):
                            prev_cost = dp.get((prev_mask, k))
                            if not prev_cost:
                                continue
                            cand = prev_cost[0] + distance_matrix[k][last]
                            if cand < best:
                                dp[(mask, last)] = (cand, k)
                                best = cand
    full_mask = (1<<n) - 1
    # Escolhe melhor fim (não retorna à origem)
    best_end = None
    best_cost = float('inf')
    for last in range(1, n):
        entry = dp.get((full_mask ^ 1, last)) or dp.get((full_mask-1, last)) or dp.get((full_mask, last))
        if not entry:
            continue
        if entry[0] < best_cost:
            best_cost = entry[0]
            best_end = last
    if best_end is None:
        return list(range(n))
    # Reconstrói
    path = [best_end]
    mask = full_mask ^ 1  # remove bit origem
    last = best_end
    while mask:
        entry = dp.get((mask, last))
        if not entry:
            break
        prev = entry[1]
        path.append(prev)
        mask ^= (1<<last)
        last = prev
        if prev == 0:
            break
    path.append(0)
    path.reverse()
    return path

def tsp_heuristic(distance_matrix: List[List[float]]) -> List[int]:
    n = len(distance_matrix)
    if n <= 2:
        return list(range(n))
    unvisited = set(range(1, n))
    path = [0]
    current = 0
    while unvisited:
        nxt = min(unvisited, key=lambda j: distance_matrix[current][j] if distance_matrix[current][j] > 0 else 1e12)
        path.append(nxt)
        unvisited.remove(nxt)
        current = nxt
    # 2-opt melhoria
    improved = True
    def total(p):
        return sum(distance_matrix[p[i]][p[i+1]] for i in range(len(p)-1))
    while improved:
        improved = False
        base = total(path)
        for i in range(1, len(path)-2):
            for j in range(i+1, len(path)-1):
                if j-i == 1:
                    continue
                newp = path[:i] + list(reversed(path[i:j])) + path[j:]
                d = total(newp)
                if d + 1 < base:
                    path = newp
                    base = d
                    improved = True
    return path

def optimize_with_distance_matrix(distance_matrix: List[List[float]]) -> List[int]:
    n = len(distance_matrix)
    if ORTOOLS_AVAILABLE and n <= 25:
        try:
            manager = pywrapcp.RoutingIndexManager(n, 1, 0)
            routing = pywrapcp.RoutingModel(manager)
            def distance_cb(from_index, to_index):
                f = manager.IndexToNode(from_index); t = manager.IndexToNode(to_index)
                return int(distance_matrix[f][t])
            transit_index = routing.RegisterTransitCallback(distance_cb)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_index)
            search_params = pywrapcp.DefaultRoutingSearchParameters()
            search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            search_params.time_limit.FromSeconds(5)
            solution = routing.SolveWithParameters(search_params)
            if solution:
                index = routing.Start(0)
                order = []
                while not routing.IsEnd(index):
                    node = manager.IndexToNode(index)
                    order.append(node)
                    index = solution.Value(routing.NextVar(index))
                # Remove possível retorno à origem duplicado
                if len(order) > 1 and order[-1] == 0:
                    order = order[:-1]
                return order
        except Exception as e:
            logger.warning(f"Falha OR-Tools: {e} - fallback heurístico")
    # Exact DP for small n
    if n <= 12:
        return tsp_exact(distance_matrix)
    return tsp_heuristic(distance_matrix)

async def optimize_and_compute(addresses: List[DeliveryAddress]) -> Tuple[List[DeliveryAddress], float, float, float, float, bool, List[str]]:
    """Produz rota otimizada e estatísticas.

    Retorna (addresses_ordenados, total_km, driving_min, service_min, total_min, via_api)
    via_api=True indica uso Distance Matrix real; False = fallback heurístico/geocoding.
    """
    if len(addresses) <= 1:
        service = len(addresses) * Config.SERVICE_TIME_PER_STOP_MIN
        return addresses, 0.0, 0.0, service, service, False
    dmat, tmat, ok, failed = await build_distance_duration_matrix(addresses)
    if ok:
        order_idx = optimize_with_distance_matrix(dmat)
        ordered = [addresses[i] for i in order_idx]
        # Distância e duração reais
        total_m = 0.0
        total_s = 0.0
        for i in range(len(order_idx)-1):
            a = order_idx[i]; b = order_idx[i+1]
            total_m += dmat[a][b]
            total_s += tmat[a][b]
        # Tempo de serviço (não conta origem coleta)
        service_min = (len(ordered)-1) * Config.SERVICE_TIME_PER_STOP_MIN
        driving_min = total_s / 60.0 if total_s > 0 else (total_m/1000.0)/Config.AVERAGE_SPEED_KMH*60
        total_min = driving_min + service_min
    return ordered, round(total_m/1000.0, 2), round(driving_min, 1), round(service_min,1), round(total_min,1), True, failed
    # Fallback: usar heurística geocoding existente
    ordered = await optimize_route(addresses)
    total_km, driving_min, service_min, total_min = await compute_route_stats(ordered)
    return ordered, total_km, driving_min, service_min, total_min, False, failed

async def compute_route_stats(ordered: List[DeliveryAddress]) -> Tuple[float, float, float, float]:
    """Calcula distância real em km e tempos a partir da rota otimizada.

    Se possuir coordenadas (lat/lng) soma haversine; caso contrário devolve heurística.
    """
    n = len(ordered)
    if n <= 1:
        service = n * Config.SERVICE_TIME_PER_STOP_MIN
        return 0.0, 0.0, service, service
    have_coords = all(a.lat is not None and a.lng is not None for a in ordered)
    if have_coords:
        total_km = 0.0
        for i in range(n-1):
            a, b = ordered[i], ordered[i+1]
            total_km += haversine(a.lat, a.lng, b.lat, b.lng)
        driving_minutes = (total_km / Config.AVERAGE_SPEED_KMH) * 60  # aproximação; poderia usar API de duração
    else:
        total_km = 1.2 * (n - 1)
        driving_minutes = (total_km / Config.AVERAGE_SPEED_KMH) * 60
    service_minutes = n * Config.SERVICE_TIME_PER_STOP_MIN
    total_minutes = driving_minutes + service_minutes
    return round(total_km, 2), round(driving_minutes, 1), round(service_minutes, 1), round(total_minutes, 1)

user_sessions: Dict[int, UserSession] = {}
# Armazena rotas para endpoint /circuit/<id>
circuit_routes: Dict[str, List[str]] = {}
BASE_URL: Optional[str] = None

async def generate_static_map(addresses: List[DeliveryAddress]) -> Optional[bytes]:
    """Gera imagem estática simples usando Google Static Maps (se chave) com marcadores e path.
    Caso sem chave, retorna None (poderíamos implementar Pillow + fundo cinza, mas preferimos falhar silenciosamente).
    """
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key or len(addresses) < 2:
        return None
    # Necessário garantir lat/lng; geocodifica faltantes rapidamente (sequencial para evitar bursts)
    for a in addresses:
        if a.lat is None or a.lng is None:
            coord = await Geocoder.geocode(a.cleaned_address)
            if coord:
                a.lat, a.lng = coord
    have_all = all(a.lat is not None and a.lng is not None for a in addresses)
    if not have_all:
        return None
    # Monta path (limite URL ~ 2k chars; nossa rota <= 20 pontos OK)
    path = 'path=color:0x0000ff|weight:4|' + '|'.join(f"{a.lat},{a.lng}" for a in addresses)
    markers = []
    for i,a in enumerate(addresses):
        color = 'green' if i==0 else ('red' if i==len(addresses)-1 else 'blue')
        label = chr(65+i) if i < 26 else ''
        markers.append(f"color:{color}|label:{label}|{a.lat},{a.lng}")
    marker_params = '&'.join('markers='+m for m in markers)
    base = 'https://maps.googleapis.com/maps/api/staticmap'
    params = f"size=640x640&scale=2&{path}&{marker_params}&key={api_key}"
    url = base + '?' + params
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
            if r.status_code == 200 and r.content.startswith(b'\x89PNG'):
                return r.content
            # 403 ou outro: gera fallback local simples
            logger.warning(f"Static Maps falhou status={r.status_code}; usando fallback local.")
    except Exception as e:
        logger.warning(f"Falha mapa estático remoto: {e}; gerando fallback.")
    # Fallback local com Pillow
    try:
        from PIL import Image, ImageDraw, ImageFont
        from io import BytesIO
        w,h = 1024,1024
        img = Image.new('RGB',(w,h),'white')
        draw = ImageDraw.Draw(img)
        # Normaliza coords para canvas
        lats = [a.lat for a in addresses if a.lat]; lngs=[a.lng for a in addresses if a.lng]
        if not lats or not lngs:
            return None
        minlat,maxlat=min(lats),max(lats); minlng,maxlng=min(lngs),max(lngs)
        def project(lat,lng):
            x = int((lng-minlng)/(maxlng-minlng+1e-9)*(w-80))+40
            y = int((1-(lat-minlat)/(maxlat-minlat+1e-9))*(h-80))+40
            return x,y
        pts=[project(a.lat,a.lng) for a in addresses]
        # Linha da rota
        draw.line(pts, fill=(0,0,255), width=4)
        # Marcadores
        for i,(x,y) in enumerate(pts):
            color = (0,200,0) if i==0 else ((220,0,0) if i==len(pts)-1 else (0,100,255))
            draw.ellipse((x-10,y-10,x+10,y+10), fill=color, outline='black')
            draw.text((x+12,y-8), chr(65+i) if i<26 else str(i+1), fill='black')
        bio = BytesIO()
        img.save(bio, format='PNG')
        bio.seek(0)
        return bio.getvalue()
    except Exception as e:
        logger.warning(f"Fallback Pillow falhou: {e}")
        return None

async def get_session(user_id: int) -> UserSession:
    if user_id not in user_sessions:
        loaded = await DataPersistence.load(user_id)
        if loaded:
            user_sessions[user_id] = loaded
        else:
            user_sessions[user_id] = UserSession(user_id=user_id, photos=[])
    return user_sessions[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        uid = update.effective_user.id if update.effective_user else 0
        logger.info(f"/start recebido de user {uid}")
        if not update.message:
            logger.warning("Update sem message em /start")
            return ConversationHandler.END
        if not await SecurityValidator.rate_limit(uid):
            await update.message.reply_text("⚠️ Limite por hora atingido. Tente depois.")
            return ConversationHandler.END
        user_sessions[uid] = UserSession(user_id=uid, photos=[], processed=False)
        msg = (
            "🚚 Olá! Envie fotos (até 8) com os endereços. Depois clique em Processar."
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📸 Enviar Fotos", callback_data="start_photos")]])
        await update.message.reply_text(msg, reply_markup=kb)
        return BotStates.WAITING_PHOTOS.value
    except Exception as e:
        logger.error(f"Falha em /start: {e}")
        if update and hasattr(update, 'message') and update.message:
            await update.message.reply_text("Erro ao iniciar. Tente novamente em instantes.")
        return ConversationHandler.END

async def start_photos_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "Envie agora suas fotos (JPG/PNG). Quando terminar clique em Processar.")
    return BotStates.WAITING_PHOTOS.value

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    session = await get_session(uid)
    if session.processed:
        await update.message.reply_text("Rota já processada. Use 🚀 Navegar ou /start para nova rota.")
        return BotStates.CONFIRMING_ROUTE.value if session.addresses else BotStates.WAITING_PHOTOS.value
    if len(session.photos) >= Config.MAX_PHOTOS_PER_REQUEST:
        await update.message.reply_text("⚠️ Limite de fotos atingido.")
        return BotStates.WAITING_PHOTOS.value
    fid = update.message.photo[-1].file_id
    session.photos.append(fid)
    await DataPersistence.save(session)
    buttons = []
    if len(session.photos) < Config.MAX_PHOTOS_PER_REQUEST:
        buttons.append([InlineKeyboardButton("➕ Mais fotos", callback_data="start_photos")])
    if len(session.photos) >= 1:
        buttons.append([InlineKeyboardButton("✅ Finalizar fotos", callback_data="process")])
    await update.message.reply_text(
        f"Foto {len(session.photos)}/{Config.MAX_PHOTOS_PER_REQUEST} recebida.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return BotStates.WAITING_PHOTOS.value

async def process_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    session = await get_session(uid)
    if session.processed:
        await q.edit_message_text("Rota já processada. Use os botões existentes abaixo.")
        return BotStates.CONFIRMING_ROUTE.value
    if not session.photos:
        await q.edit_message_text("Envie ao menos 1 foto primeiro.")
        return BotStates.WAITING_PHOTOS.value
    await q.edit_message_text("🔄 Processando fotos (OCR)...")
    raw = await ImageProcessor.ocr(context.bot, session.photos)
    if not raw.strip():
        await q.edit_message_text("Nenhum texto encontrado. Envie fotos mais nítidas.")
        return BotStates.WAITING_PHOTOS.value
    session.raw_text = raw
    session.addresses = extract_addresses(raw)
    if not session.addresses:
        await q.edit_message_text("Nenhum endereço reconhecido. Verifique se aparecem 'Rua', 'Av', etc.")
        return BotStates.WAITING_PHOTOS.value
    # Otimiza rota com Distance Matrix (se disponível) e calcula métricas reais
    optimized_objs, total_km, driving_min, service_min, total_min, via_api, failed_dm = await optimize_and_compute(session.addresses)
    session.optimized_route = [o.cleaned_address for o in optimized_objs]
    session.addresses = optimized_objs
    session.processed = True
    await DataPersistence.save(session)
    # Estatísticas da rota
    total = len(session.addresses)
    primeira = session.addresses[0].cleaned_address
    ultima = session.addresses[-1].cleaned_address

    lista = '\n'.join(f"{i+1:02d}. {a.cleaned_address}" for i, a in enumerate(session.addresses))
    text = (
        "🚀 *Resumo Profissional da Rota*\n"
        f"🔢 Entregas: *{total}*\n"
        f"🧭 Início: {primeira}\n🏁 Fim: {ultima}\n"
    f"📏 Distância {'real' if via_api else 'estimada'}: *{total_km} km*\n"
    f"⏱️ Condução: ~{driving_min} min\n"
    f"📦 Manuseio (@{Config.SERVICE_TIME_PER_STOP_MIN} min/entrega): {service_min} min\n"
    f"⏳ Total estimado: *{total_min} min*\n"
        "\n� *Ordem das Entregas:*\n" + lista +
    ("\n\n✅ Distância calculada via Google Distance Matrix." if via_api else ("\n\n💡 Fallback heurístico (Distance Matrix parcial ou indisponível)." + (f"\n⚠️ Endereços não reconhecidos: {', '.join(failed_dm[:4])}{'...' if len(failed_dm)>4 else ''}" if failed_dm else ""))) +
        "\nEscolha uma ação abaixo:" )
    # Registra rota para deep-link via endpoint HTTP
    route_id = uuid.uuid4().hex[:10]
    circuit_routes[route_id] = [a.cleaned_address for a in session.addresses]
    # Monta URL pública base
    global BASE_URL
    port = int(os.getenv('PORT', 8000))
    host_env = os.getenv('RENDER_EXTERNAL_HOSTNAME')
    if host_env:
        if not host_env.startswith('http'):
            BASE_URL = f"https://{host_env}"
        else:
            BASE_URL = host_env
    else:
        BASE_URL = BASE_URL or f"http://localhost:{port}"
    circuit_http_link = f"{BASE_URL}/circuit/{route_id}"
    # Link completo Google Maps com waypoints
    def build_gmaps_link(addresses: List[str]) -> str:
        if len(addresses) < 2:
            enc = urllib.parse.quote(addresses[0])
            return f"https://www.google.com/maps/search/{enc}"
        origin = urllib.parse.quote(addresses[0])
        destination = urllib.parse.quote(addresses[-1])
        waypoints_list = addresses[1:-1]
        # Limite prático: 23 waypoints (Maps aceita até 25 pontos total). Nosso MAX é 20.
        wp = '|'.join(urllib.parse.quote(w) for w in waypoints_list)
        return f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&travelmode=driving&waypoints={wp}"

    maps_route_link = build_gmaps_link([a.cleaned_address for a in session.addresses])
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Navegar", callback_data="nav_start")],
        [InlineKeyboardButton("📤 Exportar Circuit (CSV)", callback_data="export_circuit")],
        [InlineKeyboardButton("🧭 Google Maps (rota)", url=maps_route_link)],
        [InlineKeyboardButton("🗺️ Mapa imagem", callback_data="map_image")],
        [InlineKeyboardButton("🔗 Abrir no Circuit", url=circuit_http_link)]
    ])
    await q.edit_message_text(text, reply_markup=kb, parse_mode='Markdown')
    session.state = BotStates.CONFIRMING_ROUTE
    return BotStates.CONFIRMING_ROUTE.value

async def export_circuit_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    session = await get_session(uid)
    if not session.addresses:
        await q.edit_message_text("Nenhum endereço para exportar.")
        return BotStates.CONFIRMING_ROUTE.value
    # CSV: ordem, endereço
    lines = ["ordem,endereco"]
    for i, a in enumerate(session.addresses, start=1):
        addr = a.cleaned_address.replace('"', '""')
        lines.append(f'{i},"{addr}"')
    content = '\n'.join(lines)
    from io import BytesIO
    bio = BytesIO(content.encode('utf-8'))
    bio.name = f"rota_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    await q.message.reply_document(
        InputFile(bio),
        caption=("CSV para Circuit gerado.\nNo app Circuit: Import > File Upload (ou Paste) e selecione este CSV.\nColunas: ordem, endereco.")
    )
    # Mantém mensagem original com botões (não edita) – oferece continuidade
    return BotStates.CONFIRMING_ROUTE.value

## Removido callback antigo de link Circuit / Maps

async def map_image_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    session = await get_session(uid)
    if not session.addresses:
        await q.edit_message_text("Rota não encontrada.")
        return BotStates.CONFIRMING_ROUTE.value
    await q.message.reply_text("Gerando mapa…")
    img_bytes = await generate_static_map(session.addresses)
    if not img_bytes:
        await q.message.reply_text("Não foi possível gerar mapa estático (talvez falta GOOGLE_API_KEY ou geocoding incompleto).")
        return BotStates.CONFIRMING_ROUTE.value
    from io import BytesIO
    bio = BytesIO(img_bytes)
    bio.name = 'rota.png'
    await q.message.reply_photo(photo=InputFile(bio), caption="Mapa estimado da rota (sequência otimizada).")
    return BotStates.CONFIRMING_ROUTE.value

async def nav_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    session = await get_session(uid)
    session.state = BotStates.NAVIGATING
    session.current_delivery_index = 0
    return await show_current_stop(q, context, session)

async def show_current_stop(q_or_update, context, session: UserSession) -> int:
    idx = session.current_delivery_index
    total = len(session.optimized_route)
    if idx >= total:
        return await finish_route(q_or_update, context, session)
    addr = session.optimized_route[idx]
    enc = addr.replace(' ', '+').replace(',', '%2C')
    msg = (f"Entrega {idx+1}/{total}\n\n{addr}\n\n"
           f"Concluídas: {idx} | Restantes: {total - idx - 1}")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Maps", url=f"https://www.google.com/maps/search/{enc}"),
         InlineKeyboardButton("Waze", url=f"https://waze.com/ul?q={enc}")],
        [InlineKeyboardButton("✅ Entregue", callback_data="delivered")]
    ])
    if hasattr(q_or_update, 'edit_message_text'):
        await q_or_update.edit_message_text(msg, reply_markup=kb)
    else:
        await q_or_update.message.reply_text(msg, reply_markup=kb)
    return BotStates.NAVIGATING.value

async def delivered_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer("Marcado!")
    uid = q.from_user.id
    session = await get_session(uid)
    if session.current_delivery_index < len(session.optimized_route):
        session.completed_deliveries.append(session.optimized_route[session.current_delivery_index])
        session.current_delivery_index += 1
    await DataPersistence.save(session)
    return await show_current_stop(q, context, session)

async def finish_route(q_or_update, context, session: UserSession) -> int:
    msg = ("🎉 Rota concluída!\n\n" f"Total entregas: {len(session.completed_deliveries)}")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Nova Rota", callback_data="start_photos")]])
    user_sessions[session.user_id] = UserSession(user_id=session.user_id, photos=[])
    if hasattr(q_or_update, 'edit_message_text'):
        await q_or_update.edit_message_text(msg, reply_markup=kb)
    else:
        await q_or_update.message.reply_text(msg, reply_markup=kb)
    return BotStates.WAITING_PHOTOS.value

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envie /start para iniciar uma nova rota.")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    session = await get_session(uid)
    await update.message.reply_text(
        f"Fotos: {len(session.photos)} | Endereços: {len(session.addresses)} | Estado: {session.state.name}"
    )

async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in user_sessions:
        del user_sessions[uid]
    await update.message.reply_text("Sessão cancelada. /start para recomeçar.")
    return ConversationHandler.END

# Alias /cancelar
async def cancelar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await cancel_cmd(update, context)

conflict_counter = 0

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    global conflict_counter
    err_str = str(context.error)
    if 'Conflict: terminated by other getUpdates request' in err_str:
        conflict_counter += 1
        logger.info(f'Conflito 409 detectado ({conflict_counter}). Outra instância ativa.')
        # Após vários conflitos seguidos encerra para liberar recursos
        if conflict_counter >= 6:
            logger.warning('Muitos conflitos 409. Encerrando esta instância para deixar somente a principal em execução.')
            raise SystemExit(0)
        return
    if 'Timed out' in err_str or 'Query is too old' in err_str:
        logger.debug(f"Erro transitório supresso: {err_str}")
        return
    logger.error(f"Erro: {err_str}")
    try:
        if update and hasattr(update, 'effective_message') and update.effective_message:
            await update.effective_message.reply_text("Erro interno. Tente novamente.")
    except Exception:
        pass

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
            return
        if self.path.startswith('/circuit/'):
            route_id = self.path.split('/')[-1]
            addresses = circuit_routes.get(route_id)
            if not addresses:
                self.send_response(404)
                self.end_headers()
                return
            joined = '|'.join(addresses)
            deep = f"circuit://import?stops={urllib.parse.quote(joined)}"
            html = f"""<!DOCTYPE html><html lang='pt-br'><head><meta charset='utf-8'>
<title>Rota Circuit</title>
<meta http-equiv='refresh' content='0;url={deep}'>
<script>window.location='{deep}';setTimeout(()=>{{document.getElementById('fb').style.display='block';}},1500);</script>
<style>body{{font-family:Arial;margin:20px;}}pre{{white-space:pre-wrap;background:#f4f4f4;padding:10px;border-radius:6px;}}</style>
</head><body>
<h3>Abrindo no Circuit...</h3>
<p>Se não abrir automaticamente em alguns segundos use o link ou copie os endereços.</p>
<div id='fb' style='display:none'>
<p><a href='{deep}'>Abrir no Circuit</a></p>
<h4>Endereços</h4>
<pre>{chr(10).join(addresses)}</pre>
</div>
</body></html>"""
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            return
        self.send_response(404)
        self.end_headers()
    def log_message(self, format, *args):
        return

def start_health_server():
    port = int(os.getenv('PORT', 8000))
    try:
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        logger.info(f"Health server na porta {port}")
        return server
    except Exception as e:
        logger.error(f"Erro ao iniciar health server: {e}")
        return None

LOCK_FILE = '/tmp/bot_entregador.lock'

def ensure_single_instance() -> bool:
    """Evita múltiplas instâncias concorrentes em produção criando um arquivo de lock.

    Retorna True se lock obtido ou ambiente sem /tmp (Windows dev). False se já existe outra instância.
    """
    try:
        tmpdir = Path('/tmp')
        if not tmpdir.exists():
            return True
        lock_path = Path(LOCK_FILE)
        
        # Verifica se lock antigo existe e remove se processo não existe mais
        if lock_path.exists():
            try:
                with open(lock_path, 'r') as f:
                    old_pid = int(f.read().strip())
                # Tenta verificar se processo ainda existe
                try:
                    os.kill(old_pid, 0)  # Não mata, só verifica se existe
                    logger.warning(f'Processo {old_pid} ainda ativo. Aguardando...')
                    return False
                except ProcessLookupError:
                    logger.info(f'Lock órfão encontrado (PID {old_pid} morto). Removendo...')
                    lock_path.unlink()
            except (ValueError, FileNotFoundError):
                logger.info('Lock file corrompido. Removendo...')
                lock_path.unlink(missing_ok=True)
        
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, 'w') as f:
            f.write(str(os.getpid()))
        logger.info('Lock de instância adquirido.')
        return True
    except OSError as e:
        if e.errno == errno.EEXIST:
            logger.warning('Outra instância já está rodando (lock file presente). Abortando polling desta instância.')
            return False
        logger.error(f'Falha ao criar lock file: {e}')
        return True

def main():
    logger.info("Iniciando bot simplificado...")
    
    # Limpa lock órfão caso exista de deploy anterior que falhou
    try:
        lock_path = Path('/tmp/bot_entregador.lock')
        if lock_path.exists():
            logger.info("Removendo lock órfão de deploy anterior...")
            lock_path.unlink()
    except Exception as e:
        logger.debug(f"Erro ao limpar lock órfão: {e}")
    
    start_health_server()

    if not ensure_single_instance():
        return

    try:
        builder = Application.builder().token(Config.TELEGRAM_BOT_TOKEN)
        # Define timeouts via builder (evita DeprecationWarning de run_polling)
        # Aumenta timeouts para evitar falha inicial
        builder.get_updates_read_timeout(60)
        builder.get_updates_write_timeout(30)
        builder.get_updates_connect_timeout(60)
        builder.get_updates_pool_timeout(60)
        app = builder.build()

        conv = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                BotStates.WAITING_PHOTOS.value: [
                    MessageHandler(filters.PHOTO, photo_handler),
                    CallbackQueryHandler(start_photos_cb, pattern='^start_photos$'),
                    CallbackQueryHandler(process_cb, pattern='^process$')
                ],
                BotStates.CONFIRMING_ROUTE.value: [
                    CallbackQueryHandler(nav_start_cb, pattern='^nav_start$'),
                    CallbackQueryHandler(process_cb, pattern='^process$'),
                    CallbackQueryHandler(export_circuit_cb, pattern='^export_circuit$'),
                    CallbackQueryHandler(map_image_cb, pattern='^map_image$'),
                    # Callback removido: link Circuit agora é botão URL direto
                ],
                BotStates.NAVIGATING.value: [
                    CallbackQueryHandler(delivered_cb, pattern='^delivered$'),
                    CallbackQueryHandler(start_photos_cb, pattern='^start_photos$')
                ]
            },
            fallbacks=[CommandHandler('cancel', cancel_cmd)],
            per_message=False,  # volta para False para permitir CommandHandler /start sem warning crítico
            per_chat=True,
            per_user=True
        )

        # Registra handlers (mantém apenas uma duplicata /start fora do conv se necessário)
        app.add_handler(conv)
        app.add_handler(CommandHandler('start', start))  # fallback extra caso estado corrompido
        app.add_handler(CommandHandler('help', help_cmd))
        app.add_handler(CommandHandler('status', status_cmd))
        app.add_handler(CommandHandler('cancel', cancel_cmd))
        app.add_handler(CommandHandler('cancelar', cancelar_cmd))
        app.add_error_handler(error_handler)

        logger.info("Bot configurado, iniciando polling...")
        app.run_polling(drop_pending_updates=True, poll_interval=2.0)

    except Exception as e:
        logger.error(f"Erro crítico ao inicializar bot: {e}")
        raise

if __name__ == '__main__':
    main()
