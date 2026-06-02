import React, { useEffect, useState } from 'react';
import { Wifi, WifiOff, CloudOff, RefreshCw } from 'lucide-react';
import offlineSync from '../services/offlineSync';

/**
 * COMPONENTE DE STATUS OFFLINE/ONLINE
 * Mostra banner quando está offline e contador de dados pendentes
 */
export default function OfflineIndicator() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [pendingCount, setPendingCount] = useState({ deliveries: 0, locations: 0, total: 0 });
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    // Listeners de conectividade
    const handleOnline = () => {
      setIsOnline(true);
      checkPendingData();
    };

    const handleOffline = () => {
      setIsOnline(false);
      checkPendingData();
    };

    const handleConnectivityChange = (event) => {
      setIsOnline(event.detail.online);
      checkPendingData();
    };

    const handleSyncComplete = () => {
      setSyncing(false);
      checkPendingData();
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    window.addEventListener('connectivity-change', handleConnectivityChange);
    window.addEventListener('sync-complete', handleSyncComplete);
    window.addEventListener('sw-sync-complete', handleSyncComplete);
    window.addEventListener('delivery-saved-offline', checkPendingData);

    // Checa dados pendentes ao montar
    checkPendingData();

    // Atualiza periodicamente
    const interval = setInterval(checkPendingData, 5000);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('connectivity-change', handleConnectivityChange);
      window.removeEventListener('sync-complete', handleSyncComplete);
      window.removeEventListener('sw-sync-complete', handleSyncComplete);
      window.removeEventListener('delivery-saved-offline', checkPendingData);
      clearInterval(interval);
    };
  }, []);

  const checkPendingData = async () => {
    try {
      const count = await offlineSync.getPendingCount();
      setPendingCount(count);
    } catch (error) {
      console.error('Erro ao checar dados pendentes:', error);
    }
  };

  const handleManualSync = async () => {
    if (!isOnline || syncing) return;
    
    setSyncing(true);
    try {
      await offlineSync.syncPendingData();
    } catch (error) {
      console.error('Erro ao sincronizar:', error);
    } finally {
      setSyncing(false);
    }
  };

  // Não mostra nada se está online e sem pendências
  if (isOnline && pendingCount.total === 0) {
    return null;
  }

  return (
    <div className="fixed top-0 left-0 right-0 z-50 animate-slide-down">
      {/* Banner Offline */}
      {!isOnline && (
        <div className="bg-red-600 text-white px-4 py-3 shadow-lg">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <div className="flex items-center gap-3">
              <WifiOff size={20} className="animate-pulse" />
              <div>
                <p className="font-bold text-sm">Modo Offline Ativo</p>
                <p className="text-xs opacity-90">
                  Suas ações serão sincronizadas quando o sinal voltar
                </p>
              </div>
            </div>
            <CloudOff size={24} />
          </div>
        </div>
      )}

      {/* Banner de Sincronização Pendente */}
      {isOnline && pendingCount.total > 0 && (
        <div className="bg-yellow-500 text-gray-900 px-4 py-3 shadow-lg">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <div className="flex items-center gap-3">
              <Wifi size={20} />
              <div>
                <p className="font-bold text-sm">
                  {pendingCount.total} {pendingCount.total === 1 ? 'item' : 'itens'} aguardando sincronização
                </p>
                <p className="text-xs">
                  {pendingCount.deliveries > 0 && `${pendingCount.deliveries} entregas`}
                  {pendingCount.deliveries > 0 && pendingCount.locations > 0 && ' • '}
                  {pendingCount.locations > 0 && `${pendingCount.locations} localizações`}
                </p>
              </div>
            </div>
            <button
              onClick={handleManualSync}
              disabled={syncing}
              className="bg-white text-yellow-700 px-4 py-2 rounded-lg font-bold text-sm flex items-center gap-2 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              <RefreshCw size={16} className={syncing ? 'animate-spin' : ''} />
              {syncing ? 'Sincronizando...' : 'Sincronizar'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
