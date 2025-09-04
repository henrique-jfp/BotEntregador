from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.models.core import BotStates
from bot.session import get_session
from bot.persistence import DataPersistence
from bot.config import Config

async def nav_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    session = await get_session(q.from_user.id)
    session.state = BotStates.NAVIGATING
    session.current_delivery_index = 0
    return await _show_current_stop(q, session)

async def nav_prev_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    session = await get_session(q.from_user.id)
    if session.current_delivery_index > 0:
        session.current_delivery_index -= 1
    return await _show_current_stop(q, session)

async def nav_skip_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    session = await get_session(q.from_user.id)
    if session.current_delivery_index < len(session.optimized_route) - 1:
        cur = session.optimized_route.pop(session.current_delivery_index)
        session.optimized_route.append(cur)
    return await _show_current_stop(q, session)

async def delivered_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    session = await get_session(q.from_user.id)
    if session.current_delivery_index < len(session.optimized_route):
        session.completed_deliveries.append(session.optimized_route[session.current_delivery_index])
        session.current_delivery_index += 1
    await DataPersistence.save(session)
    return await _show_current_stop(q, session)

async def _show_current_stop(q_or_update, session):
    idx = session.current_delivery_index
    total = len(session.optimized_route)
    if idx >= total:
        return await _finish_route(q_or_update, session)
    addr = session.optimized_route[idx]
    enc = addr.replace(' ', '+').replace(',', '%2C')
    remaining = total - idx
    km_per_stop = 2
    est_km_remaining = km_per_stop * remaining
    drive_min = (est_km_remaining / Config.AVERAGE_SPEED_KMH) * 60
    service_min = remaining * session.config.get('service_time_min', Config.SERVICE_TIME_PER_STOP_MIN)
    eta_total = int(drive_min + service_min)
    msg = (f"Entrega {idx+1}/{total}\n\n{addr}\n\n" f"Concluídas: {idx} | Restantes: {total - idx - 1}\nETA restante ~ {eta_total} min")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Maps", url=f"https://www.google.com/maps/search/{enc}"), InlineKeyboardButton("Waze", url=f"https://waze.com/ul?q={enc}")],
        [InlineKeyboardButton("⬅️", callback_data="nav_prev"), InlineKeyboardButton("⏭️ Pular", callback_data="nav_skip"), InlineKeyboardButton("✅ Entregue", callback_data="delivered")]
    ])
    if hasattr(q_or_update, 'edit_message_text'):
        await q_or_update.edit_message_text(msg, reply_markup=kb)
    else:
        await q_or_update.message.reply_text(msg, reply_markup=kb)
    return BotStates.NAVIGATING.value

async def _finish_route(q_or_update, session):
    total_ent = len(session.completed_deliveries)
    msg = f"🎉 Rota concluída!\n\nTotal entregas: {total_ent}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Nova Rota", callback_data="start_photos")]])
    # reset simples
    from bot.models.core import UserSession
    new_session = UserSession(user_id=session.user_id, photos=[])
    from bot.session import user_sessions
    user_sessions[session.user_id] = new_session
    if hasattr(q_or_update, 'edit_message_text'):
        await q_or_update.edit_message_text(msg, reply_markup=kb)
    else:
        await q_or_update.message.reply_text(msg, reply_markup=kb)
    return BotStates.WAITING_PHOTOS.value
