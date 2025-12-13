"""
Parser para romaneios em formato CSV.
Suporta múltiplos formatos com detecção automática de colunas.
Agora com suporte a ID e prioridade.
"""

import csv
import io
from typing import List, Dict


def parse_csv_romaneio(file_content: bytes) -> List[Dict[str, str]]:
    """
    Parse romaneio em formato CSV com suporte a metadados.
    
    Args:
        file_content: Conteúdo do arquivo CSV em bytes
        
    Returns:
        Lista de dicts com:
        - address: Endereço (obrigatório)
        - id: ID do pacote (opcional, gera automático se não tiver)
        - priority: Prioridade (opcional, padrão: normal)
        
    Formatos aceitos:
        1. id,endereco,prioridade
        2. endereco,prioridade
        3. endereco (apenas)
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


def _extract_addresses_from_rows(rows: List[dict]) -> List[Dict[str, str]]:
    """
    Extrai endereços e metadados de linhas CSV.
    
    Returns:
        Lista de dicts com: address, id (opcional), priority (opcional)
    """
    if not rows:
        return []
    
    paMapear colunas
    id_cols = ['id', 'package_id', 'pacote_id', 'codigo', 'code']
    priority_cols = ['prioridade', 'priority', 'prio']
    address_columns = ['endereco', 'endereço', 'address', 'addr', 'end']
    
    id_col = next((c for c in id_cols if c in headers), None)
    priority_col = next((c for c in priority_cols if c in headers), None)
    
    # Estratégia 1: Procura coluna de endereço completo
    for col_name in address_columns:
        if col_name in headers:
            for i, row in enumerate(rows):
                addr = row.get(col_name) or row.get(col_name.title())
                if addr and addr.strip():
                    package = {
                        'address': addr.strip(),
                        'id': row.get(id_col, f'PKG{i:03d}') if id_col else f'PKG{i:03d}',
                        'priority': row.get(priority_col, 'normal').lower() if priority_col else 'normal'
                    }
                    packages.append(package)
            if packages:
                return packagdr.strip():
                    addresses.append(addr.strip())
            if addresses:
                return addresses
    
    # Estrati, row in enumerate(rows):
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
                package = {
                    'address': ', '.join(parts),
                    'id': row.get(id_col, f'PKG{i:03d}') if id_col else f'PKG{i:03d}',
                    'priority': row.get(priority_col, 'normal').lower() if priority_col else 'normal'
                }
                packages.append(package)
        
        if packages:
            i, row in enumerate(rows):
            addr = row.get(col_name, '').strip()
            if addr:
                package = {
                    'address': addr,
                    'id': f'PKG{i:03d}',
                    'priority': 'normal'
                }
                packages.append(package)
        return packag row.get(city_col, '').strip()
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
