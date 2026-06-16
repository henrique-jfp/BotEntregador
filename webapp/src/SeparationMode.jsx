import { useState, useEffect, useRef, useCallback } from 'react';
import { Html5Qrcode } from 'html5-qrcode';
import { 
  Package, Truck, Barcode, Play, Flag, Camera, Keyboard, RotateCcw,
  AlertCircle, Loader2, Wifi, WifiOff, X, SwitchCamera, Zap, RefreshCw
} from 'lucide-react';
import { fetchSafe } from './api_client';
import { addScanToQueue, getPendingScans, removeScanFromQueue } from './lib/offlineQueue';

// Color map helper
const COLOR_NAMES = {
    '#FF4444': 'VERMELHO', '#44FF44': 'VERDE', '#4444FF': 'AZUL',
    '#FFD700': 'AMARELO', '#FF69B4': 'ROSA', '#9370DB': 'ROXO',
    '#FF8C00': 'LARANJA', '#00CED1': 'CIANO', '#32CD32': 'VERDE-LIMA',
    '#FF1493': 'ROSA-ESCURO', '#EF4444': 'VERMELHO', '#22C55E': 'VERDE',
    '#3B82F6': 'AZUL', '#EAB308': 'AMARELO', '#EC4899': 'ROSA',
    '#A855F7': 'ROXO', '#F97316': 'LARANJA', '#06B6D4': 'CIANO',
};

function getColorName(hex) {
    return COLOR_NAMES[hex?.toUpperCase()] || COLOR_NAMES[hex] || 'INDEFINIDA';
}

// Hook responsivo
function useResponsive() {
  const [screen, setScreen] = useState({ isMobile: true, isTablet: false, isDesktop: false });
  
  useEffect(() => {
    const check = () => {
      const width = window.innerWidth;
      // Allow developer override to force desktop layout (useful when embedded)
      const forced = localStorage.getItem('forceDesktop');
      const forcedDesktop = forced === '1';
      setScreen({
        isMobile: forcedDesktop ? false : width < 640,
        isTablet: forcedDesktop ? false : (width >= 640 && width < 1024),
        isDesktop: forcedDesktop ? true : width >= 1024
      });
    };
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);
  
  return screen;
}

export default function SeparationMode() {
  const { isMobile, isTablet, isDesktop } = useResponsive();
  
  const [routes, setRoutes] = useState([]);
  const [viewMode, setViewMode] = useState('scanner');
  const [scanMode, setScanMode] = useState('barcode');
  const [barcodeInput, setBarcodeInput] = useState('');
  const [separationSession, setSeparationSession] = useState(null);
  const [lastScanned, setLastScanned] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [pendingScans, setPendingScans] = useState([]);
  const [isSyncing, setIsSyncing] = useState(false);
  
  // Camera states
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState(null);
  const [isScanning, setIsScanning] = useState(false);

  const inputRef = useRef(null);
  const html5QrCodeRef = useRef(null);
  const scannerContainerRef = useRef(null);

  // Online/Offline detection & Background Sync
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      syncPendingScans();
    };
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    // Check pending on load
    refreshPendingCount();
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const refreshPendingCount = async () => {
    try {
      const pending = await getPendingScans();
      setPendingScans(pending || []);
    } catch (e) {
      console.error("Erro ao ler IndexedDB", e);
    }
  };

  const syncPendingScans = async () => {
    const pending = await getPendingScans();
    if (!pending || pending.length === 0 || isSyncing) return;
    
    setIsSyncing(true);
    console.log(`🔄 Iniciando sincronização de ${pending.length} bipes...`);
    
    for (const item of pending) {
      try {
        const res = await fetchSafe('/separation/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ barcode: item.barcode })
        });
        
        if (res.ok) {
          await removeScanFromQueue(item.id);
          console.log(`✅ Sincronizado: ${item.barcode}`);
        } else {
          console.warn(`⚠️ Falha ao sincronizar ${item.barcode}:`, res.error);
          break; // Para se houver erro no servidor
        }
      } catch (e) {
        console.error("❌ Erro de rede na sincronização", e);
        break;
      }
    }
    
    await refreshPendingCount();
    setIsSyncing(false);
  };

  // Load routes
  useEffect(() => {
    fetchRoutes();
    const interval = setInterval(fetchRoutes, 5000);
    return () => clearInterval(interval);
  }, []);

  // Initialize session
  useEffect(() => {
    startSeparationSession();
  }, []);

  // Focus Input
  useEffect(() => {
    if (viewMode === 'scanner' && scanMode === 'barcode' && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 200);
    }
  }, [viewMode, scanMode, lastScanned]);

  // 📷 CAMERA SETUP - Usando Html5Qrcode diretamente para controle total
  const startCamera = useCallback(async () => {
    if (html5QrCodeRef.current || scanMode !== 'camera') return;
    
    setCameraError(null);
    setCameraReady(false);
    
    try {
      // Criar instância
      const html5QrCode = new Html5Qrcode("camera-reader");
      html5QrCodeRef.current = html5QrCode;
      
      // Configuração otimizada para leitura rápida
      const config = {
        fps: 30, // Aumentado para 30 para leitura muito mais rápida
        qrbox: { width: 260, height: 260 }, // Quadrado para ler tanto QR quanto Barras facilmente
        aspectRatio: 1.0, // Foco melhor no centro
        disableFlip: false,
        experimentalFeatures: {
          useBarCodeDetectorIfSupported: true
        }
      };
      
      // Variável para ignorar leituras repetidas muito rápidas (debounce)
      let lastScannedText = '';
      let lastScannedTime = 0;

      // Iniciar com câmera traseira (facingMode: environment)
      await html5QrCode.start(
        { facingMode: "environment" }, // Câmera traseira!
        config,
        (decodedText, decodedResult) => {
          // Debounce para evitar 50 chamadas da mesma caixa no mesmo segundo
          const now = Date.now();
          if (decodedText === lastScannedText && (now - lastScannedTime) < 2000) {
              return; // Ignora se for o mesmo texto a menos de 2 segundos
          }
          lastScannedText = decodedText;
          lastScannedTime = now;
          
          // Sucesso no scan!
          handleScan(decodedText);
        },
        (errorMessage) => {
          // Erro de scan (normal, ignora)
        }
      );
      
      setCameraReady(true);
      setIsScanning(true);
      console.log('📷 Câmera traseira iniciada com sucesso (Alta performance)!');
      
    } catch (err) {
      console.error('❌ Erro ao iniciar câmera:', err);
      setCameraError(
        err.message?.includes('Permission') 
          ? 'Permissão de câmera negada. Permita o acesso nas configurações.'
          : err.message?.includes('NotFoundError')
            ? 'Nenhuma câmera encontrada no dispositivo.'
            : `Erro ao acessar câmera: ${err.message}`
      );
    }
  }, [scanMode]);

  const stopCamera = useCallback(async () => {
    if (html5QrCodeRef.current) {
      try {
        await html5QrCodeRef.current.stop();
        html5QrCodeRef.current.clear();
      } catch (e) {
        console.warn('Erro ao parar câmera:', e);
      }
      html5QrCodeRef.current = null;
      setCameraReady(false);
      setIsScanning(false);
    }
  }, []);

  // Iniciar/parar câmera baseado no modo
  useEffect(() => {
    if (viewMode === 'scanner' && scanMode === 'camera') {
      // Pequeno delay para garantir que o DOM está pronto
      const timer = setTimeout(() => {
        startCamera();
      }, 300);
      return () => clearTimeout(timer);
    } else {
      stopCamera();
    }
    
    return () => {
      stopCamera();
    };
  }, [viewMode, scanMode, startCamera, stopCamera]);

  // Cleanup no unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  const fetchRoutes = async () => {
    try {
      const res = await fetchSafe('/session/routes_status');
      if (res.ok) setRoutes(res.json);
    } catch (e) {
      console.error("Error fetching routes", e);
    }
  };

  const startSeparationSession = async () => {
    try {
      const res = await fetchSafe('/separation/start', { method: 'POST' });
      if (res.ok) setSeparationSession(res.json.session);
    } catch (e) {
      console.error("Error starting separation", e);
    }
  };

  const handleScan = async (barcode) => {
    if (!barcode?.trim() || loading) return;
    const cleanBarcode = barcode.trim();
    setLoading(true);
    setError('');

    try {
      // Se estiver explicitamente offline, nem tenta o fetch
      if (!navigator.onLine) {
        throw new Error('NETWORK_ERROR');
      }

      const res = await fetchSafe('/separation/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ barcode: cleanBarcode })
      });
      
      if (!res.ok) {
        // Se for erro de rede (não erro 4xx/5xx), jogamos para o catch do offline
        if (res.status === 0 || res.error?.includes('Failed to fetch')) {
            throw new Error('NETWORK_ERROR');
        }
        throw new Error(res.error || 'Erro ao escanear');
      }
      
      const data = res.json;
      if (data.status === 'not_found') {
        setError(data.message);
        playBeep('error');
      } else {
        setLastScanned(data);
        if (data.progress) {
          setSeparationSession(prev => ({
            ...prev,
            scanned_packages: data.progress.scanned,
            progress: data.progress.percentage
          }));
        }
        playBeep('success');
      }
      setBarcodeInput('');

    } catch (err) {
      if (err.message === 'NETWORK_ERROR' || !navigator.onLine) {
        // MODO OFFLINE: Salvar na fila
        try {
          await addScanToQueue(cleanBarcode);
          await refreshPendingCount();
          
          setLastScanned({
            address: 'MODO OFFLINE - Sincronização pendente',
            route_color: '#9ca3af',
            deliverer: 'Aguardando Conexão',
            sequence: '?',
            total_in_route: '?',
            offline: true
          });
          
          setError('Conexão instável. Bipe salvo para sincronizar depois.');
          playBeep('success');
          setBarcodeInput('');
        } catch (dbErr) {
          setError('Erro ao salvar bipe offline.');
          playBeep('error');
        }
      } else {
        setError(err.message);
        playBeep('error');
      }
    } finally {
      setLoading(false);
    }
  };
  
  const handleStartRoute = async (routeId) => {
    if (!confirm("Confirmar saída do entregador para rota?")) return;
    try {
      const res = await fetchSafe(`/route/${routeId}/start`, { method: 'POST' });
      if (res.ok) {
        fetchRoutes();
        alert("Rota iniciada!");
      }
    } catch (e) {
      alert("Erro ao iniciar rota");
    }
  };

  const handleFinishRoute = async (routeId) => {
    if (!confirm("Confirmar que a rota foi concluída?")) return;
    try {
      const res = await fetchSafe(`/route/${routeId}/finish`, { method: 'POST' });
      if (res.ok) {
        fetchRoutes();
        alert("Rota finalizada!");
      }
    } catch (e) {
      alert("Erro ao finalizar rota");
    }
  };

  const playBeep = (type) => {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      if (type === 'success') {
        oscillator.frequency.value = 1200;
        gainNode.gain.value = 0.3;
        oscillator.start();
        oscillator.stop(audioContext.currentTime + 0.15);
      } else {
        oscillator.frequency.value = 200;
        gainNode.gain.value = 0.5;
        oscillator.start();
        oscillator.stop(audioContext.currentTime + 0.3);
      }
    } catch (e) {}
  };

  const clearLastScan = () => {
    setLastScanned(null);
    setError('');
    if (scanMode === 'barcode') {
      inputRef.current?.focus();
    }
  };

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-gray-900 overflow-hidden">
      {/* Header Compacto */}
      <div className={`bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm z-10 ${isMobile ? 'px-4 py-3' : 'px-6 py-4'}`}>
        <div className="flex justify-between items-center gap-3">
          <div className="flex-1 min-w-0">
            <h1 className={`font-bold flex items-center gap-2 text-gray-900 dark:text-white ${isMobile ? 'text-lg' : 'text-xl'}`}>
              <Barcode className="text-primary-500" size={isMobile ? 20 : 24} /> 
              <span className="truncate">{isMobile ? 'Separação' : 'Separação de Cargas'}</span>
            </h1>
            <div className="flex items-center gap-2 mt-1">
              {isOnline ? <Wifi size={12} className="text-green-500" /> : <WifiOff size={12} className="text-red-500" />}
              
              {pendingScans.length > 0 && (
                <div className="flex items-center gap-1 px-2 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 rounded-full text-[10px] font-bold animate-pulse">
                  <RefreshCw size={10} className={isSyncing ? 'animate-spin' : ''} />
                  {pendingScans.length} PENDENTE{pendingScans.length > 1 ? 'S' : ''}
                </div>
              )}

              <span className="text-xs text-gray-500 dark:text-gray-400">
                {separationSession?.scanned_packages || 0} / {separationSession?.total_packages || 0}
              </span>
              <div className="flex-1 max-w-[80px] h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div className="h-full bg-primary-500 transition-all" style={{ width: `${separationSession?.progress || 0}%` }} />
              </div>
            </div>
          </div>

          {/* View Toggle */}
          <div className="flex bg-gray-100 dark:bg-gray-700 rounded-xl p-1">
            <button 
              onClick={() => setViewMode('scanner')}
              className={`px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
                viewMode === 'scanner' 
                  ? 'bg-white dark:bg-gray-600 text-primary-600 dark:text-primary-400 shadow-sm' 
                  : 'text-gray-500 dark:text-gray-400'
              }`}
            >
              {isMobile ? <Barcode size={18} /> : 'Scanner'}
            </button>
            <button 
              onClick={() => setViewMode('manage')}
              className={`px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
                viewMode === 'manage' 
                  ? 'bg-white dark:bg-gray-600 text-primary-600 dark:text-primary-400 shadow-sm' 
                  : 'text-gray-500 dark:text-gray-400'
              }`}
            >
              {isMobile ? <Truck size={18} /> : 'Gerenciar'}
            </button>
          </div>
          {/* Botão Maximizar para Desktop */}
          {(isMobile || isTablet) && (
            <button
              className="ml-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full p-2 shadow-lg transition-all flex items-center"
              title="Maximizar (modo desktop)"
              onClick={() => {
                try { localStorage.setItem('forceDesktop', '1'); } catch {}
                window.dispatchEvent(new Event('resize'));
              }}
            >
              <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <polyline points="9 3 9 9 3 9" />
                <polyline points="15 21 15 15 21 15" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        
        {/* SCANNER VIEW */}
        {viewMode === 'scanner' && (
          <div className={`h-full flex ${isMobile ? 'flex-col' : 'flex-row'}`}>
            
            {/* Scanner Panel */}
            <div className={`bg-white dark:bg-gray-800 flex flex-col ${
              isMobile ? 'flex-1' : isTablet ? 'w-2/5 border-r border-gray-200 dark:border-gray-700' : 'w-1/3 border-r border-gray-200 dark:border-gray-700'
            }`}>
              
              {/* Mode Toggle */}
              <div className="p-4 border-b border-gray-100 dark:border-gray-700">
                <div className="flex bg-gray-100 dark:bg-gray-700 rounded-xl p-1">
                  <button 
                    onClick={() => setScanMode('barcode')} 
                    className={`flex-1 py-3 text-sm font-semibold rounded-lg transition-all flex items-center justify-center gap-2 ${
                      scanMode === 'barcode' 
                        ? 'bg-white dark:bg-gray-600 shadow-sm text-gray-900 dark:text-white' 
                        : 'text-gray-500 dark:text-gray-400'
                    }`}
                  >
                    <Keyboard size={18} />
                    Bipadora
                  </button>
                  <button 
                    onClick={() => setScanMode('camera')} 
                    className={`flex-1 py-3 text-sm font-semibold rounded-lg transition-all flex items-center justify-center gap-2 ${
                      scanMode === 'camera' 
                        ? 'bg-white dark:bg-gray-600 shadow-sm text-gray-900 dark:text-white' 
                        : 'text-gray-500 dark:text-gray-400'
                    }`}
                  >
                    <Camera size={18} />
                    Câmera
                  </button>
                </div>
              </div>

              {/* Scanner Content */}
              <div className="flex-1 flex flex-col p-4">
                {scanMode === 'barcode' ? (
                  /* BARCODE INPUT MODE */
                  <form onSubmit={(e) => { e.preventDefault(); handleScan(barcodeInput); }} className="flex-1 flex flex-col justify-center">
                    <label className="block text-gray-400 text-xs mb-3 text-center uppercase tracking-wider font-bold">
                      Aguardando Leitura
                    </label>
                    <div className="relative">
                      <input
                        ref={inputRef}
                        value={barcodeInput}
                        onChange={e => setBarcodeInput(e.target.value)} 
                        className="w-full h-16 text-center text-2xl font-mono tracking-widest bg-gray-50 dark:bg-gray-900 border-2 border-primary-500 rounded-xl focus:ring-4 focus:ring-primary-500/20 outline-none text-gray-900 dark:text-white"
                        placeholder="• • • • • • •"
                        autoComplete="off"
                        autoFocus
                      />
                      {loading && (
                        <div className="absolute right-4 top-1/2 -translate-y-1/2">
                          <Loader2 className="animate-spin text-primary-500" size={24} />
                        </div>
                      )}
                    </div>
                    <p className="text-center text-gray-400 text-xs mt-3">
                      Use um leitor USB ou digite o código
                    </p>
                  </form>
                ) : (
                  /* CAMERA MODE - UI Moderna e Clean */
                  <div className="flex-1 flex flex-col">
                    {/* Camera Preview Container */}
                    <div className="flex-1 relative bg-black rounded-2xl overflow-hidden min-h-[300px]">
                      {/* Scanner video element */}
                      <div 
                        id="camera-reader" 
                        ref={scannerContainerRef}
                        className="absolute inset-0 w-full h-full"
                        style={{ 
                          background: '#000',
                        }}
                      />
                      
                      {/* Overlay com guia de scan */}
                      {cameraReady && (
                        <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                          {/* Guia de código de barras */}
                          <div className="relative">
                            <div className="w-72 h-32 border-2 border-white/50 rounded-lg relative">
                              {/* Cantos destacados */}
                              <div className="absolute -top-0.5 -left-0.5 w-6 h-6 border-t-4 border-l-4 border-primary-400 rounded-tl-lg" />
                              <div className="absolute -top-0.5 -right-0.5 w-6 h-6 border-t-4 border-r-4 border-primary-400 rounded-tr-lg" />
                              <div className="absolute -bottom-0.5 -left-0.5 w-6 h-6 border-b-4 border-l-4 border-primary-400 rounded-bl-lg" />
                              <div className="absolute -bottom-0.5 -right-0.5 w-6 h-6 border-b-4 border-r-4 border-primary-400 rounded-br-lg" />
                              
                              {/* Linha de scan animada */}
                              <div className="absolute inset-x-2 h-0.5 bg-gradient-to-r from-transparent via-primary-400 to-transparent animate-pulse top-1/2" />
                            </div>
                            
                            {/* Label */}
                            <p className="text-white/80 text-xs text-center mt-3 font-medium">
                              Posicione o código de barras aqui
                            </p>
                          </div>
                        </div>
                      )}
                      
                      {/* Loading state */}
                      {!cameraReady && !cameraError && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900">
                          <div className="relative">
                            <Camera size={48} className="text-gray-600 animate-pulse" />
                            <Loader2 size={20} className="absolute -bottom-1 -right-1 text-primary-500 animate-spin" />
                          </div>
                          <p className="text-gray-400 text-sm mt-4">Iniciando câmera...</p>
                        </div>
                      )}
                      
                      {/* Error state */}
                      {cameraError && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900 p-6 text-center">
                          <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mb-4">
                            <X size={32} className="text-red-500" />
                          </div>
                          <p className="text-red-400 text-sm font-medium mb-2">Erro na câmera</p>
                          <p className="text-gray-500 text-xs mb-4">{cameraError}</p>
                          <button 
                            onClick={() => {
                              setCameraError(null);
                              stopCamera().then(() => startCamera());
                            }}
                            className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium flex items-center gap-2"
                          >
                            <RotateCcw size={16} />
                            Tentar novamente
                          </button>
                        </div>
                      )}
                      
                      {/* Status badge */}
                      {isScanning && (
                        <div className="absolute top-4 left-4 px-3 py-1.5 bg-green-500/90 text-white text-xs font-bold rounded-full flex items-center gap-1.5 shadow-lg">
                          <Zap size={12} className="animate-pulse" />
                          ESCANEANDO
                        </div>
                      )}
                    </div>
                    
                    {/* Dica */}
                    <p className="text-center text-gray-400 text-xs mt-3">
                      Câmera traseira • Aponte para o código de barras
                    </p>
                  </div>
                )}
              </div>

              {/* Error Message */}
              {error && (
                <div className="mx-4 mb-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl text-red-600 dark:text-red-300 text-sm text-center flex items-center justify-center gap-2">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}
            </div>

            {/* Result Panel - Notificação Flutuante no Mobile ou Painel no Desktop */}
            {(!isMobile || lastScanned) && (
              <div 
                className={
                  isMobile 
                    ? `absolute bottom-4 left-4 right-4 z-40 pointer-events-auto transition-all duration-300 animate-in slide-in-from-bottom-8 fade-in ${lastScanned ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10 pointer-events-none'}`
                    : `flex-1 flex flex-col items-center justify-center relative overflow-hidden transition-colors duration-500`
                }
                style={!isMobile ? { backgroundColor: lastScanned?.route_color || 'rgb(249 250 251)' } : {}}
              >
                {lastScanned ? (
                  isMobile ? (
                    /* BANNER FLUTUANTE MOBILE */
                    <div 
                      className="bg-white dark:bg-gray-800 rounded-2xl shadow-[0_10px_40px_rgba(0,0,0,0.5)] border-l-8 overflow-hidden flex items-stretch"
                      style={{ borderLeftColor: lastScanned.route_color }}
                    >
                      <div className="flex-1 p-3 pl-4">
                        <div className="flex justify-between items-start mb-1">
                          <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                            {getColorName(lastScanned.route_color)} • {lastScanned.deliverer || 'S/ Entregador'}
                          </span>
                          <button onClick={clearLastScan} className="text-gray-400 p-1 -mr-1 -mt-1 rounded-full hover:bg-gray-100">
                            <X size={16} />
                          </button>
                        </div>
                        
                        <div className="flex items-center gap-3">
                          <div className="flex items-baseline gap-1">
                            <span className="text-4xl font-black text-gray-900 dark:text-white leading-none">
                              {lastScanned.sequence}
                            </span>
                            <span className="text-sm font-bold text-gray-400">
                              /{lastScanned.total_in_route}
                            </span>
                          </div>
                          
                          <div className="flex-1 border-l border-gray-200 dark:border-gray-700 pl-3">
                            <p className="text-xs font-medium text-gray-600 dark:text-gray-300 line-clamp-2">
                              {lastScanned.address}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    /* DESKTOP FULL PANEL (Manteve Original) */
                    <>
                      <div className="absolute inset-0 bg-black/40" />
                      <div className="relative z-10 text-center p-6 w-full max-w-md animate-in fade-in zoom-in duration-300">
                        <div className="mb-4 px-4 py-3 rounded-2xl bg-black/30 backdrop-blur-md inline-block">
                          <h2 className="text-sm font-medium text-white/80 uppercase tracking-widest mb-1">Rota de Entrega</h2>
                          <div className="text-3xl font-black text-white flex items-center justify-center gap-3">
                            <div className="w-8 h-8 rounded-full border-4 border-white shadow-lg" style={{ backgroundColor: lastScanned.route_color }} />
                            <span>{getColorName(lastScanned.route_color)}</span>
                          </div>
                          {lastScanned.deliverer && <p className="text-white font-semibold mt-2">{lastScanned.deliverer}</p>}
                        </div>

                        <div className="bg-white text-gray-900 rounded-3xl shadow-2xl mx-auto p-6 max-w-[200px] border-4 border-white/50">
                          <span className="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Posição</span>
                          <span className="block text-[80px] leading-none font-black text-gray-900">{lastScanned.sequence}</span>
                          <div className="mt-3 pt-3 border-t-2 border-gray-100 flex justify-between text-xs font-bold text-gray-400">
                            <span>TOTAL</span>
                            <span className="text-lg text-gray-700">{lastScanned.total_in_route}</span>
                          </div>
                        </div>

                        <div className="mt-4 text-white/90 text-sm truncate bg-black/40 px-4 py-2 rounded-full">
                          📍 {lastScanned.address}
                        </div>
                        
                        <p className="text-[10px] text-white/70 font-bold uppercase mt-6 animate-pulse tracking-widest">
                          Pronto para o próximo bipe...
                        </p>
                      </div>
                    </>
                  )
                ) : !isMobile && (
                  <div className="text-center text-gray-400">
                    <Package size={80} className="mx-auto mb-4 opacity-30" />
                    <h2 className="text-2xl font-bold mb-2">Pronto para Separar</h2>
                    <p>Bipe um pacote para identificar a rota</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* MANAGE VIEW */}
        {viewMode === 'manage' && (
          <div className={`h-full overflow-y-auto ${isMobile ? 'p-4' : 'p-6'} bg-gray-50 dark:bg-gray-900`}>
            {routes.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <Truck size={64} className="text-gray-300 dark:text-gray-600 mb-4" />
                <h3 className="text-xl font-bold text-gray-600 dark:text-gray-400 mb-2">Nenhuma rota</h3>
                <p className="text-gray-400 text-sm">Importe um romaneio na aba Roteirização</p>
              </div>
            ) : (
              <div className={`grid gap-4 max-w-7xl mx-auto ${isMobile ? 'grid-cols-1' : isTablet ? 'grid-cols-2' : 'grid-cols-3'}`}>
                {routes.map(route => (
                  <div key={route.id} className="bg-white dark:bg-gray-800 rounded-2xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
                    <div className="flex items-center gap-4 mb-5">
                      <div 
                        className="w-14 h-14 rounded-2xl flex items-center justify-center font-bold text-white text-xl shadow-lg" 
                        style={{ backgroundColor: route.color }}
                      >
                        {route.assigned_to_name?.charAt(0) || '?'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-bold text-gray-900 dark:text-white truncate">
                          {route.assigned_to_name || 'Sem entregador'}
                        </h3>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-sm text-gray-500">{route.total_packages} volumes</span>
                          <BadgeStatus status={route.status} />
                        </div>
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <button
                        onClick={() => handleStartRoute(route.id)}
                        disabled={!['pending', 'separating', 'ready'].includes(route.status)} 
                        className="w-full py-3 bg-primary-600 hover:bg-primary-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-primary-500/20"
                      >
                        <Play size={18} fill="currentColor" /> LIBERAR SAÍDA
                      </button>
                      
                      <button
                        onClick={() => handleFinishRoute(route.id)}
                        disabled={route.status !== 'in_transit'}
                        className="w-full py-3 bg-green-600 hover:bg-green-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-green-500/20"
                      >
                        <Flag size={18} fill="currentColor" /> FINALIZAR
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function BadgeStatus({ status }) {
  const styles = {
    pending: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300',
    separating: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400',
    ready: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
    in_transit: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 animate-pulse',
    completed: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400'
  };

  const labels = {
    pending: 'Pendente', separating: 'Separando', ready: 'Pronto',
    in_transit: 'Em Rota', completed: 'Finalizado'
  };

  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-bold uppercase ${styles[status] || styles.pending}`}>
      {labels[status] || status}
    </span>
  );
}
