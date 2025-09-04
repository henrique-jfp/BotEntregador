import os, base64, json, asyncio, logging
from typing import List, Optional
from google.cloud import vision
from google.oauth2 import service_account
import google.generativeai as genai
from PIL import Image
from bot.utils.security import SecurityValidator

logger = logging.getLogger("bot_delivery.ocr")

_vision_client = None
_gemini_model = None

def setup_vision_client():
    global _vision_client
    if _vision_client is not None:
        return _vision_client
    try:
        json_base64 = os.getenv('GOOGLE_VISION_CREDENTIALS_JSON_BASE64')
        if json_base64:
            try:
                json_base64 = json_base64.strip().strip('"').replace('\n','').replace('\r','').replace(' ','')
                missing_padding = len(json_base64) % 4
                if missing_padding:
                    json_base64 += '=' * (4 - missing_padding)
                decoded_json = base64.b64decode(json_base64).decode('utf-8')
                info = json.loads(decoded_json)
                credentials = service_account.Credentials.from_service_account_info(info)
                _vision_client = vision.ImageAnnotatorClient(credentials=credentials)
                logger.info("Vision client configurado via Base64")
                return _vision_client
            except Exception as e:
                logger.error(f"Erro credenciais Base64: {e}")
        json_env = os.getenv('GOOGLE_VISION_CREDENTIALS_JSON')
        if json_env:
            try:
                info = json.loads(json_env)
                credentials = service_account.Credentials.from_service_account_info(info)
                _vision_client = vision.ImageAnnotatorClient(credentials=credentials)
                logger.info("Vision client configurado via JSON env")
                return _vision_client
            except Exception as e:
                logger.error(f"Erro credenciais JSON: {e}")
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if creds_path and os.path.exists(creds_path):
            credentials = service_account.Credentials.from_service_account_file(creds_path)
            _vision_client = vision.ImageAnnotatorClient(credentials=credentials)
            logger.info("Vision client via arquivo")
            return _vision_client
        logger.warning("Credenciais Vision ausentes")
    except Exception as e:
        logger.error(f"Falha setup vision: {e}")
    return None


def setup_gemini_model():
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        logger.info('Sem GOOGLE_API_KEY para Gemini')
        return None
    try:
        genai.configure(api_key=api_key)
        _gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info('Modelo Gemini configurado')
        return _gemini_model
    except Exception as e:
        logger.error(f'Falha modelo Gemini: {e}')
        return None


class ImageProcessor:
    @staticmethod
    async def download(bot, file_id: str) -> Optional[bytes]:
        try:
            file = await bot.get_file(file_id)
            ba = await file.download_as_bytearray()
            return bytes(ba)
        except Exception as e:
            logger.error(f"Erro download {file_id}: {e}")
            return None

    @staticmethod
    async def ocr(bot, photo_ids: List[str]) -> str:
        vision_client = setup_vision_client()
        if vision_client:
            texts = []
            for fid in photo_ids:
                img_bytes = await ImageProcessor.download(bot, fid)
                if not img_bytes:
                    continue
                if not await SecurityValidator.validate_image(img_bytes):
                    continue
                image = vision.Image(content=img_bytes)
                try:
                    resp = vision_client.text_detection(image=image)
                    if resp.error.message:
                        logger.warning(f"Vision erro: {resp.error.message}")
                        continue
                    if resp.text_annotations:
                        texts.append(resp.text_annotations[0].description)
                except Exception as e:
                    logger.error(f"Vision falhou: {e}")
            if texts:
                return '\n'.join(texts)
            logger.info('Vision vazio; fallback Gemini')
        gemini_model = setup_gemini_model()
        if gemini_model:
            results = []
            for fid in photo_ids:
                img_bytes = await ImageProcessor.download(bot, fid)
                if not img_bytes:
                    continue
                if not await SecurityValidator.validate_image(img_bytes):
                    continue
                try:
                    b64 = base64.b64encode(img_bytes).decode('utf-8')
                    prompt = (
                        "Extraia exatamente o texto de endereços da imagem.\n"
                        "1. NÃO traduza, NÃO corrija.\n"
                        "2. Preserve números, hífens, CEP.\n"
                        "3. Uma linha por endereço.\n"
                        "4. NÃO expanda abreviações.\n"
                        "Saída: apenas linhas."
                    )
                    resp = await asyncio.to_thread(
                        gemini_model.generate_content,
                        [ {'mime_type': 'image/jpeg', 'data': b64}, prompt ]
                    )
                    if hasattr(resp, 'text') and resp.text:
                        results.append(resp.text.strip())
                except Exception as e:
                    logger.error(f"Gemini falhou: {e}")
            if results:
                return '\n'.join(results)
        return ''
