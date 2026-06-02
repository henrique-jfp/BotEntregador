import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Dados simulados (substitua por props ou API)
const mockMarkers = [
  // ...adicione markers reais aqui ou passe via props...
];
const mockBase = { lat: -22.966441, lng: -43.188863, address: 'Lat: -22.966441, Lng: -43.188863' };

export default function MapShopee({ markers = mockMarkers, base = mockBase, entregadores = [] }) {
  const mapRef = useRef(null);
  const [currentMarker, setCurrentMarker] = useState(null);
  const [deliveryStatus, setDeliveryStatus] = useState({});
  const [showCard, setShowCard] = useState(false);
  const [showTransfer, setShowTransfer] = useState(false);
  const [receivedCount, setReceivedCount] = useState(0);

  // Inicializa mapa
  useEffect(() => {
    if (!mapRef.current) {
      mapRef.current = L.map('map-shopee').setView([base.lat, base.lng], 16);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19,
        minZoom: 12
      }).addTo(mapRef.current);
    }
    // Adiciona base
    if (base) {
      const baseIcon = L.divIcon({
        className: 'pin-container',
        html: `<div class="pin-marker pin-base"><div class="pin-body"></div><div class="pin-number">🏠</div></div>`,
        iconSize: [32, 40],
        iconAnchor: [16, 40],
        popupAnchor: [0, -40]
      });
      L.marker([base.lat, base.lng], { icon: baseIcon }).addTo(mapRef.current).bindPopup(`<b>🏠 BASE</b><br>${base.address}`);
    }
    // Adiciona markers
    markers.forEach((m) => {
      const pinIcon = createShopeePin(m.number, m.status);
      const marker = L.marker([m.lat, m.lon], { icon: pinIcon }).addTo(mapRef.current);
      marker.on('click', () => openCard(m));
      if (m.is_current) marker.setZIndexOffset(1000);
    });
    // Ajusta bounds
    const allPoints = [ [base.lat, base.lng], ...markers.map(m => [m.lat, m.lon]) ];
    if (allPoints.length > 0) {
      const bounds = L.latLngBounds(allPoints);
      mapRef.current.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
    }
    // eslint-disable-next-line
  }, []);

  // Função para criar pin Shopee
  function createShopeePin(number, status) {
    let statusClass = `pin-${status}`;
    let displayText = number;
    if (status === 'completed') displayText = '✓';
    else if (status === 'failed') displayText = '✗';
    return L.divIcon({
      className: 'pin-container',
      html: `<div class="pin-marker ${statusClass}"><div class="pin-body"></div><div class="pin-number">${displayText}</div></div>`,
      iconSize: [32, 40],
      iconAnchor: [16, 40],
      popupAnchor: [0, -40]
    });
  }

  // Card e ações
  function openCard(marker) {
    setCurrentMarker(marker);
    setShowCard(true);
  }
  function closeCard() {
    setShowCard(false);
  }
  function markDelivered() {
    if (!currentMarker) return;
    setDeliveryStatus(ds => ({ ...ds, [currentMarker.number]: 'completed' }));
    closeCard();
  }
  function markFailed() {
    if (!currentMarker) return;
    setDeliveryStatus(ds => ({ ...ds, [currentMarker.number]: 'failed' }));
    closeCard();
  }
  function transferPackage() {
    setShowTransfer(true);
  }
  function closeTransferModal() {
    setShowTransfer(false);
  }

  // Render
  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      <div id="map-shopee" style={{ width: '100vw', height: '100vh' }}></div>
      {/* Header */}
      <div className="header" style={{ position: 'absolute', top: 10, left: '50%', transform: 'translateX(-50%)', zIndex: 1000 }}>
        <div className="title">ROTA_2</div>
        <div className="stats">
          <span>{Object.values(deliveryStatus).filter(s => s === 'completed' || s === 'failed').length} de {markers.length} paradas</span> | <span>{markers.length} pacotes</span>
        </div>
      </div>
      {/* Card */}
      {showCard && currentMarker && (
        <div className="bottom-card visible">
          <div className="card-header">
            <div className="card-number">{currentMarker.number}</div>
            <button className="card-close" onClick={closeCard}>×</button>
          </div>
          <div className="card-address">{currentMarker.address}</div>
          <div className="card-info">Entrega {currentMarker.packages} unidade{currentMarker.packages > 1 ? 's' : ''} | {deliveryStatus[currentMarker.number] === 'completed' ? '✅ Entregue' : deliveryStatus[currentMarker.number] === 'failed' ? '❌ Insucesso' : '📦 Pendente'}</div>
          <button className="btn btn-maps" onClick={() => window.open(`https://www.google.com/maps/dir/?api=1&destination=${currentMarker.lat},${currentMarker.lon}`, '_blank')}>Abrir no Google Maps</button>
          <div className="action-buttons">
            <button className="btn btn-success" onClick={markDelivered}>Entregue</button>
            <button className="btn btn-danger" onClick={markFailed}>Insucesso</button>
            <button className="btn btn-transfer" onClick={transferPackage}>Transferir</button>
          </div>
        </div>
      )}
      {/* Transfer Modal */}
      {showTransfer && (
        <div className="transfer-modal visible">
          <div className="transfer-content">
            <div className="transfer-title">↗️ Transferir para:</div>
            <div id="entregadores-list">
              {entregadores.length === 0 ? (
                <input type="text" placeholder="Nome do entregador" style={{ width: '100%', padding: 15, border: '2px solid #ddd', borderRadius: 12, fontSize: 16, marginBottom: 10 }} />
              ) : (
                entregadores.map(e => (
                  <button className="entregador-btn" key={e.id}>{e.name}</button>
                ))
              )}
            </div>
            <button className="cancel-transfer" onClick={closeTransferModal}>Cancelar</button>
          </div>
        </div>
      )}
      {/* Estilos inline para pins Shopee */}
      <style>{`
        .pin-marker { position: relative; width: 32px; height: 40px; }
        .pin-marker .pin-body { position: absolute; top: 0; left: 0; width: 32px; height: 32px; border-radius: 50% 50% 50% 0; transform: rotate(-45deg); box-shadow: 0 3px 8px rgba(0,0,0,0.4); }
        .pin-marker .pin-number { position: absolute; top: 4px; left: 0; width: 32px; height: 24px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 13px; text-shadow: 0 1px 2px rgba(0,0,0,0.3); z-index: 1; }
        .pin-pending .pin-body { background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%); }
        .pin-current .pin-body { background: linear-gradient(135deg, #FF9800 0%, #E65100 100%); }
        .pin-completed .pin-body { background: linear-gradient(135deg, #9E9E9E 0%, #616161 100%); }
        .pin-failed .pin-body { background: linear-gradient(135deg, #F44336 0%, #C62828 100%); }
        .pin-base .pin-body { background: linear-gradient(135deg, #9C27B0 0%, #6A1B9A 100%); }
      `}</style>
    </div>
  );
}
// Arquivo removido. Nova versão premium em MapCircuitPremium.jsx
