/**
 * OFFLINE SYNC SERVICE
 * Gerencia sincronização de dados offline usando IndexedDB
 */

const DB_NAME = 'BotEntregadorDB';
const DB_VERSION = 1;

class OfflineSyncService {
  constructor() {
    this.db = null;
    this.dbPromise = this.openDB()
      .then((db) => {
        this.db = db;
        return db;
      })
      .catch((error) => {
        console.error('❌ Erro ao abrir IndexedDB:', error);
        return null;
      });  // ✅ Promise que garante db está pronto
    this.isOnline = navigator.onLine;
    this.syncInProgress = false;
    
    // Listeners de conectividade
    window.addEventListener('online', () => this.handleOnline());
    window.addEventListener('offline', () => this.handleOffline());
    
    this.init();
  }

  /**
   * Garante que o IndexedDB está pronto antes de usar
   */
  async ensureDB() {
    if (this.db) return this.db;
    if (this.dbPromise) {
      this.db = await this.dbPromise;
      return this.db;
    }

    this.dbPromise = this.openDB()
      .then((db) => {
        this.db = db;
        return db;
      })
      .catch((error) => {
        console.error('❌ Erro ao abrir IndexedDB:', error);
        return null;
      });

    this.db = await this.dbPromise;
    return this.db;
  }

  /**
   * Inicializa IndexedDB
   */
  async init() {
    try {
      await this.ensureDB();
      console.log('✅ IndexedDB inicializado');
      
      // Se está online, tenta sincronizar dados pendentes
      if (this.isOnline && this.db) {
        await this.syncPendingData();
      }
    } catch (error) {
      console.error('❌ Erro ao inicializar IndexedDB:', error);
    }
  }

  /**
   * Abre conexão com IndexedDB
   */
  openDB() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // Store de entregas pendentes
        if (!db.objectStoreNames.contains('pending_deliveries')) {
          const deliveriesStore = db.createObjectStore('pending_deliveries', {
            keyPath: 'id',
            autoIncrement: true
          });
          deliveriesStore.createIndex('package_id', 'package_id', { unique: false });
          deliveriesStore.createIndex('timestamp', 'timestamp', { unique: false });
        }

        // Store de atualizações de localização
        if (!db.objectStoreNames.contains('pending_locations')) {
          const locationsStore = db.createObjectStore('pending_locations', {
            keyPath: 'id',
            autoIncrement: true
          });
          locationsStore.createIndex('timestamp', 'timestamp', { unique: false });
        }

        // Cache de rotas
        if (!db.objectStoreNames.contains('route_cache')) {
          db.createObjectStore('route_cache', { keyPath: 'route_id' });
        }

        // Cache de mapas (HTML)
        if (!db.objectStoreNames.contains('map_cache')) {
          db.createObjectStore('map_cache', { keyPath: 'map_id' });
        }
      };
    });
  }

  /**
   * Handler quando fica online
   */
  async handleOnline() {
    console.log('🟢 Conectividade restaurada');
    this.isOnline = true;
    
    // Dispara sincronização automática
    await this.syncPendingData();
    
    // Notifica componentes
    window.dispatchEvent(new CustomEvent('connectivity-change', { 
      detail: { online: true } 
    }));
  }

  /**
   * Handler quando fica offline
   */
  handleOffline() {
    console.log('🔴 Sem conectividade - Modo offline ativado');
    this.isOnline = false;
    
    window.dispatchEvent(new CustomEvent('connectivity-change', { 
      detail: { online: false } 
    }));
  }

  /**
   * Salva entrega marcada offline
   */
  async saveDeliveryOffline(packageId, status, location = null) {
    try {
      await this.ensureDB();
      if (!this.db) {
        console.warn('⚠️ IndexedDB não disponível, falha silenciosa');
        return false;
      }
      
      const tx = this.db.transaction('pending_deliveries', 'readwrite');
      const store = tx.objectStore('pending_deliveries');
      
      const delivery = {
        package_id: packageId,
        status: status,
        timestamp: new Date().toISOString(),
        location: location,
        token: localStorage.getItem('auth_token')
      };
      
      await store.add(delivery);
      console.log('💾 Entrega salva offline:', packageId);
      
      // Dispara evento para atualizar UI
      window.dispatchEvent(new CustomEvent('delivery-saved-offline', {
        detail: { packageId, status }
      }));
      
      return true;
    } catch (error) {
      console.error('❌ Erro ao salvar entrega offline:', error);
      return false;
    }
  }

  /**
   * Salva atualização de localização offline
   */
  async saveLocationOffline(lat, lng) {
    try {
      await this.ensureDB();
      if (!this.db) {
        console.warn('⚠️ IndexedDB não disponível, falha silenciosa');
        return false;
      }
      
      const tx = this.db.transaction('pending_locations', 'readwrite');
      const store = tx.objectStore('pending_locations');
      
      const location = {
        lat,
        lng,
        timestamp: new Date().toISOString(),
        token: localStorage.getItem('auth_token')
      };
      
      await store.add(location);
      console.log('📍 Localização salva offline');
      
      return true;
    } catch (error) {
      console.error('❌ Erro ao salvar localização offline:', error);
      return false;
    }
  }

  /**
   * Cache de rota completa
   */
  async cacheRoute(routeId, routeData) {
    try {
      if (!this.db) {
        console.warn('⚠️ IndexedDB não disponível, cache desabilitado');
        return false;
      }
      
      const tx = this.db.transaction('route_cache', 'readwrite');
      const store = tx.objectStore('route_cache');
      
      await store.put({
        route_id: routeId,
        data: routeData,
        cached_at: new Date().toISOString()
      });
      
      console.log('💾 Rota cacheada:', routeId);
      return true;
    } catch (error) {
      console.error('❌ Erro ao cachear rota:', error);
      return false;
    }
  }

  /**
   * Busca rota do cache
   */
  async getCachedRoute(routeId) {
    try {
      if (!this.db) {
        return null;
      }
      
      const tx = this.db.transaction('route_cache', 'readonly');
      const store = tx.objectStore('route_cache');
      const request = store.get(routeId);
      
      const result = await new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
      
      if (result) {
        console.log('📦 Rota recuperada do cache:', routeId);
        return result.data;
      }
      
      return null;
    } catch (error) {
      console.error('❌ Erro ao buscar rota do cache:', error);
      return null;
    }
  }

  /**
   * Cache de mapa HTML
   */
  async cacheMap(mapId, mapHtml) {
    try {
      if (!this.db) {
        console.warn('⚠️ IndexedDB não disponível, cache desabilitado');
        return false;
      }
      
      const tx = this.db.transaction('map_cache', 'readwrite');
      const store = tx.objectStore('map_cache');
      
      await store.put({
        map_id: mapId,
        html: mapHtml,
        cached_at: new Date().toISOString()
      });
      
      console.log('🗺️ Mapa cacheado:', mapId);
      return true;
    } catch (error) {
      console.error('❌ Erro ao cachear mapa:', error);
      return false;
    }
  }

  /**
   * Busca mapa do cache
   */
  async getCachedMap(mapId) {
    try {
      if (!this.db) {
        return null;
      }
      
      const tx = this.db.transaction('map_cache', 'readonly');
      const store = tx.objectStore('map_cache');
      const request = store.get(mapId);
      
      const result = await new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
      
      if (result) {
        console.log('🗺️ Mapa recuperado do cache:', mapId);
        return result.html;
      }
      
      return null;
    } catch (error) {
      console.error('❌ Erro ao buscar mapa do cache:', error);
      return null;
    }
  }

  /**
   * Sincroniza todos os dados pendentes
   */
  async syncPendingData() {
    const db = await this.ensureDB();
    if (this.syncInProgress || !this.isOnline || !db || typeof db.transaction !== 'function') {
      return;
    }

    this.syncInProgress = true;
    console.log('🔄 Iniciando sincronização de dados offline...');

    try {
      // Sincroniza entregas
      await this.syncDeliveries().catch(err => {
        console.error('❌ Erro ao sincronizar entregas:', err);
      });
      
      // Sincroniza localizações
      await this.syncLocations().catch(err => {
        console.error('❌ Erro ao sincronizar localizações:', err);
      });
      
      console.log('✅ Sincronização concluída');
      
      // Notifica componentes
      window.dispatchEvent(new CustomEvent('sync-complete'));
    } catch (error) {
      console.error('❌ Erro na sincronização:', error);
    } finally {
      this.syncInProgress = false;
    }
  }

  /**
   * Sincroniza entregas pendentes
   */
  async syncDeliveries() {
    const db = await this.ensureDB();
    if (!db || typeof db.transaction !== 'function') return;
    
    try {
      const tx = db.transaction('pending_deliveries', 'readwrite');
      const store = tx.objectStore('pending_deliveries');
      const request = store.getAll();
      
      const deliveries = await new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(request.result || []);
        request.onerror = () => reject(request.error);
      });

      const deliveriesList = Array.isArray(deliveries) ? deliveries : [];
      if (!Array.isArray(deliveries)) {
        console.warn('⚠️ Entregas não é array, pulando sincronização');
      }

      console.log(`📤 Sincronizando ${deliveriesList.length} entregas...`);

      for (const delivery of deliveriesList) {
        try {
          const response = await fetch('/api/deliverer/mark-delivered', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${delivery.token}`
            },
            body: JSON.stringify({
              package_id: delivery.package_id,
              status: delivery.status,
              timestamp: delivery.timestamp,
              location: delivery.location
            })
          });

          if (response.ok) {
            await store.delete(delivery.id);
            console.log('✅ Entrega sincronizada:', delivery.package_id);
            
            // Dispara evento para cada entrega sincronizada
            window.dispatchEvent(new CustomEvent('delivery-synced', {
              detail: { packageId: delivery.package_id }
            }));
          }
        } catch (err) {
          console.error('❌ Erro ao sincronizar entrega:', err);
        }
      }
    } catch (error) {
      console.error('❌ Erro ao sincronizar entregas:', error);
    }
  }

  /**
   * Sincroniza localizações pendentes
   */
  async syncLocations() {
    const db = await this.ensureDB();
    if (!db || typeof db.transaction !== 'function') return;
    
    try {
      const tx = db.transaction('pending_locations', 'readwrite');
      const store = tx.objectStore('pending_locations');
      const request = store.getAll();
      
      const locations = await new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(request.result || []);
        request.onerror = () => reject(request.error);
      });

      const locationsList = Array.isArray(locations) ? locations : [];
      if (!Array.isArray(locations)) {
        console.warn('⚠️ Localizações não é array, pulando sincronização');
      }

      for (const loc of locationsList) {
        try {
          const response = await fetch('/api/deliverer/update-location', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${loc.token}`
            },
            body: JSON.stringify({
              lat: loc.lat,
              lng: loc.lng,
              timestamp: loc.timestamp
            })
          });

          if (response.ok) {
            await store.delete(loc.id);
          }
        } catch (err) {
          console.error('❌ Erro ao sincronizar localização:', err);
        }
      }
    } catch (error) {
      console.error('❌ Erro ao sincronizar localizações:', error);
    }
  }

  /**
   * Retorna contagem de dados pendentes
   */
  async getPendingCount() {
    try {
      const db = await this.ensureDB();
      // Guard forte: se db é null ou não tem transaction, retornar safe
      if (!db || typeof db?.transaction !== 'function') {
        console.warn('⚠️ IndexedDB não disponível em getPendingCount');
        return { deliveries: 0, locations: 0, total: 0 };
      }

      try {
        const deliveriesRequest = db.transaction('pending_deliveries', 'readonly').objectStore('pending_deliveries').getAll();
        const locationsRequest = db.transaction('pending_locations', 'readonly').objectStore('pending_locations').getAll();

        const deliveries = await new Promise((resolve) => {
          deliveriesRequest.onsuccess = () => resolve(deliveriesRequest.result || []);
          deliveriesRequest.onerror = () => resolve([]);
        });

        const locations = await new Promise((resolve) => {
          locationsRequest.onsuccess = () => resolve(locationsRequest.result || []);
          locationsRequest.onerror = () => resolve([]);
        });

        const deliveriesCount = Array.isArray(deliveries) ? deliveries.length : 0;
        const locationsCount = Array.isArray(locations) ? locations.length : 0;
        
        return {
          deliveries: deliveriesCount,
          locations: locationsCount,
          total: deliveriesCount + locationsCount
        };
      } catch (dbError) {
        console.error('⚠️ Erro ao acessar IndexedDB:', dbError);
        return { deliveries: 0, locations: 0, total: 0 };
      }
    } catch (error) {
      console.error('❌ Erro ao contar pendências:', error);
      return { deliveries: 0, locations: 0, total: 0 };
    }
  }

  /**
   * Limpa todos os dados offline (usar com cuidado)
   */
  async clearAllData() {
    try {
      if (!this.db) {
        console.warn('⚠️ IndexedDB não disponível, nada a limpar');
        return false;
      }
      
      const stores = ['pending_deliveries', 'pending_locations', 'route_cache', 'map_cache'];
      
      for (const storeName of stores) {
        const tx = this.db.transaction(storeName, 'readwrite');
        const request = tx.objectStore(storeName).clear();
        
        await new Promise((resolve, reject) => {
          request.onsuccess = () => resolve();
          request.onerror = () => reject(request.error);
        });
      }
      
      console.log('🗑️ Todos os dados offline foram limpos');
      return true;
    } catch (error) {
      console.error('❌ Erro ao limpar dados:', error);
      return false;
    }
  }
}

// Exporta instância única (singleton)
export const offlineSync = new OfflineSyncService();
export default offlineSync;
