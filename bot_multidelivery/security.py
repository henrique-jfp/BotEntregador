import os
import logging
from fastapi import Security, HTTPException, status, Request
from fastapi.security.api_key import APIKeyHeader
from dotenv import load_dotenv

load_dotenv()

# Nome do Header que o Frontend deve enviar
# Sugestão: Configurar o frontend para enviar 'X-API-Key'
API_KEY_NAME = "X-API-Key"
API_KEY_HEADER = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# A chave secreta deve estar no .env
# Se não estiver, gera um aviso crítico no log mas usa valor default inseguro para não crashar
DEFAULT_SECRET = "TROQUE_ISSO_POR_UMA_CHAVE_FORTE_NO_ENV"
SERVER_API_KEY = os.getenv("API_SECRET_KEY", DEFAULT_SECRET)

logger = logging.getLogger("Security")

if SERVER_API_KEY == DEFAULT_SECRET:
    logger.warning("🚨 [SEGURANÇA] API_SECRET_KEY não configurada! Usando chave padrão insegura.")

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """
    Valida se a requisição tem a chave de API correta.
    """
    # 1. Se estiver em modo DEBUG/DEV explícito, pode ser opcional (comentado por segurança)
    # if os.getenv("DEBUG_MODE") == "true":
    #     return api_key

    # 2. Validação
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API ausente (Header X-API-Key)"
        )
            
    if api_key != SERVER_API_KEY:
        logger.warning(f"⛔ Tentativa de acesso com chave inválida: {api_key}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: Chave de API inválida"
        )
    
    return api_key
