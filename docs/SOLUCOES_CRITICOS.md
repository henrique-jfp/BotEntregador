# 🔧 SOLUÇÕES PARA OS CRÍTICOS DO FLOW DIÁRIO

**Autor:** Enzo  
**Data:** 04/02/2026  
**Objetivo:** Corrigir os 5 pontos críticos que causaram o crash

---

## 🎯 CRÍTICO #1: WebSocket Desconecta Silenciosamente

### Problema:
```javascript
// Atualmente:
const ws = new WebSocket('ws://...');
// ⚠️ Se desconectar, nada acontece!
// ⚠️ Frontend não sabe que está desconectado
// ⚠️ Dados param de chegar
```

### Solução: Reconexão com Exponential Backoff

**Arquivo a criar:** `webapp/src/hooks/useWebSocketWithReconnect.js`

```javascript
/**
 * Hook para WebSocket com reconexão automática
 * Tenta reconectar com intervalo crescente até 30s
 */
export function useWebSocketWithReconnect(url, onMessage, dependencies = []) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const wsRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);
      
      ws.onopen = () => {
        console.log('✅ WebSocket conectado:', url);
        setIsConnected(true);
        reconnectAttemptsRef.current = 0; // Reset contagem
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
    if (reconnectAttemptsRef.current >= 10) {
      console.error('❌ Máximo de tentativas de reconexão atingido');
      return;
    }

    // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s, 30s...
    const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
    reconnectAttemptsRef.current++;

    console.log(`🔄 Reconectando em ${delay / 1000}s... (tentativa ${reconnectAttemptsRef.current})`);
    
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
      }
    }
  };
}
```

### Como usar no MapRealtimeView:

```javascript
// webapp/src/components/MapRealtimeView.jsx
import { useWebSocketWithReconnect } from '../hooks/useWebSocketWithReconnect';

export default function MapRealtimeView({ sessionId }) {
  const { isConnected, lastMessage } = useWebSocketWithReconnect(
    `wss://seu-app.railway.app/api/map/ws/${sessionId}`,
    (data) => {
      // Atualizar mapa quando entregador marca entrega
      if (data.type === 'delivery_update') {
        updateMapPoint(data.point_id, data.status);
      }
    },
    [sessionId]
  );

  return (
    <div className="relative">
      {!isConnected && (
        <div className="bg-red-500 text-white px-4 py-2 text-sm">
          ⚠️ Desconectado. Tentando reconectar...
        </div>
      )}
      {/* Mapa aqui */}
    </div>
  );
}
```

---

## 🎯 CRÍTICO #2: Dashboard Não Atualiza

### Problema:
```python
# Atualmente:
GET /api/session/{id}/dashboard
# ⚠️ Retorna dados estáticos
# ⚠️ Admin precisa recarregar para ver atualizações
```

### Solução: Adicionar Polling ao Dashboard

**Arquivo a modificar:** `webapp/src/pages/DashboardView.jsx`

```javascript
export default function DashboardView({ sessionId }) {
  const [stats, setStats] = useState({
    delivered: 0,
    failed: 0,
    pending: 0,
    progress: 0
  });
  const [isLoading, setIsLoading] = useState(false);
  const pollIntervalRef = useRef(null);

  // 🔄 Polling a cada 2 segundos
  const fetchDashboard = useCallback(async () => {
    try {
      const response = await fetchWithAuth(`/api/session/${sessionId}/dashboard`);
      if (!response.ok) return;
      
      const data = await response.json();
      setStats({
        delivered: data.total_delivered,
        failed: data.total_failed,
        pending: data.total_pending,
        progress: data.progress_percentage
      });
    } catch (error) {
      console.error('Erro ao carregar dashboard:', error);
    }
  }, [sessionId]);

  useEffect(() => {
    // Carregar primeira vez imediatamente
    fetchDashboard();
    
    // Depois polling a cada 2 segundos
    pollIntervalRef.current = setInterval(() => {
      fetchDashboard();
    }, 2000);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [sessionId, fetchDashboard]);

  return (
    <div className="grid grid-cols-4 gap-4">
      <StatCard 
        title="Entregues" 
        value={stats.delivered} 
        color="green"
      />
      <StatCard 
        title="Falhas" 
        value={stats.failed} 
        color="red"
      />
      <StatCard 
        title="Pendentes" 
        value={stats.pending} 
        color="yellow"
      />
      <StatCard 
        title="Progresso" 
        value={`${stats.progress.toFixed(1)}%`} 
        color="blue"
      />
    </div>
  );
}
```

---

## 🎯 CRÍTICO #3: Broadcast Falha Silenciosamente

### Problema:
```python
# Atualmente:
async def broadcast_delivery_update(session_id, point_id, status, route_id):
    if session_id not in active_connections:
        return  # ⚠️ Falha silenciosa!
    
    for ws in active_connections[session_id]:
        await ws.send_json({...})  # ⚠️ Sem tratamento de erro
```

### Solução: Adicionar Retry Logic e Logging

**Arquivo a modificar:** `bot_multidelivery/routers/map_realtime.py`

```python
import asyncio
import logging

logger = logging.getLogger(__name__)

# Fila de updates pendentes (para reconexão)
pending_updates: dict = {}  # session_id -> [updates]

async def broadcast_delivery_update(
    session_id: str, 
    point_id: str, 
    status: str, 
    route_id: str,
    max_retries: int = 3
):
    """
    Broadcast com retry logic e persistência
    """
    update_data = {
        "type": "delivery_update",
        "point_id": point_id,
        "status": status,
        "route_id": route_id,
        "timestamp": datetime.now().isoformat()
    }
    
    # Adicionar à fila de pendentes (para clientes que reconectam)
    if session_id not in pending_updates:
        pending_updates[session_id] = []
    pending_updates[session_id].append(update_data)
    
    logger.info(f"📤 Broadcasting delivery update: {point_id} → {status}")
    
    if session_id not in active_connections:
        logger.warning(f"⚠️ Nenhum cliente conectado para {session_id}. Salvo na fila.")
        return
    
    failed_clients = []
    
    for idx, websocket in enumerate(active_connections[session_id]):
        retry_count = 0
        while retry_count < max_retries:
            try:
                await websocket.send_json(update_data)
                logger.info(f"✅ Update entregue ao cliente {idx}")
                break
            except Exception as e:
                retry_count += 1
                logger.warning(f"⚠️ Tentativa {retry_count}/{max_retries} falhou: {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(0.5 * retry_count)  # Backoff
                else:
                    failed_clients.append(idx)
                    logger.error(f"❌ Cliente {idx} não respondeu após {max_retries} tentativas")
    
    # Remover clientes mortos
    if failed_clients:
        for idx in sorted(failed_clients, reverse=True):
            if idx < len(active_connections[session_id]):
                active_connections[session_id].pop(idx)
        logger.info(f"🗑️ Removidos {len(failed_clients)} clientes inativos")


@router.websocket("/ws/{session_id}")
async def websocket_map_updates(websocket: WebSocket, session_id: str):
    """
    WebSocket com suporte a replay de updates pendentes
    """
    await websocket.accept()
    logger.info(f"✅ Cliente conectado ao mapa da sessão {session_id}")
    
    if session_id not in active_connections:
        active_connections[session_id] = []
    active_connections[session_id].append(websocket)
    
    # 🆕 Enviar todos os updates pendentes ao cliente que acaba de conectar
    if session_id in pending_updates:
        logger.info(f"📬 Enviando {len(pending_updates[session_id])} updates pendentes...")
        for update in pending_updates[session_id][-50:]:  # Últimos 50 updates
            try:
                await websocket.send_json(update)
            except Exception as e:
                logger.error(f"❌ Erro ao enviar update pendente: {e}")
    
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        logger.info(f"🔌 Cliente desconectou de {session_id}")
        if session_id in active_connections:
            try:
                active_connections[session_id].remove(websocket)
            except ValueError:
                pass
```

---

## 🎯 CRÍTICO #4: Notificação "Todos Finalizaram" Pode Falhar

### Problema:
```python
# Atualmente:
admin_id = os.getenv('ADMIN_TELEGRAM_ID')
if admin_id:
    await notifier.send_message(...)  # ⚠️ Se falhar, não há retry
```

### Solução: Adicionar Retry com Queue

**Arquivo a modificar:** `bot_multidelivery/routers/deliverer.py`

```python
import asyncio
from datetime import datetime

# Fila de notificações importantes
notification_queue = []

async def check_all_routes_completed(session):
    """
    Verifica se todas as rotas foram finalizadas
    Com retry logic para notificação
    """
    all_completed = all(
        route.completion_rate >= 100.0 
        for route in session.routes
    )
    
    if not all_completed:
        logger.debug(f"⏳ Rotas pendentes: {[r.color for r in session.routes if r.completion_rate < 100]}")
        return
    
    logger.info(f"🎉 TODAS as rotas foram finalizadas na sessão {session.session_id}")
    
    try:
        from bot_multidelivery.services.telegram_notifier import notifier
        admin_id = os.getenv('ADMIN_TELEGRAM_ID')
        
        if not admin_id:
            logger.error("❌ ADMIN_TELEGRAM_ID não configurado!")
            notification_queue.append({
                "type": "all_routes_completed",
                "session_id": session.session_id,
                "timestamp": datetime.now(),
                "attempts": 0
            })
            return
        
        message = f"""
🎉 <b>TODAS AS ROTAS FORAM FINALIZADAS!</b>

📦 Sessão: {session.session_name or session.session_id[:8]}
📅 Data: {session.date}
⏰ Hora: {datetime.now().strftime('%H:%M:%S')}

✅ <b>Estatísticas Finais:</b>
• Total de Pacotes: {session.total_packages}
• Entregadores: {session.num_deliverers}
• Rotas Completas: {len(session.routes)}/{len(session.routes)}

💰 <b>Próximo Passo:</b>
Venha fazer o fechamento diário no app! 👇
Acesse: Fechamento → Adicione custos → Finalize a sessão

<i>Não se esqueça de incluir: Combustível, Outros, Salários dos entregadores</i>
"""
        
        webapp_url = os.getenv('WEBAPP_URL', 'https://seu-app.railway.app')
        
        reply_markup = {
            "inline_keyboard": [[
                {
                    "text": "💰 Fazer Fechamento Agora",
                    "web_app": {"url": f"{webapp_url}?tab=closure"}
                }
            ]]
        }
        
        # Tentar enviar com retry
        success = False
        for attempt in range(3):
            try:
                result = await notifier.send_message(
                    chat_id=int(admin_id),
                    text=message,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
                
                if result:
                    logger.info(f"✅ Notificação de finalização enviada ao admin {admin_id}")
                    success = True
                    break
                else:
                    logger.warning(f"⚠️ Tentativa {attempt + 1}/3 falhou")
                    await asyncio.sleep(2 ** attempt)  # Backoff exponencial
            
            except Exception as e:
                logger.error(f"❌ Erro tentativa {attempt + 1}/3: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
        
        if not success:
            logger.critical(f"❌ Falha ao notificar admin após 3 tentativas!")
            notification_queue.append({
                "type": "all_routes_completed",
                "session_id": session.session_id,
                "admin_id": admin_id,
                "timestamp": datetime.now(),
                "attempts": 3
            })
    
    except Exception as e:
        logger.error(f"❌ Erro ao verificar rotas: {e}")
        notification_queue.append({
            "type": "all_routes_completed",
            "session_id": session.session_id,
            "error": str(e),
            "timestamp": datetime.now(),
            "attempts": 0
        })
```

---

## 🎯 CRÍTICO #5: Estatísticas do Entregador Não Existem

### Problema:
```python
# Atualmente:
# ❌ Nenhum endpoint que rastreia stats semanais
```

### Solução: Implementar Endpoints de Stats

**Arquivo a criar:** `bot_multidelivery/routers/deliverer_stats.py`

```python
"""
Router para Estatísticas de Entregadores
Rastreia: pacotes entregues, insucessos, transferências, salários
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from bot_multidelivery.persistence import data_store
from bot_multidelivery.session import session_manager
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/deliverer", tags=["Deliverer Stats"])


@router.get("/{deliverer_id}/stats/weekly")
async def get_weekly_stats(deliverer_id: int = Query(...)):
    """
    Retorna estatísticas semanais de um entregador
    """
    try:
        # Buscar todos as sessões da semana
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        
        deliverer = data_store.get_deliverer(deliverer_id)
        if not deliverer:
            raise HTTPException(status_code=404, detail="Entregador não encontrado")
        
        # Inicializar contadores
        stats = {
            "deliverer_id": deliverer_id,
            "deliverer_name": deliverer.name,
            "week_start": week_start.strftime('%Y-%m-%d'),
            "week_end": today.strftime('%Y-%m-%d'),
            "total_deliveries": 0,
            "total_failures": 0,
            "total_transfers": 0,
            "total_packages": 0,
            "success_rate": 0.0,
            "week_salary_accumulated": 0.0,
            "sessions": []
        }
        
        # Buscar do banco de dados (implementado em persistence.py)
        # FROM delivery_sessions WHERE date >= week_start AND assigned_to_id = deliverer_id
        sessions = data_store.get_deliverer_sessions(
            deliverer_id=deliverer_id,
            date_from=week_start.strftime('%Y-%m-%d'),
            date_to=today.strftime('%Y-%m-%d')
        )
        
        for session in sessions:
            session_stats = {
                "session_id": session.session_id,
                "date": session.date,
                "deliveries": 0,
                "failures": 0,
                "transfers": 0,
                "salary": 0.0
            }
            
            # Contar pacotes da sessão
            for package in session.packages:
                if package.deliverer_id == deliverer_id:
                    if package.status == "delivered":
                        session_stats["deliveries"] += 1
                    elif package.status == "failed":
                        session_stats["failures"] += 1
                    elif package.status == "returned":
                        session_stats["transfers"] += 1
                    
                    session_stats["total_packages"] += 1
            
            # Buscar salário (de daily_closures)
            daily_closure = data_store.get_daily_closure(session.session_id)
            if daily_closure and deliverer_id in daily_closure.deliverer_breakdown:
                session_stats["salary"] = daily_closure.deliverer_breakdown[deliverer_id]
            
            stats["sessions"].append(session_stats)
            stats["total_deliveries"] += session_stats["deliveries"]
            stats["total_failures"] += session_stats["failures"]
            stats["total_transfers"] += session_stats["transfers"]
            stats["week_salary_accumulated"] += session_stats["salary"]
        
        # Calcular taxa de sucesso
        total_packages = stats["total_deliveries"] + stats["total_failures"] + stats["total_transfers"]
        if total_packages > 0:
            stats["total_packages"] = total_packages
            stats["success_rate"] = (stats["total_deliveries"] / total_packages) * 100
        
        return stats
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao buscar stats: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats/team")
async def get_team_stats():
    """
    Retorna estatísticas de TODOS os entregadores da semana
    """
    try:
        deliverers = data_store.get_all_deliverers()
        team_stats = []
        
        for deliverer in deliverers:
            weekly = await get_weekly_stats(deliverer.id)
            team_stats.append(weekly)
        
        return {
            "total_deliverers": len(team_stats),
            "deliverers": team_stats,
            "team_totals": {
                "total_deliveries": sum(d["total_deliveries"] for d in team_stats),
                "total_failures": sum(d["total_failures"] for d in team_stats),
                "total_transfers": sum(d["total_transfers"] for d in team_stats),
                "team_salary": sum(d["week_salary_accumulated"] for d in team_stats),
            }
        }
    
    except Exception as e:
        logger.error(f"❌ Erro ao buscar stats do time: {e}")
        raise HTTPException(status_code=400, detail=str(e))
```

**Arquivo a modificar:** `bot_multidelivery/__init__.py` (routers)

```python
# Adicionar novo router
from .routers import deliverer_stats
app.include_router(deliverer_stats.router)
```

**Componente React:** `webapp/src/pages/TeamStatsView.jsx`

```javascript
import React, { useState, useEffect } from 'react';
import { TrendingUp, Users, CheckCircle, XCircle } from 'lucide-react';

export default function TeamStatsView() {
  const [teamStats, setTeamStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('/api/deliverer/stats/team');
        const data = await response.json();
        setTeamStats(data);
      } catch (error) {
        console.error('Erro ao carregar stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) return <div>Carregando...</div>;
  if (!teamStats) return <div>Erro ao carregar dados</div>;

  return (
    <div className="space-y-6">
      {/* Totais do time */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Entregas"
          value={teamStats.team_totals.total_deliveries}
          icon={<CheckCircle className="w-6 h-6 text-green-500" />}
        />
        <StatCard
          title="Falhas"
          value={teamStats.team_totals.total_failures}
          icon={<XCircle className="w-6 h-6 text-red-500" />}
        />
        <StatCard
          title="Transferências"
          value={teamStats.team_totals.total_transfers}
          icon={<TrendingUp className="w-6 h-6 text-yellow-500" />}
        />
        <StatCard
          title="Salários"
          value={`R$ ${teamStats.team_totals.team_salary.toFixed(2)}`}
          icon={<Users className="w-6 h-6 text-blue-500" />}
        />
      </div>

      {/* Tabela individual */}
      <div className="card-premium overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-100">
            <tr>
              <th>Entregador</th>
              <th>Entregas</th>
              <th>Falhas</th>
              <th>Taxa Sucesso</th>
              <th>Salário Semana</th>
            </tr>
          </thead>
          <tbody>
            {teamStats.deliverers.map(d => (
              <tr key={d.deliverer_id} className="border-b hover:bg-gray-50">
                <td>{d.deliverer_name}</td>
                <td className="text-center font-bold">{d.total_deliveries}</td>
                <td className="text-center text-red-600">{d.total_failures}</td>
                <td className="text-center">{d.success_rate.toFixed(1)}%</td>
                <td className="text-right font-bold">
                  R$ {d.week_salary_accumulated.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

- [ ] Implementar `useWebSocketWithReconnect` hook
- [ ] Adicionar polling ao Dashboard
- [ ] Adicionar retry logic ao `broadcast_delivery_update()`
- [ ] Implementar fila de updates pendentes
- [ ] Adicionar retry logic à notificação "todos finalizaram"
- [ ] Criar endpoints de estatísticas
- [ ] Testar flow completo com 2 entregadores
- [ ] Fazer commit e push para redeploy

---

## 🚀 Como Testar

```bash
# 1. Simular 2 entregadores completando rota
python test_daily_flow_with_retry.py

# 2. Verificar logs de reconexão
tail -f logs/reconnect.log | grep "WebSocket\|reconect\|broadcast"

# 3. Monitorar notificações
tail -f logs/telegram.log | grep "Notificação\|finalizado"
```

