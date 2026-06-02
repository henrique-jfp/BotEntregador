/**
 * SERVICE WORKER - PWA com Cache Inteligente e Background Sync
 * Permite funcionamento offline completo do sistema
 */

// Bump this version to force clients to refresh cached assets on next load
const CACHE_VERSION = 'v1.2.2'; // 🔥 CACHE BUST: incrementado para forçar atualização
const CACHE_NAME = `bot-entregador-${CACHE_VERSION}`;

// Recursos estáticos para cache (sempre disponíveis offline)
const STATIC_CACHE = [
  '/',
  '/index.html',
  '/manifest.json'
];

// Recursos dinâmicos que podem ser cacheados sob demanda
const DYNAMIC_CACHE = [
  '/api/deliverer/route',
  '/api/session/state',
  '/api/admin/stats'
];

// ============================================
// INSTALAÇÃO DO SERVICE WORKER
// ============================================
self.addEventListener('install', (event) => {
  console.log('🔧 Service Worker: Instalando...');
  
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      console.log('📦 Service Worker: Cache criado');
      
      // ✅ Usa Promise.allSettled + fetch manual para falhas gracefulosas
      for (const url of STATIC_CACHE) {
        try {
          const response = await fetch(url);
          if (response.ok) {
            await cache.put(url, response);
            console.log('✅ Cacheado:', url);
          } else {
            console.warn(`⚠️ Status ${response.status} para ${url} (não cacheado)`);
          }
        } catch (err) {
          console.warn(`⚠️ Falha ao cachear ${url}:`, err.message);
          // Continua instalação mesmo se falhar
        }
      }
    }).then(() => {
      console.log('✅ Service Worker: Instalado com sucesso');
      return self.skipWaiting(); // Ativa imediatamente
    }).catch(err => {
      console.error('❌ Erro na instalação:', err);
    })
  );
});

// ============================================
// ATIVAÇÃO E LIMPEZA DE CACHES ANTIGOS
// ============================================
self.addEventListener('activate', (event) => {
  console.log('🚀 Service Worker: Ativando...');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('🗑️ Service Worker: Removendo cache antigo:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('✅ Service Worker: Ativado');
      return self.clients.claim(); // Assume controle de todas as páginas
    })
  );
});

// ============================================
// ESTRATÉGIA DE FETCH (Network First + Cache Fallback)
// ============================================
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignora requisições non-GET ou de outros domínios
  if (request.method !== 'GET' || !url.origin.includes(self.location.origin)) {
    return;
  }

  // Nunca cacheia API para evitar dados antigos
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(request));
    return;
  }

  const isNavigation = request.mode === 'navigate' || request.destination === 'document';

  // ESTRATÉGIA: Network First (tenta rede primeiro, fallback para cache)
  event.respondWith(
    fetch(request, isNavigation ? { cache: 'no-store' } : undefined)
      .then((response) => {
        // Se a resposta é válida, salva no cache
        if (response && response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        // Se falhar (offline), tenta buscar do cache
        return caches.match(request).then((cachedResponse) => {
          if (cachedResponse) {
            console.log('📦 Service Worker: Servindo do cache:', request.url);
            return cachedResponse;
          }

          // Se não há cache, retorna página offline
          if (isNavigation) {
            return caches.match('/index.html');
          }

          // Para outros recursos, retorna resposta vazia
          return new Response('Offline', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: new Headers({
              'Content-Type': 'text/plain'
            })
          });
        });
      })
  );
});

// ============================================
// BACKGROUND SYNC (Sincroniza dados quando online)
// ============================================
self.addEventListener('sync', (event) => {
  console.log('🔄 Service Worker: Background Sync disparado:', event.tag);

  if (event.tag === 'sync-deliveries') {
    event.waitUntil(syncPendingDeliveries());
  }

  if (event.tag === 'sync-location') {
    event.waitUntil(syncLocationUpdates());
  }
});

/**
 * Sincroniza entregas marcadas offline
 */
async function syncPendingDeliveries() {
  try {
    // Busca entregas pendentes do IndexedDB
    const db = await openDB();
    const tx = db.transaction('pending_deliveries', 'readonly');
    const store = tx.objectStore('pending_deliveries');
    const pendingDeliveries = await store.getAll();

    console.log(`📤 Sincronizando ${pendingDeliveries.length} entregas offline...`);

    // Envia cada entrega para o servidor
    for (const delivery of pendingDeliveries) {
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
          // Remove do IndexedDB após sync bem-sucedido
          const delTx = db.transaction('pending_deliveries', 'readwrite');
          const delStore = delTx.objectStore('pending_deliveries');
          await delStore.delete(delivery.id);
          console.log('✅ Entrega sincronizada:', delivery.package_id);
        }
      } catch (err) {
        console.error('❌ Erro ao sincronizar entrega:', err);
      }
    }

    // Notifica o cliente sobre a sincronização
    const clients = await self.clients.matchAll();
    clients.forEach((client) => {
      client.postMessage({
        type: 'SYNC_COMPLETE',
        count: pendingDeliveries.length
      });
    });
  } catch (error) {
    console.error('❌ Erro no background sync:', error);
  }
}

/**
 * Sincroniza atualizações de localização
 */
async function syncLocationUpdates() {
  try {
    const db = await openDB();
    const tx = db.transaction('pending_locations', 'readonly');
    const store = tx.objectStore('pending_locations');
    const locations = await store.getAll();

    for (const loc of locations) {
      try {
        await fetch('/api/deliverer/update-location', {
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

        // Remove após sync
        const delTx = db.transaction('pending_locations', 'readwrite');
        await delTx.objectStore('pending_locations').delete(loc.id);
      } catch (err) {
        console.error('❌ Erro ao sincronizar localização:', err);
      }
    }
  } catch (error) {
    console.error('❌ Erro ao sincronizar localizações:', error);
  }
}

/**
 * Abre conexão com IndexedDB
 */
function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('BotEntregadorDB', 1);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;

      // Cria object stores se não existirem
      if (!db.objectStoreNames.contains('pending_deliveries')) {
        const deliveriesStore = db.createObjectStore('pending_deliveries', {
          keyPath: 'id',
          autoIncrement: true
        });
        deliveriesStore.createIndex('package_id', 'package_id', { unique: false });
        deliveriesStore.createIndex('timestamp', 'timestamp', { unique: false });
      }

      if (!db.objectStoreNames.contains('pending_locations')) {
        const locationsStore = db.createObjectStore('pending_locations', {
          keyPath: 'id',
          autoIncrement: true
        });
        locationsStore.createIndex('timestamp', 'timestamp', { unique: false });
      }

      if (!db.objectStoreNames.contains('route_cache')) {
        db.createObjectStore('route_cache', { keyPath: 'route_id' });
      }
    };
  });
}

// ============================================
// NOTIFICAÇÕES PUSH (Opcional)
// ============================================
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  
  const options = {
    body: data.body || 'Nova notificação do Bot Entregador',
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    vibrate: [200, 100, 200],
    data: data
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'Bot Entregador', options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  event.waitUntil(
    clients.openWindow(event.notification.data.url || '/')
  );
});

console.log('🤖 Service Worker: Inicializado');
