from datetime import datetime
import uuid, os, urllib.parse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes
from bot.models.core import BotStates, DeliveryAddress
from bot.session import get_session, circuit_routes
from bot.services.ocr import ImageProcessor
from bot.utils.text import extract_addresses
from bot.services.optimize import optimize_and_compute
from bot.persistence import DataPersistence
from bot.config import Config, logger


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    logger.info(f"/start {uid}")
    session = await get_session(uid)
    # reset básico
    session.photos = []
    session.addresses = []
    session.optimized_route = []
    session.processed = False
    session.completed_deliveries = []
    session.state = BotStates.WAITING_PHOTOS
    await DataPersistence.save(session)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📸 Enviar Fotos", callback_data="start_photos")]])
    await update.message.reply_text("🚚 Envie fotos (até 8) com endereços e depois clique em Processar.", reply_markup=kb)
    return BotStates.WAITING_PHOTOS.value

async def start_photos_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    await q.edit_message_text("Envie agora suas fotos. Quando terminar clique em Processar.")
    return BotStates.WAITING_PHOTOS.value

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    session = await get_session(uid)
    if session.processed:
        await update.message.reply_text("Rota já processada. Use /start para nova rota.")
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
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    session = await get_session(uid)
    if session.processed:
        await q.edit_message_text("Rota já processada.")
        return BotStates.CONFIRMING_ROUTE.value
    if not session.photos:
        await q.edit_message_text("Envie ao menos 1 foto.")
        return BotStates.WAITING_PHOTOS.value
    await q.edit_message_text("🔄 Processando fotos (OCR)...")
    raw = await ImageProcessor.ocr(context.bot, session.photos)
    if not raw.strip():
        await q.edit_message_text("Nenhum texto encontrado.")
        return BotStates.WAITING_PHOTOS.value
    session.raw_text = raw
    extracted = extract_addresses(raw)
    if not extracted:
        await q.edit_message_text("Nenhum endereço reconhecido.")
        return BotStates.WAITING_PHOTOS.value
    session.addresses = extracted
    session.state = BotStates.REVIEWING_ADDRESSES
    await DataPersistence.save(session)
    lines = '\n'.join(f"{i+1:02d}. {a.cleaned_address}" for i,a in enumerate(session.addresses))
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar lista", callback_data="confirm_addresses")],
        [InlineKeyboardButton("➕ Adicionar", callback_data="add_address")]
    ])
    await q.edit_message_text("📋 *Revise os endereços extraídos*\n" + lines + "\n\nVocê pode editar enviando: 3: Novo Endereço 123", parse_mode='Markdown', reply_markup=kb)
    return BotStates.REVIEWING_ADDRESSES.value

async def reviewing_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    session = await get_session(uid)
    if session.state != BotStates.REVIEWING_ADDRESSES:
        return session.state.value
    text = update.message.text.strip()
    if text.startswith('+') or text.lower().startswith('add '):
        new_addr = text.lstrip('+').split(' ',1)
        if isinstance(new_addr, list):
            new_addr = new_addr[-1]
        new_addr = new_addr.strip()
        if new_addr:
            session.addresses.append(DeliveryAddress(original_text=new_addr, cleaned_address=new_addr))
            await update.message.reply_text(f"Adicionado: {new_addr}")
    else:
        import re
        m = re.match(r'^(\d{1,2})\s*[:\-|]\s*(.+)$', text)
        if m:
            idx = int(m.group(1)) - 1
            new_val = m.group(2).strip()
            if 0 <= idx < len(session.addresses) and new_val:
                old = session.addresses[idx].cleaned_address
                session.addresses[idx].cleaned_address = new_val
                await update.message.reply_text(f"Atualizado {idx+1}: '{old}' -> '{new_val}'")
    await DataPersistence.save(session)
    lines = '\n'.join(f"{i+1:02d}. {a.cleaned_address}" for i,a in enumerate(session.addresses))
    await update.message.reply_text("Lista agora:\n" + lines + "\nConfirme quando pronto (botão).")
    return BotStates.REVIEWING_ADDRESSES.value

async def confirm_addresses_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    session = await get_session(uid)
    if not session.addresses:
        await q.edit_message_text("Lista vazia.")
        return BotStates.WAITING_PHOTOS.value
    await q.edit_message_text("🛣️ Otimizando rota...")
    optimized_objs, total_km, driving_min, service_min, total_min, via_api, failed_dm = await optimize_and_compute(session.addresses)
    session.optimized_route = [o.cleaned_address for o in optimized_objs]
    session.addresses = optimized_objs
    session.processed = True
    session.state = BotStates.CONFIRMING_ROUTE
    await DataPersistence.save(session)
    total = len(session.addresses)
    primeira = session.addresses[0].cleaned_address
    ultima = session.addresses[-1].cleaned_address
    lista = '\n'.join(f"{i+1:02d}. {a.cleaned_address}" for i,a in enumerate(session.addresses))
    valor_ent = session.config.get('valor_entrega', 0) if session.config else 0
    custo_km = session.config.get('custo_km', 0) if session.config else 0
    receita = valor_ent * total
    custo_dist = custo_km * total_km
    lucro = receita - custo_dist
    econ_line = f"💰 Receita: R$ {receita:.2f} | Custo: R$ {custo_dist:.2f} | Lucro: R$ {lucro:.2f}" if (valor_ent or custo_km) else ""
    text = (
        f"🧭 Início: {primeira}\n🏁 Fim: {ultima}\n"
        f"📏 Distância {'real' if via_api else 'estimada'}: *{total_km} km*\n"
        f"⏱️ Condução: ~{driving_min} min\n"
        f"📦 Manuseio: {service_min} min\n"
        f"⏳ Total estimado: *{total_min} min*\n" +
        (econ_line + '\n' if econ_line else '') +
        "\n*Ordem:*\n" + lista +
        ("\n✅ Distance Matrix." if via_api else "\n💡 Heurístico.") +
        "\nEscolha uma ação:" )
    route_id = uuid.uuid4().hex[:10]
    circuit_routes[route_id] = [a.cleaned_address for a in session.addresses]
    host_env = os.getenv('RENDER_EXTERNAL_HOSTNAME')
    port = int(os.getenv('PORT', '8000'))
    base_url = f"https://{host_env}" if host_env else f"http://localhost:{port}"
    circuit_http_link = f"{base_url}/circuit/{route_id}"
    def build_gmaps_link(addresses):
        if len(addresses) < 2:
            enc = urllib.parse.quote(addresses[0])
            return f"https://www.google.com/maps/search/{enc}"
        origin = urllib.parse.quote(addresses[0]); destination = urllib.parse.quote(addresses[-1])
        wp = '|'.join(urllib.parse.quote(w) for w in addresses[1:-1])
        return f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&travelmode=driving&waypoints={wp}"
    maps_route_link = build_gmaps_link([a.cleaned_address for a in session.addresses])
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Navegar", callback_data="nav_start")],
        [InlineKeyboardButton("📤 Exportar CSV", callback_data="export_circuit")],
        [InlineKeyboardButton("🧭 Google Maps", url=maps_route_link)],
        [InlineKeyboardButton("🗺️ Mapa imagem", callback_data="map_image")],
        [InlineKeyboardButton("🔗 Circuit", url=circuit_http_link)],
        [InlineKeyboardButton("⚙️ Config", callback_data="config_open")]
    ])
    await q.edit_message_text(text, reply_markup=kb, parse_mode='Markdown')
    return BotStates.CONFIRMING_ROUTE.value
