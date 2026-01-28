"""
Parser Excel da Shopee - Extrai entregas do romaneio oficial
"""
from typing import List, Dict
from dataclasses import dataclass
import openpyxl


@dataclass
class ShopeeDelivery:
    """Entrega individual do romaneio Shopee"""
    tracking: str
    address: str
    bairro: str
    city: str
    latitude: float
    longitude: float
    stop: int
    customer_name: str = ""
    phone: str = ""


def parse_shopee_excel(file_path: str) -> List[Dict[str, any]]:
    """
    Parse Excel da Shopee (formato DD-MM-YYYY Nome.xlsx)
    
    Extrai:
    - Tracking code
    - Endereço completo
    - Lat/Lon (embutidos na planilha)
    - STOP (agrupamento de mesmo prédio)
    
    Returns:
        Lista de dicts com: id, address, lat, lon, stop
    """
    try:
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active
        
        # Procura cabeçalhos (geralmente na linha 1 ou 2)
        headers = {}
        header_row = None
        
        for row in range(1, min(5, ws.max_row + 1)):
            for col in range(1, ws.max_column + 1):
                cell_value = ws.cell(row, col).value
                if cell_value and isinstance(cell_value, str):
                    cell_lower = cell_value.lower().strip()
                    
                    # Tracking: SPX TN, tracking, código, AT ID
                    if any(x in cell_lower for x in ['spx tn', 'spx_tn', 'tracking', 'código', 'at id', 'atid']):
                        headers['tracking'] = col
                        header_row = row
                    # Endereço: Destination, address, endereço
                    elif any(x in cell_lower for x in ['destination', 'endereço', 'endereco', 'address']):
                        headers['address'] = col
                        if header_row is None:  # Define header_row se ainda não definido
                            header_row = row
                    # Bairro: neighborhood, bairro, distrito, district
                    elif any(x in cell_lower for x in ['bairro', 'distrito', 'district', 'neighborhood', 'neighbour']):
                        headers['bairro'] = col
                        if header_row is None:
                            header_row = row
                    # Cidade
                    elif 'city' in cell_lower or 'cidade' in cell_lower:
                        headers['city'] = col
                    # Latitude
                    elif 'latitude' in cell_lower or (cell_lower == 'lat'):
                        headers['lat'] = col
                    # Longitude
                    elif 'longitude' in cell_lower or (cell_lower in ['lng', 'lon', 'long']):
                        headers['lon'] = col
                    # Stop (Sequence ou Stop)
                    elif any(x in cell_lower for x in ['stop', 'parada', 'sequence']):
                        headers['stop'] = col
                    # Cliente
                    elif any(x in cell_lower for x in ['nome', 'cliente', 'customer', 'name']):
                        headers['customer'] = col
                    # Telefone
                    elif any(x in cell_lower for x in ['telefone', 'phone', 'tel']):
                        headers['phone'] = col
        
        # Validação flexível: precisa de pelo menos tracking OU address
        if not header_row:
            raise ValueError("Cabeçalhos não encontrados. Formato inválido.")
        
        if 'tracking' not in headers and 'address' not in headers:
            raise ValueError("Não encontrei coluna de Tracking (SPX TN) nem Endereço (Destination).")
        
        # Extrai dados
        addresses = []
        stop_counter = 1
        
        for row in range(header_row + 1, ws.max_row + 1):
            # Pega tracking (pode ser SPX TN ou outra coluna)
            tracking = None
            if 'tracking' in headers:
                tracking_cell = ws.cell(row, headers['tracking'])
                if tracking_cell.value:
                    tracking = str(tracking_cell.value).strip()
            
            # Pega endereço (pode ser Destination)
            address = ""
            if 'address' in headers:
                addr_cell = ws.cell(row, headers['address'])
                if addr_cell.value:
                    address = str(addr_cell.value).strip()
            
            # Se não tem tracking nem endereço, pula linha
            if not tracking and not address:
                continue
            
            # Se não tem tracking, gera um ID
            if not tracking:
                tracking = f"PKG{row:04d}"
            
            bairro = ""
            if 'bairro' in headers:
                bairro_cell = ws.cell(row, headers['bairro'])
                if bairro_cell.value:
                    bairro = str(bairro_cell.value).strip()
            
            city = ""
            if 'city' in headers:
                city_cell = ws.cell(row, headers['city'])
                if city_cell.value:
                    city = str(city_cell.value).strip()
            
            # Lat/Lon (podem estar embutidos ou precisar geocoding)
            lat = None
            lon = None
            
            if 'lat' in headers:
                lat_cell = ws.cell(row, headers['lat']).value
                if lat_cell:
                    try:
                        lat = float(lat_cell)
                    except:
                        pass
            
            if 'lon' in headers:
                lon_cell = ws.cell(row, headers['lon']).value
                if lon_cell:
                    try:
                        lon = float(lon_cell)
                    except:
                        pass
            
            # STOP (agrupamento)
            stop = stop_counter
            if 'stop' in headers:
                stop_cell = ws.cell(row, headers['stop']).value
                if stop_cell:
                    try:
                        stop = int(stop_cell)
                    except:
                        pass
            
            # Cliente e telefone (opcional)
            customer = ""
            if 'customer' in headers:
                customer = str(ws.cell(row, headers['customer']).value or '').strip()
            
            phone = ""
            if 'phone' in headers:
                phone = str(ws.cell(row, headers['phone']).value or '').strip()
            
            if address:  # Só adiciona se tem endereço
                addresses.append({
                    'id': tracking,
                    'address': f"{address}, {bairro}, {city}".strip(', '),
                    'lat': lat,
                    'lon': lon,
                    'stop': stop,
                    'bairro': bairro,
                    'city': city,
                    'customer': customer,
                    'phone': phone,
                    'tracking': tracking
                })
                
                stop_counter += 1
        
        return addresses
        
    except Exception as e:
        raise Exception(f"Erro ao parsear Excel Shopee: {str(e)}")


class ShopeeRomaneioParser:
    """Parser compatível com código legado"""
    
    @staticmethod
    def parse(file_path: str) -> List[ShopeeDelivery]:
        """Parse e retorna lista de ShopeeDelivery objects"""
        data = parse_shopee_excel(file_path)
        
        deliveries = []
        for item in data:
            delivery = ShopeeDelivery(
                tracking=item['tracking'],
                address=item['address'],
                bairro=item.get('bairro', ''),
                city=item.get('city', ''),
                latitude=item.get('lat', 0.0),
                longitude=item.get('lon', 0.0),
                stop=item.get('stop', 0),
                customer_name=item.get('customer', ''),
                phone=item.get('phone', '')
            )
            deliveries.append(delivery)
        
        return deliveries
