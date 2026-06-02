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
    
    # Tenta delimitadores. Só aceita um delimiter se gerar múltiplas colunas
    for delimiter in [',', ';', '\t', '|']:
        try:
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            rows = list(reader)
            fieldnames = reader.fieldnames or []
            if rows and len(fieldnames) > 1:
                return _extract_from_rows(rows)
        except Exception:
            continue
    
    return []


def _extract_from_rows(rows: List[dict]) -> List[Dict[str, str]]:
    """Extrai pacotes das linhas CSV"""
    if not rows:
        return []
    packages = []

    # Construir mapeamento seguro entre header lower -> header original
    original_headers = list(rows[0].keys())
    headers = [h.lower().strip() for h in original_headers]
    lower_to_original = {h.lower().strip(): h for h in original_headers}

    # Mapeia colunas (inclui NF e lat/lon)
    id_cols = ['id', 'package_id', 'pacote_id', 'codigo', 'nf', 'nota', 'invoice']
    priority_cols = ['prioridade', 'priority', 'prio']
    addr_cols = ['endereco', 'endereço', 'address', 'addr', 'endereco completo', 'endereço completo']
    bairro_cols = ['bairro', 'distrito', 'neighborhood', 'district']
    lat_cols = ['latitude', 'lat']
    lon_cols = ['longitude', 'lon', 'lng', 'long']

    def find_col(candidate_list):
        for low in headers:
            for cand in candidate_list:
                if cand in low:
                    return lower_to_original.get(low)
        return None

    id_col = find_col(id_cols)
    priority_col = find_col(priority_cols)
    addr_col = find_col(addr_cols)
    bairro_col = find_col(bairro_cols)
    lat_col = find_col(lat_cols)
    lon_col = find_col(lon_cols)
    
    # Estratégia 1: BAIRRO + ENDEREÇO (formato simples e preciso!)
    if bairro_col and addr_col:
        for i, row in enumerate(rows, start=1):
            bairro = (row.get(bairro_col) or '').strip()
            endereco = (row.get(addr_col) or '').strip()

            if not endereco:
                continue

            # Combina bairro + endereço
            if bairro:
                full_address = f"{endereco}, {bairro}, Rio de Janeiro"
            else:
                full_address = f"{endereco}, Rio de Janeiro"

            pkg_id = (row.get(id_col) or f'CSV{i:03d}').strip() if id_col else f'CSV{i:03d}'
            priority = 'normal'

            if priority_col and row.get(priority_col):
                p = (row.get(priority_col) or '').strip().lower()
                priority = p if p in ['low', 'normal', 'high', 'urgent'] else 'normal'

            # Lat/Lon se disponíveis
            lat = None
            lon = None
            if lat_col and row.get(lat_col):
                try:
                    lat = float(str(row.get(lat_col)).strip().replace(',', '.'))
                except:
                    lat = None
            if lon_col and row.get(lon_col):
                try:
                    lon = float(str(row.get(lon_col)).strip().replace(',', '.'))
                except:
                    lon = None

            pkg = {
                'address': full_address,
                'id': pkg_id,
                'priority': priority
            }
            if lat is not None and lon is not None:
                pkg['lat'] = lat
                pkg['lon'] = lon

            packages.append(pkg)
    
    # Estratégia 2: Coluna de endereço completo (sem bairro separado)
    elif addr_col:
        for i, row in enumerate(rows, start=1):
            addr = (row.get(addr_col) or '').strip()
            if not addr:
                continue

            pkg_id = (row.get(id_col) or f'CSV{i:03d}').strip() if id_col else f'CSV{i:03d}'
            priority = 'normal'

            if priority_col and row.get(priority_col):
                p = (row.get(priority_col) or '').strip().lower()
                priority = p if p in ['low', 'normal', 'high', 'urgent'] else 'normal'

            lat = None
            lon = None
            if lat_col and row.get(lat_col):
                try:
                    lat = float(str(row.get(lat_col)).strip().replace(',', '.'))
                except:
                    lat = None
            if lon_col and row.get(lon_col):
                try:
                    lon = float(str(row.get(lon_col)).strip().replace(',', '.'))
                except:
                    lon = None

            pkg = {
                'address': addr,
                'id': pkg_id,
                'priority': priority
            }
            if lat is not None and lon is not None:
                pkg['lat'] = lat
                pkg['lon'] = lon

            packages.append(pkg)
    
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


def parse_csv_addresses(file_content: bytes) -> List[Dict[str, str]]:
    """
    Função de compatibilidade para import legado.
    Retorna a mesma saída do parse_csv_romaneio.
    """
    return parse_csv_romaneio(file_content)
