import requests
from geopy.distance import geodesic

# Exemplo de pontos do Leblon
coords = [
    (-22.9805684, -43.218275),
    (-22.9831773, -43.2257259),
    (-22.98592, -43.224365),
    (-22.9857941, -43.2250247),
    (-22.9843111, -43.2228142),
]

osrm_url = "http://localhost:5000/route/v1/foot/"
coords_str = ";".join([f"{lng},{lat}" for lat, lng in coords])
url = f"{osrm_url}{coords_str}?overview=full&geometries=geojson"

resp = requests.get(url)
print(f"Status: {resp.status_code}")
if resp.ok:
    data = resp.json()
    print(f"Distância total: {data['routes'][0]['distance']/1000:.2f} km")
    print(f"Duração estimada: {data['routes'][0]['duration']/60:.1f} min")
    print(f"Coordenadas da rota: {data['routes'][0]['geometry']['coordinates'][:3]} ...")
else:
    print(resp.text)
