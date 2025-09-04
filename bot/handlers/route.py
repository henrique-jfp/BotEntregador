from datetime import datetime
from io import BytesIO
import uuid, os, urllib.parse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes
from bot.models.core import BotStates
from bot.session import get_session, circuit_routes
from bot.persistence import DataPersistence
from bot.services.optimize import optimize_and_compute
from bot.services.mapgen import generate_static_map
from bot.config import Config

async def export_circuit_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    session = await get_session(q.from_user.id)
    if not session.addresses:
        await q.edit_message_text("Nenhum endereço para exportar.")
        return BotStates.CONFIRMING_ROUTE.value
    lines = ["ordem,endereco"]
    for i,a in enumerate(session.addresses, start=1):
        addr = a.cleaned_address.replace('"','""')
        lines.append(f'{i},"{addr}"')
    content='\n'.join(lines)
    bio = BytesIO(content.encode('utf-8')); bio.name=f"rota_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    await q.message.reply_document(InputFile(bio), caption="CSV gerado para Circuit (ordem,endereco)")
    return BotStates.CONFIRMING_ROUTE.value

async def map_image_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    session = await get_session(q.from_user.id)
    if not session.addresses:
        await q.edit_message_text("Rota não encontrada.")
        return BotStates.CONFIRMING_ROUTE.value
    await q.message.reply_text("Gerando mapa…")
    img_bytes = await generate_static_map(session.addresses)
    if not img_bytes:
        await q.message.reply_text("Não foi possível gerar mapa.")
        return BotStates.CONFIRMING_ROUTE.value
    bio = BytesIO(img_bytes); bio.name='rota.png'
    await q.message.reply_photo(InputFile(bio), caption="Mapa da rota")
    return BotStates.CONFIRMING_ROUTE.value

async def reopt_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    session = await get_session(q.from_user.id)
    if not session.addresses:
        await q.edit_message_text("Nada para re-otimizar.")
        return BotStates.WAITING_PHOTOS.value
    await q.edit_message_text("♻️ Re-otimizando rota...")
    optimized_objs, total_km, driving_min, service_min, total_min, via_api, failed_dm = await optimize_and_compute(session.addresses)
    session.optimized_route = [o.cleaned_address for o in optimized_objs]
    session.addresses = optimized_objs
    await DataPersistence.save(session)
    lista = '\n'.join(f"{i+1:02d}. {a.cleaned_address}" for i,a in enumerate(session.addresses))
    text = (
        f"📏 Distância {'real' if via_api else 'estimada'}: *{total_km} km*\n"
        f"⏱️ Condução: ~{driving_min} min\n📦 Manuseio: {service_min} min\n⏳ Total: *{total_min} min*\n\n" +
        "*Ordem:*\n" + lista + ("\n✅ Distance Matrix." if via_api else "\n💡 Heurístico.")
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Navegar", callback_data="nav_start")],
        [InlineKeyboardButton("♻️ Re-otimizar", callback_data="reopt")],
        [InlineKeyboardButton("📤 Exportar CSV", callback_data="export_circuit"), InlineKeyboardButton("🗺️ Mapa", callback_data="map_image")]
    ])
    await q.edit_message_text(text, reply_markup=kb, parse_mode='Markdown')
    return BotStates.CONFIRMING_ROUTE.value
