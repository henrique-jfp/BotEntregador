"""
Parser para romaneios em formato texto (manual).
Aceita um endereço por linha.
"""

from typing import List, Dict
import re


def parse_text_romaneio(text: str) -> List[Dict[str, str]]:
    """
    Parse romaneio em formato texto.
    
    Args:
        text: String com endereços separados por quebra de linha
        
    Returns:
        Lista de endereços (strings)
        
    Exemplos aceitos:
        - "Rua A, 123\nRua B, 456"
        - "1. Av. Paulista, 1000\n2. Rua Augusta, 500"
        - "📦 Rua X, 100\n📦 Rua Y, 200"
    """
    addresses = []
    
    for line in text.strip().split('\n'):
        # Remove whitespace
        line = line.strip()
        
        # Pula linhas vazias
        if not line:
            continue
            
        # Remove numeração (ex: "1. ", "1) ", "1- ")
        import re
        line = re.sub(r'^\d+[\.\)\-]\s*', '', line)
        
        # Remove emojis comuns (📦, 🏠, etc)
        line = re.sub(r'[📦🏠🎯📍✅]', '', line).strip()
        
        # Adiciona se não estiver vazio
        if line:
            addresses.append(line)
    
    return addresses
