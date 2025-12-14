"""
🌐 SERVIDOR INTEGRADO - Bot + WebSocket Dashboard
Roda ambos simultaneamente
"""
import asyncio
import logging
from bot_multidelivery.bot import run_bot
from bot_multidelivery.services import dashboard_ws

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Inicia bot + dashboard em paralelo"""
    
    # Inicia dashboard em background
    logger.info("🌐 Iniciando WebSocket Dashboard...")
    await dashboard_ws.start_background()
    
    # Inicia bot (bloqueia aqui)
    logger.info("🤖 Iniciando Telegram Bot...")
    from bot_multidelivery.bot import run_bot
    
    # Cria task para o bot
    bot_task = asyncio.create_task(run_bot_async())
    
    # Aguarda
    await bot_task


async def run_bot_async():
    """Wrapper assíncrono para run_bot"""
    import asyncio
    loop = asyncio.get_event_loop()
    
    # run_bot() é síncrono, precisa rodar em executor
    await loop.run_in_executor(None, run_bot)


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════╗
    ║  🚀 BOT MULTI-ENTREGADOR - SISTEMA 12/10  ║
    ╚═══════════════════════════════════════════╝
    
    ✅ Telegram Bot
    ✅ WebSocket Dashboard (http://localhost:8765/dashboard)
    ✅ IA Preditiva de tempo de entrega
    
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Encerrando sistema...")
