import json
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from bot.session import get_session, user_sessions
from bot.models.core import BotStates

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    session = await get_session(uid)
    await update.message.reply_text(
        f"Fotos: {len(session.photos)} | Endereços: {len(session.addresses)} | Estado: {session.state.name}"
    )

async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    p = Path('history') / f'history_{uid}.jsonl'
    if not p.exists():
        await update.message.reply_text('Sem histórico.')
        return
    try:
        lines = p.read_text(encoding='utf-8').strip().splitlines()[-5:]
        out = []
        for l in lines:
            try:
                j = json.loads(l)
                out.append(f"{j.get('ts','')} - {j.get('entregas_total',0)} entregas, receita R$ {j.get('receita',0):.2f}")
            except Exception:
                pass
        await update.message.reply_text('📜 Últimas rotas:\n'+'\n'.join(out) if out else 'Sem histórico.')
    except Exception as e:
        await update.message.reply_text(f'Erro histórico: {e}')

async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in user_sessions:
        del user_sessions[uid]
    await update.message.reply_text("Sessão cancelada. /start para recomeçar.")
    return BotStates.WAITING_PHOTOS.value

cancelar_cmd = cancel_cmd  # alias

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    err_str = str(context.error)
    if 'Timed out' in err_str or 'Query is too old' in err_str:
        return
    try:
        if update and hasattr(update, 'effective_message') and update.effective_message:
            await update.effective_message.reply_text("Erro interno. Tente novamente.")
    except Exception:
        pass
