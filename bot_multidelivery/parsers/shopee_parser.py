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
                    
                    if 'tracking' in cell_lower or 'código' in cell_lower:
                        headers['tracking'] = col
                        header_row = row
                    elif 'endereço' in cell_lower or 'address' in cell_lower:
                        headers['address'] = col
                    elif 'bairro' in cell_lower or 'distrito' in cell_lower:
                        headers['bairro'] = col
                    elif 'cidade' in cell_lower or 'city' in cell_lower:
                        headers['city'] = col
                    elif 'latitude' in cell_lower or 'lat' in cell_lower:
                        headers['lat'] = col
                    elif 'longitude' in cell_lower or 'lng' in cell_lower or 'long' in cell_lower:
                        headers['lon'] = col
                    elif 'stop' in cell_lower or 'parada' in cell_lower:
                        headers['stop'] = col
                    elif 'nome' in cell_lower or 'cliente' in cell_lower or 'customer' in cell_lower:
                        headers['customer'] = col
                    elif 'telefone' in cell_lower or 'phone' in cell_lower:
                        headers['phone'] = col
        
        if not header_row or 'tracking' not in headers:
            raise ValueError("Cabeçalhos não encontrados. Formato inválido.")
        
        # Extrai dados
        addresses = []
        stop_counter = 1
        
        for row in range(header_row + 1, ws.max_row + 1):
            tracking_cell = ws.cell(row, headers.get('tracking'))
            if not tracking_cell.value:
                continue
            
            tracking = str(tracking_cell.value).strip()
            address = str(ws.cell(row, headers.get('address')).value or '').strip()
            bairro = str(ws.cell(row, headers.get('bairro')).value or '').strip()
            city = str(ws.cell(row, headers.get('city')).value or '').strip()
            
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
