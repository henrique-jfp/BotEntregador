import React, { useEffect, useState, useMemo } from 'react';
import styled from 'styled-components';
import { MapContainer, TileLayer, Marker, Popup, useMap, Polyline, Circle } from 'react-leaflet';
import { useRef } from 'react';
// Componente de localização premium com direção (bússola)
function LocationMarker({ lat, lng, heading }) {
  // Bolinha azul animada igual Google Maps
  return (
    <Marker
      position={[lat, lng]}
      icon={L.divIcon({
        html: `
          <div style="position:relative;display:flex;align-items:center;justify-content:center;width:44px;height:44px;">
            <div style="width:36px;height:36px;border-radius:50%;background:#2563eb;border:3px solid white;box-shadow:0 0 12px #2563eb55;animation:pulse 1.2s infinite;">
            </div>
            <div style="position:absolute;top:2px;left:50%;transform:translateX(-50%) rotate(${heading || 0}deg);">
              <svg width="18" height="18" viewBox="0 0 18 18">
                <polygon points="9,0 13,18 9,14 5,18" fill="#2563eb" opacity="0.8"/>
              </svg>
            </div>
          </div>
          <style>
            @keyframes pulse {
              0% { box-shadow: 0 0 0 0 #2563eb55; }
              70% { box-shadow: 0 0 0 10px #2563eb22; }
              100% { box-shadow: 0 0 0 0 #2563eb55; }
            }
          </style>
        `,
        iconSize: [44, 44],
        className: 'location-marker-premium',
      })}
    />
  );
}
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { MapPin, Package } from 'lucide-react';

// Fix icons
delete L.Icon.Default.prototype._getIconUrl;

// Extra CSS para animações suaves dos marcadores
const extraStyles = `
  .simple-marker, .simple-marker-current, .simple-marker-start, .simple-marker-end { transition: transform .22s ease, opacity .22s ease, filter .25s ease; }
  .simple-marker.delivered, .simple-marker-current.delivered { opacity: .55; transform: scale(.86); filter: grayscale(.4) contrast(.9); }
  .simple-marker-current { box-shadow: 0 6px 18px rgba(0,0,0,0.22) !important; transform: translateY(-3px) scale(1.02); }
  .base-marker { box-shadow: 0 0 16px #10b98155; border: 2px solid #10b981; background: #fff; }
  .progress-bar { position: absolute; bottom: 0; left: 0; width: 100%; background: #fff; box-shadow: 0 -2px 8px #0001; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; z-index: 10; }
`.trim();
// Barra de progresso estilizada
const ProgressBar = styled.div`
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  background: #fff;
  box-shadow: 0 -2px 8px #0001;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 10;
`;

const Progress = styled.div`
  font-size: 1rem;
  color: #555;
`;

const Button = styled.button`
  background: ${({ color }) => color || "#222"};
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-weight: 600;
  font-size: 1rem;
  margin-left: 12px;
  cursor: pointer;
  transition: background 0.2s;
  &:hover {
    background: ${({ color }) => color ? "#333" : "#444"};
  }
`;

// ⚡ MARCADORES ULTRA-SIMPLES (suportam classe "delivered" para animações)
const createSimpleIcon = (index, total, isCurrent, color, stop) => {
  const isStart = index === 0;
  const isEnd = index === total - 1;
  
  // Ícone: detecta delivered/failed
  const isDelivered = stop && (stop.status === 'delivered' || stop.delivered);
  const isFailed = stop && stop.status === 'failed';

  const deliveredSymbol = '✓';
  const failedSymbol = '✕';

  const makeHtml = (w, h, bg, content, fontSize = 14, border = 3) =>
    `<div style="display:flex;align-items:center;justify-content:center;width:${w}px;height:${h}px;border-radius:50%;border:${border}px solid white;background:${bg};color:white;font-weight:900;font-size:${fontSize}px;">${content}</div>`;

  if (isCurrent) {
    const content = isDelivered ? deliveredSymbol : (isFailed ? failedSymbol : String(index + 1));
    const bg = isDelivered ? '#10B981' : (isFailed ? '#EF4444' : color);
    return L.divIcon({
      html: makeHtml(44, 44, bg, content, 14, 3),
      iconSize: [44, 44],
      className: `simple-marker-current${isDelivered || isFailed ? ' delivered' : ''}`,
    });
  }

  if (isStart) {
    const content = isDelivered ? deliveredSymbol : (isFailed ? failedSymbol : 'A');
    const bg = isDelivered ? '#10B981' : (isFailed ? '#EF4444' : '#10b981');
    return L.divIcon({
      html: makeHtml(36, 36, bg, content, 16, 2),
      iconSize: [36, 36],
      className: `simple-marker-start${isDelivered || isFailed ? ' delivered' : ''}`,
    });
  }

  if (isEnd) {
    const content = isDelivered ? deliveredSymbol : (isFailed ? failedSymbol : 'B');
    const bg = isDelivered ? '#10B981' : (isFailed ? '#EF4444' : '#ef4444');
    return L.divIcon({
      html: makeHtml(36, 36, bg, content, 16, 2),
      iconSize: [36, 36],
      className: `simple-marker-end${isDelivered || isFailed ? ' delivered' : ''}`,
    });
  }

  // Marcadores intermediários MINIMALISTAS
  const content = isDelivered ? deliveredSymbol : (isFailed ? failedSymbol : String(index + 1));
  const bg = isDelivered ? '#9CA3AF' : (isFailed ? '#9B1C1C' : color);
  return L.divIcon({
    html: `<div style="display:flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:50%;border:2px solid white;background:${bg};color:white;font-weight:bold;font-size:12px;">${content}</div>`,
    iconSize: [32, 32],
    className: `simple-marker${isDelivered || isFailed ? ' delivered' : ''}`,
  });
};

// Componente para ajustar zoom
function MapAdjuster({ points }) {
  const map = useMap();

  useEffect(() => {
    if (points && points.length > 0) {
      const bounds = L.latLngBounds(points.map(p => [p.lat, p.lng]));
      map.fitBounds(bounds, { padding: [100, 100] });
    }
  }, [points, map]);

  return null;
}

export default function MapView({ stops, currentStopIndex = 0, routeColor = '#7C3AED', onStopSelect, routeGeometry, onMarkDelivered, userLocation, base, onStatusChange, onFinishRoute }) {
  // Localização em tempo real
  const [currentLocation, setCurrentLocation] = useState(userLocation);
  const [heading, setHeading] = useState(0);
  useEffect(() => {
    const watch = navigator.geolocation.watchPosition(
      (pos) => setCurrentLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => {},
      { enableHighAccuracy: true }
    );
    // Bússola (DeviceOrientation)
    const handleOrientation = (e) => {
      if (e.alpha !== null) setHeading(e.alpha);
    };
    window.addEventListener('deviceorientation', handleOrientation, true);
    return () => {
      navigator.geolocation.clearWatch(watch);
      window.removeEventListener('deviceorientation', handleOrientation, true);
    };
  }, []);
  // Progresso
  const delivered = stops.filter(s => s.status === "delivered" || s.status === "success").length;
  const failed = stops.filter(s => s.status === "failed" || s.status === "fail").length;
  const transferred = stops.filter(s => s.status === "transfer").length;
  const total = stops.length;

  // Sempre declarar hooks no topo do componente (evita invariant hook errors)
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [tileLayerUrl, setTileLayerUrl] = useState(null);
  const [tileErrorCount, setTileErrorCount] = useState(0);

  useEffect(() => {
    // Detectar dark mode
    const isDark = document.documentElement.classList.contains('dark') ||
                   window.matchMedia('(prefers-color-scheme: dark)').matches;
    setIsDarkMode(isDark);

    // Listener para mudanças
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e) => setIsDarkMode(e.matches);
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  useEffect(() => {
    // Tenta obter configuração do backend (expõe GEOAPIFY_API_KEY quando presente)
    let mounted = true;
    (async () => {
      try {
        const res = await fetch('/api/deliverer/config');
        if (!res.ok) return;
        const j = await res.json();
        const key = j && j.geoapify_key;
        if (key) {
          // Geoapify tiles (fallback para OSM se necessário)
          const url = `https://maps.geoapify.com/v1/tile/osm-carto/{z}/{x}/{y}.png?apiKey=${key}`;
          if (mounted) setTileLayerUrl(url);
          return;
        }
      } catch (e) {
        // ignore and fallback
      }
      if (mounted) setTileLayerUrl(isDarkMode ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png' : 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png');
    })();
    return () => { mounted = false };
  }, [isDarkMode]);

  // ⚡ MEMOIZAR polyline positions (defensivo: usa array vazio se stops ausente)
  const polylinePositions = useMemo(() => {
    if (routeGeometry && routeGeometry.type === 'LineString' && Array.isArray(routeGeometry.coordinates) && routeGeometry.coordinates.length > 0) {
      return routeGeometry.coordinates.map(c => [c[1], c[0]]);
    }
    if (!stops || stops.length === 0) return [];
    return stops.map(stop => [stop.lat, stop.lng]);
  }, [stops, routeGeometry]);

  const effectiveTileLayerUrl = tileLayerUrl || (isDarkMode ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png' : 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png');

  const polylineColor = routeColor || (isDarkMode ? '#8B5CF6' : '#7C3AED');

  const handleTileError = (err) => {
    // Ao menos um tile falhar, converte para fallback OSM
    setTileErrorCount(c => c + 1);
    console.warn('Tile load error, switching to fallback tiles', err);
    setTileLayerUrl('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png');
  };

  if (!stops || stops.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center bg-gray-100 dark:bg-gray-800">
        <style>{extraStyles}</style>
        <MapPin className="w-12 h-12 text-gray-400 mb-3" />
        <p className="text-gray-500 dark:text-gray-400 font-medium">Sem pontos no mapa</p>
      </div>
    );
  }

  const center = [stops[0].lat, stops[0].lng];

  return (
    <div className="h-full w-full relative z-0">
      <MapContainer 
        center={center} 
        zoom={13} 
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
        zoomControl={false}
        attributionControl={false}
        className="map-container"
      >
        <style>{extraStyles}</style>
        <TileLayer
          attribution={effectiveTileLayerUrl.includes('geoapify') ? '© Geoapify / © OpenStreetMap' : '© OpenStreetMap'}
          url={effectiveTileLayerUrl}
          maxZoom={18}
          eventHandlers={{
            tileerror: handleTileError
          }}
        />
        {/* Polyline da rota */}
        <Polyline 
          positions={polylinePositions} 
          pathOptions={{ 
            color: polylineColor, 
            weight: 4, 
            opacity: 0.8,
            lineCap: 'round',
            lineJoin: 'bevel',
          }} 
        />

        {/* Base */}
        {base && base.lat && base.lng && (
          <Marker
            position={[base.lat, base.lng]}
            icon={L.divIcon({
              html: `<div style="display:flex;align-items:center;justify-content:center;width:40px;height:40px;border-radius:50%;background:#fff;border:3px solid #10b981;box-shadow:0 0 16px #10b98155;color:#10b981;font-weight:900;font-size:15px;">🏠</div>`,
              iconSize: [40, 40],
              className: 'base-marker',
            })}
          >
            <Popup className="custom-popup" maxWidth={180}>
              <div className="text-sm font-bold text-green-700">Base</div>
            </Popup>
          </Marker>
        )}

        {/* Paradas */}
        {stops.map((stop, idx) => (
          <Marker 
            key={`${idx}-${stop.lat}-${stop.lng}-${stop.status || 'pending'}`}
            position={[stop.lat, stop.lng]}
            icon={createSimpleIcon(idx, stops.length, idx === currentStopIndex, routeColor, stop)}
            eventHandlers={{
              click: () => onStopSelect && onStopSelect(idx),
            }}
          >
            <Popup className="custom-popup" maxWidth={250}>
              <div className="text-sm">
                <p className="font-bold mb-1">📍 Parada {idx + 1}</p>
                <p className="text-gray-700">{stop.address}</p>
                {stop.packages && (
                  <p className="text-xs text-gray-500 mt-1">
                    📦 {stop.packages.length} pacote{stop.packages.length !== 1 ? 's' : ''}
                  </p>
                )}
                <div className="mt-2 flex gap-2">
                  <a
                    href={`https://www.google.com/maps/dir/?api=1&destination=${stop.lat},${stop.lng}`}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-2 bg-blue-600 text-white rounded-lg text-xs font-bold"
                  >Navegar</a>
                  {onStatusChange && (
                    <Button color="#4caf50" onClick={() => onStatusChange(idx, "success")}>Entregue</Button>
                  )}
                  {onStatusChange && (
                    <Button color="#f44336" onClick={() => onStatusChange(idx, "fail")}>Insucesso</Button>
                  )}
                  {onStatusChange && (
                    <Button color="#2196f3" onClick={() => onStatusChange(idx, "transfer")}>Transferir</Button>
                  )}
                </div>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Círculo de aproximação para parada atual */}
        {currentStopIndex < stops.length && (
          <Circle
            center={[stops[currentStopIndex].lat, stops[currentStopIndex].lng]}
            radius={50}
            pathOptions={{
              color: routeColor,
              fillColor: routeColor,
              fillOpacity: 0.1,
              weight: 2,
              opacity: 0.4,
            }}
          />
        )}

        {/* Localização premium com direção */}
        {currentLocation && currentLocation.lat && currentLocation.lng && (
          <LocationMarker lat={currentLocation.lat} lng={currentLocation.lng} heading={heading} />
        )}

        <MapAdjuster points={stops} />
      </MapContainer>
      {/* Barra de progresso dinâmica */}
      <ProgressBar style={{
        position: 'fixed',
        left: 0,
        bottom: 0,
        width: '100vw',
        maxWidth: '100vw',
        zIndex: 1000,
        borderTop: '1px solid #e5e7eb',
        boxShadow: '0 -2px 8px #0001',
        background: '#fff',
        padding: '16px 12px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <Progress style={{ textAlign: 'center', width: '100%' }}>
          <b>Próxima:</b> {stops.find(s => s.status === "pending")?.address || "Rota concluída!"}
          <br />
          <span>
            <b>Entregues:</b> {delivered} &nbsp;
            <b>Insucesso:</b> {failed} &nbsp;
            <b>Transferidos:</b> {transferred}
          </span>
        </Progress>
        <div style={{ width: '100%', marginTop: 12, display: 'flex', justifyContent: 'center' }}>
          {delivered + failed + transferred < total ? (
            <Button color="#2196f3" style={{ width: '100%', maxWidth: 340, fontSize: 18, padding: '14px 0' }} onClick={() => onFinishRoute && onFinishRoute()}>
              Finalizar Rota
            </Button>
          ) : (
            <Button color="#10b981" style={{ width: '100%', maxWidth: 340, fontSize: 18, padding: '14px 0' }} disabled>
              Rota concluída
            </Button>
          )}
        </div>
      </ProgressBar>
    </div>
  );
}

// Arquivo removido. Nova versão premium em MapCircuitPremium.jsx

