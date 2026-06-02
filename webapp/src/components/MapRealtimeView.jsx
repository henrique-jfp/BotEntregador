import React, { useState, useEffect, useRef, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Maximize, Minimize } from 'lucide-react';

/**
 * MapRealtimeView
 * Mostra mapa com rotas coloridas
 * Atualiza em tempo real via WebSocket quando entregador completa entrega
 */
export default function MapRealtimeView({ sessionId }) {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const markersLayer = useRef(null);
  const markersById = useRef({});
  const [mapData, setMapData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [emptyState, setEmptyState] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const [activeSessionId, setActiveSessionId] = useState(sessionId || null);
  const routesSummary = mapData?.routes_summary || [];
  const [isFullscreen, setIsFullscreen] = useState(false);
  const viewContainerRef = useRef(null);

  // Resolver sessão ativa quando sessionId não é fornecido
  useEffect(() => {
    if (sessionId) {
      setActiveSessionId(sessionId);
      return;
    }

    const loadActiveSession = async () => {
      try {
        const response = await fetch('/api/map/realtime/active');
        if (response.ok) {
          const data = await response.json();
          setActiveSessionId(data.session_id);
          setError(null);
          return;
        }

        const stateResponse = await fetch('/api/session/state');
        if (stateResponse.ok) {
          const stateData = await stateResponse.json();
          if (stateData?.active && stateData.session_id) {
            setActiveSessionId(stateData.session_id);
            setError(null);
            return;
          }
        }

        setError('Nenhuma sessão ativa');
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    loadActiveSession();
  }, [sessionId]);

  // Carregar mapa inicial
  useEffect(() => {
    if (!activeSessionId) return;

    const loadInitialMap = async () => {
      try {
        const response = await fetch(`/api/map/realtime/${activeSessionId}`);
        if (!response.ok) {
          const errData = await response.json().catch(() => null);
          throw new Error(errData?.detail || 'Erro ao carregar mapa');
        }
        
        const data = await response.json();
        const points = Array.isArray(data?.points) ? data.points : [];
        setMapData({ ...data, points });
        if (data?.status === 'empty' || points.length === 0) {
          setEmptyState('Nenhuma rota iniciada. Otimize as rotas para ver o mapa.');
        } else {
          setEmptyState(null);
        }
        setError(null);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    loadInitialMap();
  }, [activeSessionId]);

  const updatePointMarker = useCallback((update) => {
    const marker = markersById.current[update.point_id];
    if (marker) {
      marker.setStyle({ fillColor: update.new_color });
    }

    setMapData(prev => {
      if (!prev) return prev;
      const updatedPoints = prev.points.map(p => {
        if (p.id === update.point_id) {
          return { ...p, color: update.new_color, status: update.status };
        }
        return p;
      });

      const updatedRoutes = prev.routes_summary.map(r => {
        if (r.route_id === update.route_id) {
          return {
            ...r,
            delivered: update.delivered,
            completion_rate: update.route_completion
          };
        }
        return r;
      });

      return {
        ...prev,
        points: updatedPoints,
        routes_summary: updatedRoutes
      };
    });
  }, []);

  const updateRoutesSummary = useCallback((update) => {
    setMapData(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        routes_summary: prev.routes_summary.map(r => {
          const newRoute = update.routes.find(u => u.route_id === r.route_id);
          return newRoute
            ? { ...r, delivered: newRoute.delivered, completion_rate: newRoute.completion }
            : r;
        })
      };
    });
  }, []);

  // Inicializar mapa (sem reiniciar WebSocket)
  useEffect(() => {
    if (!mapData || !mapContainer.current || !activeSessionId) return;
    if (!Array.isArray(mapData.points) || mapData.points.length === 0) return;

    // Criar mapa
    if (!map.current) {
      map.current = L.map(mapContainer.current).setView([-23.5505, -46.6333], 12);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
      }).addTo(map.current);
      markersLayer.current = L.layerGroup().addTo(map.current);
    }

    // Limpar marcadores anteriores
    if (markersLayer.current) {
      markersLayer.current.clearLayers();
    }

    // Adicionar pontos ao mapa
    const group = new L.FeatureGroup();
    markersById.current = {};
      mapData.points.forEach(point => {
      const marker = L.circleMarker(
        [point.lat, point.lng],
        {
          radius: 8,
          fillColor: point.color,
          color: '#000',
          weight: 2,
          opacity: 1,
          fillOpacity: 0.8
        }
      );

      // Criar popup com botão Navegar + botão Marcar entregue quando aplicável
      const popupHtml = `
        <div style="font-size:12px; width:220px">
          <strong>${point.address}</strong><br/>
          <small>Rota: ${point.route_color} | Parada: ${point.sequence}</small><br/>
          <small>Status: ${point.status === 'delivered' ? '✅ Entregue' : '⏳ Pendente'}</small>
          <div style="margin-top:8px; display:flex; gap:6px">
            <a target="_blank" rel="noreferrer" href="https://www.google.com/maps/dir/?api=1&destination=${point.lat},${point.lng}" style="flex:1;padding:6px 8px;background:#2563eb;color:white;border-radius:8px;text-decoration:none;font-size:12px;text-align:center">Navegar</a>
            ${point.status !== 'delivered' ? `<button data-point-id="${point.id}" data-route-id="${point.route_id}" data-sequence="${point.sequence}" style="flex:1;padding:6px 8px;background:#16a34a;color:white;border-radius:8px;border:none;font-size:12px;cursor:pointer">Entregar</button>` : ''}
            <button class="generate-link" data-route-id="${point.route_id}" style="padding:6px 8px;background:#f59e0b;color:white;border-radius:8px;border:none;font-size:12px;cursor:pointer">Gerar link</button>
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml);
      
      markersById.current[point.id] = marker;
      group.addLayer(marker);
      markersLayer.current?.addLayer(marker);
    });

    if (group.getLayers().length > 0) {
      map.current.fitBounds(group.getBounds().pad(0.1));
    }

    // Delegação de clique para botões dentro dos popups (marcar entrega)
    map.current.on('popupopen', (e) => {
      try {
        const popupNode = e.popup.getElement();
        if (!popupNode) return;
        const btn = popupNode.querySelector('button[data-point-id]');
        if (btn) {
          const handler = async (ev) => {
            ev.preventDefault();
            const pointId = btn.getAttribute('data-point-id');
            const routeId = btn.getAttribute('data-route-id');
            const seq = parseInt(btn.getAttribute('data-sequence') || '0', 10) - 1;

            try {
              btn.disabled = true;
              // POST para marcar parada completa
              const params = new URLSearchParams({ route_id: routeId, stop_index: seq.toString(), status: 'delivered' });
              const res = await fetch(`/api/deliverer/complete-stop?${params.toString()}`, { method: 'POST' });
              if (res.ok) {
                // Atualizar visual localmente
                btn.textContent = '✅ OK';
                setTimeout(() => { if (e.popup) e.popup.close(); }, 700);
              } else {
                const body = await res.json().catch(() => ({}));
                alert('Erro: ' + (body.detail || 'Não foi possível marcar entrega'));
                btn.disabled = false;
              }
            } catch (er) {
              console.error('Erro ao marcar entrega:', er);
              alert('Erro de rede ao marcar entrega');
              btn.disabled = false;
            }
          };

          btn.addEventListener('click', handler, { once: true });
        }
        // Botão Gerar Link
        const gen = popupNode.querySelector('button.generate-link');
        if (gen) {
          gen.addEventListener('click', async (ev) => {
            ev.preventDefault();
            try {
              gen.disabled = true;
              const routeId = gen.getAttribute('data-route-id');
              const res = await fetch('/api/deliverer/link', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ route_id: routeId })
              });
              if (res.ok) {
                const body = await res.json();
                const url = body.url || (body.token ? `/deliverer/public/${body.token}` : null);
                if (url) {
                  try { await navigator.clipboard.writeText(url); } catch(e) {}
                  alert('Link gerado e copiado: ' + url);
                } else {
                  alert('Link gerado: ' + JSON.stringify(body));
                }
              } else {
                const err = await res.json().catch(() => ({}));
                alert('Erro ao gerar link: ' + (err.detail || res.statusText));
              }
            } catch (er) {
              console.error('Erro gerando link:', er);
              alert('Erro de rede ao gerar link');
            } finally {
              gen.disabled = false;
            }
          });
        }
      } catch (er) {
        console.warn('Erro no popupopen handler', er);
      }
    });

  }, [mapData, activeSessionId]);

  // Conectar WebSocket para atualizações em tempo real
  useEffect(() => {
    if (!activeSessionId) return;

    const connectWebSocket = () => {
      // Limpar conexão anterior e timeouts
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//${window.location.host}/api/map/ws/${activeSessionId}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ WebSocket conectado');
        setWsConnected(true);
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
        pingIntervalRef.current = setInterval(() => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send('ping');
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const update = JSON.parse(event.data);

          if (update.type === 'point_update') {
            updatePointMarker(update);
          } else if (update.type === 'state_update') {
            updateRoutesSummary(update);
          }
        } catch (err) {
          console.error('Erro ao processar update WebSocket:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket erro:', error);
        setWsConnected(false);
      };

      ws.onclose = () => {
        console.log('❌ WebSocket desconectado');
        setWsConnected(false);
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        if (wsRef.current === ws) {
          reconnectTimeoutRef.current = setTimeout(connectWebSocket, 5000);
        }
      };
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [activeSessionId, updatePointMarker, updateRoutesSummary]);

  useEffect(() => {
    function onFullscreenChange() {
      setIsFullscreen(Boolean(document.fullscreenElement));
    }
    document.addEventListener('fullscreenchange', onFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', onFullscreenChange);
  }, []);

  const toggleFullscreen = () => {
    if (!viewContainerRef.current) return;
    if (!document.fullscreenElement) {
      viewContainerRef.current.requestFullscreen().catch(err => {
        alert(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
      });
    } else {
      document.exitFullscreen();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p>Carregando mapa...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="font-semibold text-red-800">Erro ao carregar mapa</h3>
        <p className="text-red-700 text-sm">{error}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            onClick={() => window.location.reload()}
            className="px-3 py-2 bg-red-600 text-white text-xs rounded-lg font-semibold"
          >
            Tentar novamente
          </button>
          <a
            href="/?tab=analysis"
            className="px-3 py-2 bg-white text-red-700 text-xs rounded-lg font-semibold border border-red-200"
          >
            Ir para Roteirização
          </a>
        </div>
      </div>
    );
  }

  if (emptyState) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-5">
        <h3 className="font-semibold text-amber-800">Mapa ainda não disponível</h3>
        <p className="text-amber-700 text-sm mt-1">{emptyState}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <a
            href="/?tab=analysis"
            className="px-3 py-2 bg-amber-600 text-white text-xs rounded-lg font-semibold"
          >
            Otimizar rotas agora
          </a>
          <button
            onClick={() => window.location.reload()}
            className="px-3 py-2 bg-white text-amber-700 text-xs rounded-lg font-semibold border border-amber-200"
          >
            Recarregar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4" ref={viewContainerRef}>
      {/* Indicador de conexão WebSocket */}
      <div className="flex items-center gap-2 text-sm">
        <div className={`w-3 h-3 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
        <span className="font-medium">
          {wsConnected ? '🟢 Mapa ao vivo' : '🔴 Desconectado'}
        </span>
      </div>

      {/* Legenda de cores */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        {routesSummary.map(route => (
          <div key={route.route_id} className="bg-white border rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <div 
                className="w-4 h-4 rounded-full" 
                style={{ backgroundColor: route.color }}
              ></div>
              <span className="font-semibold">{route.color.toUpperCase()}</span>
            </div>
            <p className="text-xs text-gray-600 mb-1">Entregador: {route.deliverer || 'Não atribuído'}</p>
            <p className="text-xs font-medium">
              {route.delivered}/{route.total} entregues ({route.completion_rate.toFixed(0)}%)
            </p>
          </div>
        ))}
      </div>

      {/* Mapa */}
      <div className="relative">
        <div 
          ref={mapContainer} 
          className="border rounded-lg"
          style={{ height: '500px', width: '100%' }}
        ></div>
        <button 
          onClick={toggleFullscreen}
          className="absolute top-2 right-2 bg-white p-2 rounded-md shadow-lg z-[1000] focus:outline-none"
          aria-label="Toggle fullscreen"
        >
          {isFullscreen ? <Minimize className="w-5 h-5" /> : <Maximize className="w-5 h-5" />}
        </button>
      </div>

      {/* Resumo */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 mb-2">📊 Resumo</h3>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-gray-600">Total de Rotas</p>
            <p className="text-2xl font-bold text-blue-600">{mapData.total_routes}</p>
          </div>
          <div>
            <p className="text-gray-600">Total de Pontos</p>
            <p className="text-2xl font-bold text-blue-600">{mapData.total_points}</p>
          </div>
          <div>
            <p className="text-gray-600">Entregues</p>
            <p className="text-2xl font-bold text-green-600">
              {mapData.points.filter(p => p.status === 'delivered').length}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
