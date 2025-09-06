from telegram.ext import Application
from bot.config import Config, logger

async def build_app():
    builder = Application.builder().token(Config.TELEGRAM_BOT_TOKEN)
    builder.get_updates_read_timeout(60)
    builder.get_updates_write_timeout(30)
    builder.get_updates_connect_timeout(60)
    builder.get_updates_pool_timeout(60)
    app = builder.build()
    # TODO: registrar handlers após modularização completa
    return app

def run_bot():
    import asyncio
    async def _run():
        app = await build_app()
        logger.info("(Modular) Bot iniciando polling... (handlers incompletos ainda)")
        app.run_polling(drop_pending_updates=True, poll_interval=2.0)
    asyncio.run(_run())
