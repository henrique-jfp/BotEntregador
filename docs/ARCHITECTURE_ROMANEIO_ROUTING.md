# 🏛️ Arquitetura da Feature Principal: Import + Routing

## 📐 Visão Geral

O sistema de romaneio (entrega) funciona em **4 estágios principais**:

```
┌─────────────────────────────────────────────────────────────┐
│  STAGE 1: SESSION CREATION                                  │
│  - Admin abre app                                            │
│  - Sistema carrega /session/state                            │
│  - Se não existe, cria nova DailySession                     │
│  - SessionManager armazena em memória + salva em DB          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 2: ROMANEIO IMPORT (Multi-Import)                    │
│  - Upload de Excel/PDF/CSV                                  │
│  - Parsers extraem endereços                                │
│  - Cria Romaneio com filename rastreado                     │
│  - Appenda à session.romaneios[]                             │
│  - Auto-save em PostgreSQL + JSON                            │
│  - Frontend lista romaneios importados                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 3: ROUTE OPTIMIZATION (Clustering)                   │
│  - Frontend envia: { num_deliverers, session_id }           │
│  - Backend coleta todos os pontos (∑romaneios)              │
│  - TerritoryDivider cria K clusters (K-Means)               │
│  - TSP dentro de cada cluster (OSRM + fallback)             │
│  - Retorna preview: cor, mapa, paradas/pacotes              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 4: ASSIGNMENT & TRACKING                              │
│  - Admin seleciona entregador para cada rota                │
│  - POST /assign com (route_id, deliverer_id)                │
│  - SessionManager.assign_route() atualiza Route             │
│  - Frontend mostra "Rota #1 → João" com confirmação         │
│  - Entregador recebe URL com sua rota no bot                │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Estrutura de Dados

### **DailySession** (Estado Global por Dia)
```python
@dataclass
class DailySession:
    session_id: str           # UUID (ex: "abc12345")
    session_name: str         # "Segunda Manhã" (auto-gerado)
    date: str                 # "2024-01-15" (YYYY-MM-DD)
    period: str               # "manhã" ou "tarde"
    base_address: str         # "R. Principal, 100"
    base_lat/lng: float       # coordenadas da base
    
    romaneios: List[Romaneio] # Múltiplos uploads
    routes: List[Route]       # Rotas otimizadas + atribuídas
    
    total_packages → property # ∑(r.points para r em romaneios)
    total_delivered → property
    current_step: str         # "importing" | "optimized" | "assigned"
    num_deliverers: int       # Setado no optimize
```

### **Romaneio** (Um Upload = Um Romaneio)
```python
@dataclass
class Romaneio:
    id: str                   # UUID (ex: "rom_xyz789")
    filename: str             # "vendas_marco.xlsx" ou "Manual"
    uploaded_at: datetime     # Quando foi importado
    points: List[DeliveryPoint]  # 63 pacotes (ex)
    
    total_packages → property # len(points)
```

### **DeliveryPoint** (Um Pacote)
```python
@dataclass
class DeliveryPoint:
    package_id: str           # "PKG_12345"
    romaneio_id: str          # ref ao Romaneio (para rastreabilidade)
    address: str              # "R. das Flores, 123, Apt 401"
    lat/lng: float            # Geocodificadas (0,0 se falhar)
    priority: str             # "normal" | "priority" | "fragile"
```

### **Route** (Uma Rota = Um Entregador)
```python
@dataclass
class Route:
    id: str                   # "ROTA_1"
    cluster: Cluster          # Dados geoespaciais (K-Means)
    
    assigned_to_telegram_id: int  # ID do bot (ex: 12345)
    assigned_to_name: str     # "João Silva"
    color: str                # "#667eea" (cor única)
    
    optimized_order: List[DeliveryPoint]  # Ordem TSP
    delivered_packages: List[str]         # IDs já entregues
    
    total_packages → property
    delivered_count → property
    total_distance_km → property  # OSRM
```

---

## 🔌 Endpoints Principais

### **Session Management**

| Método | Endpoint | Função |
|--------|----------|--------|
| GET | `/api/session/state` | Retorna estado completo (NEW) |
| POST | `/api/session/start` | Cria/reutiliza sessão |
| POST | `/api/session/cancel-import` | Limpa romaneios/rotas (NEW) |
| POST | `/api/session/finalize` | Encerra sessão |
| GET | `/api/session/report` | Relatório de entrega |

### **Romaneio Management**

| Método | Endpoint | Função |
|--------|----------|--------|
| POST | `/api/romaneio/import` | Upload e parse do arquivo |
| GET | `/api/romaneio/session/{id}/summary` | Lista romaneios com filename |
| DELETE | `/api/romaneio/romaneio/{session_id}/{rom_id}` | Remove um romaneio |

### **Route Optimization**

| Método | Endpoint | Função |
|--------|----------|--------|
| POST | `/api/routes/optimize` | Divide em K clusters + TSP |
| POST | `/api/routes/assign` | Atribui rota a entregador |
| POST | `/api/routes/send` | Envia rotas aos entregadores |

---

## 🧠 Algoritmos Chave

### **1. Clustering (TerritoryDivider)**
```python
class TerritoryDivider:
    def divide_into_clusters(points: List[DeliveryPoint], k: int):
        # K-Means geoespacial
        # Base location como centróide inicial
        # Retorna K clusters balanceados
        # Cada cluster: {"points": [...], "centroid": (lat, lng)}
```

### **2. Route Optimization (TSP)**
```python
def optimize_cluster_route(cluster: Cluster) -> List[DeliveryPoint]:
    # Ordena pontos do cluster
    # Tenta usar OSRM (distance matrix)
    # Fallback: Haversine (distância euclidiana)
    # Retorna ordem otimizada (mais curta)
```

### **3. Distance Calculation (OSRM Service)**
```python
class OSRMClient:
    def get_distance_matrix(coords) → distances:
        # Chama OSRM table endpoint
        # Cache em Redis/memory
        
    def get_route_geometry(coords) → geometria:
        # Chama OSRM route endpoint
        # Usa para desenhar polyline no mapa
```

---

## 💾 Persistência

### **Multi-Layer Storage**

```
┌────────────────────────────────────┐
│   SessionManager (Memory)           │
│   active_sessions: Dict[id→Session] │ ← Runtime
│   current_session_id: str           │
└────────┬──────────────────────────┘
         │ auto-save (on create/update)
         ↓
┌────────────────────────────────────┐
│   PostgreSQL (Primary DB)           │ ← Persistência
│   - SessionDB table                 │
│   - romaneios_data: JSON[]          │
│   - routes: RouteDB[]               │
└────────────────────────────────────┘
         ↑ fallback
         │
┌────────────────────────────────────┐
│   JSON Files (Backup)               │
│   data/sessions/{session_id}.json   │
└────────────────────────────────────┘
```

### **Load Process (Startup)**
```python
def _load_all_sessions(self):
    # 1. Carrega PostgreSQL (se conectado)
    # 2. Se falhar, carrega JSON local
    # 3. Reconstrói objetos (Romaneio, Route, etc)
    # 4. Popula active_sessions dict
    # Result: SessionManager restaurado com histórico
```

---

## 🔄 Frontend-Backend Communication

### **Initialize Session**
```
Frontend:
  GET /api/session/state
  
Backend response:
  {
    "active": true,
    "session_id": "abc123",
    "has_romaneio": false,
    "total_packages": 0,
    "romaneios": []
  }
  
Frontend:
  - Se active=true, restaura state
  - Exibe lista de romaneios já importados
  - Oferece opção de "Novo Romaneio" ou "Continuar"
```

### **Import Romaneio**
```
Frontend:
  POST /api/romaneio/import (multipart/form-data)
    - file: Excel/PDF/CSV
    - route_value: float
    
Backend response:
  {
    "status": "success",
    "session_id": "abc123",
    "romaneio_id": "rom_xyz",
    "total_addresses": 63,
    "session_total_packages": 63,
    "imported_romaneios": 1,
    "message": "Importado com sucesso: 63 endereços"
  }
  
Frontend:
  - Salva session_id em state
  - Recarrega GET /api/romaneio/session/{id}/summary
  - Renderiza lista visual de romaneios
  - Oferece "+ Mais" para upload adicional
```

### **Optimize Routes**
```
Frontend:
  POST /api/routes/optimize (application/json)
    {
      "num_deliverers": 3,
      "session_id": "abc123"  ← NOVO (obrigatório)
    }
    
Backend:
  1. get_session(session_id)
  2. Coleta points de todos os romaneios
  3. divider.divide_into_clusters(points, 3)
  4. Para cada cluster: optimize_cluster_route()
  5. Cria Route objects
  6. session_manager.set_routes(routes)
  
Backend response:
  {
    "status": "success",
    "optimized": true,
    "routes": [
      {
        "id": "ROTA_1",
        "name": "Rota 1",
        "packages_count": 21,
        "color": "#667eea",
        "center": {"lat": -22.9, "lng": -43.1},
        "map_url": "/api/maps/route_1.html"
      }
    ],
    "map_url": "/api/maps/combined.html",
    "server_clusters": 3,
    "available_deliverers": [...]
  }
  
Frontend:
  - Renderiza cards de rotas
  - Mostra dropdown de entregadores
  - Ativa botão "Confirmar e Enviar"
```

---

## 🎨 UI Flow (React)

```jsx
RouteAnalysisView
  ├─ State:
  │  ├─ sessionId: "abc123"
  │  ├─ hasRomaneio: boolean
  │  ├─ importAnalysis: summary object
  │  ├─ routes: List[Route]
  │  └─ assignments: Dict[routeId → delivererId]
  │
  ├─ useEffect (init):
  │  ├─ GET /admin/team → deliverers
  │  └─ GET /session/state → restaura estado
  │
  ├─ Tab 1: Simple Analysis (não crítico)
  │
  └─ Tab 2: Import Romaneio (PRINCIPAL)
     ├─ [Upload Area]
     │  └─ input type=file
     │
     ├─ [Romaneios Listados] (NEW)
     │  ├─ Card: "1. vendas_marco.xlsx • 63 pacotes"
     │  │  └─ Botão ✕ (remover)
     │  └─ Card: "2. devolucoes.pdf • 12 pacotes"
     │     └─ Botão ✕ (remover)
     │
     ├─ [Botões de Ação]
     │  ├─ "+ Mais" (upload adicional)
     │  ├─ "Relatório" (recarregar análise)
     │  └─ "❌ Cancelar" (limpar tudo)
     │
     ├─ [Otimização]
     │  ├─ Input: "Quantos entregadores?"
     │  └─ Button: "🚀 Otimizar Rotas"
     │
     └─ [Atribuição & Envio]
        ├─ Card por rota com dropdown
        └─ Button: "Confirmar e Enviar"
```

---

## ✅ Checklist de Funcionamento

- [x] `GET /session/state` retorna estado completo
- [x] `POST /romaneio/import` rastreia `filename`
- [x] Frontend exibe lista de romaneios com remoção
- [x] Multi-import funciona (append à sessão)
- [x] `POST /routes/optimize` recebe `session_id`
- [x] Backend usa correto `session_id` para otimizar
- [x] `SessionManager.assign_route()` implementado
- [x] Persistência salva `filename` (JSON + PostgreSQL)
- [x] Cross-device sync via `/session/state`
- [x] Cancel-import limpa romaneios/rotas

---

## 🧪 Exemplos de Uso

### **Teste Local (curl)**
```bash
# 1. Restaurar estado
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/session/state | jq

# 2. Importar romaneio
curl -F "file=@vendas.xlsx" \
  -F "route_value=500" \
  http://localhost:8000/api/romaneio/import | jq

# 3. Listar romaneios
curl http://localhost:8000/api/romaneio/session/abc123/summary | jq

# 4. Otimizar rotas (com session_id)
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "num_deliverers": 3,
    "session_id": "abc123"
  }' \
  http://localhost:8000/api/routes/optimize | jq

# 5. Atribuir rota
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "route_id": "ROTA_1",
    "deliverer_id": 12345
  }' \
  http://localhost:8000/api/routes/assign | jq

# 6. Cancelar importação
curl -X POST \
  http://localhost:8000/api/session/cancel-import | jq
```

---

## 📊 Performance

| Operação | Tempo | Bottleneck |
|----------|-------|-----------|
| Geocodificação (Google) | 3-5s/endereço | Depende de quota |
| K-Means clustering (100 pontos) | ~200ms | CPU |
| OSRM distance matrix (50 coords) | ~500ms | Rede + Cache |
| TSP (2-opt heuristic) | ~100ms | CPU |
| Persistência (PostgreSQL) | ~50ms | I/O |
| Frontend re-render (lista) | <16ms | React optimization |

---

## 🚨 Possíveis Erros e Soluções

| Erro | Causa | Solução |
|------|-------|--------|
| "Nenhum romaneio importado" | `/session/state` não chamado | ✅ Agora restaura automático |
| "Falha ao otimizar" | `session_id` nulo | ✅ Frontend passou, backend recebe |
| "Rota não encontrada" | `route_id` inválido | Validar IDs antes de atribuir |
| Romaneios perdidos | Sem persistência | ✅ PostgreSQL + JSON backup |
| Filename nulo | Campo não serializado | ✅ JSON + DB agora salvam |

---

## 🔮 Roadmap Futuro

1. **Renomear romaneio** (UI: duplo clique no nome)
2. **Preview de endereços** (expandir card do romaneio)
3. **Merge manual** (combinar romaneios antes de otimizar)
4. **Histórico de assignments** (quem fez, quando, mudanças)
5. **Export em PDF** com turn-by-turn directions
6. **Rastreamento em tempo real** (Telegram + mapa live)
7. **Análise pós-entrega** (tempo real, distância, eficiência)
8. **Split de rota** (se entregador não conseguir completar)
