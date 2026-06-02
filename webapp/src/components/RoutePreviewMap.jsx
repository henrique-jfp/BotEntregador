/**
 * 🗺️ RoutePreviewMap - Mini mapa para preview de rotas
 * Usa react-leaflet + OSRM para traçar rotas reais pelas vias
 */
import React, { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, useMap, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix para ícones do Leaflet
delete L.Icon.Default.prototype._getIconUrl;

/**
 * Cria ícone numérico para marcador
 */
const createNumberIcon = (number, color) => {
  return L.divIcon({
    html: `<div style="
      background: ${color};
      color: white;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 12px;
      border: 3px solid white;
      box-shadow: 0 2px 6px rgba(0,0,0,0.35);
    ">${number}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    className: ''
  });
};

/**
 * Cria ícone para base
 */
const createBaseIcon = () => {
  return L.divIcon({
    html: `<div style="
      background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
      color: white;
      padding: 6px 10px;
      border-radius: 6px;
      font-weight: bold;
      font-size: 11px;
      white-space: nowrap;
      box-shadow: 0 3px 8px rgba(0,0,0,0.3);
      border: 2px solid white;
    ">🏠 BASE</div>`,
    iconSize: [70, 28],
    iconAnchor: [35, 14],
    className: ''
  });
};

/**
 * Componente para desenhar rota recebida do backend (geometry)
 */
const GeometryRoute = ({ geometry, points, baseLat, baseLng, color }) => {
  const map = useMap();
  const polylineRef = useRef(null);
  // Se geometry vier como GeoJSON (Feature/LineString)
  let routeCoords = [];
  if (geometry && Array.isArray(geometry)) {
    // Espera array de [lat, lng] ou [lng, lat]
    if (geometry.length > 0 && Array.isArray(geometry[0])) {
      // Detecta se está em [lat, lng] ou [lng, lat]
      if (geometry[0][0] > 0 && geometry[0][0] <= 90) {
        // Provavelmente [lat, lng]
        routeCoords = geometry;
      } else {
        // Provavelmente [lng, lat]
        routeCoords = geometry.map(([lng, lat]) => [lat, lng]);
      }
    }
  }
  // Fallback: desenha linha simples base->pontos->base
  if (!routeCoords || routeCoords.length === 0) {
    routeCoords = [
      [baseLat, baseLng],
      ...points.map(p => [p.lat, p.lng]),
      [baseLat, baseLng]
    ];
  }
  useEffect(() => {
    if (routeCoords.length > 0 && map) {
      const bounds = L.latLngBounds(routeCoords);
      map.fitBounds(bounds, { padding: [25, 25] });
    }
  }, [routeCoords, map]);
  if (routeCoords.length === 0) return null;
  return (
    <>
      <Polyline
        positions={routeCoords}
        color="#000"
        weight={6}
        opacity={0.15}
      />
      <Polyline
        positions={routeCoords}
        color={color}
        weight={4}
        opacity={0.9}
        lineCap="round"
        lineJoin="round"
      />
    </>
  );
}

/**
 * Componente para ajustar bounds do mapa
 */
function MapBoundsAdjuster({ points, baseLat, baseLng }) {
  const map = useMap();

  useEffect(() => {
    if (points && points.length > 0) {
      const allCoords = [
        [baseLat, baseLng],
        ...points.map(p => [p.lat, p.lng])
      ];
      const bounds = L.latLngBounds(allCoords);
      map.fitBounds(bounds, { padding: [30, 30] });
    }
  }, [points, baseLat, baseLng, map]);

  return null;
}

/**
 * RoutePreviewMap - Mini mapa para preview de rotas com OSRM
 * @param {Object} props
 * @param {Array} props.points - Array de pontos {lat, lng, address, packages}
 * @param {number} props.baseLat - Latitude da base
 * @param {number} props.baseLng - Longitude da base
 * @param {string} props.color - Cor da rota (hex)
 * @param {number} props.routeIndex - Índice da rota (para título)
 * @param {string} props.height - Altura do mapa (default: '200px')
 */
export default function RoutePreviewMap({ 
  points = [], 
  baseLat, 
  baseLng, 
  color = '#3B82F6',
  routeIndex = 0,
  height = '200px',
  geometry = null // NOVO: rota pronta do backend
}) {
  // Validar pontos - filtrar pontos com coordenadas 0,0 ou inválidas
  const validPoints = points.filter(p => 
    p && 
    typeof p.lat === 'number' && 
    typeof p.lng === 'number' &&
    !(p.lat === 0 && p.lng === 0) &&
    Math.abs(p.lat) <= 90 &&
    Math.abs(p.lng) <= 180
  );

  // Se não tiver pontos válidos, mostrar mensagem
  if (validPoints.length === 0) {
    return (
      <div 
        className="flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600"
        style={{ height }}
      >
        <div className="text-center text-gray-500 dark:text-gray-400">
          <span className="text-2xl">📍</span>
          <p className="text-sm mt-1">Geocodificando...</p>
        </div>
      </div>
    );
  }

  // Calcular centro do mapa
  const centerLat = validPoints.reduce((sum, p) => sum + p.lat, 0) / validPoints.length;
  const centerLng = validPoints.reduce((sum, p) => sum + p.lng, 0) / validPoints.length;

  return (
    <div className="rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 shadow-sm" style={{ height }}>
      <MapContainer
        center={[centerLat, centerLng]}
        zoom={14}
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
        attributionControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        
        {/* Ajustar bounds automaticamente */}
        <MapBoundsAdjuster 
          points={validPoints} 
          baseLat={baseLat} 
          baseLng={baseLng} 
        />

        {/* 🚗 Rota desenhada a partir da geometria do backend */}
        <GeometryRoute 
          geometry={geometry}
          points={validPoints}
          baseLat={baseLat}
          baseLng={baseLng}
          color={color}
        />

        {/* Marcador da Base */}
        <Marker 
          position={[baseLat, baseLng]} 
          icon={createBaseIcon()}
        >
          <Popup>🏠 Ponto de partida e chegada</Popup>
        </Marker>

        {/* Marcadores dos pontos de entrega */}
        {validPoints.map((point, idx) => (
          <Marker
            key={idx}
            position={[point.lat, point.lng]}
            icon={createNumberIcon(idx + 1, color)}
          >
            <Popup>
              <div className="text-sm min-w-max">
                <strong className="text-base">Parada {idx + 1}</strong>
                <p className="text-gray-600 mt-1">{point.address || 'Endereço'}</p>
                {point.packages && point.packages.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-200">
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      📦 {point.packages.length} pacote{point.packages.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
