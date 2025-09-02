import os
import re
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from google.cloud import vision
from google.oauth2 import service_account

# Configuração de logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Regex otimizado para extrair endereços brasileiros
# Captura linhas que começam com palavras comuns de endereços, seguidas de texto
ADDRESS_REGEX = re.compile(
    r'^(rua|av\.?|avenida|praça|alameda|travessa|beco|rodovia|estrada|bloco|apartamento|condomínio|vila|jardim|centro|setor|quadra|lote)\s+.*$',
    re.IGNORECASE | re.MULTILINE
)

# Função para extrair texto da imagem usando Google Vision. Aceita credencial via:
# 1) Variável GOOGLE_VISION_CREDENTIALS_JSON contendo o JSON inteiro (mais seguro em Render)
# 2) Variável GOOGLE_APPLICATION_CREDENTIALS apontando para um arquivo json no disco
def extract_text_from_image(image_path):
    try:
        credentials_path = ensure_credentials_file()
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        client = vision.ImageAnnotatorClient(credentials=credentials)
    except Exception as e:
        logger.error(f"Falha ao configurar Google Vision: {e}")
        raise RuntimeError("Erro nas credenciais do Google Vision. Recrie a chave ou use Base64.") from e
    with open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations

    if texts:
        return texts[0].description
    return ""
def ensure_credentials_file() -> str:
    """Garante que existe um arquivo de credenciais local e retorna o caminho.
    Suporta:
      - GOOGLE_VISION_CREDENTIALS_JSON (JSON bruto)
      - GOOGLE_VISION_CREDENTIALS_JSON_BASE64 (JSON inteiro base64)
      - GOOGLE_APPLICATION_CREDENTIALS (caminho já existente)
    Corrige o campo private_key substituindo sequências \n literais por novas linhas reais.
    """
    # Caminho explícito já fornecido
    explicit_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if explicit_path and os.path.isfile(explicit_path):
        return explicit_path

    json_env = os.getenv('GOOGLE_VISION_CREDENTIALS_JSON')
    json_b64 = os.getenv('GOOGLE_VISION_CREDENTIALS_JSON_BASE64')
    if not json_env and not json_b64:
        raise RuntimeError("Nenhuma credencial encontrada nas variáveis de ambiente.")

    try:
        if json_b64:
            import base64  # lazy import
            decoded = base64.b64decode(json_b64).decode('utf-8')
            data = json.loads(decoded)
        else:
            data = json.loads(json_env)
    except Exception as e:
        raise RuntimeError(f"Falha ao decodificar JSON de credenciais: {e}") from e

    # Corrigir private_key com '\n' - mais agressivo
    if 'private_key' in data:
        private_key = data['private_key']
        # Se não tem quebras reais, mas tem \n literais, substituir
        if '\\n' in private_key and '\n' not in private_key:
            data['private_key'] = private_key.replace('\\n', '\n')
        # Se tem quebras misturadas, normalizar
        elif '\\n' in private_key:
            data['private_key'] = private_key.replace('\\n', '\n')
            
        # Garantir formato correto: deve começar e terminar com headers
        pk = data['private_key'].strip()
        if not pk.startswith('-----BEGIN PRIVATE KEY-----'):
            logger.warning("private_key não começa com header esperado")
        if not pk.endswith('-----END PRIVATE KEY-----'):
            logger.warning("private_key não termina com footer esperado")

    # Escrever arquivo temporário (estável durante o processo)
    path = 'temp_credentials.json'
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Arquivo de credenciais criado: {path}")
    except Exception as e:
        raise RuntimeError(f"Não foi possível escrever arquivo de credenciais: {e}") from e
    return path

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: D401
    """Handler global de erros: loga e avisa o usuário de forma amigável."""
    logger.exception("Erro não tratado durante processamento de update")
    try:
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Ocorreu um erro interno. Tente novamente em instantes."
            )
    except Exception:
        logger.exception("Falha ao enviar mensagem de erro")

    # (bloco movido para extract_text_from_image)

# Função para filtrar endereços usando regex
def filter_addresses(text):
    lines = text.split('\n')
    addresses = []
    for line in lines:
        line = line.strip()
        if ADDRESS_REGEX.match(line):
            addresses.append(line)
    return addresses

# Handler para comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Olá! Envie uma foto (print) da lista de endereços do seu app de entregas, e eu extrairei os endereços e criarei rotas otimizadas para você."
    )

    # Handler para mensagens de foto
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        photo = update.message.photo[-1]  # Maior resolução
        file = await context.bot.get_file(photo.file_id)
        image_path = f"temp_{update.message.from_user.id}.jpg"
        await file.download_to_drive(image_path)

        # Extrair texto
        text = extract_text_from_image(image_path)
        os.remove(image_path)  # Limpar arquivo temporário

        if not text:
            await update.message.reply_text("Não consegui extrair texto da imagem. Tente novamente com uma foto mais clara.")
            return

        # Filtrar endereços
        addresses = filter_addresses(text)

        if not addresses:
            await update.message.reply_text("Nenhum endereço encontrado na imagem. Verifique se a foto contém endereços visíveis.")
            return

        # Salvar endereços no contexto para uso posterior
        context.user_data['addresses'] = addresses

        # Responder com lista de endereços
        address_list = "\n".join(f"{i+1}. {addr}" for i, addr in enumerate(addresses))
        await update.message.reply_text(f"Endereços extraídos:\n{address_list}")

        # Criar keyboard inline
        keyboard = [
            [InlineKeyboardButton("🗺️ Google Maps", callback_data='maps')],
            [InlineKeyboardButton("🚗 Waze", callback_data='waze')],
            [InlineKeyboardButton("📋 Circuit (Copiar)", callback_data='circuit')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Escolha uma opção para gerar a rota:", reply_markup=reply_markup)

    except RuntimeError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        logger.exception("Erro inesperado ao processar foto")
        await update.message.reply_text("Erro inesperado ao processar a imagem. Tente novamente.")

# Handler para callback queries
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    addresses = context.user_data.get('addresses', [])
    if not addresses:
        await query.edit_message_text("Nenhum endereço encontrado. Envie uma foto primeiro.")
        return

    if query.data == 'maps':
        # Gerar URL do Google Maps com waypoints
        origin = addresses[0]
        destination = addresses[-1]
        waypoints = addresses[1:-1] if len(addresses) > 2 else []
        waypoints_str = '/'.join(waypoints)
        url = f"https://www.google.com/maps/dir/{origin}/{waypoints_str}/{destination}"
        await query.edit_message_text(f"Acesse sua rota otimizada no Google Maps: {url}")

    elif query.data == 'waze':
        # Gerar URL do Waze para o primeiro endereço
        first_address = addresses[0]
        url = f"https://waze.com/ul?q={first_address.replace(' ', '%20')}"
        await query.edit_message_text(f"Acesse o primeiro endereço no Waze: {url}")

    elif query.data == 'circuit':
        # Enviar lista formatada para copiar
        address_list = "\n".join(addresses)
        await query.edit_message_text(f"Lista de endereços para copiar no Circuit:\n{address_list}")

class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 método padrão http.server
        if self.path not in ('/', '/health', '/healthz'):
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'OK')

    # Silenciar logs padrão do http.server para não poluir Render logs
    def log_message(self, format, *args):  # noqa: A003 (nome herdado)
        return


def start_health_server():
    """Inicia um pequeno servidor HTTP para satisfazer verificação de porta do Render.
    Caso o serviço esteja configurado como Web Service, o Render exige uma porta aberta.
    """
    try:
        port = int(os.getenv('PORT', '10000'))  # Render define PORT para Web Service.
        server = HTTPServer(('0.0.0.0', port), _HealthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info(f"Servidor de health iniciado na porta {port}.")
    except Exception as e:  # pragma: no cover (melhor esforço)
        logger.error(f"Falha ao iniciar servidor de health: {e}")


def main():
    # Suporta tanto TELEGRAM_TOKEN (recomendado) quanto BOT_TOKEN (legacy)
    token = os.getenv('TELEGRAM_TOKEN') or os.getenv('BOT_TOKEN')
    if not token:
        logger.error("Nenhum token encontrado (TELEGRAM_TOKEN / BOT_TOKEN).")
        return

    # Inicia servidor de health se estivermos em ambiente que requer porta (Web Service)
    start_health_server()

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_error_handler(error_handler)

    # Execução de polling (bloqueante)
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
