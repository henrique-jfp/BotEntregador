"""
Parser para romaneios em formato texto (manual).
Aceita múltiplos formatos: um por linha, separados por vírgula dupla, ponto-e-vírgula, etc.
"""

from typing import List, Dict
import re


def parse_text_romaneio(text: str) -> List[Dict[str, str]]:
    """
    Parse romaneio em formato texto com suporte a múltiplos formatos.
    
    Args:
        text: String com endereços em qualquer formato
        
    Returns:
        Lista de endereços (strings)
        
    Exemplos aceitos:
        - "Rua A, 123\nRua B, 456" (um por linha)
        - "1. Av. Paulista, 1000\n2. Rua Augusta, 500" (numerados)
        - "📦 Rua X, 100\n📦 Rua Y, 200" (com emojis)
        - "Rua A, 123; Rua B, 456; Rua C, 789" (separados por ;)
        - "Rua A, 123 | Rua B, 456 | Rua C, 789" (separados por |)
        - Texto corrido com múltiplos endereços
    """
    addresses = []
    
    # Remove emojis comuns no texto inteiro primeiro
    text = re.sub(r'[📦🏠🎯📍✅❌💰🚗🚴]', '', text).strip()
    
    # ═══════════════════════════════════════════════════════════
    # ESTRATÉGIA 1: Detecta separadores explícitos
    # ═══════════════════════════════════════════════════════════
    
    # Tenta ponto-e-vírgula (;)
    if ';' in text and text.count(';') >= 2:
        parts = text.split(';')
        for part in parts:
            cleaned = clean_address(part)
            if cleaned and len(cleaned) > 10:  # Mínimo 10 chars
                addresses.append(cleaned)
        if addresses:
            return addresses
    
    # Tenta pipe (|)
    if '|' in text and text.count('|') >= 2:
        parts = text.split('|')
        for part in parts:
            cleaned = clean_address(part)
            if cleaned and len(cleaned) > 10:
                addresses.append(cleaned)
        if addresses:
            return addresses
    
    # ═══════════════════════════════════════════════════════════
    # ESTRATÉGIA 2: Quebra por linha
    # ═══════════════════════════════════════════════════════════
    lines = text.strip().split('\n')
    if len(lines) >= 2:  # Se tem múltiplas linhas
        for line in lines:
            cleaned = clean_address(line)
            if cleaned and len(cleaned) > 10:
                addresses.append(cleaned)
        if addresses:
            return addresses
    
    # ═══════════════════════════════════════════════════════════
    # ESTRATÉGIA 3: Detecta padrão "Número. Endereço" (ex: "1. Rua A, 123 2. Rua B, 456")
    # ═══════════════════════════════════════════════════════════
    pattern_numbered = r'\d+[\.\)]\s*([^0-9]+?)(?=\d+[\.\)]|$)'
    matches = re.findall(pattern_numbered, text)
    if matches and len(matches) >= 2:
        for match in matches:
            cleaned = clean_address(match)
            if cleaned and len(cleaned) > 10:
                addresses.append(cleaned)
        if addresses:
            return addresses
    
    # ═══════════════════════════════════════════════════════════
    # ESTRATÉGIA 4: Detecta padrão de endereço completo no texto corrido
    # Procura por: Rua/Av/Travessa + número + vírgula + bairro + vírgula
    # ═══════════════════════════════════════════════════════════
    # Padrão: Logradouro (Rua/Av/etc) + nome + número + vírgula + bairro/cidade
    pattern_address = r'(?:Rua|Avenida|Av\.?|Travessa|Trv\.?|Alameda|Praça|Estrada|Rod\.?|Rodovia)[^,]+?,\s*\d+[^,]*,\s*[^,]+?(?:,\s*[A-Z]{2})?'
    matches = re.findall(pattern_address, text, re.IGNORECASE)
    if matches and len(matches) >= 2:
        for match in matches:
            cleaned = clean_address(match)
            if cleaned and len(cleaned) > 10:
                addresses.append(cleaned)
        if addresses:
            return addresses
    
    # ═══════════════════════════════════════════════════════════
    # ESTRATÉGIA 5: Fallback - quebra por vírgula dupla ", " seguida de maiúscula
    # Ex: "Rua A, 123, Centro, Rua B, 456, Botafogo" → detecta início de novo endereço
    # ═══════════════════════════════════════════════════════════
    # Procura por ", " seguido de letra maiúscula (provável início de logradouro)
    parts = re.split(r',\s+(?=[A-Z](?:ua|venida|v\.|ravessa))', text)
    if len(parts) >= 2:
        for part in parts:
            cleaned = clean_address(part)
            if cleaned and len(cleaned) > 10:
                addresses.append(cleaned)
        if addresses:
            return addresses
    
    # ═══════════════════════════════════════════════════════════
    # Se nada funcionou, retorna o texto inteiro como 1 endereço
    # (usuário pode ter colado apenas 1 endereço)
    # ═══════════════════════════════════════════════════════════
    cleaned = clean_address(text)
    if cleaned and len(cleaned) > 10:
        addresses.append(cleaned)
    
    return addresses


def clean_address(text: str) -> str:
    """
    Limpa um endereço: remove numeração, espaços extras, etc.
    
    Args:
        text: Endereço bruto
        
    Returns:
        Endereço limpo
    """
    # Remove whitespace excessivo
    text = text.strip()
    
    # Remove numeração no início (1., 2), 3-, etc)
    text = re.sub(r'^\d+[\.\)\-\:]\s*', '', text)
    
    # Remove múltiplos espaços
    text = re.sub(r'\s+', ' ', text)
    
    # Remove vírgulas duplicadas
    text = re.sub(r',+', ',', text)
    
    # Remove vírgula no final
    text = text.rstrip(',').strip()
    
    return text
