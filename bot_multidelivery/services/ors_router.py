import requests
import os
import logging

ORS_API_KEY = os.getenv("ORS_API_KEY") or "SUA_API_KEY_AQUI"
ORS_URL = "https://api.openrouteservice.org/optimization"

logger = logging.getLogger(__name__)

def optimize_route(coords, profile="foot-walking"):
    """
    coords: lista de [lng, lat]
    profile: 'foot-walking', 'driving-car', etc
    """
    if len(coords) < 2:
        return coords

    jobs = [{"id": i+1, "location": coord} for i, coord in enumerate(coords[1:])]
    vehicles = [{
        "id": 1,
        "profile": profile,
        "start": coords[0],
        "end": coords[0]
    }]
    body = {"jobs": jobs, "vehicles": vehicles}

    try:
        resp = requests.post(
            ORS_URL,
            json=body,
            headers={"Authorization": ORS_API_KEY}
        )
        resp.raise_for_status()
        data = resp.json()
        steps = data["routes"][0]["steps"]
        # O primeiro ponto é o start, depois os jobs na ordem ótima
        ordered = [coords[0]] + [jobs[step["job"]-1]["location"] for step in steps if "job" in step]
        return ordered
    except Exception as e:
        logger.warning(f"[ORS] Falha ao otimizar rota: {e}. Usando ordem original.")
        return coords
