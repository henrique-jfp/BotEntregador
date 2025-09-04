from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = (
    "*BOT ENTREGADOR – Ajuda*\n"
    "Versão modular (parcial).\n\n"
    "*Fluxo principal (ainda em migração)*:\n"
    "• /start (no monolítico) inicia envio de fotos. Nesta versão modular parcial apenas /ganhos e /apps estão ativos aqui.\n\n"
    "*Ganhos (/ganhos)*:\n"
    "1. Escolha data (Hoje/ Ontem / Outra).\n"
    "2. Escolha aplicativo.\n"
    "3. Informe valor.\n"
    "4. Use resumos (dia / semana / mês).\n"
    "Gerencie a lista de aplicativos em /apps ou botão Gerenciar Apps.\n\n"
    "*Gerenciar Apps (/apps)*:\n"
    "• Adicionar, renomear e remover apps personalizados. Limite 15.\n\n"
    "*Outros (disponíveis no main.py enquanto migração não conclui)*:\n"
    "• /history histórico básico de rotas.\n"
    "• /cancel encerra fluxo de ganhos atual.\n"
    "Após completar a migração o /start e navegação aparecerão neste módulo."
)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(HELP_TEXT, parse_mode='Markdown')
