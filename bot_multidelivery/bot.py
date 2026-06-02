# -*- coding: utf-8 -*-
"""
🤖 BOT TELEGRAM - MÓDULO SLIM (Mini App Focus)
----------------------------------------------
Este arquivo substitui o antigo monolito de 4000+ linhas.
Seu único propósito é autenticar o usuário e abrir o WebApp.

"O código mais rápido é aquele que não existe."
"""
import os
import logging
import time
from telegram.ext import Application, CommandHandler
from telegram.error import Conflict
from .config import BotConfig
from .handlers import common

# Configuração de Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("SlimBot")

def create_application():
    """Cria a aplicação Telegram minimalista"""
    
    # 1. Obter Token
    token = os.getenv('TELEGRAM_BOT_TOKEN') or BotConfig.TELEGRAM_TOKEN
    
    if not token or str(token).startswith("123456"):
        logger.error("🛑 Erro Fatal: Token do Telegram inválido ou não configurado.")
        logger.error("👉 Edite o arquivo .env com seu token real.")
        return None

    # 2. Builder Otimizado
    app = (
        Application.builder()
        .token(token)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .build()
    )

    # 3. Registrar Rotas de Entrada
    # Toda a lógica de negócio complexa foi movida para api_routes.py
    app.add_handler(CommandHandler("start", common.cmd_start))
    app.add_handler(CommandHandler("help", common.cmd_help))
    app.add_handler(CommandHandler("saldo", common.cmd_saldo))
    # app.add_handler(CommandHandler("ping", common.cmd_ping)) # Futuro

    return app

def run_bot():
    """Loop principal de execução do bot"""
    logger.info("🚀 Iniciando Bot em Modo SLIM (WebApp Only)...")
    
    max_retries = 10
    retry_count = 0
    # Permitir desabilitar o bot em ambientes onde não queremos polling (ex: production com webhook)
    telegram_enabled = os.getenv('TELEGRAM_ENABLED', '1').lower()
    if telegram_enabled in ('0', 'false', 'no'):
        logger.warning('⛔ Telegram bot startup disabled via TELEGRAM_ENABLED env var')
        return

    while retry_count < max_retries:
        try:
            app = create_application()
            if not app:
                return # Falha fatal de config

            logger.info("✅ Bot conectado! Aguardando comandos /start...")

            # drop_pending_updates=True evita processar mensagens antigas acumuladas
            # enquanto o bot estava desligado ou reiniciando
            try:
                app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query"])
            except Conflict as c:
                # Erro comum quando outro processo já está usando o mesmo token
                logger.error("❌ Telegram conflict detected: outro processo está consumindo getUpdates para este token.")
                logger.error(f"Detalhe: {c}")
                logger.error("🛑 Parando inicialização do bot para evitar loops. Verifique instâncias em execução ou use TELEGRAM_ENABLED=0.")
                return

            break

        except Exception as e:
            logger.error(f"⚠️ Falha na conexão com Telegram (Tentativa {retry_count+1}/{max_retries})")
            logger.error(f"📝 Erro: {e}")
            retry_count += 1
            time.sleep(5)
            
    if retry_count >= max_retries:
        logger.critical("💀 Desistindo após múltiplas falhas. Verifique sua conexão ou token.")

if __name__ == "__main__":
    run_bot()


