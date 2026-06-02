/**
 * API CLIENT COM SUPORTE OFFLINE
 * Wrapper sobre fetch() que salva requisições offline no IndexedDB
 */

import offlineSync from './services/offlineSync';

/**
 * Fetch com autenticação e fallback offline
 */
export async function fetchWithAuth(url, options = {}) {
  const token = localStorage.getItem('auth_token');
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const config = {
    ...options,
    headers
  };

  try {
    // Tenta fazer requisição normal
    const response = await fetch(url, config);
    
    // Se sucesso, retorna normalmente
    if (response.ok) {
      return response;
    }
    
    // Se erro de autenticação, redireciona
    if (response.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
      throw new Error('Não autorizado');
    }
    
    return response;
  } catch (error) {
    // Se está offline e é uma requisição GET, tenta buscar do cache
    if (!navigator.onLine && options.method === 'GET') {
      console.log('📦 Tentando buscar do cache offline:', url);
      
      // Verifica se é uma rota específica com cache
      if (url.includes('/api/deliverer/route')) {
        const routeId = extractRouteIdFromUrl(url);
        const cachedRoute = await offlineSync.getCachedRoute(routeId);
        
        if (cachedRoute) {
          return new Response(JSON.stringify(cachedRoute), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
          });
        }
      }
    }
    
    // Se está offline e é POST de entrega, salva offline
    if (!navigator.onLine && url.includes('/mark-delivered')) {
      console.log('💾 Salvando entrega offline...');
      
      const body = JSON.parse(options.body);
      await offlineSync.saveDeliveryOffline(
        body.package_id,
        body.status,
        body.location
      );
      
      // Retorna resposta simulada de sucesso
      return new Response(JSON.stringify({ 
        status: 'queued',
        message: 'Entrega salva offline e será sincronizada' 
      }), {
        status: 202, // Accepted
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Para outros casos, rejeita o erro
    throw error;
  }
}

/**
 * Helper para extrair ID da rota de uma URL
 */
function extractRouteIdFromUrl(url) {
  const match = url.match(/route\/([^?]+)/);
  return match ? match[1] : null;
}

/**
 * Salva rota no cache offline
 */
export async function cacheRouteData(routeId, routeData) {
  try {
    await offlineSync.cacheRoute(routeId, routeData);
    console.log('✅ Rota cacheada para uso offline:', routeId);
  } catch (error) {
    console.error('❌ Erro ao cachear rota:', error);
  }
}

/**
 * Salva mapa HTML no cache
 */
export async function cacheMapData(mapId, mapHtml) {
  try {
    await offlineSync.cacheMap(mapId, mapHtml);
    console.log('✅ Mapa cacheado para uso offline:', mapId);
  } catch (error) {
    console.error('❌ Erro ao cachear mapa:', error);
  }
}

export default fetchWithAuth;
