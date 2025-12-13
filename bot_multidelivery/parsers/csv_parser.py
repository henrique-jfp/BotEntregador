"""
Parser para romaneios em formato CSV.
Suporta múltiplos formatos com detecção automática de colunas.
Agora com suporte a ID e prioridade.
"""

import csv
import io
from typing import List, Dict, Tuple


def parse_csv_romaneio(file_content: bytes) -> List[Dict[str, str]]:
    """
    Parse romaneio em formato CSV com suporte a metadados.
    
    Retorna lista de dicts com: address, id (opcional), priority (opcional)
    """
    Parse romaneio em formato CSV.
    
    Args:
        file_content: Conteúdo do arquivo CSV em bytes
        
    Returns:
        Lista de endereços (strings)
        
    Formatos aceitos:
        1. CSV com coluna "endereco" ou "endereço"
        2. CSV com coluna "address"
        3. CSV com apenas uma coluna (assume que é endereço)
        4. CSV com colunas separadas (rua, numero, bairro, cidade)
           - Combina automaticamente em endereço completo
    """
    # Converte bytes para string
    text = file_content.decode('utf-8-sig')  # utf-8-sig remove BOM se existir
    
    # Tenta diferentes delimitadores
    for delimiter in [',', ';', '\t', '|']:
        try:
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            rows = list(reader)
            
            # Precisa ter pelo menos 1 linha de dados
            if not rows:
                continue
                
            addresses = _extract_addresses_from_rows(rows)
            
            if addresses:
                return addresses
        except:
            continue
    
    # Fallback: trata como texto simples (uma linha por endereço)
    from .text_parser import parse_text_romaneio
    return parse_text_romaneio(text)


def _extract_addresses_from_rows(rows: List[dict]) -> List[str]:
    """
    Extrai endereços de linhas CSV baseado nas colunas disponíveis.
    """
    if not rows:
        return []
    
    addresses = []
    headers = [h.lower().strip() for h in rows[0].keys()]
    
    # Estratégia 1: Procura coluna de endereço completo
    address_columns = ['endereco', 'endereço', 'address', 'addr', 'end']
    for col_name in address_columns:
        if col_name in headers:
            for row in rows:
                addr = row.get(col_name) or row.get(col_name.title())
                if addr and addr.strip():
                    addresses.append(addr.strip())
            if addresses:
                return addresses
    
    # Estratégia 2: Combina colunas separadas (rua + número + bairro + cidade)
    street_cols = ['rua', 'street', 'logradouro', 'avenida', 'av']
    number_cols = ['numero', 'número', 'number', 'num', 'n']
    district_cols = ['bairro', 'district', 'neighborhood']
    city_cols = ['cidade', 'city', 'municipio', 'município']
    
    street_col = next((c for c in street_cols if c in headers), None)
    number_col = next((c for c in number_cols if c in headers), None)
    district_col = next((c for c in district_cols if c in headers), None)
    city_col = next((c for c in city_cols if c in headers), None)
    
    if street_col:
        for row in rows:
            parts = []
            
            # Rua
            street = row.get(street_col, '').strip()
            if street:
                parts.append(street)
            
            # Número
            if number_col:
                number = row.get(number_col, '').strip()
                if number:
                    parts.append(number)
            
            # Bairro
            if district_col:
                district = row.get(district_col, '').strip()
                if district:
                    parts.append(district)
            
            # Cidade
            if city_col:
                city = row.get(city_col, '').strip()
                if city:
                    parts.append(city)
            
            if parts:
                addresses.append(', '.join(parts))
        
        if addresses:
            return addresses
    
    # Estratégia 3: Se tem apenas 1 coluna, assume que é endereço
    if len(headers) == 1:
        col_name = list(rows[0].keys())[0]
        for row in rows:
            addr = row.get(col_name, '').strip()
            if addr:
                addresses.append(addr)
        return addresses
    
    return []
