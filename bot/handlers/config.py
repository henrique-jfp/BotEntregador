from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.models.core import BotStates
from bot.session import get_session
from bot.persistence import DataPersistence

async def config_open_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    session = await get_session(q.from_user.id)
    session.ensure_config()
    cfg = session.config
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💲 +1", callback_data="cfg_valor_up"), InlineKeyboardButton("-1", callback_data="cfg_valor_down")],
        [InlineKeyboardButton("⛽ +0.1", callback_data="cfg_km_up"), InlineKeyboardButton("-0.1", callback_data="cfg_km_down")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="review_back")]
    ])
    await q.edit_message_text(
        f"⚙️ *Configuração*\nValor por entrega: R$ {cfg['valor_entrega']:.2f}\nCusto por km: R$ {cfg['custo_km']:.2f}\nTempo serviço: {cfg['service_time_min']} min",
        reply_markup=kb, parse_mode='Markdown'
    )
    return session.state.value

async def config_adjust_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    session = await get_session(q.from_user.id)
    session.ensure_config()
    data = q.data
    if data == 'cfg_valor_up':
        session.config['valor_entrega'] += 1
    elif data == 'cfg_valor_down':
        session.config['valor_entrega'] = max(0, session.config['valor_entrega'] - 1)
    elif data == 'cfg_km_up':
        session.config['custo_km'] += 0.1
    elif data == 'cfg_km_down':
        session.config['custo_km'] = max(0, session.config['custo_km'] - 0.1)
    await DataPersistence.save(session)
    return await config_open_cb(update, context)

async def review_back_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    session = await get_session(q.from_user.id)
    if not session.addresses:
        await q.edit_message_text("Lista vazia.")
        return BotStates.WAITING_PHOTOS.value
    lines = '\n'.join(f"{i+1:02d}. {a.cleaned_address}" for i,a in enumerate(session.addresses))
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar lista", callback_data="confirm_addresses")],
        [InlineKeyboardButton("⚙️ Config", callback_data="config_open")]
    ])
    await q.edit_message_text(
        "📋 *Revise os endereços*\n" + lines + "\n\nPara editar: 3: Rua Nova 123  / Para adicionar: + Rua Tal 99",
        reply_markup=kb, parse_mode='Markdown'
    )
    session.state = BotStates.REVIEWING_ADDRESSES
    await DataPersistence.save(session)
    return BotStates.REVIEWING_ADDRESSES.value
