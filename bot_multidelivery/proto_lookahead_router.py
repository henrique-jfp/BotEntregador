# -*- coding: utf-8 -*-
"""
Protótipo de roteirizador lookahead + penalidade de U-turn
Interface mínima: `route = lookahead_route(base: (lat,lng), stops: List[DeliveryStop])`
Retorna lista de `stops` ordenada.
"""
from __future__ import annotations

import math
import logging
from typing import List, Tuple

from bot_multidelivery.services.osrm_service import osrm_client

logger = logging.getLogger(__name__)

Point = Tuple[float, float]


def haversine(a: Point, b: Point) -> float:
    R = 6371.0
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(h))


def angle_between(a: Point, b: Point, c: Point) -> float:
    v1 = (a[0]-b[0], a[1]-b[1])
    v2 = (c[0]-b[0], c[1]-b[1])
    dot = v1[0]*v2[0] + v1[1]*v2[1]
    m1 = math.hypot(*v1); m2 = math.hypot(*v2)
    if m1 < 1e-6 or m2 < 1e-6:
        return 0.0
    cosang = max(-1.0, min(1.0, dot/(m1*m2)))
    return math.degrees(math.acos(cosang))


def _build_matrices(coords: List[Point]):
    # coords: base + stops
    res = osrm_client.get_distance_matrix(coords)
    if not res or res.fallback_used or not res.distances_km:
        # fallback to haversine
        n = len(coords)
        dmat = [[0.0]*n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i==j:
                    dmat[i][j]=0.0
                else:
                    dmat[i][j]=haversine(coords[i], coords[j])
        return dmat, None

    distances_km = res.distances_km
    durations_min = res.durations_min
    return distances_km, durations_min


def _combine(distances_km, durations_min, coords_all=None, weight=0.6, avg_speed_km_per_min=0.083333, uturn_penalty_km=0.05):
    if not durations_min:
        return distances_km
    n = len(distances_km)
    combined = [[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            d = distances_km[i][j]
            dur = durations_min[i][j] if durations_min and durations_min[i][j] is not None else (d/ max(avg_speed_km_per_min,1e-6))
            dur_km = dur * avg_speed_km_per_min
            val = (1-weight)*d + weight*dur_km
            penalty = 0.0
            try:
                if coords_all and i!=j:
                    ang = angle_between(coords_all[i], coords_all[j], coords_all[0])
                    if ang>150:
                        penalty = uturn_penalty_km
            except Exception:
                penalty = 0.0
            combined[i][j] = max(0.0, val+penalty)
    return combined


def lookahead_route(base: Point, stops: List) -> List:
    if not stops:
        return []
    coords = [base] + [(s.lat, s.lng) for s in stops]
    distances_km, durations_min = _build_matrices(coords)
    cost = _combine(distances_km, durations_min, coords_all=coords)

    remaining = set(range(1, len(coords)))
    order_indices = []
    current = 0
    prev = None

    while remaining:
        best = None
        best_score = float('inf')
        for cand in list(remaining):
            c1 = cost[current][cand]
            if len(remaining) > 1:
                min_next = float('inf')
                for nxt in remaining:
                    if nxt == cand:
                        continue
                    val = cost[cand][nxt]
                    ang = angle_between(coords[current], coords[cand], coords[nxt])
                    if ang > 140:
                        val += 0.05
                    min_next = min(min_next, val)
            else:
                min_next = cost[cand][0]

            score = c1 + 0.5 * min_next
            if prev is not None:
                ang_back = angle_between(coords[prev], coords[current], coords[cand])
                if ang_back > 160:
                    score += 0.05
            if score < best_score:
                best_score = score
                best = cand

        order_indices.append(best-1)
        remaining.remove(best)
        prev = current
        current = best

    return [stops[i] for i in order_indices]
