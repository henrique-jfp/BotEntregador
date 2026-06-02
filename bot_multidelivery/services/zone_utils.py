import json
from shapely.geometry import shape, Point
from typing import Dict, Any, Optional

class ZoneUtils:
    def __init__(self, geojson_path: str):
        with open(geojson_path, 'r', encoding='utf-8') as f:
            self.geojson = json.load(f)
        self.polygons = [
            (feature['properties']['name'], shape(feature['geometry']))
            for feature in self.geojson['features']
        ]

    def get_zone(self, lat: float, lng: float) -> Optional[str]:
        point = Point(lng, lat)
        for name, polygon in self.polygons:
            if polygon.contains(point):
                return name
        return None

    def get_zone_feature(self, lat: float, lng: float) -> Optional[Dict[str, Any]]:
        point = Point(lng, lat)
        for feature in self.geojson['features']:
            polygon = shape(feature['geometry'])
            if polygon.contains(point):
                return feature
        return None

    def get_all_zones(self):
        return [name for name, _ in self.polygons]

    def get_zone_polygon(self, zone_name: str):
        for name, polygon in self.polygons:
            if name == zone_name:
                return polygon
        return None
