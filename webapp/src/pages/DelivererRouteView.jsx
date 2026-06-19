import React, { useState, useEffect, useRef } from 'react';
import MapCircuitPremium from './MapCircuitPremium.jsx';
import { 
  Navigation, Check, X, MapPin, Locate, 
  AlertTriangle, Package, Phone, ChevronUp, WifiOff, 
  ArrowRightLeft, CheckCircle2, XCircle, Maximize, Minimize,
  AlertCircle, MessageSquare
} from 'lucide-react';
import { fetchWithAuth } from '../api_client'

// --- CONFIGURAÇÃO DE ESTILO E ÍCONES ---

// Estilo do Mapa (Clean/Muted)
const MAP_TILES_URL = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";

const FAILURE_REASONS = [
  "Pacote Avariado",
  "Recusado",
  "Cliente Ausente"
];

// Função para criar ícones personalizados (L.divIcon)
const createStopIcon = (index, status, isSelected) => {
  const isCompleted = status === 'delivered';
  const isFailed = status === 'failed';
  
  let bgColor = 'bg-blue-500';
  let borderColor = 'border-white';
  let content = `<span class="text-white font-bold text-sm">${index + 1}</span>`;
  let size = isSelected ? 'w-10 h-10' : 'w-8 h-8';
  let animation = '';

  if (isCompleted) {
    bgColor = 'bg-gray-400';
    content = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
  } else if (isFailed) {
    bgColor = 'bg-red-500';
    content = `<span class="text-white font-bold text-lg">!</span>`;
  } else if (isSelected) {
    // Próxima parada / Selecionada (Pulse)
    animation = `<span class="absolute inset-0 rounded-full bg-blue-400 opacity-75 animate-ping"></span>`;
  }

  return L.divIcon({
    className: 'bg-transparent',
    html: `
      <div class="relative flex items-center justify-center ${size}">
        ${animation}
        <div class="relative flex items-center justify-center w-full h-full rounded-full shadow-md border-2 ${borderColor} ${bgColor}">
          ${content}
        </div>
        ${isSelected ? '<div class="absolute -bottom-1 w-2 h-2 bg-blue-500 rotate-45"></div>' : ''}
      </div>
    `,
    iconSize: isSelected ? [40, 40] : [32, 32],
    iconAnchor: isSelected ? [20, 44] : [16, 16],
  });
};

// Ícone de Localização do Usuário (Ponto Azul + Cone)
const createUserLocationIcon = (heading) => {
  const rotation = heading || 0;
  return L.divIcon({
    className: 'bg-transparent',
    html: `
      <div class="relative w-16 h-16 flex items-center justify-center" style="transform: rotate(${rotation}deg); transition: transform 0.3s ease-out;">
        <!-- Cone de Visão -->
        <div class="absolute -top-4 w-0 h-0 border-l-[20px] border-l-transparent border-r-[20px] border-r-transparent border-b-[40px] border-b-blue-400/30 rounded-full blur-[2px]"></div>
        <!-- Ponto Central -->
        <div class="relative w-4 h-4 bg-blue-600 border-2 border-white rounded-full shadow-sm z-10"></div>
      </div>
    `,
    iconSize: [64, 64],
    iconAnchor: [32, 32],
  });
};

// Controlador de Eventos do Mapa (Auto-Center e Drag)
const MapController = ({ center, zoom, autoCenter, onDragStart }) => {
  const map = useMap();
  
  useEffect(() => {
    if (autoCenter && center) {
      map.flyTo(center, zoom, { animate: true, duration: 1.5 });
    }
  }, [center, zoom, autoCenter, map]);

  useMapEvents({
    dragstart: () => {
      onDragStart(); // Desativa auto-center se o usuário arrastar
    },
  });

  return null;
};

export default function DelivererRouteView() {
  const [routeInfo, setRouteInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [userLocation, setUserLocation] = useState(null)
  const [heading, setHeading] = useState(0)
  const [selectedStop, setSelectedStop] = useState(null)
  const [isUpdating, setIsUpdating] = useState(false)
  const [autoCenter, setAutoCenter] = useState(true)
  const [isOffline, setIsOffline] = useState(!navigator.onLine)
  const [bottomSheetOpen, setBottomSheetOpen] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [failureModalOpen, setFailureModalOpen] = useState(false)
  
  const pollIntervalRef = useRef(null)
  const mapRef = useRef(null)

  useEffect(() => {
    // 1. Identificar se é acesso via Token Público ou User ID
    const pathParts = window.location.pathname.split('/');
    // Verifica se a URL contém 'public/deliverer'
    const isPublicLink = window.location.pathname.includes('/public/deliverer');
    const tokenOrId = pathParts[pathParts.length - 1];

    const params = new URLSearchParams(window.location.search);
    const idFromQuery = params.get('user_id');
    
    // Prioridade: Token da URL pública > ID da URL > ID da Query > Telegram User ID
    const identifier = (isPublicLink && tokenOrId) ? tokenOrId : 
                       (tokenOrId && tokenOrId.length > 10 ? tokenOrId : idFromQuery || (window.Telegram?.WebApp?.initDataUnsafe?.user?.id));
    
    console.log("🔍 Rota ID/Token:", identifier, "Public:", isPublicLink);
    if (!identifier) {
      setError('Rota não identificada')
      setLoading(false)
      return
    }

    // 2. Carregar rota
    fetchUserRoute(identifier, isPublicLink)
    
    // 3. Polling em tempo real
    pollIntervalRef.current = setInterval(() => {
      fetchUserRoute(identifier, isPublicLink, true)
    }, 5000)
    
    // 4. Obter localização e orientação
    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const { latitude, longitude, heading: gpsHeading } = pos.coords;
        setUserLocation([latitude, longitude]);
        if (gpsHeading) setHeading(gpsHeading);
      },
      (err) => console.warn("Erro GPS:", err),
      { enableHighAccuracy: true, maximumAge: 1000, timeout: 5000 }
    );

    const handleOrientation = (event) => {
      if (event.webkitCompassHeading) {
        setHeading(event.webkitCompassHeading);
      } else if (event.alpha) {
        setHeading(360 - event.alpha);
      }
    };

    window.addEventListener('deviceorientation', handleOrientation, true);
    window.addEventListener('online', () => setIsOffline(false));
    window.addEventListener('offline', () => setIsOffline(true));

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      navigator.geolocation.clearWatch(watchId);
      window.removeEventListener('deviceorientation', handleOrientation);
      window.removeEventListener('online', () => setIsOffline(false));
      window.removeEventListener('offline', () => setIsOffline(true));
    }
  }, [])

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(err => console.error("Erro ao entrar em tela cheia:", err));
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
  };

  const fetchUserRoute = async (identifier, isPublic = false, isPolling = false) => {
    try {
      if (!isPolling) setLoading(true)
      
      let url = isPublic 
        ? `/api/deliverer/public-route/${identifier}`
        : `/api/deliverer/route?user_id=${identifier}`;
        
      const res = await fetchWithAuth(url)
      if (!res.ok) throw new Error('Rota não carregada')
      
      const data = await res.json()
      console.log("📦 Dados da rota recebidos:", data);
      setRouteInfo(data)
      
      // Lógica para selecionar a parada correta
      if (!selectedStop && data.stops && data.stops.length > 0) {
        if (data.current_stop_index !== undefined && data.stops[data.current_stop_index]) {
          setSelectedStop(data.stops[data.current_stop_index]);
        } else {
          const firstPending = data.stops.find(s => s.status === 'pending') || data.stops[0];
          setSelectedStop(firstPending);
        }
      } else if (selectedStop && data.stops) {
        // Atualizar objeto selectedStop com dados novos
        const updated = data.stops.find(s => s.id === selectedStop.id) || data.stops.find(s => s.lat === selectedStop.lat && s.lng === selectedStop.lng);
        if (updated) setSelectedStop(updated);
      }
    } catch (err) {
      if (!isPolling) setError(err.message)
    } finally {
      if (!isPolling) setLoading(false)
    }
  }
  
  const handleStopClick = (stop) => {
    setSelectedStop(stop);
    setAutoCenter(false);
    setBottomSheetOpen(false);
  };

  const handleStatusChange = async (status, reason = null) => {
    if (!selectedStop || isUpdating || !routeInfo) return;
    
    // Se for falha e não tiver motivo ainda, abre o modal
    if (status === 'failed' && !reason) {
      setFailureModalOpen(true);
      return;
    }

    try {
      setIsUpdating(true)
      const stopIndex = routeInfo.stops.findIndex(s => s.id === selectedStop.id);
      const actualIndex = stopIndex !== -1 ? stopIndex : routeInfo.stops.indexOf(selectedStop);
      
      if (actualIndex === -1) return;

      const params = new URLSearchParams({
        route_id: routeInfo.route_id,
        stop_index: actualIndex.toString(),
        status: status
      })
      
      if (reason) {
        params.append('reason', reason);
      }
      
      if (userLocation) {
        params.append('lat', userLocation[0].toString())
        params.append('lng', userLocation[1].toString())
      }
      
      const res = await fetchWithAuth(`/api/deliverer/complete-stop?${params.toString()}`, {
        method: 'POST'
      })
      
      if (res.ok) {
        setFailureModalOpen(false);
        // Atualizar imediatamente após sucesso
        const pathParts = window.location.pathname.split('/');
        const isPublicLink = window.location.pathname.includes('/public/deliverer');
        const tokenOrId = pathParts[pathParts.length - 1];
        const identifier = isPublicLink ? tokenOrId : (new URLSearchParams(window.location.search).get('user_id') || tokenOrId);
        await fetchUserRoute(identifier, isPublicLink);
        // Auto-center na próxima pendente será tratado pelo useEffect/fetchUserRoute logic se implementado,
        // mas aqui vamos forçar recentralizar se o usuário completou a atual
        setAutoCenter(true);
      }
    } catch (err) {
      console.error("Erro ao atualizar status:", err)
      alert('❌ Erro ao atualizar status')
    } finally {
      setIsUpdating(false)
    }
  }

  const handleNavigate = () => {
    if (!selectedStop) return;
    const url = `https://www.google.com/maps/dir/?api=1&destination=${selectedStop.lat},${selectedStop.lng}`;
    window.open(url, '_blank');
  };

  if (loading && !routeInfo) return <div className="flex items-center justify-center h-screen bg-gray-100">Carregando rota...</div>;
  if (error) return <div className="flex items-center justify-center h-screen"><div className="text-center p-6 bg-red-50 rounded-xl border border-red-200"><p className="text-red-600 font-semibold">❌ {error}</p></div></div>;
  if (!routeInfo) return <div className="flex items-center justify-center h-screen"><p className="text-gray-600">Sem rota atribuída</p></div>;

  const stops = routeInfo.stops || [];

  return (
    <div className="relative w-full h-screen overflow-hidden bg-gray-100">
      
      {/* 1. HEADER FLUTUANTE (Status e Offline) */}
      <div className="absolute top-4 left-4 right-4 z-[1000] flex flex-col gap-2 pointer-events-none">
        {isOffline && (
          <div className="bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center justify-center gap-2 animate-pulse">
            <WifiOff size={18} />
            <span className="font-medium text-sm">Sem conexão</span>
          </div>
        )}
        <div className="flex justify-between items-start">
          <div className="bg-white/90 backdrop-blur-sm px-4 py-2 rounded-full shadow-md pointer-events-auto">
            <span className="text-gray-700 font-bold text-sm">
              {stops.filter(s => s.status === 'delivered').length}/{stops.length} Entregues
            </span>
          </div>
          
          <button 
            onClick={toggleFullscreen}
            className="bg-blue-600 text-white p-3 rounded-full shadow-lg pointer-events-auto hover:bg-blue-700 active:scale-95 transition-all flex items-center justify-center"
            title={isFullscreen ? "Sair da tela cheia" : "Tela cheia"}
            style={{ minWidth: '44px', minHeight: '44px' }}
          >
            {isFullscreen ? <Minimize size={20} /> : <Maximize size={20} />}
          </button>
        </div>
      </div>

      {/* 2. BOTÃO RECENTRALIZAR */}
      {!autoCenter && (
        <button 
          onClick={() => setAutoCenter(true)}
          className="absolute bottom-[35%] right-4 z-[500] bg-white p-3 rounded-full shadow-lg text-blue-600 hover:bg-blue-50 transition-all active:scale-95"
        >
          <Locate size={24} />
        </button>
      )}

      {/* 3. MAPA PREMIUM SHOPEE */}
      <MapCircuitPremium 
        stops={routeInfo.stops} 
        hideUI={true}
        userLocation={userLocation}
        heading={heading}
        onPinClick={(idx) => {
          if (routeInfo.stops[idx]) {
            handleStopClick(routeInfo.stops[idx]);
          }
        }}
      />

      {/* 4. BOTTOM SHEET INTERATIVO */}
      {selectedStop && (
        <div 
          className={`absolute bottom-0 left-0 right-0 bg-white rounded-t-3xl shadow-[0_-5px_20px_rgba(0,0,0,0.1)] z-[600] transition-all duration-300 ease-in-out flex flex-col ${bottomSheetOpen ? 'h-[80vh]' : 'h-auto pb-4'}`}
        >
          {/* Handle para arrastar */}
          <div 
            className="w-full h-8 flex items-center justify-center cursor-pointer"
            onClick={() => setBottomSheetOpen(!bottomSheetOpen)}
            onTouchMove={() => setBottomSheetOpen(true)} // Gesto simples de swipe up
          >
            <div className="w-12 h-1.5 bg-gray-300 rounded-full"></div>
          </div>

          {/* Conteúdo Principal (Sempre visível) */}
          <div className="px-6 pb-4 flex flex-col gap-4">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-2xl font-bold text-gray-800 leading-tight">
                  Parada {stops.indexOf(selectedStop) + 1}
                </h2>
                <p className="text-gray-500 text-sm font-medium mt-1">
                  {selectedStop.recipient || 'Destinatário'}
                </p>
              </div>
              <div className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide ${
                selectedStop.status === 'pending' ? 'bg-blue-100 text-blue-700' :
                selectedStop.status === 'delivered' ? 'bg-green-100 text-green-700' :
                'bg-red-100 text-red-700'
              }`}>
                {selectedStop.status === 'pending' ? 'Pendente' : selectedStop.status}
              </div>
            </div>

            <div className="flex items-start gap-3">
              <MapPin className="text-gray-400 mt-1 shrink-0" size={20} />
              <p className="text-lg text-gray-800 font-medium leading-snug">
                {selectedStop.address}
              </p>
            </div>

            {/* Botões de Ação Primária */}
            <div className="flex flex-col gap-3 mt-2">
              <div className="grid grid-cols-[1fr_auto] gap-3">
                <button 
                  onClick={handleNavigate}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-xl flex items-center justify-center gap-2 shadow-blue-200 shadow-lg active:scale-95 transition-transform"
                >
                  <Navigation size={20} />
                  Navegar
                </button>
                
                <button 
                  onClick={() => setBottomSheetOpen(!bottomSheetOpen)}
                  className="bg-gray-100 hover:bg-gray-200 p-3 rounded-xl text-gray-600"
                >
                  <ChevronUp size={24} className={`transition-transform ${bottomSheetOpen ? 'rotate-180' : ''}`} />
                </button>
              </div>

              {selectedStop.status === 'pending' && (
                <div className="grid grid-cols-2 gap-3">
                  <button 
                    onClick={() => handleStatusChange('failed')}
                    className="border-2 border-red-100 bg-red-50 text-red-600 font-bold py-3 rounded-xl flex items-center justify-center gap-2 hover:bg-red-100 active:scale-95 transition-all"
                  >
                    <X size={20} />
                    Insucesso
                  </button>
                  <button 
                    onClick={() => handleStatusChange('delivered')}
                    className="bg-green-500 text-white font-bold py-3 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-green-200 hover:bg-green-600 active:scale-95 transition-all"
                  >
                    <Check size={20} />
                    Entregue
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Conteúdo Expandido (Detalhes e Ações de Finalização) */}
          <div className={`flex-1 overflow-y-auto px-6 pb-6 transition-opacity duration-300 ${bottomSheetOpen ? 'opacity-100' : 'opacity-0 pointer-events-none hidden'}`}>
            <div className="space-y-6">
              {/* Info Adicional */}
              <div className="bg-gray-50 p-4 rounded-xl border border-gray-100 space-y-3">
                <div className="flex items-center gap-3 text-gray-600">
                  <Package size={18} />
                  <span className="text-sm">Pacote #{selectedStop.id?.toString().slice(-5) || '---'} • {selectedStop.packages?.length || 1} vol</span>
                </div>
                {selectedStop.note && (
                  <div className="flex items-start gap-3 text-orange-600 bg-orange-50 p-2 rounded-lg">
                    <AlertTriangle size={18} className="shrink-0 mt-0.5" />
                    <span className="text-sm font-medium">{selectedStop.note}</span>
                  </div>
                )}
                <div className="flex items-center gap-3 text-gray-600">
                  <Phone size={18} />
                  <span className="text-sm underline decoration-dotted">Contato não disponível</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5. MODAL DE MOTIVO DE FALHA */}
      {failureModalOpen && (
        <div className="fixed inset-0 z-[2000] flex items-end sm:items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 w-full max-w-md rounded-2xl shadow-2xl overflow-hidden animate-in slide-in-from-bottom duration-300">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-3 bg-red-100 dark:bg-red-900/30 rounded-full text-red-600 dark:text-red-400">
                  <AlertCircle size={24} />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900 dark:text-white">Motivo do Insucesso</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Por que esta entrega não foi realizada?</p>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-2 mb-8">
                {FAILURE_REASONS.map(reason => (
                  <button
                    key={reason}
                    onClick={() => handleStatusChange('failed', reason)}
                    className="flex items-center justify-between p-4 rounded-xl border-2 border-gray-100 dark:border-gray-700 hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all text-left group"
                  >
                    <span className="font-semibold text-gray-700 dark:text-gray-300 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                      {reason}
                    </span>
                    <ArrowRightLeft size={16} className="text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                ))}
              </div>

              <button
                onClick={() => setFailureModalOpen(false)}
                className="w-full py-4 text-gray-500 dark:text-gray-400 font-bold hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
