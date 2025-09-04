import math, os, httpx, uuid
from typing import List, Tuple, Dict
from bot.models.core import DeliveryAddress
from bot.services.geocode import Geocoder
from bot.config import Config, logger

try:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    ORTOOLS_AVAILABLE = True
except Exception:
    ORTOOLS_AVAILABLE = False

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

class DistanceMatrixBuilder:
    cache_file = 'distance_cache.json'
    cache: Dict[str, Dict[str, Dict[str, float]]] = {}

    @classmethod
    def load(cls):
        if not cls.cache:
            try:
                import json, pathlib
                p = pathlib.Path(cls.cache_file)
                if p.exists():
                    cls.cache = json.loads(p.read_text(encoding='utf-8'))
            except Exception:
                cls.cache = {}

    @classmethod
    def save(cls):
        try:
            import json, pathlib
            pathlib.Path(cls.cache_file).write_text(json.dumps(cls.cache, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass

    @classmethod
    def get_cached(cls, o: str, d: str):
        okey = o.lower(); dkey = d.lower()
        return cls.cache.get(okey, {}).get(dkey)

    @classmethod
    def set_cached(cls, o: str, d: str, dist: float, dur: float):
        okey = o.lower(); dkey = d.lower()
        cls.cache.setdefault(okey, {})[dkey] = {'distance': dist, 'duration': dur}

async def build_distance_duration_matrix(addresses: List[DeliveryAddress]):
    api_key = os.getenv('GOOGLE_API_KEY')
    n = len(addresses)
    DistanceMatrixBuilder.load()
    if not api_key:
        return [], [], False, []
    dmat = [[0.0]*n for _ in range(n)]
    tmat = [[0.0]*n for _ in range(n)]
    failed = []
    total_pairs = n*(n-1)
    ok_pairs = 0
    BIG = 5_000_000
    async with httpx.AsyncClient(timeout=20) as client:
        for i, origin_obj in enumerate(addresses):
            origin = origin_obj.cleaned_address
            missing = []
            for j, dest_obj in enumerate(addresses):
                if i == j:
                    continue
                cached = DistanceMatrixBuilder.get_cached(origin, dest_obj.cleaned_address)
                if cached:
                    dmat[i][j] = cached['distance']
                    tmat[i][j] = cached['duration']
                    if cached['distance'] > 0:
                        ok_pairs += 1
                else:
                    missing.append((j, dest_obj.cleaned_address))
            if not missing:
                continue
            destinations_str = '|'.join(m[1] for m in missing)
            params = {
                'origins': origin,
                'destinations': destinations_str,
                'mode': 'driving',
                'language': 'pt-BR',
                'key': api_key
            }
            try:
                r = await client.get('https://maps.googleapis.com/maps/api/distancematrix/json', params=params)
                data = r.json()
                if data.get('status') != 'OK':
                    logger.warning(f"Distance Matrix status {data.get('status')}")
                    return [], [], False, [a.cleaned_address for a in addresses]
                elements = data['rows'][0]['elements']
                for idx, el in enumerate(elements):
                    j = missing[idx][0]
                    dest_addr = addresses[j].cleaned_address
                    st = el.get('status')
                    if st == 'OK':
                        dist = el['distance']['value']
                        dur = el['duration']['value']
                        dmat[i][j] = dist
                        tmat[i][j] = dur
                        DistanceMatrixBuilder.set_cached(origin, dest_addr, dist, dur)
                        ok_pairs += 1
                    else:
                        dmat[i][j] = BIG
                        tmat[i][j] = 0
                        if dest_addr not in failed:
                            failed.append(dest_addr)
            except Exception as e:
                logger.warning(f"Falha DM origem {origin}: {e}")
                failed.extend([m[1] for m in missing if m[1] not in failed])
    DistanceMatrixBuilder.save()
    usable_ratio = ok_pairs/total_pairs if total_pairs else 0
    via_api = usable_ratio >= 0.7 and ok_pairs > 0
    return dmat, tmat, via_api, failed

# Heurísticas
async def optimize_route(addresses: List[DeliveryAddress]) -> List[DeliveryAddress]:
    if len(addresses) <= 2:
        return addresses
    Geocoder.load_cache()
    geocoded = 0
    for a in addresses:
        if a.lat is None or a.lng is None:
            coord = await Geocoder.geocode(a.cleaned_address)
            if coord:
                a.lat, a.lng = coord
                geocoded += 1
    if geocoded:
        Geocoder.save_cache()
    if sum(1 for a in addresses if a.lat and a.lng) < max(3, len(addresses)//2):
        logger.warning('Poucos geocodificados - mantendo ordem')
        return addresses
    origin = addresses[0]
    remaining = addresses[1:]
    route = [origin]
    current = origin
    rem = remaining.copy()
    while rem:
        nxt = min(rem, key=lambda x: haversine(current.lat, current.lng, x.lat, x.lng) if x.lat and x.lng else 1e9)
        route.append(nxt)
        rem.remove(nxt)
        current = nxt
    # 2-opt
    improved = True
    def total_dist(seq):
        d=0
        for i in range(len(seq)-1):
            a,b=seq[i],seq[i+1]
            if a.lat and b.lat:
                d+=haversine(a.lat,a.lng,b.lat,b.lng)
        return d
    while improved:
        improved = False
        best = total_dist(route)
        for i in range(1, len(route)-2):
            for j in range(i+1, len(route)-1):
                if j - i == 1:
                    continue
                new_route = route[:]
                new_route[i:j] = reversed(new_route[i:j])
                dist = total_dist(new_route)
                if dist + 0.01 < best:
                    route = new_route
                    best = dist
                    improved = True
    return route

# Distance matrix optimization wrapper
async def optimize_and_compute(addresses: List[DeliveryAddress]):
    if len(addresses) <= 1:
        service = len(addresses) * Config.SERVICE_TIME_PER_STOP_MIN
        return addresses, 0.0, 0.0, service, service, False, []
    dmat, tmat, ok, failed = await build_distance_duration_matrix(addresses)
    if ok:
        order_idx = optimize_with_distance_matrix(dmat)
        ordered = [addresses[i] for i in order_idx]
        total_m = 0.0; total_s = 0.0
        for i in range(len(order_idx)-1):
            a = order_idx[i]; b = order_idx[i+1]
            total_m += dmat[a][b]
            total_s += tmat[a][b]
        service_min = (len(ordered)-1) * Config.SERVICE_TIME_PER_STOP_MIN
        driving_min = total_s / 60.0 if total_s > 0 else (total_m/1000.0)/Config.AVERAGE_SPEED_KMH*60
        total_min = driving_min + service_min
        return ordered, round(total_m/1000.0, 2), round(driving_min,1), round(service_min,1), round(total_min,1), True, failed
    ordered = await optimize_route(addresses)
    total_km, driving_min, service_min, total_min = await compute_route_stats(ordered)
    return ordered, total_km, driving_min, service_min, total_min, False, failed

# OR-Tools / heurística index order
def optimize_with_distance_matrix(distance_matrix):
    n = len(distance_matrix)
    if ORTOOLS_AVAILABLE and n <= 25:
        try:
            manager = pywrapcp.RoutingIndexManager(n, 1, 0)
            routing = pywrapcp.RoutingModel(manager)
            def distance_cb(from_index, to_index):
                f = manager.IndexToNode(from_index); t = manager.IndexToNode(to_index)
                return int(distance_matrix[f][t])
            transit_index = routing.RegisterTransitCallback(distance_cb)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_index)
            search_params = pywrapcp.DefaultRoutingSearchParameters()
            search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            search_params.time_limit.FromSeconds(5)
            solution = routing.SolveWithParameters(search_params)
            if solution:
                index = routing.Start(0); order=[]
                while not routing.IsEnd(index):
                    node = manager.IndexToNode(index)
                    order.append(node)
                    index = solution.Value(routing.NextVar(index))
                if len(order)>1 and order[-1]==0:
                    order = order[:-1]
                return order
        except Exception as e:
            logger.warning(f"Falha OR-Tools: {e}")
    # fallback simples
    unvisited = set(range(1, n))
    path=[0]; current=0
    while unvisited:
        nxt = min(unvisited, key=lambda j: distance_matrix[current][j] if distance_matrix[current][j] > 0 else 1e12)
        path.append(nxt); unvisited.remove(nxt); current=nxt
    return path

async def compute_route_stats(ordered: List[DeliveryAddress]):
    n = len(ordered)
    if n <= 1:
        service = n * Config.SERVICE_TIME_PER_STOP_MIN
        return 0.0, 0.0, service, service
    have_coords = all(a.lat is not None and a.lng is not None for a in ordered)
    if have_coords:
        total_km = 0.0
        for i in range(n-1):
            a, b = ordered[i], ordered[i+1]
            total_km += haversine(a.lat, a.lng, b.lat, b.lng)
        driving_minutes = (total_km / Config.AVERAGE_SPEED_KMH) * 60
    else:
        total_km = 1.2 * (n - 1)
        driving_minutes = (total_km / Config.AVERAGE_SPEED_KMH) * 60
    service_minutes = n * Config.SERVICE_TIME_PER_STOP_MIN
    total_minutes = driving_minutes + service_minutes
    return round(total_km, 2), round(driving_minutes,1), round(service_minutes,1), round(total_minutes,1)
