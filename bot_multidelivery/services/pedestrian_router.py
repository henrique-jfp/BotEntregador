import requests
from typing import List, Tuple

class PedestrianRouter:
    """
    Wrapper para API de roteirização pedestre (ex: OSRM, OpenRouteService, Google Directions)
    """
    def __init__(self, api_url: str):
        self.api_url = api_url

    def get_route(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Recebe lista de pontos [(lat, lng), ...] e retorna rota otimizada para pedestre.
        """
        # Exemplo com OSRM (profile=foot)
        coords = ";".join([f"{lng},{lat}" for lat, lng in points])
        url = f"{self.api_url}/route/v1/foot/{coords}?overview=full&geometries=geojson"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        if not data['routes']:
            return points
        geometry = data['routes'][0]['geometry']['coordinates']
        # OSRM retorna [lng, lat], converter para [lat, lng]
        return [(lat, lng) for lng, lat in geometry]
