# 🚀 QUICK START - IMPLEMENTAR SOLUÇÃO DE RECONEXÃO

**Tempo estimado:** 1-2 horas  
**Dificuldade:** Média  
**Impacto:** Crítico (elimina falha do crash anterior)

---

## 📋 PASSO 1: Criar Hook de Reconexão

**Arquivo:** `webapp/src/hooks/useWebSocketWithReconnect.js`

Copie exatamente o código abaixo:

```javascript
/**
 * Hook para WebSocket com reconexão automática
 * Tenta reconectar com intervalo crescente até 30s
 */
import { useEffect, useRef, useCallback, useState } from 'react';

export function useWebSocketWithReconnect(url, onMessage, dependencies = []) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const wsRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    // Evitar múltiplas conexões simultâneas
    if (wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    try {
      const ws = new WebSocket(url);
      
      ws.onopen = () => {
        console.log('✅ WebSocket conectado:', url);
        setIsConnected(true);
        reconnectAttemptsRef.current = 0; // Reset
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          onMessage?.(data);
        } catch (err) {
          console.error('❌ Erro ao parsear WebSocket:', err);
        }
      };
      
      ws.onerror = (error) => {
        console.error('❌ WebSocket erro:', error);
        setIsConnected(false);
      };
      
      ws.onclose = () => {
        console.warn('⚠️ WebSocket fechado. Tentando reconectar...');
        setIsConnected(false);
        scheduleReconnect();
      };
      
      wsRef.current = ws;
    } catch (err) {
      console.error('❌ Erro ao criar WebSocket:', err);
      scheduleReconnect();
    }
  }, [url, onMessage]);

  const scheduleReconnect = useCallback(() => {
    // Máximo de tentativas
    if (reconnectAttemptsRef.current >= 10) {
      console.error('❌ Máximo de tentativas de reconexão atingido');
      return;
    }

    // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s, 30s...
    const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
    reconnectAttemptsRef.current++;

    console.log(`🔄 Reconectando em ${(delay / 1000).toFixed(1)}s... (tentativa ${reconnectAttemptsRef.current}/10)`);
    
    reconnectTimeoutRef.current = setTimeout(() => {
      connect();
    }, delay);
  }, [connect]);

  useEffect(() => {
    connect();
    
    return () => {
      wsRef.current?.close();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, dependencies);

  return {
    isConnected,
    lastMessage,
    send: (data) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(data));
      } else {
        console.warn('⚠️ WebSocket não está conectado');
      }
    }
  };
}
```

---

## 📋 PASSO 2: Atualizar MapRealtimeView

**Arquivo:** `webapp/src/components/MapRealtimeView.jsx`

Substitua o bloco de WebSocket:

**Antes:**
```javascript
useEffect(() => {
  const ws = new WebSocket(`wss://...api/map/ws/${sessionId}`);
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    updateMapPoint(data.point_id, data.status);
  };
  // ⚠️ Sem tratamento de desconexão!
}, [sessionId]);
```

**Depois:**
```javascript
import { useWebSocketWithReconnect } from '../hooks/useWebSocketWithReconnect';

export default function MapRealtimeView({ sessionId }) {
  const { isConnected, lastMessage } = useWebSocketWithReconnect(
    `wss://seu-app.railway.app/api/map/ws/${sessionId}`,
    (data) => {
      if (data.type === 'delivery_update') {
        updateMapPoint(data.point_id, data.status);
      }
    },
    [sessionId]
  );

  return (
    <div className="relative h-screen">
      {/* Banner de status */}
      <div className="absolute top-0 left-0 right-0 z-10">
        {!isConnected && (
          <div className="bg-red-500 text-white px-4 py-2 text-sm flex items-center gap-2">
            <span className="animate-spin">🔄</span>
            ⚠️ Desconectado. Tentando reconectar...
          </div>
        )}
        {isConnected && (
          <div className="bg-green-500 text-white px-4 py-2 text-sm">
            ✅ Conectado em tempo real
          </div>
        )}
      </div>

      {/* Mapa aqui */}
      <MapComponent sessionId={sessionId} />
    </div>
  );
}
```

---

## 📋 PASSO 3: Adicionar Fallback com Polling

Se WebSocket falhar, usar polling como backup:

```javascript
import { useWebSocketWithReconnect } from '../hooks/useWebSocketWithReconnect';

export default function MapRealtimeView({ sessionId }) {
  const [mapData, setMapData] = useState(null);
  const pollIntervalRef = useRef(null);

  // WebSocket com reconexão
  const { isConnected } = useWebSocketWithReconnect(
    `wss://seu-app.railway.app/api/map/ws/${sessionId}`,
    (data) => {
      if (data.type === 'delivery_update') {
        updateMapPoint(data.point_id, data.status);
      }
    },
    [sessionId]
  );

  // Fallback: polling se não estiver conectado
  useEffect(() => {
    if (isConnected) {
      // Se WebSocket está conectado, parar polling
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      return;
    }

    // Se desconectado, fazer polling a cada 5 segundos
    console.log('📡 WebSocket desconectado. Iniciando polling...');
    
    const fetchMapData = async () => {
      try {
        const response = await fetch(`/api/map/realtime/${sessionId}`);
        const data = await response.json();
        
        if (data.points) {
          setMapData(data.points);
          // Atualizar mapa com dados do polling
          data.points.forEach(point => {
            updateMapPoint(point.id, point.status);
          });
        }
      } catch (error) {
        console.error('❌ Erro no polling:', error);
      }
    };

    // Fazer fetch imediato
    fetchMapData();

    // Depois polling a cada 5 segundos
    pollIntervalRef.current = setInterval(fetchMapData, 5000);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [isConnected, sessionId]);

  return (
    <div className="relative h-screen">
      {/* Banner de status */}
      <div className="absolute top-0 left-0 right-0 z-10">
        {isConnected ? (
          <div className="bg-green-500 text-white px-4 py-2 text-sm">
            ✅ Conectado em tempo real (WebSocket)
          </div>
        ) : (
          <div className="bg-yellow-500 text-gray-900 px-4 py-2 text-sm flex items-center gap-2">
            <span className="animate-pulse">⚠️</span>
            Modo fallback: Polling a cada 5 segundos
          </div>
        )}
      </div>

      {/* Mapa */}
      <MapComponent sessionId={sessionId} />
    </div>
  );
}
```

---

## 📋 PASSO 4: Testar Localmente

### Teste 1: Reconexão Automática

```javascript
// No console do navegador (F12):

// 1. Abrir mapa
// Ver: ✅ Conectado em tempo real

// 2. Desligar WiFi por 5 segundos
// Ver em tempo real:
// ⚠️ Desconectado
// 🔄 Reconectando em 1s... (tentativa 1/10)

// 3. Ligar WiFi
// Ver:
// ✅ Conectado em tempo real (alguns segundos depois)

// ✅ SUCESSO se reconectou automaticamente
```

### Teste 2: Fallback Polling

```javascript
// No DevTools > Network:

// 1. Throttle para "Slow 3G" (simula conexão ruim)
// 2. Ver que polling começa a cada 5 segundos:
//    GET /api/map/realtime/{sessionId}
// 3. Mapa continua atualizando (mais lento, mas funciona)

// ✅ SUCESSO se mapa não congela
```

### Teste 3: Marcação de Entrega em Tempo Real

```bash
# Terminal 1: Monitorar logs
tail -f logs/websocket.log | grep "broadcast\|update\|deliverer"

# Terminal 2: Fazer requisição de teste
curl -X POST http://localhost:8080/api/deliverer/complete-stop \
  -d "route_id=route_1&stop_index=0&status=delivered" \
  -H "Content-Type: application/x-www-form-urlencoded"

# Ver nos logs:
# 📤 Broadcasting delivery update: pkg_1 → delivered
# ✅ Update entregue ao cliente 0
# ✅ Update entregue ao cliente 1
```

---

## 🔧 PASSO 5: Deploy

### 1. Commit local
```bash
cd c:\BotEntregador

git add webapp/src/hooks/useWebSocketWithReconnect.js
git add webapp/src/components/MapRealtimeView.jsx
git commit -m "🔧 Implementar reconexão WebSocket com fallback polling"
```

### 2. Push para GitHub
```bash
git push origin main
```

### 3. Railway redeploy automático
```
Railway detectará o push e fará deploy automático
Verificar em: https://railway.app/dashboard
```

### 4. Validar em produção
```javascript
// Abrir app em produção:
// https://seu-app.railway.app

// Testar:
// 1. Abrir aba Mapa
// 2. Desligar WiFi por 10s
// 3. Ligar WiFi
// ✅ Mapa continua funcionando
```

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

```
[ ] Passo 1: Criar hook useWebSocketWithReconnect.js
[ ] Passo 2: Atualizar MapRealtimeView.jsx
[ ] Passo 3: Adicionar fallback polling
[ ] Passo 4: Testar localmente
    [ ] Teste 1: Reconexão automática
    [ ] Teste 2: Fallback polling
    [ ] Teste 3: Marcação em tempo real
[ ] Passo 5: Deploy
    [ ] Commit
    [ ] Push
    [ ] Validar em produção
```

---

## 🎯 RESULTADO ESPERADO

Depois dessa implementação:

✅ **Antes:** Admin desconecta → mapa congela → app parece quebrado  
✅ **Depois:** Admin desconecta → reconecta automaticamente → mapa continua atualizando

**Taxa de sucesso esperada:** 99%+ (só falha se sem internet)

---

## 📞 Problemas Comuns

### "Mapa ainda congela após reconectar"
- Verifique que `isConnected` atualiza no UI
- Confirme que browser console mostra "✅ WebSocket conectado"
- Se não funcionar, limpar cache (Ctrl+Shift+Delete)

### "Polling muito lento"
- Pode reduzir para 3 segundos se quiser mais realtime
- Mas aumenta carga no servidor
- 5 segundos é balanço bom

### "Reconexão fica em loop"
- Verificar que `ADMIN_TELEGRAM_ID` está configurado
- Confirmar que `/api/map/ws/{session_id}` retorna 200 OK
- Logs devem mostrar o erro específico

---

## 🚀 Próximos Passos (Após Implementação)

1. **Hoje:** Implementar reconexão WebSocket
2. **Amanhã:** Testar com 2 entregadores reais em staging
3. **Sexta:** Deploy final em produção com monitoramento
4. **Próxima semana:** Adicionar persistência de updates na DB

---

**Boa sorte! Qualquer dúvida, ping! 🔥**

