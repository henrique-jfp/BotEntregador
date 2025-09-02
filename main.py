#!/usr/bin/env python3
"""
🚀 BOT DE OTIMIZAÇÃO DE ROTAS - TELEGRAM
Versão: 2.0 - Profissional

Desenvolvido para auxiliar entregadores a otimizar suas rotas diárias
através de inteligência artificial, OCR e navegação GPS integrada.

Author: GitHub Copilot
Date: 2025-09-02
"""

import os
import re
import json
import logging
import asyncio
import aiohttp
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Telegram imports
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from telegram.error import NetworkError, TimedOut, BadRequest

# Google Cloud imports
from google.cloud import vision
from google.oauth2 import service_account
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Image processing
from PIL import Image
import io

# Environment and utilities
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==================== CONFIGURAÇÃO DE LOGGING ====================
def setup_logging() -> logging.Logger:
    """Configuração avançada de logging com múltiplos handlers."""
    
    # Criar diretório de logs se não existir
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configuração do logger principal
    logger = logging.getLogger('bot_delivery')
    logger.setLevel(logging.INFO)
    
    # Remover handlers existentes para evitar duplicação
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Formatter padrão
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para arquivo geral
    file_handler = logging.FileHandler(logs_dir / 'bot.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Handler para erros
    error_handler = logging.FileHandler(logs_dir / 'errors.log', encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger

# Inicializar logger
logger = setup_logging()

# ==================== ESTADOS E ESTRUTURAS DE DADOS ====================

class BotStates(Enum):
    """Estados da máquina de estados do bot."""
    WAITING_PHOTOS = 1
    PROCESSING = 2
    CONFIRMING_ROUTE = 3
    NAVIGATING = 4
    PAUSED = 5

@dataclass
class DeliveryAddress:
    """Estrutura de dados para um endereço de entrega."""
    original_text: str
    cleaned_address: str
    confidence: float
    delivery_index: Optional[int] = None
    completed: bool = False
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None

@dataclass
class UserSession:
    """Estrutura de dados para sessão do usuário."""
    user_id: int
    photos: List[str] = None  # file_ids
    raw_text: str = ""
    addresses: List[DeliveryAddress] = None
    optimized_route: List[str] = None
    current_delivery_index: int = 0
    start_time: Optional[datetime] = None
    completed_deliveries: List[str] = None
    state: BotStates = BotStates.WAITING_PHOTOS
    
    def __post_init__(self):
        if self.photos is None:
            self.photos = []
        if self.addresses is None:
            self.addresses = []
        if self.completed_deliveries is None:
            self.completed_deliveries = []
        if self.start_time is None:
            self.start_time = datetime.now()

# ==================== CONFIGURAÇÕES E CONSTANTES ====================

class Config:
    """Configurações do bot."""
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    MAX_PHOTOS_PER_REQUEST = int(os.getenv('MAX_PHOTOS_PER_REQUEST', '8'))
    MAX_ADDRESSES_PER_ROUTE = int(os.getenv('MAX_ADDRESSES_PER_ROUTE', '20'))
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
    MAX_IMAGE_SIZE_MB = 20
    RATE_LIMIT_PER_HOUR = 50
    
    # Rate limiting storage
    user_requests: Dict[int, List[datetime]] = {}

# Validar configurações obrigatórias
if not Config.TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN não encontrado nas variáveis de ambiente")

# Configurar Gemini
if Config.GOOGLE_API_KEY:
    genai.configure(api_key=Config.GOOGLE_API_KEY)
else:
    logger.warning("GOOGLE_API_KEY não encontrado - funcionalidades de IA limitadas")

# ==================== SISTEMA DE PERSISTÊNCIA ====================

class DataPersistence:
    """Sistema de persistência de dados."""
    
    DATA_DIR = Path("user_data")
    
    @classmethod
    def ensure_data_dir(cls):
        """Garantir que o diretório de dados existe."""
        cls.DATA_DIR.mkdir(exist_ok=True)
    
    @classmethod
    async def save_user_session(cls, session: UserSession) -> bool:
        """Salvar sessão do usuário."""
        try:
            cls.ensure_data_dir()
            file_path = cls.DATA_DIR / f"user_{session.user_id}.json"
            
            # Converter dataclass para dict, tratando objetos não serializáveis
            session_dict = asdict(session)
            
            # Converter datetime para string
            if session_dict['start_time']:
                session_dict['start_time'] = session_dict['start_time'].isoformat()
            
            # Tratar endereços
            for addr in session_dict['addresses']:
                if addr['start_time']:
                    addr['start_time'] = addr['start_time'].isoformat()
                if addr['completion_time']:
                    addr['completion_time'] = addr['completion_time'].isoformat()
            
            # Converter enum para string
            session_dict['state'] = session.state.name
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(session_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Sessão salva para usuário {session.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar sessão do usuário {session.user_id}: {e}")
            return False
    
    @classmethod
    async def load_user_session(cls, user_id: int) -> Optional[UserSession]:
        """Carregar sessão do usuário."""
        try:
            cls.ensure_data_dir()
            file_path = cls.DATA_DIR / f"user_{user_id}.json"
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                session_dict = json.load(f)
            
            # Converter string para datetime
            if session_dict['start_time']:
                session_dict['start_time'] = datetime.fromisoformat(session_dict['start_time'])
            
            # Tratar endereços
            addresses = []
            for addr_data in session_dict['addresses']:
                if addr_data['start_time']:
                    addr_data['start_time'] = datetime.fromisoformat(addr_data['start_time'])
                if addr_data['completion_time']:
                    addr_data['completion_time'] = datetime.fromisoformat(addr_data['completion_time'])
                
                addresses.append(DeliveryAddress(**addr_data))
            
            session_dict['addresses'] = addresses
            
            # Converter string para enum
            session_dict['state'] = BotStates[session_dict['state']]
            
            session = UserSession(**session_dict)
            logger.info(f"Sessão carregada para usuário {user_id}")
            return session
            
        except Exception as e:
            logger.error(f"Erro ao carregar sessão do usuário {user_id}: {e}")
            return None

# ==================== UTILITÁRIOS E VALIDAÇÕES ====================

class SecurityValidator:
    """Validações de segurança."""
    
    @staticmethod
    async def validate_image_safety(image_bytes: bytes) -> bool:
        """Verificar se imagem não contém conteúdo malicioso."""
        try:
            # Verificar se é uma imagem válida
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Verificar formato
                if img.format not in ['JPEG', 'PNG', 'WEBP']:
                    return False
                
                # Verificar tamanho
                if len(image_bytes) > Config.MAX_IMAGE_SIZE_MB * 1024 * 1024:
                    return False
                
                # Verificar dimensões razoáveis
                width, height = img.size
                if width * height > 50_000_000:  # 50MP max
                    return False
                
                return True
                
        except Exception as e:
            logger.error(f"Erro na validação de imagem: {e}")
            return False
    
    @staticmethod
    async def rate_limit_check(user_id: int) -> bool:
        """Verificar limite de requisições por usuário."""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Inicializar se necessário
        if user_id not in Config.user_requests:
            Config.user_requests[user_id] = []
        
        # Limpar requisições antigas
        Config.user_requests[user_id] = [
            req_time for req_time in Config.user_requests[user_id]
            if req_time > hour_ago
        ]
        
        # Verificar limite
        if len(Config.user_requests[user_id]) >= Config.RATE_LIMIT_PER_HOUR:
            return False
        
        # Registrar nova requisição
        Config.user_requests[user_id].append(now)
        return True

# ==================== GOOGLE CLOUD VISION SETUP ====================

def setup_vision_client():
    """Configurar cliente do Google Cloud Vision."""
    try:
        # Tentar carregar credenciais de diferentes formas
        json_env = os.getenv('GOOGLE_VISION_CREDENTIALS_JSON')
        json_b64 = os.getenv('GOOGLE_VISION_CREDENTIALS_JSON_BASE64')
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if json_b64:
            # Decodificar Base64
            decoded = base64.b64decode(json_b64).decode('utf-8')
            creds_info = json.loads(decoded)
            
            # Corrigir private_key se necessário
            if 'private_key' in creds_info:
                private_key = creds_info['private_key']
                if '\\n' in private_key and '\n' not in private_key:
                    creds_info['private_key'] = private_key.replace('\\n', '\n')
            
            credentials = service_account.Credentials.from_service_account_info(creds_info)
            
        elif json_env:
            creds_info = json.loads(json_env)
            credentials = service_account.Credentials.from_service_account_info(creds_info)
            
        elif creds_path and os.path.exists(creds_path):
            credentials = service_account.Credentials.from_service_account_file(creds_path)
            
        else:
            logger.warning("Credenciais do Google Cloud Vision não encontradas")
            return None
        
        client = vision.ImageAnnotatorClient(credentials=credentials)
        logger.info("Cliente Google Cloud Vision configurado com sucesso")
        return client
        
    except Exception as e:
        logger.error(f"Erro ao configurar Google Cloud Vision: {e}")
        return None

# Inicializar cliente Vision
vision_client = setup_vision_client()

# ==================== PROCESSAMENTO DE IMAGENS E OCR ====================

class ImageProcessor:
    """Processador de imagens e OCR."""
    
    @staticmethod
    async def download_telegram_image(bot, file_id: str) -> Optional[bytes]:
        """Download assíncrono de imagem do Telegram."""
        try:
            file = await bot.get_file(file_id)
            file_bytes = await file.download_as_bytearray()
            return bytes(file_bytes)
        except Exception as e:
            logger.error(f"Erro ao baixar imagem {file_id}: {e}")
            return None
    
    @staticmethod
    async def extract_text_from_images(bot, photo_files: List[str]) -> Tuple[str, float]:
        """Extração de texto com Google Vision API."""
        if not vision_client:
            logger.error("Cliente Google Vision não disponível")
            return "", 0.0
        
        all_text = []
        total_confidence = 0.0
        processed_images = 0
        
        try:
            for file_id in photo_files:
                logger.info(f"Processando imagem: {file_id}")
                
                # Download da imagem
                image_bytes = await ImageProcessor.download_telegram_image(bot, file_id)
                if not image_bytes:
                    continue
                
                # Validação de segurança
                if not await SecurityValidator.validate_image_safety(image_bytes):
                    logger.warning(f"Imagem {file_id} falhou na validação de segurança")
                    continue
                
                # Processamento OCR
                image = vision.Image(content=image_bytes)
                response = vision_client.text_detection(image=image)
                
                if response.error.message:
                    logger.error(f"Erro do Google Vision: {response.error.message}")
                    continue
                
                # Extrair texto
                texts = response.text_annotations
                if texts:
                    detected_text = texts[0].description
                    confidence = sum(
                        vertex.confidence if hasattr(vertex, 'confidence') else 0.8
                        for vertex in texts
                    ) / len(texts)
                    
                    if confidence > 0.7:  # Apenas textos com alta confiança
                        all_text.append(detected_text)
                        total_confidence += confidence
                        processed_images += 1
                        
                        logger.info(f"Texto extraído da imagem {file_id} (confidence: {confidence:.2f})")
                
        except Exception as e:
            logger.error(f"Erro durante extração de texto: {e}")
        
        # Calcular confiança média
        avg_confidence = total_confidence / processed_images if processed_images > 0 else 0.0
        combined_text = "\n\n".join(all_text)
        
        logger.info(f"OCR completo: {processed_images} imagens processadas, confiança média: {avg_confidence:.2f}")
        return combined_text, avg_confidence

# ==================== INTELIGÊNCIA ARTIFICIAL - GEMINI ====================

class AIProcessor:
    """Processador de IA usando Gemini Pro."""
    
    @staticmethod
    def get_gemini_model():
        """Obter modelo Gemini configurado."""
        try:
            model = genai.GenerativeModel(
                'gemini-pro',
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )
            return model
        except Exception as e:
            logger.error(f"Erro ao configurar modelo Gemini: {e}")
            return None
    
    @staticmethod
    async def clean_and_extract_addresses(raw_text: str) -> Tuple[List[DeliveryAddress], Dict]:
        """Limpeza inteligente e extração de endereços."""
        if not Config.GOOGLE_API_KEY:
            logger.warning("Google API Key não disponível - usando regex simples")
            return AIProcessor._fallback_address_extraction(raw_text)
        
        model = AIProcessor.get_gemini_model()
        if not model:
            return AIProcessor._fallback_address_extraction(raw_text)
        
        prompt = f"""
Você é um especialista em logística brasileira. Analise o texto abaixo extraído de screenshots de aplicativos de entrega (iFood, Rappi, Uber Eats, etc.).

TAREFA:
1. Identifique APENAS endereços completos de entrega
2. Ignore: nomes de clientes, valores, instruções de entrega, números de pedido
3. Padronize o formato: "Rua/Av Nome, Número, Bairro, Cidade - UF"
4. Valide se o endereço está completo e faz sentido
5. Remova duplicatas

FORMATO DE SAÍDA (JSON):
{{
    "addresses": [
        "Rua das Flores, 123, Centro, São Paulo - SP",
        "Avenida Paulista, 456, Bela Vista, São Paulo - SP"
    ],
    "confidence": 0.95,
    "rejected_entries": ["texto inválido encontrado"]
}}

TEXTO A ANALISAR:
{raw_text[:3000]}
"""

        try:
            response = model.generate_content(prompt)
            result_text = response.text
            
            # Extrair JSON da resposta
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = result_text[json_start:json_end]
                result = json.loads(json_text)
                
                addresses = []
                for addr_text in result.get('addresses', []):
                    address = DeliveryAddress(
                        original_text=addr_text,
                        cleaned_address=addr_text,
                        confidence=result.get('confidence', 0.8)
                    )
                    addresses.append(address)
                
                logger.info(f"IA extraiu {len(addresses)} endereços com confiança {result.get('confidence', 0):.2f}")
                return addresses, result
            else:
                logger.error("Resposta da IA não contém JSON válido")
                return AIProcessor._fallback_address_extraction(raw_text)
                
        except Exception as e:
            logger.error(f"Erro na extração de endereços com IA: {e}")
            return AIProcessor._fallback_address_extraction(raw_text)
    
    @staticmethod
    def _fallback_address_extraction(raw_text: str) -> Tuple[List[DeliveryAddress], Dict]:
        """Extração de endereços usando regex como fallback."""
        address_patterns = [
            r'(?:rua?|r\.|av\.?|avenida|praça|alameda|travessa|tv\.|gen\.)\s+[^,\n]+(?:,\s*\d+)?[^,\n]*(?:,\s*[^,\n]+)*',
            r'[^,\n]*(?:rua|av\.?|avenida|praça|alameda|travessa|tv\.|r\.|gen\.)[^,\n]*\d+[^,\n]*'
        ]
        
        addresses = []
        found_addresses = set()
        
        for pattern in address_patterns:
            matches = re.findall(pattern, raw_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                cleaned = match.strip()
                if len(cleaned) > 10 and cleaned.lower() not in found_addresses:
                    address = DeliveryAddress(
                        original_text=cleaned,
                        cleaned_address=cleaned,
                        confidence=0.7
                    )
                    addresses.append(address)
                    found_addresses.add(cleaned.lower())
        
        result = {
            "addresses": [addr.cleaned_address for addr in addresses],
            "confidence": 0.7,
            "rejected_entries": []
        }
        
        logger.info(f"Regex extraiu {len(addresses)} endereços")
        return addresses, result
    
    @staticmethod
    async def optimize_delivery_route(addresses: List[str]) -> Dict:
        """Otimização de rota usando IA."""
        if not Config.GOOGLE_API_KEY or len(addresses) <= 1:
            return {
                "optimized_route": addresses,
                "estimated_distance_km": 0,
                "estimated_time_minutes": 0,
                "optimization_notes": "Otimização não necessária ou IA indisponível",
                "fuel_savings_percentage": 0
            }
        
        model = AIProcessor.get_gemini_model()
        if not model:
            return {"optimized_route": addresses, "estimated_distance_km": 0, "estimated_time_minutes": 0, "optimization_notes": "IA indisponível", "fuel_savings_percentage": 0}
        
        prompt = f"""
Você é um especialista em otimização de rotas com 15 anos de experiência em logística urbana brasileira.

CONTEXTO: Otimizar rota de entregas para minimizar:
- Distância total percorrida
- Tempo em trânsito
- Consumo de combustível
- Considerar trânsito típico brasileiro

REGRAS:
1. NUNCA altere, adicione ou remova endereços
2. Considere proximidade geográfica
3. Evite voltas desnecessárias
4. Priorize fluxo de trânsito unidirecional quando possível

DADOS:
Endereços: {json.dumps(addresses, ensure_ascii=False)}

RETORNO (JSON):
{{
    "optimized_route": ["endereço1", "endereço2", ...],
    "estimated_distance_km": 25.3,
    "estimated_time_minutes": 180,
    "optimization_notes": "Rota otimizada considerando...",
    "fuel_savings_percentage": 23
}}
"""

        try:
            response = model.generate_content(prompt)
            result_text = response.text
            
            # Extrair JSON da resposta
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = result_text[json_start:json_end]
                result = json.loads(json_text)
                
                # Validar que todos os endereços estão presentes
                if len(result.get('optimized_route', [])) == len(addresses):
                    logger.info("Rota otimizada com sucesso pela IA")
                    return result
            
            # Fallback se a IA falhar
            logger.warning("IA falhou na otimização - usando ordem original")
            return {
                "optimized_route": addresses,
                "estimated_distance_km": len(addresses) * 3.5,
                "estimated_time_minutes": len(addresses) * 25,
                "optimization_notes": "Ordem original mantida (IA indisponível)",
                "fuel_savings_percentage": 0
            }
            
        except Exception as e:
            logger.error(f"Erro na otimização de rota: {e}")
            return {
                "optimized_route": addresses,
                "estimated_distance_km": len(addresses) * 3.5,
                "estimated_time_minutes": len(addresses) * 25,
                "optimization_notes": f"Erro na otimização: {str(e)}",
                "fuel_savings_percentage": 0
            }

# ==================== HANDLERS DO BOT ====================

# Dicionário global para sessões de usuários
user_sessions: Dict[int, UserSession] = {}

async def get_user_session(user_id: int) -> UserSession:
    """Obter ou criar sessão do usuário."""
    if user_id not in user_sessions:
        # Tentar carregar sessão salva
        saved_session = await DataPersistence.load_user_session(user_id)
        if saved_session:
            user_sessions[user_id] = saved_session
        else:
            user_sessions[user_id] = UserSession(user_id=user_id)
    
    return user_sessions[user_id]

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Comando /start - Ponto de entrada."""
    user_id = update.effective_user.id
    logger.info(f"Usuário {user_id} iniciou o bot")
    
    # Verificar rate limiting
    if not await SecurityValidator.rate_limit_check(user_id):
        await update.message.reply_text(
            "⚠️ Limite de requisições atingido. Tente novamente em 1 hora."
        )
        return ConversationHandler.END
    
    # Criar nova sessão
    user_sessions[user_id] = UserSession(user_id=user_id)
    
    welcome_message = """
🚚 **Olá, entregador! Pronto para otimizar suas rotas hoje?**

🎯 **Como funciona:**
1️⃣ Envie fotos do seu roteiro de entregas
2️⃣ Aguarde a IA extrair os endereços
3️⃣ Receba sua rota otimizada
4️⃣ Navegue com GPS integrado

📱 **Suporta:** iFood, Rappi, Uber Eats e outros apps

⚡ **Vantagens:**
• Economia de combustível
• Menos tempo no trânsito
• Mais entregas por dia
• Navegação passo a passo

👇 **Clique no botão abaixo para começar!**
"""
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📸 Enviar Fotos do Roteiro", callback_data="start_photos")
    ]])
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    return BotStates.WAITING_PHOTOS.value

async def start_photos_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Callback para iniciar envio de fotos."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    session = await get_user_session(user_id)
    session.state = BotStates.WAITING_PHOTOS
    
    await query.edit_message_text(
        "📸 **ENVIO DE FOTOS**\n\n"
        "🔹 Envie até 8 fotos do seu roteiro de entregas\n"
        "🔹 Formatos aceitos: JPG, PNG, WEBP\n"
        "🔹 Tamanho máximo: 20MB por foto\n\n"
        "💡 **Dica:** Tire fotos claras dos endereços para melhor resultado!",
        parse_mode='Markdown'
    )
    
    return BotStates.WAITING_PHOTOS.value

async def handle_photo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler para recebimento de fotos."""
    user_id = update.effective_user.id
    session = await get_user_session(user_id)
    
    # Verificar se ainda pode receber fotos
    if len(session.photos) >= Config.MAX_PHOTOS_PER_REQUEST:
        await update.message.reply_text(
            f"⚠️ Limite de {Config.MAX_PHOTOS_PER_REQUEST} fotos atingido. Use o botão 'Processar Fotos' para continuar."
        )
        return BotStates.WAITING_PHOTOS.value
    
    # Obter maior resolução disponível
    photo = update.message.photo[-1]
    session.photos.append(photo.file_id)
    
    # Salvar progresso
    await DataPersistence.save_user_session(session)
    
    # Criar botões dinâmicos
    buttons = []
    if len(session.photos) >= 1:
        buttons.append([InlineKeyboardButton("✅ Processar Fotos", callback_data="process_photos")])
    
    if len(session.photos) < Config.MAX_PHOTOS_PER_REQUEST:
        buttons.append([InlineKeyboardButton("📸 Enviar Mais Fotos", callback_data="add_more_photos")])
    
    keyboard = InlineKeyboardMarkup(buttons)
    
    await update.message.reply_text(
        f"📸 **Foto {len(session.photos)}/{Config.MAX_PHOTOS_PER_REQUEST} recebida!**\n\n"
        f"✅ Fotos coletadas: {len(session.photos)}\n"
        f"⏳ Restantes: {Config.MAX_PHOTOS_PER_REQUEST - len(session.photos)}\n\n"
        "👇 Escolha uma opção:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    return BotStates.WAITING_PHOTOS.value

async def process_photos_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Callback para processar fotos."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    session = await get_user_session(user_id)
    session.state = BotStates.PROCESSING
    
    if not session.photos:
        await query.edit_message_text("⚠️ Nenhuma foto encontrada. Envie fotos primeiro!")
        return BotStates.WAITING_PHOTOS.value
    
    # Mensagem de processamento
    processing_msg = await query.edit_message_text(
        "🔄 **PROCESSANDO SUAS FOTOS...**\n\n"
        "⏳ Extraindo texto das imagens...\n"
        "🤖 Analisando endereços com IA...\n"
        "🗺️ Otimizando rota...\n\n"
        "📱 *Isso pode levar alguns segundos...*",
        parse_mode='Markdown'
    )
    
    try:
        # Etapa 1: Extração de texto
        await context.bot.edit_message_text(
            "🔄 **PROCESSANDO SUAS FOTOS...**\n\n"
            "✅ Extraindo texto das imagens...\n"
            "⏳ Analisando endereços com IA...\n"
            "🗺️ Otimizando rota...\n\n"
            "📱 *Processando...*",
            chat_id=query.message.chat_id,
            message_id=processing_msg.message_id,
            parse_mode='Markdown'
        )
        
        raw_text, ocr_confidence = await ImageProcessor.extract_text_from_images(
            context.bot, session.photos
        )
        
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
