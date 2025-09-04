from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.models.core import BotStates
from bot.session import get_session
from bot.persistence import DataPersistence
from bot.services.gains import DEFAULT_APPS

# Menu dinâmico de apps

def _render_apps_menu(session) -> InlineKeyboardMarkup:
    apps = session.apps or DEFAULT_APPS
    rows = []
    for i, a in enumerate(apps):
        rows.append([
            InlineKeyboardButton(a, callback_data=f"apps_sel_{i}"),
            InlineKeyboardButton("✏️", callback_data=f"apps_ren_{i}"),
            InlineKeyboardButton("🗑️", callback_data=f"apps_del_{i}")
        ])
    rows.append([
        InlineKeyboardButton("➕ Adicionar", callback_data="apps_add"),
        InlineKeyboardButton("⬅️ Voltar", callback_data="apps_back")
    ])
    return InlineKeyboardMarkup(rows)

async def apps_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    session = await get_session(uid)
    session.state = BotStates.APPS_MENU
    await update.message.reply_text("📱 *Gerenciar Apps de Ganhos*", reply_markup=_render_apps_menu(session), parse_mode='Markdown')
    await DataPersistence.save(session)
    return session.state.value

async def apps_manage_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    session = await get_session(q.from_user.id)
    session.state = BotStates.APPS_MENU
    await q.edit_message_text("📱 *Gerenciar Apps de Ganhos*\nToque em ✏️ para renomear ou 🗑️ para remover.", reply_markup=_render_apps_menu(session), parse_mode='Markdown')
    await DataPersistence.save(session)
    return session.state.value

async def apps_menu_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; await q.answer()
    session = await get_session(q.from_user.id)
    data = q.data
    apps = session.apps or DEFAULT_APPS
    if data == 'apps_back':
        # volta para escolha de app em ganhos
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(app, callback_data=f"gains_app_{i}")] for i, app in enumerate(apps)] + [[InlineKeyboardButton("Gerenciar Apps", callback_data="apps_manage")]])
        await q.edit_message_text("Escolha o aplicativo:", reply_markup=kb)
        session.state = BotStates.GAINS_APP
        return session.state.value
    if data == 'apps_add':
        if len(apps) >= 15:
            await q.edit_message_text("Limite de 15 apps atingido.", reply_markup=_render_apps_menu(session))
            return session.state.value
        session.state = BotStates.APPS_ADD
        await q.edit_message_text("Digite o nome do novo app:")
        await DataPersistence.save(session)
        return session.state.value
    if data.startswith('apps_del_'):
        idx = int(data.split('_')[-1])
        if 0 <= idx < len(apps):
            if len(apps) <= 1:
                await q.edit_message_text("Não é possível remover todos os apps.", reply_markup=_render_apps_menu(session))
                return session.state.value
            removed = apps.pop(idx)
            session.apps = apps
            await q.edit_message_text(f"Removido: {removed}", reply_markup=_render_apps_menu(session))
            await DataPersistence.save(session)
        return session.state.value
    if data.startswith('apps_ren_'):
        idx = int(data.split('_')[-1])
        if 0 <= idx < len(apps):
            session.gains_temp['rename_index'] = str(idx)
            session.state = BotStates.APPS_RENAME_INPUT
            await q.edit_message_text(f"Digite novo nome para '{apps[idx]}':")
            await DataPersistence.save(session)
        return session.state.value
    return session.state.value

async def apps_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    session = await get_session(uid)
    apps = session.apps or DEFAULT_APPS
    txt = (update.message.text or '').strip()
    if session.state == BotStates.APPS_ADD:
        if not txt:
            await update.message.reply_text("Nome vazio. Digite novamente ou /cancel.")
            return session.state.value
        if txt.lower() in [a.lower() for a in apps]:
            await update.message.reply_text("Já existe app com esse nome.")
            return session.state.value
        apps.append(txt[:40])
        session.apps = apps
        session.state = BotStates.APPS_MENU
        await DataPersistence.save(session)
        await update.message.reply_text("Adicionado.", reply_markup=_render_apps_menu(session))
        return session.state.value
    if session.state == BotStates.APPS_RENAME_INPUT and 'rename_index' in session.gains_temp:
        try:
            idx = int(session.gains_temp.get('rename_index'))
        except ValueError:
            idx = -1
        if 0 <= idx < len(apps):
            if not txt:
                await update.message.reply_text("Nome vazio. Digite novamente.")
                return session.state.value
            if txt.lower() in [a.lower() for a in apps if a != apps[idx]]:
                await update.message.reply_text("Já existe outro app com esse nome.")
                return session.state.value
            old = apps[idx]
            apps[idx] = txt[:40]
            session.apps = apps
            session.gains_temp.pop('rename_index', None)
            session.state = BotStates.APPS_MENU
            await DataPersistence.save(session)
            await update.message.reply_text(f"Renomeado '{old}' -> '{apps[idx]}'", reply_markup=_render_apps_menu(session))
            return session.state.value
    return session.state.value
