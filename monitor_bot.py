"""
🔍 Monitor do Bot - Verifica se o bot está respondendo
"""
import os
import sys
import logging
from telegram import Bot
from telegram.error import TelegramError
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_bot_status():
    """Verifica se o bot está online e respondendo"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN não configurado!")
        return False
    
    try:
        bot = Bot(token=token)
        
        # Tenta obter informações do bot
        logger.info("🔍 Verificando status do bot...")
        me = await bot.get_me()
        logger.info(f"✅ Bot está ONLINE!")
        logger.info(f"   Nome: {me.first_name}")
        logger.info(f"   Username: @{me.username}")
        logger.info(f"   ID: {me.id}")
        
        # Verifica se pode receber updates
        logger.info("🔍 Verificando updates...")
        updates = await bot.get_updates(limit=1, timeout=5)
        logger.info(f"✅ Bot pode receber updates. Últimos updates: {len(updates)}")
        
        return True
        
    except TelegramError as e:
        logger.error(f"❌ Erro ao conectar com o Telegram: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro inesperado: {e}")
        return False


async def send_test_message():
    """Envia uma mensagem de teste para o admin"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    admin_id = os.getenv('ADMIN_TELEGRAM_ID')
    
    if not token or not admin_id:
        logger.error("❌ Token ou Admin ID não configurado")
        return False
    
    try:
        bot = Bot(token=token)
        admin_id = int(admin_id)
        
        logger.info(f"📨 Enviando mensagem de teste para {admin_id}...")
        message = await bot.send_message(
            chat_id=admin_id,
            text="✅ <b>Bot Monitor</b>\n\n"
                 "O bot está funcionando corretamente!\n"
                 f"Data/Hora: {asyncio.get_event_loop().time()}",
            parse_mode='HTML'
        )
        logger.info(f"✅ Mensagem enviada com sucesso! ID: {message.message_id}")
        return True
        
    except TelegramError as e:
        logger.error(f"❌ Erro ao enviar mensagem: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro inesperado: {e}")
        return False


async def main():
    """Função principal do monitor"""
    print("=" * 50)
    print("🔍 MONITOR DO BOT TELEGRAM")
    print("=" * 50)
    print()
    
    # Verifica status do bot
    if await check_bot_status():
        print()
        print("✅ Bot está funcionando!")
        
        # Pergunta se quer enviar mensagem de teste
        if len(sys.argv) > 1 and sys.argv[1] == "--test":
            print()
            await send_test_message()
    else:
        print()
        print("❌ Bot não está respondendo!")
        print()
        print("Possíveis causas:")
        print("1. Token inválido ou expirado")
        print("2. Problemas de conexão com a internet")
        print("3. Bot bloqueado pelo Telegram")
        print("4. Múltiplas instâncias rodando (conflito)")
    
    print()
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
