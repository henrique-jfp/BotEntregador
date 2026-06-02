// Utilitário global para fetch seguro
export async function fetchSafe(endpoint, options = {}) {
  // Sempre usar um caminho relativo.
  // Se endpoint já começar com http(s), mantém como absoluto.
  let url = endpoint;
  if (!endpoint.startsWith('http')) {
    // Garante prefixo '/api'
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    url = cleanEndpoint.startsWith('/api') ? cleanEndpoint : `/api${cleanEndpoint}`;
  }

  try {
    const res = await fetch(url, options);
    const text = await res.text();
    try {
      return { ok: res.ok, status: res.status, json: JSON.parse(text) };
    } catch (e) {
      return { ok: res.ok, status: res.status, error: `Resposta inesperada do servidor: ${text.slice(0, 120)}` };
    }
  } catch (err) {
    return { ok: false, status: 0, error: err.message };
  }
}

// Utilitário para Headers Autenticados
export const getAuthHeaders = () => {
  const apiKey = import.meta.env.VITE_API_KEY || "";
  return {
    'Content-Type': 'application/json',
    'X-API-Key': apiKey,
  };
};

export const fetchWithAuth = async (url, options = {}) => {
  const headers = { ...getAuthHeaders(), ...(options.headers || {}) };
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  if (isFormData) delete headers['Content-Type'];

  // Normaliza URLs relativas garantindo o prefixo /api
  let fullUrl = url;
  const isAbsolute = typeof url === 'string' && (url.startsWith('http') || url.startsWith('https'));
  if (!isAbsolute) {
    const cleanUrl = url.startsWith('/') ? url : `/${url}`;
    fullUrl = cleanUrl.startsWith('/api') ? cleanUrl : `/api${cleanUrl}`;
  }

  return fetch(fullUrl, { ...options, headers });
};

// Conveniência: fetch que já garante parsing JSON e erros legíveis
export const fetchJsonWithAuth = async (url, options = {}) => {
  const res = await fetchWithAuth(url, options);
  const contentType = res.headers.get ? (res.headers.get('content-type') || '') : '';

  // Se status not ok, tenta ler texto para diagnosticar
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} - ${text.slice(0, 200)}`);
  }

  if (contentType.includes('application/json')) {
    return res.json();
  }

  // Resposta não-JSON: ler texto para diagnóstico e lançar erro claro
  const text = await res.text().catch(() => '');
  throw new Error(`Expected JSON but got ${contentType || 'unknown'}: ${text.slice(0, 200)}`);
};
