# 🗄️ SCHEMA COMPLETO DO BANCO DE DADOS

## 📊 ANÁLISE COMPLETA DO PROJETO

### ✅ O QUE JÁ ESTÁ SENDO SALVO (PostgreSQL):

1. **Entregadores** (`deliverers` table)
   - ✅ telegram_id (BigInteger)
   - ✅ name, is_partner, max_capacity
   - ✅ cost_per_package, is_active
   - ✅ total_deliveries, total_earnings
   - ✅ success_rate, average_delivery_time
   - ✅ joined_date

2. **Sessões** (`sessions` table) - PARCIALMENTE
   - ✅ session_id, date, created_at
   - ✅ base_address, base_lat, base_lng
   - ✅ is_finalized, finalized_at
   - ✅ romaneios_data (JSON)
   - ⚠️ **PROBLEMA**: Nome da sessão não segue padrão "Dia+Período"

3. **Rotas** (`routes` table)
   - ✅ id, session_id, assigned_to_telegram_id
   - ✅ assigned_to_name, color, map_file
   - ✅ optimized_order (JSON)
   - ✅ delivered_packages (JSON)

### ❌ O QUE NÃO ESTÁ SENDO SALVO (apenas JSON/memória):

1. **Dados Financeiros** (`financial_service.py`)
   - ❌ Fechamentos diários (revenue, costs, profit)
   - ❌ Fechamentos semanais (divisão de lucros)
   - ❌ Configuração de sócios (percentuais)
   - ❌ Histórico de pagamentos
   - 📁 Atualmente: `data/financial/daily/*.json` e `data/financial/weekly/*.json`

2. **Pagamentos** (`persistence.py`)
   - ❌ Registro de pagamentos por entregador
   - ❌ Status de pagamento (pago/pendente)
   - ❌ Método de pagamento
   - 📁 Atualmente: `data/payments/*.csv`

3. **Cache de Geocoding** (`geocoding_service.py`)
   - ❌ Endereços já geocodificados
   - ❌ Lat/lng armazenados
   - 📁 Atualmente: `data/geocoding_cache.json`

4. **Configurações do Bot**
   - ❌ Configuração de gamificação
   - ❌ Configuração de otimização genética
   - ❌ Configuração de escaneamento de códigos de barras
   - 📁 Atualmente: hardcoded ou em memória

5. **Histórico de Entregas** (`models.py` - Package)
   - ❌ Pacotes individuais com status
   - ❌ Tempo de entrega
   - ❌ Prioridade, notas
   - 📁 Atualmente: `data/packages.jsonl`

6. **Credenciais do Banco Inter**
   - ❌ Certificado, chave, conta
   - 📁 Atualmente: `data/bank_inter_credentials.json`

7. **Métricas de Performance**
   - ❌ Histórico detalhado de entregas
   - ❌ Taxa de sucesso por período
   - ❌ Distâncias percorridas
   - 📁 Atualmente: calculado on-the-fly

---

## 🎯 SCHEMA COMPLETO NECESSÁRIO

### 1. **Tabela: `deliverers`** ✅ (JÁ EXISTE)
```sql
CREATE TABLE deliverers (
    telegram_id BIGINT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    is_partner BOOLEAN DEFAULT FALSE,
    max_capacity INTEGER DEFAULT 50,
    cost_per_package FLOAT DEFAULT 1.0,
    is_active BOOLEAN DEFAULT TRUE,
    total_deliveries INTEGER DEFAULT 0,
    total_earnings FLOAT DEFAULT 0.0,
    success_rate FLOAT DEFAULT 100.0,
    average_delivery_time FLOAT DEFAULT 0.0,
    joined_date TIMESTAMP DEFAULT NOW()
);
```

### 2. **Tabela: `sessions`** ✅ (EXISTE, PRECISA MELHORAR)
```sql
CREATE TABLE sessions (
    session_id VARCHAR(20) PRIMARY KEY,
    session_name VARCHAR(50) NOT NULL,  -- 🆕 "Segunda Manhã", "Terça Tarde"
    date VARCHAR(10) NOT NULL,
    period VARCHAR(10),  -- 🆕 "manhã" ou "tarde"
    created_at TIMESTAMP DEFAULT NOW(),
    base_address VARCHAR(300),
    base_lat FLOAT,
    base_lng FLOAT,
    is_finalized BOOLEAN DEFAULT FALSE,
    finalized_at TIMESTAMP NULL,
    romaneios_data JSON,
    
    INDEX idx_date (date),
    INDEX idx_session_name (session_name)
);
```

### 3. **Tabela: `routes`** ✅ (JÁ EXISTE)
```sql
CREATE TABLE routes (
    id VARCHAR(50) PRIMARY KEY,
    session_id VARCHAR(20) REFERENCES sessions(session_id) ON DELETE CASCADE,
    assigned_to_telegram_id BIGINT REFERENCES deliverers(telegram_id),
    assigned_to_name VARCHAR(100),
    color VARCHAR(20),
    map_file VARCHAR(200),
    optimized_order JSON,
    delivered_packages JSON DEFAULT '[]',
    
    INDEX idx_session (session_id),
    INDEX idx_deliverer (assigned_to_telegram_id)
);
```

### 4. **Tabela: `packages`** 🆕 (NOVA)
```sql
CREATE TABLE packages (
    id VARCHAR(50) PRIMARY KEY,
    session_id VARCHAR(20) REFERENCES sessions(session_id),
    romaneio_id VARCHAR(50),
    route_id VARCHAR(50) REFERENCES routes(id),
    address TEXT NOT NULL,
    lat FLOAT NOT NULL,
    lng FLOAT NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',  -- low, normal, high, urgent
    status VARCHAR(20) DEFAULT 'pending',  -- pending, in_transit, delivered, failed
    assigned_to_telegram_id BIGINT REFERENCES deliverers(telegram_id),
    delivered_at TIMESTAMP NULL,
    delivery_time_minutes INTEGER NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_session (session_id),
    INDEX idx_route (route_id),
    INDEX idx_deliverer (assigned_to_telegram_id),
    INDEX idx_status (status),
    INDEX idx_delivered_at (delivered_at)
);
```

### 5. **Tabela: `daily_financial_reports`** 🆕 (NOVA)
```sql
CREATE TABLE daily_financial_reports (
    id SERIAL PRIMARY KEY,
    date VARCHAR(10) NOT NULL UNIQUE,
    revenue FLOAT NOT NULL,
    delivery_costs FLOAT NOT NULL,
    other_costs FLOAT DEFAULT 0.0,
    net_profit FLOAT NOT NULL,
    total_packages INTEGER NOT NULL,
    total_deliveries INTEGER NOT NULL,
    deliverer_breakdown JSON,  -- {nome: custo}
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_date (date)
);
```

### 6. **Tabela: `weekly_financial_reports`** 🆕 (NOVA)
```sql
CREATE TABLE weekly_financial_reports (
    id SERIAL PRIMARY KEY,
    week_start VARCHAR(10) NOT NULL,
    week_end VARCHAR(10) NOT NULL,
    total_revenue FLOAT NOT NULL,
    total_delivery_costs FLOAT NOT NULL,
    total_operational_costs FLOAT NOT NULL,
    gross_profit FLOAT NOT NULL,
    reserve_amount FLOAT NOT NULL,  -- 10% reserva
    distributable_profit FLOAT NOT NULL,  -- 90% para distribuir
    partner_1_share FLOAT NOT NULL,  -- 70% do distribuível
    partner_2_share FLOAT NOT NULL,  -- 30% do distribuível
    daily_reports JSON,  -- Lista de datas
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_week_start (week_start),
    UNIQUE(week_start, week_end)
);
```

### 7. **Tabela: `payment_records`** 🆕 (NOVA)
```sql
CREATE TABLE payment_records (
    id SERIAL PRIMARY KEY,
    deliverer_id BIGINT REFERENCES deliverers(telegram_id),
    deliverer_name VARCHAR(100),
    period_start VARCHAR(10) NOT NULL,
    period_end VARCHAR(10) NOT NULL,
    packages_delivered INTEGER NOT NULL,
    amount_due FLOAT NOT NULL,
    paid BOOLEAN DEFAULT FALSE,
    paid_at TIMESTAMP NULL,
    payment_method VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_deliverer (deliverer_id),
    INDEX idx_period (period_start, period_end),
    INDEX idx_paid (paid)
);
```

### 8. **Tabela: `partner_config`** 🆕 (NOVA)
```sql
CREATE TABLE partner_config (
    id INTEGER PRIMARY KEY DEFAULT 1,  -- Apenas 1 registro
    partner_1_name VARCHAR(100) NOT NULL,
    partner_1_share FLOAT NOT NULL,  -- 0.70 = 70%
    partner_2_name VARCHAR(100) NOT NULL,
    partner_2_share FLOAT NOT NULL,  -- 0.30 = 30%
    reserve_percentage FLOAT NOT NULL,  -- 0.10 = 10%
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CHECK (id = 1),  -- Garante apenas 1 registro
    CHECK (partner_1_share + partner_2_share = 1.0)
);
```

### 9. **Tabela: `geocoding_cache`** 🆕 (NOVA)
```sql
CREATE TABLE geocoding_cache (
    address VARCHAR(500) PRIMARY KEY,
    lat FLOAT NOT NULL,
    lng FLOAT NOT NULL,
    formatted_address TEXT,
    cached_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_coords (lat, lng)
);
```

### 10. **Tabela: `bot_config`** 🆕 (NOVA)
```sql
CREATE TABLE bot_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    value_type VARCHAR(20),  -- string, int, float, bool, json
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Exemplos de chaves:
-- 'gamification_enabled' (bool)
-- 'genetic_algorithm_generations' (int)
-- 'barcode_separator_colors' (json)
-- 'dashboard_refresh_interval' (int)
```

### 11. **Tabela: `performance_metrics`** 🆕 (NOVA)
```sql
CREATE TABLE performance_metrics (
    id SERIAL PRIMARY KEY,
    deliverer_id BIGINT REFERENCES deliverers(telegram_id),
    deliverer_name VARCHAR(100),
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    total_assigned INTEGER NOT NULL,
    total_delivered INTEGER NOT NULL,
    total_failed INTEGER NOT NULL,
    success_rate FLOAT NOT NULL,
    average_time_minutes FLOAT NOT NULL,
    fastest_delivery_minutes INTEGER,
    slowest_delivery_minutes INTEGER,
    total_distance_km FLOAT NOT NULL,
    complaints INTEGER DEFAULT 0,
    rating FLOAT DEFAULT 5.0,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_deliverer (deliverer_id),
    INDEX idx_period (period_start, period_end)
);
```

### 12. **Tabela: `bank_credentials`** 🆕 (NOVA - SEGURA)
```sql
CREATE TABLE bank_credentials (
    id INTEGER PRIMARY KEY DEFAULT 1,
    bank_name VARCHAR(50) NOT NULL,
    account_number VARCHAR(50),
    certificate_data TEXT,  -- Base64 encoded
    key_data TEXT,  -- Base64 encoded (encrypted)
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CHECK (id = 1)  -- Apenas 1 registro
);
```

---

## 🔄 MIGRAÇÃO E COMPATIBILIDADE

### Estratégia de Migração:

1. **Não quebrar dados existentes**
   - Manter tabelas atuais funcionando
   - Adicionar novas tabelas progressivamente

2. **Fallback automático**
   - Se PostgreSQL falhar, usar JSON
   - Logs detalhados de cada operação

3. **Sincronização inicial**
   - Migrar dados de JSON → PostgreSQL
   - Script de importação one-time

4. **Validação**
   - Testes unitários para cada tabela
   - Verificação de integridade referencial

---

## 📝 NOMENCLATURA DE SESSÕES

### Formato: **"[Dia da Semana] [Período]"**

**Exemplos:**
- "Segunda Manhã"
- "Segunda Tarde"
- "Terça Manhã"
- "Terça Tarde"
- "Quarta Manhã"
- etc.

### Implementação:
```python
from datetime import datetime

def generate_session_name(date: datetime, period: str) -> str:
    """
    Gera nome automático da sessão
    period: 'manhã' ou 'tarde'
    """
    days = {
        0: "Segunda",
        1: "Terça",
        2: "Quarta",
        3: "Quinta",
        4: "Sexta",
        5: "Sábado",
        6: "Domingo"
    }
    
    day_name = days[date.weekday()]
    return f"{day_name} {period.capitalize()}"

# Exemplo:
# generate_session_name(datetime(2024, 1, 29), "manhã") → "Segunda Manhã"
```

---

## 🎯 PRIORIDADE DE IMPLEMENTAÇÃO

### **FASE 1** (CRÍTICO - IMPLEMENTAR AGORA):
1. ✅ Adicionar campo `session_name` e `period` na tabela `sessions`
2. ✅ Criar função `generate_session_name()`
3. ✅ Atualizar `SessionManager` para usar nomenclatura automática
4. ✅ Migrar sessões existentes (adicionar nomes)

### **FASE 2** (IMPORTANTE):
5. 🆕 Criar tabela `packages` (histórico de entregas)
6. 🆕 Criar tabelas financeiras (`daily_financial_reports`, `weekly_financial_reports`, `partner_config`)
7. 🆕 Criar tabela `payment_records`

### **FASE 3** (OTIMIZAÇÃO):
8. 🆕 Criar tabela `geocoding_cache`
9. 🆕 Criar tabela `bot_config`
10. 🆕 Criar tabela `performance_metrics`

### **FASE 4** (SEGURANÇA):
11. 🆕 Criar tabela `bank_credentials` (encrypted)

---

## 🔒 CONSIDERAÇÕES DE SEGURANÇA

### Dados Sensíveis:
- ❗ **Credenciais bancárias**: Encriptar antes de salvar
- ❗ **IDs do Telegram**: BigInteger (já implementado)
- ❗ **Dados financeiros**: Acesso restrito

### Backup:
- PostgreSQL: Backup automático no Railway
- Fallback JSON: Manter como redundância temporária
- Exportação periódica: CSV/Excel para auditoria

---

## 📈 BENEFÍCIOS DO SCHEMA COMPLETO

✅ **Persistência Total**: Nenhum dado perdido em restarts  
✅ **Histórico Completo**: Análise de tendências e performance  
✅ **Relatórios Precisos**: Dados estruturados e confiáveis  
✅ **Escalabilidade**: Suporta crescimento do negócio  
✅ **Auditoria**: Rastreabilidade de todas as operações  
✅ **BI/Analytics**: Integração com ferramentas de análise  

---

## 🚀 PRÓXIMOS PASSOS

1. ✅ Atualizar `database.py` com todas as tabelas
2. ✅ Implementar `generate_session_name()`
3. ✅ Atualizar `SessionManager` e `SessionStore`
4. ✅ Migrar dados de JSON → PostgreSQL
5. ✅ Testar persistência completa
6. ✅ Adicionar logs detalhados
7. ✅ Documentar API de cada tabela
