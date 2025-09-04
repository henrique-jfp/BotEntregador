from datetime import datetime, timedelta
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.models.core import BotStates
from bot.session import get_session
from bot.services.gains import append_gain, load_gains, summarize_gains, DEFAULT_APPS
from bot.persistence import DataPersistence

async def ganhos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    session = await get_session(uid)
    today = datetime.now().strftime('%Y-%m-%d')
    session.gains_temp = {'date': today}
    await DataPersistence.save(session)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Hoje", callback_data="gains_date_today"), InlineKeyboardButton("Ontem", callback_data="gains_date_yesterday")],
        [InlineKeyboardButton("Outra Data", callback_data="gains_date_other")],
        [InlineKeyboardButton("Gerenciar Apps", callback_data="apps_manage")],
        [InlineKeyboardButton("Cancelar", callback_data="gains_cancel")]
    ])
    await update.message.reply_text("📅 Selecione a data dos ganhos:", reply_markup=kb)
    session.state = BotStates.GAINS_DATE

async def gains_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    session = await get_session(uid)
    data = q.data
    apps = session.apps or DEFAULT_APPS
    if data == 'gains_cancel':
        await q.edit_message_text("Operação cancelada.")
        session.state = BotStates.WAITING_PHOTOS
        return session.state.value
    if data.startswith('gains_date_'):
        if data.endswith('today'):
            session.gains_temp['date'] = datetime.now().strftime('%Y-%m-%d')
        elif data.endswith('yesterday'):
            session.gains_temp['date'] = (datetime.now()-timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            session.gains_temp['awaiting_custom_date'] = '1'
            await q.edit_message_text("Digite a data no formato DD/MM/AAAA")
            session.state = BotStates.GAINS_DATE
            await DataPersistence.save(session)
            return session.state.value
    if data.startswith('gains_date_') and not session.gains_temp.get('awaiting_custom_date'):
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(app, callback_data=f"gains_app_{i}")] for i, app in enumerate(apps)] + [[InlineKeyboardButton("Gerenciar Apps", callback_data="apps_manage")]])
        await q.edit_message_text(f"Data: {session.gains_temp['date']}. Escolha o aplicativo:", reply_markup=kb)
        session.state = BotStates.GAINS_APP
        await DataPersistence.save(session)
        return session.state.value
    if data.startswith('gains_app_'):
        idx = int(data.split('_')[-1])
        if 0 <= idx < len(apps):
            session.gains_temp['app'] = apps[idx]
            await q.edit_message_text(f"Digite o valor ganho em {session.gains_temp['app']} (ex: 150.75)")
            session.state = BotStates.GAINS_VALUE
            await DataPersistence.save(session)
            return session.state.value
    return session.state.value

async def gains_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    session = await get_session(uid)
    apps = session.apps or DEFAULT_APPS
    if session.state == BotStates.GAINS_DATE and session.gains_temp.get('awaiting_custom_date'):
        txt = update.message.text.strip()
        import re
        m = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', txt)
        if not m:
            await update.message.reply_text("Formato inválido. Use DD/MM/AAAA ou /cancel.")
            return session.state.value
        day, mon, year = m.groups()
        from datetime import datetime
        try:
            dt = datetime(int(year), int(mon), int(day))
            session.gains_temp['date'] = dt.strftime('%Y-%m-%d')
            session.gains_temp.pop('awaiting_custom_date', None)
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(app, callback_data=f"gains_app_{i}")] for i, app in enumerate(apps)] + [[InlineKeyboardButton("Gerenciar Apps", callback_data="apps_manage")]])
            await update.message.reply_text(f"Data definida {session.gains_temp['date']}. Escolha o app:", reply_markup=kb)
            session.state = BotStates.GAINS_APP
        except ValueError:
            await update.message.reply_text("Data inválida.")
        await DataPersistence.save(session)
        return session.state.value
    if session.state == BotStates.GAINS_VALUE and 'app' in session.gains_temp:
        txt = update.message.text.replace(',', '.').strip()
        try:
            val = float(txt)
        except ValueError:
            await update.message.reply_text("Valor inválido. Tente novamente (ex: 123.45)")
            return session.state.value
        rec = {
            'user': uid,
            'date': session.gains_temp['date'],
            'app': session.gains_temp['app'],
            'valor': val
        }
        append_gain(rec)
        await update.message.reply_text(f"✅ Registrado R$ {val:.2f} em {rec['app']} no dia {rec['date']}.")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Adicionar outro", callback_data="gains_date_today"), InlineKeyboardButton("Resumo hoje", callback_data="gains_summary_day")],
            [InlineKeyboardButton("Resumo semana", callback_data="gains_summary_week"), InlineKeyboardButton("Resumo mês", callback_data="gains_summary_month")],
            [InlineKeyboardButton("Gerenciar Apps", callback_data="apps_manage")],
            [InlineKeyboardButton("Finalizar", callback_data="gains_cancel")]
        ])
        await update.message.reply_text("O que deseja agora?", reply_markup=kb)
        session.state = BotStates.GAINS_MENU
        await DataPersistence.save(session)
        return session.state.value
    return session.state.value

async def gains_summary_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    session = await get_session(uid)
    now = datetime.now()
    data = q.data
    if data == 'gains_summary_day':
        start = end = now
    elif data == 'gains_summary_week':
        start = now - timedelta(days=6); end = now
    elif data == 'gains_summary_month':
        start = now.replace(day=1); end = now
    else:
        return session.state.value
    gains = load_gains(uid, start, end)
    summary = summarize_gains(gains)
    await q.edit_message_text(f"📊 Resumo ({start.date()} a {end.date()}):\n{summary}")
    session.state = BotStates.GAINS_MENU
    return session.state.value
