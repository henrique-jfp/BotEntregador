from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from bot.config import Config, logger
from bot.handlers.gains import ganhos_cmd, gains_cb, gains_message, gains_summary_cb
from bot.handlers.apps import apps_cmd, apps_manage_cb, apps_menu_cb, apps_text_handler
from bot.handlers.start import start, start_photos_cb, photo_handler, process_cb, reviewing_message_handler, confirm_addresses_cb
from bot.handlers.route import export_circuit_cb, map_image_cb, reopt_cb
from bot.handlers.navigation import nav_start_cb, nav_prev_cb, nav_skip_cb, delivered_cb
from bot.handlers.config import config_open_cb, config_adjust_cb, review_back_cb
from bot.handlers.misc import status_cmd, history_cmd, cancel_cmd, cancelar_cmd, error_handler
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
        entry_points=[CommandHandler('ganhos', ganhos_cmd), CommandHandler('apps', apps_cmd), CommandHandler('start', start)],
        states={
            BotStates.WAITING_PHOTOS.value: [
                MessageHandler(filters.PHOTO, photo_handler),
                CallbackQueryHandler(start_photos_cb, pattern='^start_photos$'),
                CallbackQueryHandler(process_cb, pattern='^process$')
            ],
            BotStates.REVIEWING_ADDRESSES.value: [
                CallbackQueryHandler(confirm_addresses_cb, pattern='^confirm_addresses$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, reviewing_message_handler)
            ],
            BotStates.CONFIRMING_ROUTE.value: [
                CallbackQueryHandler(export_circuit_cb, pattern='^export_circuit$'),
                CallbackQueryHandler(map_image_cb, pattern='^map_image$'),
                CallbackQueryHandler(nav_start_cb, pattern='^nav_start$'),
                CallbackQueryHandler(config_open_cb, pattern='^config_open$'),
                CallbackQueryHandler(config_adjust_cb, pattern='^cfg_'),
                CallbackQueryHandler(review_back_cb, pattern='^review_back$'),
                CallbackQueryHandler(reopt_cb, pattern='^reopt$')
            ],
            BotStates.NAVIGATING.value: [
                CallbackQueryHandler(nav_prev_cb, pattern='^nav_prev$'),
                CallbackQueryHandler(nav_skip_cb, pattern='^nav_skip$'),
                CallbackQueryHandler(delivered_cb, pattern='^delivered$')
            ],
            BotStates.GAINS_DATE.value: [
                CallbackQueryHandler(gains_cb, pattern='^gains_date_'),
                CallbackQueryHandler(gains_cb, pattern='^gains_cancel$'),
                CallbackQueryHandler(apps_manage_cb, pattern='^apps_manage$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, gains_message)
            ],
            BotStates.GAINS_APP.value: [
                CallbackQueryHandler(gains_cb, pattern='^gains_app_'),
                CallbackQueryHandler(apps_manage_cb, pattern='^apps_manage$')
            ],
            BotStates.GAINS_VALUE.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, gains_message)
            ],
            BotStates.GAINS_MENU.value: [
                CallbackQueryHandler(gains_summary_cb, pattern='^gains_summary_'),
                CallbackQueryHandler(gains_cb, pattern='^gains_date_today$'),
                CallbackQueryHandler(gains_cb, pattern='^gains_cancel$'),
                CallbackQueryHandler(apps_manage_cb, pattern='^apps_manage$')
            ],
            BotStates.APPS_MENU.value: [
                CallbackQueryHandler(apps_menu_cb, pattern='^apps_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, apps_text_handler)
            ],
            BotStates.APPS_ADD.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, apps_text_handler)
            ],
            BotStates.APPS_RENAME_INPUT.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, apps_text_handler)
            ]
        },
        fallbacks=[]
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('apps', apps_cmd))
    app.add_handler(CommandHandler('status', status_cmd))
    app.add_handler(CommandHandler('history', history_cmd))
    app.add_handler(CommandHandler('cancel', cancel_cmd))
    app.add_handler(CommandHandler('cancelar', cancelar_cmd))
    app.add_error_handler(error_handler)
    return app

def run_bot():
    import asyncio
    async def _run():
        app = await build_app()
        logger.info("Bot parcial (modular) iniciado – somente /ganhos e /help registrados por enquanto")
        app.run_polling(drop_pending_updates=True, poll_interval=2.0)
    asyncio.run(_run())
