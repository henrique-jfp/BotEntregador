import os, httpx
from typing import List, Optional
from bot.services.geocode import Geocoder
from bot.models.core import DeliveryAddress
from bot.config import logger

async def generate_static_map(addresses: List[DeliveryAddress]) -> Optional[bytes]:
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key or len(addresses) < 2:
        return None
    for a in addresses:
        if a.lat is None or a.lng is None:
            coord = await Geocoder.geocode(a.cleaned_address)
            if coord:
                a.lat, a.lng = coord
    have_all = all(a.lat is not None and a.lng is not None for a in addresses)
    if not have_all:
        return None
    path = 'path=color:0x0000ff|weight:4|' + '|'.join(f"{a.lat},{a.lng}" for a in addresses)
    markers = []
    for i,a in enumerate(addresses):
        color = 'green' if i==0 else ('red' if i==len(addresses)-1 else 'blue')
        label = chr(65+i) if i < 26 else ''
        markers.append(f"color:{color}|label:{label}|{a.lat},{a.lng}")
    marker_params = '&'.join('markers='+m for m in markers)
    base = 'https://maps.googleapis.com/maps/api/staticmap'
    params = f"size=640x640&scale=2&{path}&{marker_params}&key={api_key}"
    url = base + '?' + params
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
            if r.status_code == 200 and r.content.startswith(b'\x89PNG'):
                return r.content
            logger.warning(f"Static Maps falhou status={r.status_code}")
    except Exception as e:
        logger.warning(f"Falha mapa estático: {e}")
    # fallback omitido para módulo inicial
    return None
