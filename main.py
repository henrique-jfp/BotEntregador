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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

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
                state=BotStates[data.get('state', 'WAITING_PHOTOS')]
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
                json_base64 = json_base64.strip().strip('"').replace('\n', '').replace('\r', '')
                # Corrigir padding se necessário
                missing_padding = len(json_base64) % 4
                if missing_padding:
                    json_base64 += '=' * (4 - missing_padding)
                
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
                    prompt = ("Extraia SOMENTE o texto legível presente na imagem (endereços, linhas). "
                              "Não adicione interpretações. Retorne o texto cru exatamente.")
                    # API espera lista de partes: imagem e texto
                    resp = gemini_model.generate_content([
                        { 'mime_type': 'image/jpeg', 'data': b64 },
                        prompt
                    ])
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
    found = []
    seen = set()
    for line in raw_text.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue
        if ADDRESS_REGEX.search(line_clean.lower()) and len(line_clean) > 8:
            key = line_clean.lower()
            if key not in seen:
                seen.add(key)
                found.append(DeliveryAddress(original_text=line_clean, cleaned_address=line_clean))
    return found[:Config.MAX_ADDRESSES_PER_ROUTE]

def optimize_route(addresses: List[DeliveryAddress]) -> List[str]:
    # Placeholder: mantém ordem original (minimiza mudanças)
    return [a.cleaned_address for a in addresses]

user_sessions: Dict[int, UserSession] = {}

async def get_session(user_id: int) -> UserSession:
    if user_id not in user_sessions:
        loaded = await DataPersistence.load(user_id)
        if loaded:
            user_sessions[user_id] = loaded
        else:
            user_sessions[user_id] = UserSession(user_id=user_id, photos=[])
    return user_sessions[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    if not await SecurityValidator.rate_limit(uid):
        await update.message.reply_text("⚠️ Limite por hora atingido. Tente depois.")
        return ConversationHandler.END
    user_sessions[uid] = UserSession(user_id=uid, photos=[])
    msg = (
        "🚚 Olá! Envie fotos (até 8) com os endereços. Depois clique em Processar."
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📸 Enviar Fotos", callback_data="start_photos")]])
    await update.message.reply_text(msg, reply_markup=kb)
    return BotStates.WAITING_PHOTOS.value

async def start_photos_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "Envie agora suas fotos (JPG/PNG). Quando terminar clique em Processar.")
    return BotStates.WAITING_PHOTOS.value

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    session = await get_session(uid)
    if len(session.photos) >= Config.MAX_PHOTOS_PER_REQUEST:
        await update.message.reply_text("⚠️ Limite de fotos atingido.")
        return BotStates.WAITING_PHOTOS.value
    fid = update.message.photo[-1].file_id
    session.photos.append(fid)
    await DataPersistence.save(session)
    buttons = [[InlineKeyboardButton("✅ Processar", callback_data="process")]]
    if len(session.photos) < Config.MAX_PHOTOS_PER_REQUEST:
        buttons.append([InlineKeyboardButton("➕ Mais fotos", callback_data="start_photos")])
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
    session.optimized_route = optimize_route(session.addresses)
    await DataPersistence.save(session)
    text = "📍 Endereços extraídos:\n" + '\n'.join(
        f"{i+1}. {a.cleaned_address}" for i, a in enumerate(session.addresses)
    )
    text += "\n\nClique em Navegar para iniciar a sequência."
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Navegar", callback_data="nav_start")],
        [InlineKeyboardButton("🔄 Reprocessar", callback_data="process")]
    ])
    await q.edit_message_text(text, reply_markup=kb)
    session.state = BotStates.CONFIRMING_ROUTE
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
        else:
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
    start_health_server()

    if not ensure_single_instance():
        return

    try:
        builder = Application.builder().token(Config.TELEGRAM_BOT_TOKEN)
        # Define timeouts via builder (evita DeprecationWarning de run_polling)
        builder.get_updates_read_timeout(30)
        builder.get_updates_write_timeout(30)
        builder.get_updates_connect_timeout(30)
        builder.get_updates_pool_timeout(30)
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
                    CallbackQueryHandler(process_cb, pattern='^process$')
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

        app.add_handler(conv)
        app.add_handler(CommandHandler('help', help_cmd))
        app.add_handler(CommandHandler('status', status_cmd))
        app.add_handler(CommandHandler('cancel', cancel_cmd))
        app.add_error_handler(error_handler)

        logger.info("Bot configurado, iniciando polling...")
        app.run_polling(drop_pending_updates=True, poll_interval=2.0)

    except Exception as e:
        logger.error(f"Erro crítico ao inicializar bot: {e}")
        raise

if __name__ == '__main__':
    main()
