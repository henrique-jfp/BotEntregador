import React, { useEffect, useState, useRef } from 'react';
import MapCircuitPremium from './MapCircuitPremium.jsx';
import Legend from '../components/Legend';

function BottomCard({ stop, onClose, onDeliver, onFail, onTransfer, nextLabel }) {
  if (!stop) return null;
  return (
    <div style={{position:'absolute',left:0,right:0,bottom:0,zIndex:1200}}>
      <div className="mx-3 mb-3 bg-white rounded-xl shadow-2xl" style={{overflow:'hidden'}}>
        <div className="p-3 flex items-start justify-between">
          <div style={{flex:1}}>
            <div className="font-bold text-base text-gray-800">{stop.address || `Parada ${stop.id || ''}`}</div>
            <div className="text-sm text-gray-500 mt-1">{stop.packages ? `${stop.packages.length} pacote(s)` : ''}</div>
            <div className="text-xs text-gray-400 mt-1">{stop.note || ''}</div>
          </div>
          <button onClick={onClose} className="ml-3 p-1 rounded-md bg-gray-100 text-gray-600" aria-label="Fechar">✕</button>
        </div>

        <div className="grid grid-cols-2 gap-3 p-3">
          <a className="col-span-2 md:col-span-1 flex items-center justify-center gap-2 px-4 py-3 bg-gray-700 text-white rounded-lg font-semibold shadow" href={`https://www.google.com/maps/dir/?api=1&destination=${stop.lat},${stop.lng}`} target="_blank" rel="noreferrer">Abrir no Google Maps</a>

          <button onClick={onDeliver} className="col-span-2 md:col-span-1 px-4 py-3 bg-emerald-500 text-white rounded-lg font-semibold shadow transform active:scale-95 transition">Entregue</button>

          <button onClick={onFail} className="px-4 py-3 bg-red-500 text-white rounded-lg font-semibold shadow transform active:scale-95 transition">Insucesso</button>
          <button onClick={onTransfer} className="px-4 py-3 bg-blue-600 text-white rounded-lg font-semibold shadow transform active:scale-95 transition">Transferir</button>
        </div>

        <div className="p-2 text-xs text-center text-gray-500">{nextLabel}</div>
      </div>
    </div>
  );
}

export default function DelivererPublicView() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [route, setRoute] = useState(null);
  const [selectedIndex, setSelectedIndex] = useState(null);

  const deliveredCount = route ? (route.stops || []).filter(s => s.status === 'delivered' || s.delivered).length : 0;

  // Extrai token da URL: /public/deliverer/:token
  const token = window.location.pathname.split('/').pop();

  useEffect(() => {
    if (!token) {
      setError('Token ausente');
      setLoading(false);
      return;
    }

    const load = async () => {
      try {
        const res = await fetch(`/api/deliverer/public-route/${token}`);
        if (!res.ok) {
          // If token not found, still show the map (empty route) so user sees the base map
          if (res.status === 404) {
            setRoute({ stops: [], deliverer_name: 'Entregador público', route_id: null, route_geometry: null, color: '#3b82f6' });
            return;
          }
          const b = await res.json().catch(() => ({}));
          throw new Error(b.detail || 'Link inválido');
        }
        const data = await res.json();
        // normalize stops: ensure stops is array and status flags
        data.stops = (data.stops || []).map(s => ({ ...s, delivered: s.status === 'delivered' }));
        setRoute(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [token]);

  if (loading) return <div className="p-6">Carregando rota pública...</div>;
  if (error) return <div className="p-6 text-red-600">Erro: {error}</div>;
  if (!route) return <div className="p-6">Nenhuma rota encontrada</div>;

  // seleciona uma parada (abre bottom card)
  const handleStopSelect = (idx) => {
    setSelectedIndex(idx);
  };

  // índice do próximo ponto pendente (primeiro não entregue)
  const currentPendingIndex = (route.stops || []).findIndex(s => !(s.status === 'delivered' || s.delivered));
  const currentIndexToPass = currentPendingIndex === -1 ? 0 : currentPendingIndex;

  const doAction = async (status) => {
    if (selectedIndex === null) return;
    try {
      // Optimistic update: mark locally first
      const prev = JSON.parse(JSON.stringify(route));
      const stopsCopy = (route.stops || []).slice();
      stopsCopy[selectedIndex] = { ...stopsCopy[selectedIndex], status, delivered: status === 'delivered' };
      setRoute({ ...route, stops: stopsCopy });

      // calcula próximo pendente e abre ele (auto-avançar)
      const nextPending = stopsCopy.findIndex((s, i) => i > selectedIndex && !(s.status === 'delivered' || s.delivered));
      setSelectedIndex(nextPending === -1 ? null : nextPending);

      const q = new URLSearchParams({ route_id: route.route_id || '', stop_index: String(selectedIndex), status });
      const resp = await fetch(`/api/deliverer/complete-stop?${q.toString()}`, { method: 'POST' });
      if (!resp.ok) {
        // revert on error
        setRoute(prev);
        setSelectedIndex(selectedIndex);
        const b = await resp.json().catch(() => ({}));
        throw new Error(b.detail || 'Erro ao marcar parada');
      }
      // try to refresh route, but don't clobber UI on failure
      try {
        const r2 = await (await fetch(`/api/deliverer/public-route/${token}`)).json();
        r2.stops = (r2.stops || []).map(s => ({ ...s, delivered: s.status === 'delivered' }));
        setRoute(r2);
      } catch (_) {
        // ignore refresh failures (we already applied optimistic change)
      }
    } catch (e) {
      alert('Erro: ' + e.message);
    }
  };

  const doTransfer = async () => {
    if (selectedIndex === null) return;
    const target = prompt('Transferir para (nome ou telegram id):');
    if (!target) return;
    try {
      // Optimistic transfer: remove stop locally
      const prev = JSON.parse(JSON.stringify(route));
      const stopsCopy = (route.stops || []).slice();
      stopsCopy.splice(selectedIndex, 1);
      setRoute({ ...route, stops: stopsCopy });
      setSelectedIndex(null);

      const q = new URLSearchParams({ route_id: route.route_id || '', stop_index: String(selectedIndex), target_deliverer: target });
      const resp = await fetch(`/api/deliverer/transfer-stop?${q.toString()}`, { method: 'POST' });
      if (!resp.ok) {
        setRoute(prev);
        const b = await resp.json().catch(() => ({}));
        throw new Error(b.detail || 'Erro ao transferir parada');
      }
      try {
        const r2 = await (await fetch(`/api/deliverer/public-route/${token}`)).json();
        r2.stops = (r2.stops || []).map(s => ({ ...s, delivered: s.status === 'delivered' }));
        setRoute(r2);
      } catch (_) {}
    } catch (e) {
      alert('Erro: ' + e.message);
    }
  };

  return (
    <div className="h-screen w-screen" style={{position:'relative'}}>
      <div className="p-3 bg-white border-b shadow-sm" style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <div>
          <h3 className="font-bold text-lg">Rota de: {route.deliverer_name || 'Entregador'}</h3>
          <p className="text-sm text-gray-600">Visualização pública e minimalista — apenas navegação</p>
        </div>
        <div style={{fontSize:12,color:'#374151'}}>{deliveredCount}/{(route.stops || []).length} entregues</div>
      </div>
      <div style={{ height: 'calc(100vh - 72px)', position: 'relative' }}>
        <MapCircuitPremium
          stops={(route.stops || []).map((s, idx) => ({
            id: s.id || idx,
            position: [s.lat, s.lng],
            street: s.address || s.recipient,
            neighborhood: s.neighborhood || '',
            status: s.status,
            number: idx + 1,
            isActive: idx === currentIndexToPass
          }))}
          hideUI={true}
          userLocation={[
            route.base?.lat || route.stops?.[0]?.lat || -22.966441,
            route.base?.lng || route.stops?.[0]?.lng || -43.188863
          ]}
          onPinClick={handleStopSelect}
        />
        <Legend />
      </div>

      <BottomCard
        stop={selectedIndex !== null ? route.stops[selectedIndex] : null}
        onClose={() => setSelectedIndex(null)}
        onDeliver={() => doAction('delivered')}
        onFail={() => doAction('failed')}
        onTransfer={doTransfer}
        nextLabel={(() => {
          const next = (route.stops || []).findIndex((s, i) => i > (selectedIndex||-1) && !(s.status === 'delivered' || s.delivered));
          return next === -1 ? 'Nenhuma próxima parada pendente' : `Próxima: Parada ${next + 1}`;
        })()}
      />
    </div>
  );
}
