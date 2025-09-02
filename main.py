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
#!/usr/bin/env python3
"""Bot de Otimização de Rotas - Versão simplificada estável.

Esta versão remove partes incompletas e funcionalidades quebradas (Gemini, Base64)
para colocar o bot online novamente com OCR + extração simples de endereços.
"""

import os
import re
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from dotenv import load_dotenv
from google.cloud import vision
from google.oauth2 import service_account
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
    start_time: datetime = datetime.now()
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
            session = UserSession(
                user_id=user_id,
                photos=data.get('photos', []),
                raw_text=data.get('raw_text', ''),
                addresses=[DeliveryAddress(**a) for a in data.get('addresses', [])],
                optimized_route=data.get('optimized_route', []),
                current_delivery_index=data.get('current_delivery_index', 0),
                start_time=datetime.fromisoformat(data.get('start_time')) if data.get('start_time') else datetime.now(),
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
        json_env = os.getenv('GOOGLE_VISION_CREDENTIALS_JSON')
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        credentials = None
        if json_env:
            info = json.loads(json_env)
            if 'private_key' in info and '\\n' in info['private_key'] and '\n' not in info['private_key']:
                info['private_key'] = info['private_key'].replace('\\n', '\n')
            credentials = service_account.Credentials.from_service_account_info(info)
        elif creds_path and os.path.exists(creds_path):
            credentials = service_account.Credentials.from_service_account_file(creds_path)
        else:
            logger.warning("Credenciais do Vision não encontradas - OCR indisponível")
            return None
        client = vision.ImageAnnotatorClient(credentials=credentials)
        logger.info("Vision client pronto")
        return client
    except Exception as e:
        logger.error(f"Falha configurar Vision: {e}")
        return None

vision_client = setup_vision_client()

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
        if not vision_client:
            return ""
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
                logger.error(f"OCR falhou: {e}")
        return '\n'.join(texts)

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

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Erro: {context.error}")
    try:
        if update and getattr(update, 'effective_message', None):
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
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    logger.info(f"Health server na porta {port}")
    return server

def main():
    logger.info("Iniciando bot simplificado...")
    start_health_server()
    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

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
        fallbacks=[CommandHandler('cancel', cancel_cmd)]
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('status', status_cmd))
    app.add_handler(CommandHandler('cancel', cancel_cmd))
    app.add_error_handler(error_handler)

    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
        
        if not raw_text.strip():
            await context.bot.edit_message_text(
                "❌ **NENHUM TEXTO ENCONTRADO**\n\n"
                "🔍 Não foi possível extrair texto das imagens.\n\n"
                "💡 **Sugestões:**\n"
                "• Tire fotos mais claras\n"
                "• Certifique-se que há texto visível\n"
                "• Evite fotos muito escuras\n\n"
                "👇 Tente novamente:",
                chat_id=query.message.chat_id,
                message_id=processing_msg.message_id,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Tentar Novamente", callback_data="start_photos")
                ]])
            )
            return BotStates.WAITING_PHOTOS.value
        
        session.raw_text = raw_text
        
        # Etapa 2: Análise de endereços
        await context.bot.edit_message_text(
            "🔄 **PROCESSANDO SUAS FOTOS...**\n\n"
            "✅ Extraindo texto das imagens...\n"
            "✅ Analisando endereços com IA...\n"
            "⏳ Otimizando rota...\n\n"
            "📱 *Quase pronto...*",
            chat_id=query.message.chat_id,
            message_id=processing_msg.message_id,
            parse_mode='Markdown'
        )
        
        addresses, extraction_result = await AIProcessor.clean_and_extract_addresses(raw_text)
        
        if not addresses:
            await context.bot.edit_message_text(
                "❌ **NENHUM ENDEREÇO ENCONTRADO**\n\n"
                "🔍 Não foram encontrados endereços válidos nas imagens.\n\n"
                "💡 **Verifique se as fotos contêm:**\n"
                "• Endereços completos de entrega\n"
                "• Texto legível e claro\n"
                "• Informações de apps de delivery\n\n"
                "👇 Tente novamente:",
                chat_id=query.message.chat_id,
                message_id=processing_msg.message_id,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Tentar Novamente", callback_data="start_photos")
                ]])
            )
            return BotStates.WAITING_PHOTOS.value
        
        session.addresses = addresses
        
        # Etapa 3: Otimização de rota
        address_list = [addr.cleaned_address for addr in addresses]
        optimization_result = await AIProcessor.optimize_delivery_route(address_list)
        session.optimized_route = optimization_result['optimized_route']
        
        # Salvar progresso
        await DataPersistence.save_user_session(session)
        
        # Apresentar resultado
        return await present_optimized_route(query, context, session, optimization_result)
        
    except Exception as e:
        logger.error(f"Erro durante processamento: {e}")
        await context.bot.edit_message_text(
            "❌ **ERRO NO PROCESSAMENTO**\n\n"
            f"⚠️ Ocorreu um erro: {str(e)[:100]}...\n\n"
            "🔄 Tente novamente em alguns segundos.",
            chat_id=query.message.chat_id,
            message_id=processing_msg.message_id,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Tentar Novamente", callback_data="process_photos")
            ]])
        )
        return BotStates.PROCESSING.value

async def present_optimized_route(query, context, session: UserSession, optimization_result: Dict) -> int:
    """Apresentar rota otimizada para confirmação."""
    session.state = BotStates.CONFIRMING_ROUTE
    
    # Construir mensagem de resultado
    route_text = "📍 **ROTA OTIMIZADA PRONTA!**\n\n"
    
    # Estatísticas
    route_text += f"🚚 **Estatísticas:**\n"
    route_text += f"📍 Entregas: {len(session.optimized_route)}\n"
    route_text += f"📏 Distância estimada: {optimization_result.get('estimated_distance_km', 0):.1f} km\n"
    route_text += f"⏱️ Tempo estimado: {optimization_result.get('estimated_time_minutes', 0)} min\n"
    route_text += f"⛽ Economia: {optimization_result.get('fuel_savings_percentage', 0)}% combustível\n\n"
    
    # Lista de entregas
    route_text += "📋 **SEQUÊNCIA DE ENTREGAS:**\n"
    for i, address in enumerate(session.optimized_route, 1):
        # Truncar endereço se muito longo
        display_address = address[:60] + "..." if len(address) > 60 else address
        route_text += f"{i}️⃣ {display_address}\n"
    
    route_text += f"\n💡 {optimization_result.get('optimization_notes', '')}"
    
    # Botões de ação
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Começar Navegação", callback_data="start_navigation")],
        [InlineKeyboardButton("🔄 Re-otimizar Rota", callback_data="reoptimize_route")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_session")]
    ])
    
    await context.bot.edit_message_text(
        route_text,
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    return BotStates.CONFIRMING_ROUTE.value

async def start_navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Iniciar navegação da rota."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    session = await get_user_session(user_id)
    session.state = BotStates.NAVIGATING
    session.current_delivery_index = 0
    
    # Salvar progresso
    await DataPersistence.save_user_session(session)
    
    return await show_current_delivery(query, context, session)

async def show_current_delivery(query_or_update, context, session: UserSession) -> int:
    """Mostrar entrega atual com navegação."""
    current_index = session.current_delivery_index
    total_deliveries = len(session.optimized_route)
    
    if current_index >= total_deliveries:
        return await complete_navigation(query_or_update, context, session)
    
    current_address = session.optimized_route[current_index]
    
    # Construir mensagem
    nav_text = f"🎯 **PRÓXIMA ENTREGA ({current_index + 1} de {total_deliveries})**\n\n"
    nav_text += f"📍 **Endereço:**\n{current_address}\n\n"
    
    # Status geral
    nav_text += f"📊 **STATUS:**\n"
    nav_text += f"✅ Concluídas: {current_index}\n"
    nav_text += f"📍 Atual: {current_index + 1}\n"
    nav_text += f"⏳ Restantes: {total_deliveries - current_index - 1}\n\n"
    
    # Links de navegação
    nav_text += "🗺️ **NAVEGAÇÃO:**\n"
    
    # Preparar endereço para URLs
    encoded_address = current_address.replace(' ', '+').replace(',', '%2C')
    
    # Botões de navegação
    nav_buttons = [
        [
            InlineKeyboardButton("📱 Waze", url=f"https://waze.com/ul?q={encoded_address}"),
            InlineKeyboardButton("🗺️ Google Maps", url=f"https://www.google.com/maps/search/{encoded_address}")
        ],
        [InlineKeyboardButton("✅ Entrega Concluída", callback_data="delivery_completed")],
        [
            InlineKeyboardButton("⏸️ Pausar", callback_data="pause_navigation"),
            InlineKeyboardButton("🆘 Problema", callback_data="report_problem")
        ]
    ]
    
    keyboard = InlineKeyboardMarkup(nav_buttons)
    
    # Editar ou enviar mensagem
    if hasattr(query_or_update, 'edit_message_text'):
        await query_or_update.edit_message_text(
            nav_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    else:
        await query_or_update.message.reply_text(
            nav_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    return BotStates.NAVIGATING.value

async def delivery_completed_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Marcar entrega como concluída."""
    query = update.callback_query
    await query.answer("✅ Entrega marcada como concluída!")
    
    user_id = query.from_user.id
    session = await get_user_session(user_id)
    
    # Marcar entrega atual como concluída
    current_address = session.optimized_route[session.current_delivery_index]
    session.completed_deliveries.append(current_address)
    session.current_delivery_index += 1
    
    # Salvar progresso
    await DataPersistence.save_user_session(session)
    
    return await show_current_delivery(query, context, session)

async def complete_navigation(query_or_update, context, session: UserSession) -> int:
    """Finalizar navegação - todas as entregas concluídas."""
    session.state = BotStates.WAITING_PHOTOS
    
    # Calcular estatísticas finais
    total_time = datetime.now() - session.start_time
    total_deliveries = len(session.completed_deliveries)
    
    completion_text = "🎉 **PARABÉNS! TODAS AS ENTREGAS CONCLUÍDAS!**\n\n"
    completion_text += f"📈 **RELATÓRIO FINAL:**\n"
    completion_text += f"✅ Entregas realizadas: {total_deliveries}\n"
    completion_text += f"⏱️ Tempo total: {total_time.seconds // 60} minutos\n"
    completion_text += f"📍 Rota otimizada utilizada\n\n"
    completion_text += "🎯 **Benefícios conquistados:**\n"
    completion_text += "• Economia de combustível\n"
    completion_text += "• Redução de tempo\n"
    completion_text += "• Maximização de entregas\n\n"
    completion_text += "🚚 **Pronto para uma nova rota?**"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Nova Rota", callback_data="start_photos")],
        [InlineKeyboardButton("📊 Ver Histórico", callback_data="show_history")]
    ])
    
    # Limpar sessão para nova rota
    user_sessions[session.user_id] = UserSession(user_id=session.user_id)
    
    if hasattr(query_or_update, 'edit_message_text'):
        await query_or_update.edit_message_text(
            completion_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    else:
        await query_or_update.message.reply_text(
            completion_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    return BotStates.WAITING_PHOTOS.value

# ==================== COMANDOS ADMINISTRATIVOS ====================

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando de ajuda."""
    help_text = """
🤖 **BOT DE OTIMIZAÇÃO DE ROTAS - MANUAL**

🚀 **Comandos Principais:**
• `/start` - Iniciar nova sessão
• `/help` - Este manual
• `/cancel` - Cancelar operação atual
• `/status` - Ver status atual

📸 **Como Usar:**
1. Envie fotos do seu roteiro
2. Aguarde a IA processar
3. Confirme a rota otimizada
4. Navegue com GPS integrado

⚡ **Recursos:**
• OCR inteligente
• Otimização por IA
• Navegação GPS
• Economia de combustível

🔧 **Suporte:**
• Máximo 8 fotos por sessão
• Formatos: JPG, PNG, WEBP
• Tamanho máximo: 20MB/foto

📱 **Apps Suportados:**
• iFood, Rappi, Uber Eats
• Qualquer app com endereços
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostrar status atual do usuário."""
    user_id = update.effective_user.id
    session = await get_user_session(user_id)
    
    status_text = f"📊 **STATUS ATUAL**\n\n"
    status_text += f"👤 Usuário: {user_id}\n"
    status_text += f"🔄 Estado: {session.state.name}\n"
    status_text += f"📸 Fotos enviadas: {len(session.photos)}\n"
    status_text += f"📍 Endereços encontrados: {len(session.addresses)}\n"
    status_text += f"🗺️ Entregas na rota: {len(session.optimized_route)}\n"
    status_text += f"✅ Entregas concluídas: {len(session.completed_deliveries)}\n"
    
    if session.start_time:
        elapsed = datetime.now() - session.start_time
        status_text += f"⏱️ Tempo de sessão: {elapsed.seconds // 60} min\n"
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancelar operação atual."""
    user_id = update.effective_user.id
    
    # Limpar sessão
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await update.message.reply_text(
        "❌ **Operação cancelada!**\n\n"
        "🔄 Sua sessão foi reiniciada.\n"
        "Use /start para começar novamente.",
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END

# ==================== TRATAMENTO DE ERROS ====================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler global de erros."""
    logger.error(f"Exceção durante atualização: {context.error}")
    
    if update and hasattr(update, 'effective_message'):
        try:
            await update.effective_message.reply_text(
                "⚠️ **Erro interno do bot**\n\n"
                "🔧 Algo deu errado, mas já estamos cientes.\n"
                "🔄 Tente novamente em alguns segundos.\n\n"
                "Se o problema persistir, use /cancel e /start",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem de erro: {e}")

# ==================== SERVIDOR HTTP PARA RENDER ====================

class HealthHandler(BaseHTTPRequestHandler):
    """Handler para health checks do Render."""
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            status = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'version': '2.0'
            }
            
            self.wfile.write(json.dumps(status).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suprimir logs do servidor HTTP."""
        pass

def start_health_server():
    """Iniciar servidor de health check."""
    port = int(os.getenv('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    
    def run_server():
        logger.info(f"Servidor de health check iniciado na porta {port}")
        server.serve_forever()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return server

# ==================== CONFIGURAÇÃO PRINCIPAL DO BOT ====================

def main():
    """Função principal do bot."""
    logger.info("🚀 Iniciando Bot de Otimização de Rotas v2.0")
    
    # Validar configurações
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.error("Token do Telegram não encontrado!")
        return
    
    # Iniciar servidor de health check
    health_server = start_health_server()
    
    try:
        # Criar aplicação
        app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        
        # Configurar conversation handler
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', start_command),
                CallbackQueryHandler(start_photos_callback, pattern='^start_photos$')
            ],
            states={
                BotStates.WAITING_PHOTOS.value: [
                    MessageHandler(filters.PHOTO, handle_photo_upload),
                    CallbackQueryHandler(start_photos_callback, pattern='^start_photos$'),
                    CallbackQueryHandler(start_photos_callback, pattern='^add_more_photos$'),
                    CallbackQueryHandler(process_photos_callback, pattern='^process_photos$')
                ],
                BotStates.PROCESSING.value: [
                    CallbackQueryHandler(process_photos_callback, pattern='^process_photos$')
                ],
                BotStates.CONFIRMING_ROUTE.value: [
                    CallbackQueryHandler(start_navigation_callback, pattern='^start_navigation$'),
                    CallbackQueryHandler(process_photos_callback, pattern='^reoptimize_route$'),
                    CallbackQueryHandler(cmd_cancel, pattern='^cancel_session$')
                ],
                BotStates.NAVIGATING.value: [
                    CallbackQueryHandler(delivery_completed_callback, pattern='^delivery_completed$'),
                    CallbackQueryHandler(start_photos_callback, pattern='^pause_navigation$'),
                ]
            },
            fallbacks=[
                CommandHandler('cancel', cmd_cancel),
                CommandHandler('start', start_command)
            ],
            per_message=False,
            per_chat=True,
            per_user=True
        )
        
        # Adicionar handlers
        app.add_handler(conv_handler)
        app.add_handler(CommandHandler('help', cmd_help))
        app.add_handler(CommandHandler('status', cmd_status))
        
        # Handler de erro global
        app.add_error_handler(error_handler)
        
        # Iniciar bot
        logger.info("✅ Bot configurado com sucesso!")
        logger.info("🤖 Iniciando polling...")
        
        # Executar bot
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except KeyboardInterrupt:
        logger.info("Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro fatal do bot: {e}")
    finally:
        if 'health_server' in locals():
            health_server.shutdown()
        logger.info("🔴 Bot finalizado")

if __name__ == '__main__':
    main()
