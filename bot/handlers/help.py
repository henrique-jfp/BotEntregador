from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = (
    "*BOT ENTREGADOR – Ajuda*\n"
    "Use /start para iniciar. /ganhos para registrar ganhos. /history para histórico. /cancel para finalizar sessão."
)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(HELP_TEXT, parse_mode='Markdown')
