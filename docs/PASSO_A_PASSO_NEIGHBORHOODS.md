# 🚀 PASSO A PASSO - SISTEMA DE ANÁLISE DE BAIRROS (NEIGHBORHOODS)

## ✅ Status Atual
- ✅ **Backend**: Router neighborhoods.py criado e testado
- ✅ **Frontend**: Componentes React criados (HeatmapDashboard.jsx, AnalyticsPage.jsx)
- ✅ **Dados**: GeoJSON da Zona Sul criado
- ✅ **Integração**: Router registrado em main_multidelivery.py
- ✅ **Git**: Código enviado para Railway

---

## 📋 ROTEIRO COMPLETO PASSO A PASSO

### FASE 1: VALIDAÇÃO LOCAL (SEM BANCO DE DADOS)

#### Passo 1.1: Verificar Imports
```bash
cd C:\BotEntregador
python -c "from bot_multidelivery.routers import neighborhoods; print('✅ OK')"
```
**Esperado:** `✅ OK`

#### Passo 1.2: Verificar Endpoints Registrados
```bash
python -c "from bot_multidelivery.routers import neighborhoods; print([r.path for r in neighborhoods.router.routes])"
```
**Esperado:** 
```
['/stats/neighborhoods', '/stats/neighborhoods/heatmap', '/stats/neighborhoods/{bairro}']
```

#### Passo 1.3: Verificar GeoJSON
```bash
python -c "import json; data = json.load(open('webapp/public/geojson/zona_sul_rio.json')); print(f'Bairros: {len(data[\"features\"])}')"
```
**Esperado:** `Bairros: 11`

---

### FASE 2: TESTES DE SINTAXE

#### Passo 2.1: Validar Arquivo neighborhoods.py
```bash
python -m py_compile bot_multidelivery/routers/neighborhoods.py
```
**Esperado:** Sem erros

#### Passo 2.2: Validar Arquivo main_multidelivery.py
```bash
python -m py_compile main_multidelivery.py
```
**Esperado:** Sem erros

---

### FASE 3: TESTES COM BANCO LOCAL (FALHA ESPERADA SEM DATABASE_URL)

#### Passo 3.1: Iniciar Servidor FastAPI em Dev
```bash
# Terminal 1
uvicorn main_multidelivery:app --reload --host 0.0.0.0 --port 8000
```

#### Passo 3.2: Testar Endpoints (vai retornar {} vazio - normal sem dados)
```bash
# Terminal 2 (ou novo terminal PowerShell)

# GET /stats/neighborhoods
curl -X GET "http://localhost:8000/api/stats/neighborhoods"
# Esperado: {} ou {"Copacabana": {...}} se houver dados

# GET /stats/neighborhoods/heatmap
curl -X GET "http://localhost:8000/api/stats/neighborhoods/heatmap"
# Esperado: [] ou [[lat, lng, intensity], ...] se houver dados

# GET /stats/neighborhoods/Copacabana
curl -X GET "http://localhost:8000/api/stats/neighborhoods/Copacabana"
# Esperado: {"error": "Bairro não encontrado"} ou dados se existirem
```

---

### FASE 4: VALIDAÇÃO FRONTEND

#### Passo 4.1: Instalar Dependências
```bash
cd C:\BotEntregador\webapp
npm install react-leaflet leaflet recharts
```

#### Passo 4.2: Verificar Componente React
```bash
# Validar sintaxe JSX
npm run build
# ou
npm run build:watch
```

#### Passo 4.3: Testar no Navegador
```bash
# Terminal npm dev
npm run dev

# Acessar: http://localhost:5173
# Ir para aba "Analytics" (se integrada no App.jsx)
# Mapa deve carregar (pode estar vazio sem dados)
```

---

### FASE 5: INTEGRAÇÃO NO APP.jsx

#### Passo 5.1: Adicionar Aba no App.jsx

Abrir `webapp/src/App.jsx` e adicionar:

```jsx
// Import
import AnalyticsPage from './pages/AnalyticsPage'

// No componente principal, adicionar botão de navegação:
<button 
  onClick={() => setActiveTab('analytics')}
  className="px-4 py-2 rounded"
>
  📊 Análise
</button>

// No switch de renderização:
case 'analytics':
  return <AnalyticsPage />
```

#### Passo 5.2: Testar no Navegador
- Clicar em "📊 Análise"
- Deve aparecer o mapa vazio (sem dados é normal)
- Testar interatividade: hover, click (modal)

---

### FASE 6: POPULAÇÃO DE DADOS DE TESTE

#### Passo 6.1: Criar Script de Seed (opcional)

Criar `scripts/seed_neighborhoods.py`:

```python
from bot_multidelivery.database import db_manager, PackageDB, DelivererDB
from datetime import datetime, timedelta
import random

bairros = [
    'Copacabana', 'Ipanema', 'Leblon', 'Lagoa', 
    'Jardim Botânico', 'Gávea', 'São Conrado', 
    'Laranjeiras', 'Flamengo', 'Botafogo', 'Urca'
]

bairro_coords = {
    'Copacabana': (-22.974, -43.182),
    'Ipanema': (-22.987, -43.204),
    # ... resto das coordenadas
}

with db_manager.get_session() as db:
    for i in range(100):
        bairro = random.choice(bairros)
        lat, lng = bairro_coords[bairro]
        
        package = PackageDB(
            id=f"test_{i}",
            session_id="test_session",
            address=f"Rua Test {i}, {bairro}",
            lat=lat + random.uniform(-0.01, 0.01),
            lng=lng + random.uniform(-0.01, 0.01),
            status=random.choice(['delivered', 'failed', 'pending']),
            neighborhood=bairro,
            assigned_to_telegram_id=123456789
        )
        db.add(package)
    db.commit()
    print("✅ 100 pacotes de teste criados")
```

#### Passo 6.2: Executar Script
```bash
python scripts/seed_neighborhoods.py
```

---

### FASE 7: TESTE COM DADOS REAIS (PÓS-DEPLOY NO RAILWAY)

#### Passo 7.1: Verificar Banco no Railway
- Acessar Dashboard Railway
- Confirmar PostgreSQL criado
- Verificar DATABASE_URL nas variables

#### Passo 7.2: Testar Endpoints em Produção
```bash
# Substituir por URL real do Railway
curl -X GET "https://seu-bot.railway.app/api/stats/neighborhoods"
```

#### Passo 7.3: Testar Frontend em Produção
- Acessar: https://seu-bot.railway.app
- Clicar em "📊 Análise"
- Deve aparecer mapa com dados reais

---

## 🎯 CHECKLIST FINAL

### Backend
- [ ] `bot_multidelivery/routers/neighborhoods.py` criado e testado
- [ ] 3 endpoints funcionando: `/neighborhoods`, `/neighborhoods/heatmap`, `/neighborhoods/{bairro}`
- [ ] Router registrado em `main_multidelivery.py`
- [ ] Sintaxe validada (python -m py_compile)
- [ ] Suporta queries com `start_date`, `end_date`
- [ ] Retorna coordenadas corretas para cada bairro

### Frontend
- [ ] `HeatmapDashboard.jsx` criado e importável
- [ ] `AnalyticsPage.jsx` criado
- [ ] Mapa Leaflet renderiza polígonos do GeoJSON
- [ ] Cores coroplético (volume → azul)
- [ ] Hover effects funcionam
- [ ] Click abre modal com detalhes
- [ ] Modal mostra gráfico de pizza (Recharts)
- [ ] Summary cards mostram KPIs

### Dados
- [ ] `webapp/public/geojson/zona_sul_rio.json` criado
- [ ] 11 bairros com coordenadas corretas
- [ ] Formato GeoJSON válido
- [ ] Arquivo acessível via HTTP

### Integração
- [ ] App.jsx adiciona aba "📊 Análise"
- [ ] Navegação funciona
- [ ] Componente renderiza sem erros
- [ ] Banco de dados conectado no Railway

---

## 🚨 TROUBLESHOOTING

### Erro: `ImportError: cannot import name 'SessionLocal'`
✅ **RESOLVIDO**: Usar `db_manager.get_session()` em vez de `SessionLocal()`

### Erro: GeoJSON não carrega
- Verificar caminho: `/geojson/zona_sul_rio.json`
- Validar JSON: `python -m json.tool webapp/public/geojson/zona_sul_rio.json`

### Erro: Mapa branco
- Verificar console do navegador (F12)
- Verificar Internet (tiles do OpenStreetMap precisam carregar)
- Verificar zoom inicial

### Erro: API retorna vazio
- Normal sem dados no banco
- Executar script de seed para testes
- No Railway, verificar se DATABASE_URL está configurada

---

## 📊 ENDPOINTS FINAIS

```
GET /api/stats/neighborhoods
- Retorna: Dict com todos os bairros
- Query: ?start_date=2026-01-01&end_date=2026-01-31

GET /api/stats/neighborhoods/heatmap?status=failed
- Retorna: Array de [lat, lng, intensity]
- Query: ?status=failed|delivered|pending

GET /api/stats/neighborhoods/Copacabana
- Retorna: Detalhes do bairro com breakdown de entregadores
```

---

## ✨ PRÓXIMAS MELHORIAS (APÓS DEPLOY)

1. **Heatmap Avançado**: Integrar leaflet-heatmap.js para visualização de densidade
2. **Análise Temporal**: Gráficos de série temporal
3. **Exportação**: PDF/CSV dos relatórios
4. **Real-time**: WebSocket para atualização automática
5. **Filtros**: Por date range, status, entregador
6. **Comparação**: Período anterior vs período atual

---

**Status**: 🟢 Pronto para Deploy no Railway
**Última Atualização**: 1 de fevereiro de 2026
