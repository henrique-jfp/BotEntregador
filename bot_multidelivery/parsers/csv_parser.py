"""
Parser CSV - Suporta múltiplos formatos de romaneio
"""
from typing import List, Dict
import csv
import io


def parse_csv_romaneio(file_content: bytes) -> List[Dict[str, str]]:
    """
    Parse CSV com suporte a id e priority.
    
    Retorna: List[Dict] com keys: address, id, priority
    
    Formatos aceitos:
    - id,endereco,prioridade
    - endereco
    - rua,numero,bairro (combina automaticamente)
    """
    text = file_content.decode('utf-8-sig')
    
    # Tenta delimitadores
    for delimiter in [',', ';', '\t', '|']:
        try:
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            rows = list(reader)
            if rows:
                return _extract_from_rows(rows)
        except:
            continue
    
    return []


def _extract_from_rows(rows: List[dict]) -> List[Dict[str, str]]:
    """Extrai pacotes das linhas CSV"""
    if not rows:
        return []
    
    packages = []
    headers = [h.lower().strip() for h in rows[0].keys()]
    
    # Mapeia colunas
    id_cols = ['id', 'package_id', 'pacote_id', 'codigo']
    priority_cols = ['prioridade', 'priority', 'prio']
    addr_cols = ['endereco', 'endereço', 'address', 'addr']
    bairro_cols = ['bairro', 'distrito', 'neighborhood', 'district']
    
    id_col = next((c for c in headers if any(ic in c for ic in id_cols)), None)
    priority_col = next((c for c in headers if any(pc in c for pc in priority_cols)), None)
    addr_col = next((c for c in headers if any(ac in c for ac in addr_cols)), None)
    bairro_col = next((c for c in headers if any(bc in c for bc in bairro_cols)), None)
    
    # Estratégia 1: BAIRRO + ENDEREÇO (formato simples e preciso!)
    if bairro_col and addr_col:
        for i, row in enumerate(rows, start=1):
            bairro = row.get(bairro_col, '').strip()
            endereco = row.get(addr_col, '').strip()
            
            if not endereco:
                continue
            
            # Combina bairro + endereço
            if bairro:
                full_address = f"{endereco}, {bairro}, Rio de Janeiro"
            else:
                full_address = f"{endereco}, Rio de Janeiro"
            
            pkg_id = row.get(id_col, f'CSV{i:03d}').strip() if id_col else f'CSV{i:03d}'
            priority = 'normal'
            
            if priority_col and row.get(priority_col):
                p = row.get(priority_col, '').strip().lower()
                p3iority = p if p in ['low', 'normal', 'high', 'urgent'] else 'normal'
            
            packages.append({
                'address': full_address,
                'id': pkg_id,
                'priority': priority
            })
    
    # Estratégia 2: Coluna de endereço completo (sem bairro separado)
    elif addr_col:
        for i, row in enumerate(rows, start=1):
            addr = row.get(addr_col, '').strip()
            if not addr:
                continue
            
            pkg_id = row.get(id_col, f'CSV{i:03d}').strip() if id_col else f'CSV{i:03d}'
            priority = 'normal'
            
            if priority_col and row.get(priority_col):
                p = row.get(priority_col, '').strip().lower()
                priority = p if p in ['low', 'normal', 'high', 'urgent'] else 'normal'
            
            packages.append({
                'address': addr,
                'id': pkg_id,
                'priority': priority
            })
    
    # Estratégia 2: Colunas separadas (rua, numero, bairro, cidade)
    elif any(h in headers for h in ['rua', 'street', 'numero', 'number']):
        for i, row in enumerate(rows, start=1):
            parts = []
            for key in ['rua', 'street', 'logradouro']:
                if key in headers and row.get(key):
                    parts.append(row[key].strip())
                    break
            
            for key in ['numero', 'number', 'num']:
                if key in headers and row.get(key):
                    parts.append(row[key].strip())
                    break
            
            for key in ['bairro', 'distrito', 'district']:
                if key in headers and row.get(key):
                    parts.append(row[key].strip())
                    break
            
            for key in ['cidade', 'city']:
                if key in headers and row.get(key):
                    parts.append(row[key].strip())
                    break
            
            if parts:
                packages.append({
                    'address': ', '.join(parts),
                    'id': f'CSV{i:03d}',
                    'priority': 'normal'
                })
    
    # Estratégia 3: Coluna única
    elif len(headers) == 1:
        col = list(rows[0].keys())[0]
        for i, row in enumerate(rows, start=1):
            addr = row.get(col, '').strip()
            if addr:
                packages.append({
                    'address': addr,
                    'id': f'CSV{i:03d}',
                    'priority': 'normal'
                })
    
    return packages
