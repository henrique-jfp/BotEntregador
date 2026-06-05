"""
🔗 ROUTER DE WEBHOOK - Integração Direta com Telegram
Substitui o Long Polling por notificações PUSH (FastAPI)
"""
import logging
from fastapi import APIRouter, Request, Header, HTTPException
from telegram import Update
import os

logger = logging.getLogger("WebhookRouter")
router = APIRouter(prefix="/webhook", tags=["Telegram Webhook"])

# Token secreto para validar que a requisição vem do Telegram
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "minha-chave-secreta-v2")

@router.post("/telegram")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(None)):
    """
    Recebe atualizações do Telegram.
    A validação por 'secret_token' garante que apenas o Telegram consiga postar aqui.
    """
    # 1. Validar token de segurança (opcional mas recomendado)
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        logger.warning(f"⚠️ Tentativa de acesso não autorizada ao webhook! Token: {x_telegram_bot_api_secret_token}")
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        from ..bot import get_telegram_app
        bot_app = get_telegram_app()
        
        if not bot_app:
            return {"status": "error", "message": "Bot application not initialized"}

        # 2. Processar o Update
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)
        
        # 3. Processar de forma assíncrona
        # Nota: process_update é assíncrono no python-telegram-bot v20+
        await bot_app.process_update(update)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"❌ Erro ao processar webhook do Telegram: {e}")
        return {"status": "error", "message": str(e)}
