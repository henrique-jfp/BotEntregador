# 🔄 FLUXO DE SESSÃO - Diagrama Completo

## Estados e Transições

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CICLO DE VIDA DA SESSÃO                      │
└─────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │   CREATED    │
                              │              │
                              │ Session ID   │
                              │ gerada       │
                              └──────┬───────┘
                                     │
                  create_session()    │
                                     │
                              ┌──────▼───────┐
                              │    OPENED    │
                              │              │
                    ┌─────────→│ Ready for    │◄────────────┐
                    │          │ reuse (SEM   │             │
                    │          │ re-import!)  │             │
                    │          └──────┬───────┘             │
                    │                 │                     │
                    │  open_session() │                     │
                    │    Se foi       │                     │
                    │  completada     │                     │
                    │                 │                     │
                    │          ┌──────▼───────┐             │
                    │          │   STARTED    │             │
                    │          │              │             │
                    │          │ Iniciou      │             │
                    │          │ distribuição │             │
                    │          └──────┬───────┘             │
                    │                 │                     │
                    │  start_session()│                     │
                    │                 │                     │
                    │          ┌──────▼──────────┐          │
                    │          │  IN_PROGRESS    │          │
                    │          │                 │          │
                    │          │ Entregas em     │          │
                    │          │ andamento       │          │
                    │          │ (Real-time      │          │
                    │          │ updates)        │          │
                    │          └──────┬──────────┘          │
                    │                 │                     │
                    │  update_progress()                    │
                    │                 │                     │
                    │          ┌──────▼──────────┐          │
                    │          │   COMPLETED     │          │
                    │          │                 │          │
                    │          │ Todas entregas  │          │
                    │          │ finalizadas     │          │
                    │          └──────┬──────────┘          │
                    │                 │                     │
                    │  complete_session()                   │
                    │                 │                     │
                    │          ┌──────▼──────────┐          │
                    │          │   READ_ONLY     │          │
                    │          │   (HISTÓRICO)   │          │
                    │          │                 │          │
                    │          │ ❄️ CONGELADA   │          │
                    │          │ 🔒 SEM EDIÇÃO  │          │
                    │          │ 📚 AUDITORIA   │          │
                    │          └─────────────────┘          │
                    │                                        │
                    └────────────────────────────────────────┘
                           (Pode reabirapenas
                            se retornar para OPENED)
```

---

## 📊 Fluxo de Dados Durante Sessão

```
┌──────────────────────────────────────────────────────────────────┐
│                    DADOS PERSISTIDOS EM CADA ESTÁGIO             │
└──────────────────────────────────────────────────────────────────┘

CREATED
├── session_id ✓
├── created_by ✓
├── manifest_data ✓
└── status: "created"

OPENED
├── [TUDO DO ANTERIOR]
├── addresses: [...] ✓
├── deliverers: [...] ✓
└── status: "opened"

STARTED
├── [TUDO DO ANTERIOR]
├── started_at: datetime ✓
└── status: "started"

IN_PROGRESS
├── [TUDO DO ANTERIOR]
├── route_assignments: [...] ✓
├── statistics: {...} ✓
├── last_updated: datetime ✓
└── status: "in_progress"

COMPLETED
├── [TUDO DO ANTERIOR]
├── financials: {
│   ├── total_profit ✓
│   ├── total_cost ✓
│   ├── total_salary ✓
│   └── net_margin ✓
├── completed_at: datetime ✓
└── status: "completed"

READ_ONLY (HISTÓRICO)
├── [TUDO DO ANTERIOR - IMUTÁVEL]
├── ❄️ Nenhuma alteração possível
├── 🔒 Apenas leitura
├── 📚 Completo para auditoria
└── status: "read_only"
```

---

## 💰 Fluxo de Cálculo Financeiro

```
┌─────────────────────────────────────────────────────────────┐
│            CÁLCULO DE FINANCEIRO - PASSO A PASSO            │
└─────────────────────────────────────────────────────────────┘

Input:
├── routes: [
│   ├── {id: "r1", total_value: 1000, total_km: 50}
│   └── {id: "r2", total_value: 800, total_km: 40}
└── deliverers: [
    ├── {id: "d1", name: "João", packages: 25, rate: 2.5}
    └── {id: "d2", name: "Maria", packages: 30, rate: 2.5}
    ]

Step 1: Calcular Lucro de Cada Rota
┌─────────────────────────────────────┐
│ Route 1: Valor R$ 1000              │
│   - Combustível (50km × 0.5): -$25 │
│   = Lucro: R$ 975 (97.5% margem)   │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ Route 2: Valor R$ 800               │
│   - Combustível (40km × 0.5): -$20 │
│   = Lucro: R$ 780 (97.5% margem)   │
└─────────────────────────────────────┘

Step 2: Calcular Salário de Cada Entregador
┌──────────────────────────────────────────┐
│ João: 25 packages × R$ 2.50 = R$ 62.50 │
└──────────────────────────────────────────┘
┌──────────────────────────────────────────┐
│ Maria: 30 packages × R$ 2.50 = R$ 75.00│
└──────────────────────────────────────────┘

Step 3: Resumo Financeiro Total
┌─────────────────────────────────────────────────────┐
│ Total de Rotas: R$ 1800                             │
│ Custos Totais: R$ 45                                │
│ Salários: R$ 137.50                                 │
│ ═════════════════════════════════════════════════   │
│ MARGEM LÍQUIDA: R$ 1617.50                          │
│ Percentual: 89.9%                                   │
└─────────────────────────────────────────────────────┘

Output:
├── summary: {
│   ├── total_route_value: 1800
│   ├── total_costs: 45
│   ├── total_salaries: 137.50
│   ├── net_margin: 1617.50
│   └── net_margin_percent: 89.9
├── routes: [route1_breakdown, route2_breakdown]
└── deliverers: [deliv1_breakdown, deliv2_breakdown]
```

---

## 📱 Fluxo Frontend - Scanner + Histórico

```
┌─────────────────────────────────────────────────────────┐
│              FLUXO FRONTEND - BARCODE SCANNER            │
└─────────────────────────────────────────────────────────┘

RouteAnalysisView
│
├─ [📷 Escanear Código]
│   │
│   └─→ BarcodeScanner Modal
│       │
│       ├─ TAB 1: Camera
│       │  ├─ getUserMedia()
│       │  ├─ Draw to Canvas
│       │  └─ Detect QR Code
│       │
│       ├─ TAB 2: Upload Image
│       │  ├─ File Input
│       │  ├─ Draw to Canvas
│       │  └─ OCR via Canvas
│       │
│       ├─ TAB 3: Manual Entry
│       │  ├─ Text Input
│       │  └─ Press ENTER
│       │
│       └─ [✓ Confirmar]
│           │
│           └─→ POST /api/process-barcodes
│               └─→ Backend processa

┌──────────────────────────────────────────────────────────┐
│           FLUXO FRONTEND - HISTORY VIEW                  │
└──────────────────────────────────────────────────────────┘

Navbar
│
├─ [📚 Histórico]
│   │
│   └─→ HistoryView
│       │
│       ├─ GET /api/history/sessions
│       │   ├─ Carrega todas READ_ONLY
│       │   └─ Parse JSON
│       │
│       ├─ Renderiza Cards
│       │   ├─ Status: READ_ONLY ✓
│       │   ├─ Financeiro: {profit, cost, salary}
│       │   ├─ Estatísticas: {...}
│       │   └─ Timestamps: {created, completed}
│       │
│       └─ [Expandir ▼]
│           ├─ Ver detalhes
│           ├─ Ver breakdown
│           └─ [📥 Exportar Relatório]
│               └─→ CSV download
```

---

## 🌐 Fluxo API - Endpoints

```
┌──────────────────────────────────────────────────────────────┐
│              API ENDPOINTS - FLUXO COMPLETO                  │
└──────────────────────────────────────────────────────────────┘

Session Lifecycle:
├─ POST /api/session/create
│   └─→ { session_id, status: "created" }
│
├─ GET /api/session/{id}
│   └─→ { session, addresses, deliverers, financials }
│
├─ POST /api/session/{id}/open
│   └─→ { status: "opened" }
│
├─ POST /api/session/{id}/start
│   └─→ { status: "started" }
│
├─ POST /api/session/{id}/complete
│   └─→ { status: "read_only" }
│
├─ GET /api/session/{id}/history
│   └─→ { status: "read_only", history_data }
│
└─ GET /api/session/list/all
    └─→ { sessions: [...] }

Financial Endpoints:
├─ POST /api/financials/calculate/session/{id}
│   ├─ Input: { routes, deliverers }
│   └─→ { summary, routes[], deliverers[] }
│
└─ GET /api/financials/session/{id}
    └─→ { financials: {...} }

History Endpoints:
└─ GET /api/history/sessions
    └─→ { sessions: [...read_only_only] }
```

---

## 🔒 Segurança - Fluxo de Validação

```
┌──────────────────────────────────────────────────────────┐
│         FLUXO DE VALIDAÇÃO E SEGURANÇA                   │
└──────────────────────────────────────────────────────────┘

1. REQUEST VALIDATION
   ├─ Verificar session_id (UUID válido)
   ├─ Verificar usuario autenticado
   └─ Validar payload JSON

2. STATE VALIDATION
   ├─ Verificar transição válida
   │  └─ CREATED → OPENED ✓
   │  └─ OPENED → STARTED ✓
   │  └─ STARTED → IN_PROGRESS ✓
   │  └─ IN_PROGRESS → COMPLETED ✓
   │  └─ COMPLETED → READ_ONLY ✓
   │  └─ Inverso? ❌ BLOQUEADO
   │
   └─ Verificar permissões
      └─ READ_ONLY? Apenas leitura

3. DATA VALIDATION
   ├─ routes: List[Dict]? ✓
   ├─ deliverers: List[Dict]? ✓
   ├─ financials: Dict? ✓
   └─ Campos obrigatórios preenchidos? ✓

4. IMMUTABILITY CHECK
   ├─ Status READ_ONLY?
   └─ Rejeitar POST/PUT/DELETE ❌

5. AUDIT LOGGING
   ├─ Log toda transição
   ├─ Timestamp de cada ação
   └─ Usuario responsável registrado
```

---

## 📈 Performance - Otimizações

```
┌────────────────────────────────────────────────────────┐
│          OTIMIZAÇÕES DE PERFORMANCE                    │
└────────────────────────────────────────────────────────┘

Database:
├─ Índice em sessions.id (PRIMARY KEY)
├─ Índice em sessions.status (para filtros)
├─ Índice em sessions.created_at (para ordenação)
└─ JSON columns para flexibilidade

API Response:
├─ Paginação: limit=50 por padrão
├─ Lazy loading em HistoryView
├─ Cache de cálculos financeiros
└─ Compressão GZIP habilitada

Frontend:
├─ Lazy loading de componentes
├─ Memoização de cálculos
├─ Virtual scrolling para listas longas
└─ Service workers para offline

Caching Strategy:
├─ GET /api/history/sessions → 5 minutos
├─ GET /api/financials/{id} → 10 minutos
└─ GET /api/session/{id} → 1 minuto
```

---

## 🎯 Casos de Uso Mapeados

```
┌─────────────────────────────────────────────────────────┐
│           CASOS DE USO - FLUXO REAL                     │
└─────────────────────────────────────────────────────────┘

Caso 1: Distribuição Normal (Segunda-feira)
├─ create_session("Seg 20/01")
├─ open_session()
├─ start_session()
├─ update_progress() [durante o dia]
├─ calculate_financials()
├─ complete_session()
└─ Status: READ_ONLY ✓

Caso 2: Sessão Interrompida (Quinta-feira)
├─ create_session("Qui 23/01")
├─ open_session()
├─ [PROBLEMA: Falta de combustível]
├─ [Retorna sexta-feira]
│
├─ get_session() ← DADOS SALVOS!
├─ open_session() ← REABRE SEM RE-IMPORT
├─ start_session() [continua do ponto]
├─ complete_session()
└─ Status: READ_ONLY ✓

Caso 3: Ajuste Financeiro (Após Fechamento)
├─ get_session(id) ← Recupera histórico
├─ [Consulta status: READ_ONLY]
├─ [Apenas LEITURA - sem edição]
└─ Exportar relatório em CSV

Caso 4: Análise de Lucro (Gerente)
├─ GET /api/history/sessions
├─ Filter: status=read_only
├─ [Visualiza 100 últimas sessões]
├─ [Analisa trend de margem]
└─ [Exporta para BI tool]
```

---

**✨ Tudo mapeado e pronto para rodar!**
