"""
🚗 OSRM Service
Cliente para obter distâncias reais (malha viária) via OSRM.
Inclui cache local e fallback para Haversine em caso de falha.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx


Point = Tuple[float, float]  # (lat, lng)


@dataclass
class DistanceMatrixResult:
    distances_km: List[List[float]]
    durations_min: Optional[List[List[float]]]
    fallback_used: bool


@dataclass
class RouteGeometryResult:
    geometry: dict
    distance_km: float
    duration_min: float
    fallback_used: bool


class OSRMClient:
    """Cliente OSRM com cache e fallback."""

    def __init__(
        self,
        base_url: str = "https://router.project-osrm.org",
        profile: Optional[str] = None,
        cache_path: str = "data/osrm_cache.json",
        timeout: float = 15.0,
        max_points: int = 50,  # Reduzido para rotas a pé (API restringe mais)
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.profile = (profile or os.getenv("OSRM_PROFILE", "foot")).strip() or "foot"
        self.timeout = timeout
        self.max_points = max_points

        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, dict] = {}
        self._cache_dirty = False
        self._load_cache()

    # ==================== PUBLIC API ====================

    def get_distance_matrix(
        self,
        points: List[Point],
        sources: Optional[List[int]] = None,
        destinations: Optional[List[int]] = None,
    ) -> DistanceMatrixResult:
        """
        Retorna matriz de distâncias/durações usando /table.
        Se falhar, usa Haversine como fallback.
        """
        try:
            return self._get_distance_matrix_sync(points, sources, destinations)
        except Exception:
            distances_km = self._haversine_matrix(points, sources, destinations)
            return DistanceMatrixResult(
                distances_km=distances_km,
                durations_min=None,
                fallback_used=True,
            )

    async def get_distance_matrix_async(
        self,
        points: List[Point],
        sources: Optional[List[int]] = None,
        destinations: Optional[List[int]] = None,
    ) -> DistanceMatrixResult:
        """Versão assíncrona do /table."""
        try:
            return await self._get_distance_matrix_async(points, sources, destinations)
        except Exception:
            distances_km = self._haversine_matrix(points, sources, destinations)
            return DistanceMatrixResult(
                distances_km=distances_km,
                durations_min=None,
                fallback_used=True,
            )

    def get_route_geometry(self, points: List[Point]) -> RouteGeometryResult:
        """
        Retorna geometria real da rota usando /route.
        Se falhar, retorna linha reta com fallback.
        """
        if len(points) < 2:
            return RouteGeometryResult(geometry={}, distance_km=0.0, duration_min=0.0, fallback_used=True)

        try:
            return self._get_route_geometry_sync(points)
        except Exception:
            distance_km = 0.0
            for i in range(len(points) - 1):
                distance_km += self._haversine_km(points[i], points[i + 1])

            return RouteGeometryResult(
                geometry={
                    "type": "LineString",
                    "coordinates": [[p[1], p[0]] for p in points],
                },
                distance_km=distance_km,
                duration_min=0.0,
                fallback_used=True,
            )

    async def get_route_geometry_async(self, points: List[Point]) -> RouteGeometryResult:
        if len(points) < 2:
            return RouteGeometryResult(geometry={}, distance_km=0.0, duration_min=0.0, fallback_used=True)

        try:
            return await self._get_route_geometry_async(points)
        except Exception:
            distance_km = 0.0
            for i in range(len(points) - 1):
                distance_km += self._haversine_km(points[i], points[i + 1])

            return RouteGeometryResult(
                geometry={
                    "type": "LineString",
                    "coordinates": [[p[1], p[0]] for p in points],
                },
                distance_km=distance_km,
                duration_min=0.0,
                fallback_used=True,
            )

    # ==================== INTERNALS ====================

    def _get_distance_matrix_sync(
        self,
        points: List[Point],
        sources: Optional[List[int]],
        destinations: Optional[List[int]],
    ) -> DistanceMatrixResult:
        sources = sources or list(range(len(points)))
        destinations = destinations or list(range(len(points)))

        if len(points) > self.max_points:
            return self._get_distance_matrix_sync_chunked(points, sources, destinations)

        cache_key = self._make_cache_key("table", points, sources, destinations, self.profile)
        cached = self._cache_get(cache_key)
        if cached:
            return DistanceMatrixResult(
                distances_km=cached["distances_km"],
                durations_min=cached.get("durations_min"),
                fallback_used=False,
            )

        coords = self._format_coords(points)
        params = {
            "annotations": "distance,duration",
            "sources": ";".join(map(str, sources)),
            "destinations": ";".join(map(str, destinations)),
        }

        url = f"{self.base_url}/table/v1/{self.profile}/{coords}"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        distances_km = self._meters_to_km_matrix(data.get("distances"))
        durations_min = self._seconds_to_min_matrix(data.get("durations"))

        self._cache_set(cache_key, {
            "distances_km": distances_km,
            "durations_min": durations_min,
        })

        return DistanceMatrixResult(
            distances_km=distances_km,
            durations_min=durations_min,
            fallback_used=False,
        )

    async def _get_distance_matrix_async(
        self,
        points: List[Point],
        sources: Optional[List[int]],
        destinations: Optional[List[int]],
    ) -> DistanceMatrixResult:
        sources = sources or list(range(len(points)))
        destinations = destinations or list(range(len(points)))

        if len(points) > self.max_points:
            return await self._get_distance_matrix_async_chunked(points, sources, destinations)

        cache_key = self._make_cache_key("table", points, sources, destinations, self.profile)
        cached = self._cache_get(cache_key)
        if cached:
            return DistanceMatrixResult(
                distances_km=cached["distances_km"],
                durations_min=cached.get("durations_min"),
                fallback_used=False,
            )

        coords = self._format_coords(points)
        params = {
            "annotations": "distance,duration",
            "sources": ";".join(map(str, sources)),
            "destinations": ";".join(map(str, destinations)),
        }

        url = f"{self.base_url}/table/v1/{self.profile}/{coords}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        distances_km = self._meters_to_km_matrix(data.get("distances"))
        durations_min = self._seconds_to_min_matrix(data.get("durations"))

        self._cache_set(cache_key, {
            "distances_km": distances_km,
            "durations_min": durations_min,
        })

        return DistanceMatrixResult(
            distances_km=distances_km,
            durations_min=durations_min,
            fallback_used=False,
        )

    def _get_distance_matrix_sync_chunked(
        self,
        points: List[Point],
        sources: List[int],
        destinations: List[int],
    ) -> DistanceMatrixResult:
        max_sources = max(self.max_points - len(destinations), 1)
        distances_km: List[List[float]] = []
        durations_min: List[List[float]] = []

        for i in range(0, len(sources), max_sources):
            batch_sources = sources[i:i + max_sources]
            batch_result = self._get_distance_matrix_sync(points, batch_sources, destinations)
            distances_km.extend(batch_result.distances_km)
            if batch_result.durations_min:
                durations_min.extend(batch_result.durations_min)

        return DistanceMatrixResult(
            distances_km=distances_km,
            durations_min=durations_min if durations_min else None,
            fallback_used=False,
        )

    async def _get_distance_matrix_async_chunked(
        self,
        points: List[Point],
        sources: List[int],
        destinations: List[int],
    ) -> DistanceMatrixResult:
        max_sources = max(self.max_points - len(destinations), 1)
        distances_km: List[List[float]] = []
        durations_min: List[List[float]] = []

        for i in range(0, len(sources), max_sources):
            batch_sources = sources[i:i + max_sources]
            batch_result = await self._get_distance_matrix_async(points, batch_sources, destinations)
            distances_km.extend(batch_result.distances_km)
            if batch_result.durations_min:
                durations_min.extend(batch_result.durations_min)

        return DistanceMatrixResult(
            distances_km=distances_km,
            durations_min=durations_min if durations_min else None,
            fallback_used=False,
        )

    def _get_route_geometry_sync(self, points: List[Point]) -> RouteGeometryResult:
        cache_key = self._make_cache_key("route", points, None, None, self.profile)
        cached = self._cache_get(cache_key)
        if cached:
            return RouteGeometryResult(
                geometry=cached["geometry"],
                distance_km=cached["distance_km"],
                duration_min=cached["duration_min"],
                fallback_used=False,
            )

        coords = self._format_coords(points)
        params = {"overview": "full", "geometries": "geojson"}
        url = f"{self.base_url}/route/v1/{self.profile}/{coords}"

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        route = data["routes"][0]
        geometry = route["geometry"]
        distance_km = route["distance"] / 1000.0
        duration_min = route["duration"] / 60.0

        self._cache_set(cache_key, {
            "geometry": geometry,
            "distance_km": distance_km,
            "duration_min": duration_min,
        })

        return RouteGeometryResult(
            geometry=geometry,
            distance_km=distance_km,
            duration_min=duration_min,
            fallback_used=False,
        )

    async def _get_route_geometry_async(self, points: List[Point]) -> RouteGeometryResult:
        cache_key = self._make_cache_key("route", points, None, None, self.profile)
        cached = self._cache_get(cache_key)
        if cached:
            return RouteGeometryResult(
                geometry=cached["geometry"],
                distance_km=cached["distance_km"],
                duration_min=cached["duration_min"],
                fallback_used=False,
            )

        coords = self._format_coords(points)
        params = {"overview": "full", "geometries": "geojson"}
        url = f"{self.base_url}/route/v1/{self.profile}/{coords}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        route = data["routes"][0]
        geometry = route["geometry"]
        distance_km = route["distance"] / 1000.0
        duration_min = route["duration"] / 60.0

        self._cache_set(cache_key, {
            "geometry": geometry,
            "distance_km": distance_km,
            "duration_min": duration_min,
        })

        return RouteGeometryResult(
            geometry=geometry,
            distance_km=distance_km,
            duration_min=duration_min,
            fallback_used=False,
        )

    # ==================== CACHE ====================

    def _load_cache(self) -> None:
        if self.cache_path.exists():
            try:
                self._cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except Exception:
                self._cache = {}

    def _save_cache(self) -> None:
        if not self._cache_dirty:
            return
        self.cache_path.write_text(json.dumps(self._cache, ensure_ascii=False), encoding="utf-8")
        self._cache_dirty = False

    def _cache_get(self, key: str) -> Optional[dict]:
        return self._cache.get(key)

    def _cache_set(self, key: str, value: dict) -> None:
        self._cache[key] = value
        self._cache_dirty = True
        self._save_cache()

    # ==================== UTILS ====================

    @staticmethod
    def _format_coords(points: List[Point]) -> str:
        return ";".join([f"{lng:.6f},{lat:.6f}" for lat, lng in points])

    @staticmethod
    def _meters_to_km_matrix(matrix: Optional[List[List[float]]]) -> List[List[float]]:
        if not matrix:
            return []
        return [[(v or 0.0) / 1000.0 for v in row] for row in matrix]

    @staticmethod
    def _seconds_to_min_matrix(matrix: Optional[List[List[float]]]) -> Optional[List[List[float]]]:
        if not matrix:
            return None
        return [[(v or 0.0) / 60.0 for v in row] for row in matrix]

    @staticmethod
    def _haversine_km(p1: Point, p2: Point) -> float:
        lat1, lng1 = p1
        lat2, lng2 = p2

        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _haversine_matrix(
        self,
        points: List[Point],
        sources: Optional[List[int]],
        destinations: Optional[List[int]],
    ) -> List[List[float]]:
        sources = sources or list(range(len(points)))
        destinations = destinations or list(range(len(points)))

        matrix: List[List[float]] = []
        for s in sources:
            row = []
            for d in destinations:
                row.append(self._haversine_km(points[s], points[d]))
            matrix.append(row)
        return matrix

    @staticmethod
    def _make_cache_key(
        prefix: str,
        points: List[Point],
        sources: Optional[List[int]],
        destinations: Optional[List[int]],
        profile: str,
    ) -> str:
        rounded = [(round(p[0], 6), round(p[1], 6)) for p in points]
        src = ",".join(map(str, sources)) if sources else "all"
        dst = ",".join(map(str, destinations)) if destinations else "all"
        return f"{prefix}|{profile}|{rounded}|{src}|{dst}"


# Singleton
osrm_client = OSRMClient()


def get_route_distance_km(coords: List[Tuple[float, float]]) -> Optional[float]:
    """Retorna distância total (km) via OSRM para uma sequência de pontos.

    Retorna None se falhar e usa fallback Haversine para não quebrar fluxo.
    """
    if not coords or len(coords) < 2:
        return 0.0

    result = osrm_client.get_route_geometry(coords)
    if result and result.distance_km:
        return result.distance_km

    # Fallback Haversine
    distance_km = 0.0
    for i in range(len(coords) - 1):
        distance_km += osrm_client._haversine_km(coords[i], coords[i + 1])
    return distance_km


def get_distance_km(a: Tuple[float, float], b: Tuple[float, float]) -> Optional[float]:
    """Retorna distância entre dois pontos via OSRM (km)."""
    return get_route_distance_km([a, b])
