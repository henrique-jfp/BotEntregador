from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from bot.config import Config, logger
from bot.handlers.gains import ganhos_cmd, gains_cb, gains_message, gains_summary_cb
from bot.handlers.help import help_cmd
from bot.models.core import BotStates

async def build_app():
    builder = Application.builder().token(Config.TELEGRAM_BOT_TOKEN)
    builder.get_updates_read_timeout(60)
    builder.get_updates_write_timeout(30)
    builder.get_updates_connect_timeout(60)
    builder.get_updates_pool_timeout(60)
    app = builder.build()

    conv = ConversationHandler(
        entry_points=[CommandHandler('ganhos', ganhos_cmd)],
        states={
            BotStates.GAINS_DATE.value: [
                CallbackQueryHandler(gains_cb, pattern='^gains_date_'),
                CallbackQueryHandler(gains_cb, pattern='^gains_cancel$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, gains_message)
            ],
            BotStates.GAINS_APP.value: [
                CallbackQueryHandler(gains_cb, pattern='^gains_app_')
            ],
            BotStates.GAINS_VALUE.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, gains_message)
            ],
            BotStates.GAINS_MENU.value: [
                CallbackQueryHandler(gains_summary_cb, pattern='^gains_summary_'),
                CallbackQueryHandler(gains_cb, pattern='^gains_date_today$'),
                CallbackQueryHandler(gains_cb, pattern='^gains_cancel$')
            ]
        },
        fallbacks=[]
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler('help', help_cmd))
    return app

def run_bot():
    import asyncio
    async def _run():
        app = await build_app()
        logger.info("Bot parcial (modular) iniciado – somente /ganhos e /help registrados por enquanto")
        app.run_polling(drop_pending_updates=True, poll_interval=2.0)
    asyncio.run(_run())
