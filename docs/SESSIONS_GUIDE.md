## 🚀 Sistema de Gerenciamento de Sessões de Entrega

Implementado: **Motor de Sessões Permapersistente + OCR para Códigos de Barras**

---

## 📋 Guia de Uso

### 1️⃣ Instalação das Dependências

```bash
pip install -r requirements.txt
```

### 2️⃣ Setup do Banco de Dados

#### PostgreSQL em Produção (Railway)

```bash
# Configure a variável de ambiente DATABASE_URL
# Exemplo Railway:
# postgresql://user:password@container-host:5432/railway

# Rode as migrations
python migrate.py
```

#### PostgreSQL Localmente (Dev)

```bash
# Instale PostgreSQL se não tiver

# Windows PowerShell:
$env:DATABASE_URL='postgresql://postgres:password@localhost:5432/botentregador'
python migrate.py

# Linux/Mac:
export DATABASE_URL='postgresql://postgres:password@localhost:5432/botentregador'
python migrate.py
```

---

## 🎯 Endpoints da API

### Criar Nova Sessão
```bash
POST /api/sessions/create
{
    "user_id": 123,
    "session_type": "manual",
    "file_name": "romaneiro_segunda.csv"
}
```

### Adicionar Pacotes à Sessão
```bash
POST /api/sessions/{session_id}/packages
{
    "packages": [
        {
            "barcode": "1234567890123",
            "recipient_name": "João Silva",
            "address": "Rua X, 123",
            "value": 50.00
        },
        ...
    ]
}
```

### Reutilizar Sessão (Não Iniciada)
```bash
POST /api/sessions/{session_id}/reuse
{
    "new_packages": [
        {"barcode": "...", "recipient_name": "..."},
        ...
    ]
}
```

### Iniciar Sessão com Distribuição
```bash
POST /api/sessions/{session_id}/start
{
    "deliverer_ids": [123, 456, 789]
}
```

### Marcar Entrega Completa
```bash
POST /api/sessions/{session_id}/delivery/complete
{
    "package_id": "pkg-uuid",
    "deliverer_id": 123,
    "delivery_notes": "Entregue na portaria"
}
```

### Finalizar Sessão (Histórico)
```bash
POST /api/sessions/{session_id}/complete
```

### Obter Sessão Completa (Real-time)
```bash
GET /api/sessions/{session_id}
```

### Listar Sessões do Usuário
```bash
GET /api/sessions/user/{user_id}?status=open
```

### Scanner OCR para Código de Barras
```bash
POST /api/sessions/{session_id}/scan-barcode
FormData:
    file: <imagem da câmera>
```

### Dashboard Real-time
```bash
GET /api/sessions/{session_id}/dashboard
```

---

## 🤖 Comandos do Telegram Bot

```
/sessions          - Menu principal de gerenciamento
/start_session     - Iniciar uma sessão
/session_dashboard - Ver dashboard de uma sessão
```

### Fluxo no Telegram:

1. **`/sessions`** → Menu com 4 opções
   - ➕ Nova Sessão
   - 📂 Minhas Sessões
   - 🔄 Reutilizar
   - 📊 Dashboard

2. **Criar Nova Sessão** → Retorna `session_id`

3. **Enviar Pacotes** → Via Telegram ou API

4. **`/start_session`** → Pede lista de entregadores (IDs separados por vírgula)

5. **Entregas em andamento** → `/session_dashboard` mostra progresso

6. **Finalizar** → Sessão vira read-only com `financial_snapshot`

---

## 🔥 Sistema de OCR para Códigos de Barras

Quando a câmera falha, o sistema tenta **3 métodos em cascata**:

### Método 1: ZBar (Rápido)
- Decodifica QR codes e códigos de barras diretos
- 95% confiança se funcionar

### Método 2: Tesseract OCR (Preciso)
- Extrai texto via OCR
- Procura por sequências de números

### Método 3: ML Template Matching
- Detecta padrão branco/preto de código de barras
- Funciona com câmera ruim/borrada

### Uso:

```bash
POST /api/sessions/{session_id}/scan-barcode
Content-Type: multipart/form-data
file: <imagem base64 ou arquivo JPG/PNG>
```

Retorno:
```json
{
    "success": true,
    "barcode": "1234567890123",
    "package_found": true,
    "package_id": "pkg-uuid",
    "metadata": {
        "method": "tesseract_ocr",
        "confidence": 75,
        "raw_text": "..."
    }
}
```

---

## 💾 Estrutura de Dados

### DeliverySession (Sessão)
```
- session_id: UUID única
- user_id: FK para usuário
- status: OPEN → ACTIVE → COMPLETED → ARCHIVED
- created_at, started_at, completed_at, archived_at
- total_packages, total_deliverers
- total_cost, total_revenue, total_profit
- financial_snapshot: JSON (snapshot pós-completion)
- is_readonly: Flag pós-completion
- was_reused, reuse_count: Rastreamento de reutilização
```

### SessionPackage (Pacote)
```
- package_id: UUID
- session_id: FK
- barcode: Código de barras
- address_id: FK para endereço
- assigned_deliverer_id: FK para entregador
- delivery_status: pending → picked_up → delivered → failed
- package_value, delivery_fee
- barcode_ocr_attempt: Flag se usou OCR
```

### SessionDeliverer (Performance)
```
- session_id + deliverer_id: Chave composta
- packages_assigned, packages_delivered
- base_salary, commission_per_delivery
- total_earned: Auto-calculado
- route_optimization: JSON
```

### SessionAddress (Endereço)
```
- address_id: UUID
- session_id: FK
- address: String do endereço
- latitude, longitude
- geocoding_cache: JSON (cache de chamadas geolocalização)
- package_count
```

### SessionAudit (Auditoria Imutável)
```
- session_id: FK
- action: Tipo de ação
- actor_id: Quem fez
- details: JSON com contexto
- created_at: Timestamp
```

---

## 📊 Estados da Sessão

```
OPEN ────────→ ACTIVE ────────→ COMPLETED ────────→ ARCHIVED
↓                   ↓                   ↓                   ↓
Vazia          Entregas         Finalizada         Histórico
Pode             em              Gera               Read-only
reutilizar      progresso       snapshot           Consultável
```

---

## 🎯 Checklist de Implementação

- ✅ Schema PostgreSQL com 5 tabelas linkadas
- ✅ SessionEngine com ciclo de vida completo
- ✅ Barcode OCR Service (3 métodos)
- ✅ API REST completa (CRUD + scanner)
- ✅ Handlers Telegram integrados
- ✅ Migrations Alembic prontas
- ✅ Real-time dashboard
- ⏳ WebSocket para atualizações em tempo real (próximo)
- ⏳ Integração com roteamento genético (próximo)

---

## 🐛 Troubleshooting

### Erro: `DATABASE_URL não configurada`
```bash
# Windows PowerShell:
$env:DATABASE_URL='postgresql://...'

# Linux/Mac:
export DATABASE_URL='postgresql://...'
```

### Erro: `TELEGRAM_BOT_TOKEN vazio`
```bash
$env:TELEGRAM_BOT_TOKEN='seu_token_aqui'
```

### OCR não funciona
1. Instale Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
2. Adicione ao PATH
3. Verifique: `tesseract --version`

### PostgreSQL recusa conexão
```bash
# Verifique se está rodando:
# Windows: services.msc → PostgreSQL
# Linux: sudo systemctl status postgresql
# Mac: brew services list | grep postgres
```

---

## 🚀 Deploy no Railway

1. Push para GitHub
2. Conecte repositório no Railway
3. Configure variáveis:
   ```
   DATABASE_URL=postgresql://...
   TELEGRAM_BOT_TOKEN=...
   ADMIN_TELEGRAM_ID=...
   ```
4. Escolha Python como linguagem
5. Build command: `pip install -r requirements.txt && python migrate.py`
6. Start command: `python main_hybrid.py`

---

**Implementação: Enzo 🔥 | Data: 31/01/2026**
