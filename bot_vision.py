import os
import re
import logging
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

# Função para extrair texto da imagem usando Google Vision
def extract_text_from_image(image_path):
    credentials_json = os.getenv('GOOGLE_VISION_CREDENTIALS_JSON')
    if credentials_json:
        # Escrever o JSON em um arquivo temporário
        with open('temp_credentials.json', 'w') as f:
            f.write(credentials_json)
        credentials_path = 'temp_credentials.json'
    else:
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'google-credentials.json')
    
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    client = vision.ImageAnnotatorClient(credentials=credentials)

    with open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations

    if texts:
        return texts[0].description
    return ""

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

# Função principal
def main():
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        logger.error("TELEGRAM_TOKEN não definido.")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CallbackQueryHandler(handle_callback))

    application.run_polling()

if __name__ == '__main__':
    main()
