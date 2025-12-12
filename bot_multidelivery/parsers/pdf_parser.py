"""
Parser para romaneios em formato PDF.
Suporta PDFs com texto extraível e PDFs escaneados (via OCR).
"""

from typing import List
import re


def parse_pdf_romaneio(file_content: bytes) -> List[str]:
    """
    Parse romaneio em formato PDF.
    
    Args:
        file_content: Conteúdo do arquivo PDF em bytes
        
    Returns:
        Lista de endereços (strings)
        
    Fluxo:
        1. Tenta extrair texto do PDF (PDFs digitais)
        2. Se falhar, usa OCR (PDFs escaneados/imagens)
        3. Parse o texto extraído procurando padrões de endereço
    """
    text = ""
    
    # Tenta extrair texto do PDF
    try:
        import pdfplumber
        import io
        
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except ImportError:
        # Fallback: PyPDF2
        try:
            import PyPDF2
            import io
            
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except ImportError:
            raise ImportError(
                "Instale 'pdfplumber' ou 'PyPDF2': "
                "pip install pdfplumber"
            )
    
    # Se não conseguiu extrair texto, pode ser PDF escaneado (precisa OCR)
    if not text.strip():
        text = _extract_text_with_ocr(file_content)
    
    # Parse o texto extraído
    addresses = _extract_addresses_from_text(text)
    
    return addresses


def _extract_text_with_ocr(file_content: bytes) -> str:
    """
    Extrai texto de PDF escaneado usando OCR.
    Requer: pytesseract + pdf2image
    """
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        
        # Converte PDF para imagens
        images = convert_from_bytes(file_content)
        
        # OCR em cada página
        text = ""
        for img in images:
            page_text = pytesseract.image_to_string(img, lang='por')
            text += page_text + "\n"
        
        return text
    except ImportError:
        raise ImportError(
            "Para PDFs escaneados, instale: "
            "pip install pytesseract pdf2image\n"
            "E configure Tesseract: https://github.com/tesseract-ocr/tesseract"
        )


def _extract_addresses_from_text(text: str) -> List[str]:
    """
    Extrai endereços de texto usando padrões comuns.
    
    Procura por:
    - Linhas com padrões de endereço (Rua/Av + número)
    - Linhas após marcadores (1., 2., -, *, etc)
    - Linhas com CEP
    """
    addresses = []
    
    # Padrão de endereço brasileiro
    # Ex: "Rua das Flores, 123", "Av. Paulista 1000"
    address_pattern = re.compile(
        r'(?:Rua|R\.|Avenida|Av\.|Alameda|Al\.|Travessa|Trav\.|Praça|Pça\.)'
        r'[^,\n]+(?:,\s*\d+|[\s]+\d+)',
        re.IGNORECASE
    )
    
    # Procura endereços explícitos
    matches = address_pattern.findall(text)
    addresses.extend([m.strip() for m in matches])
    
    # Se não encontrou endereços explícitos, trata como texto simples
    if not addresses:
        from .text_parser import parse_text_romaneio
        return parse_text_romaneio(text)
    
    return addresses
