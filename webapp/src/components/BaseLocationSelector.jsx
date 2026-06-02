/**
 * 📍 BaseLocationSelector - Componente para selecionar localização base
 * Permite clicar/arrastar no mapa para definir ponto de partida
 */
import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix para ícones do Leaflet
delete L.Icon.Default.prototype._getIconUrl;

// Ícone para o marcador da base
const baseIcon = L.divIcon({
  html: `<div style="
    background: linear-gradient(135deg, #FF6600 0%, #FF8800 100%);
    color: white;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    border: 3px solid white;
    box-shadow: 0 2px 8px rgba(0,0,0,0.4);
  ">🏠</div>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  className: ''
});

// Componente para capturar cliques no mapa
function MapClickHandler({ onLocationSelect }) {
  useMapEvents({
    click: (e) => {
      onLocationSelect(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

/**
 * BaseLocationSelector
 * @param {number} lat - Latitude atual
 * @param {number} lng - Longitude atual  
 * @param {function} onLocationChange - Callback (lat, lng) => void
 * @param {string} height - Altura do mapa
 */
export default function BaseLocationSelector({ 
  lat = -22.9068, 
  lng = -43.1729, 
  onLocationChange,
  height = '256px'
}) {
  const [position, setPosition] = useState([lat, lng]);

  // Atualizar posição quando props mudam
  useEffect(() => {
    setPosition([lat, lng]);
  }, [lat, lng]);

  const handleLocationSelect = (newLat, newLng) => {
    setPosition([newLat, newLng]);
    if (onLocationChange) {
      onLocationChange(newLat, newLng);
    }
  };

  return (
    <div className="rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600" style={{ height }}>
      <MapContainer
        center={position}
        zoom={14}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          attribution='© OpenStreetMap'
        />
        
        {/* Captura cliques */}
        <MapClickHandler onLocationSelect={handleLocationSelect} />
        
        {/* Marcador da base */}
        <Marker 
          position={position} 
          icon={baseIcon}
          draggable={true}
          eventHandlers={{
            dragend: (e) => {
              const newPos = e.target.getLatLng();
              handleLocationSelect(newPos.lat, newPos.lng);
            }
          }}
        />
      </MapContainer>
      <div className="bg-gray-50 dark:bg-gray-700 p-2 text-xs text-gray-600 dark:text-gray-300 text-center">
        👆 Clique no mapa ou arraste o marcador para definir a base
      </div>
    </div>
  );
}
