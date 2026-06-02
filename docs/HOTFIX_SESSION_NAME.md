# 🔧 Hotfix: Campo session_name Muito Curto

## Problema Identificado

O banco de dados PostgreSQL estava rejeitando importações porque o campo `session_name` na tabela `sessions` estava definido como `VARCHAR(50)`, mas nomes de arquivo podem ter até 200+ caracteres.

**Erro:**
```
psycopg2.errors.StringDataRightTruncation: value too long for type character varying(50)
session_name: 'Romaneio: 29-01-2026 Henrique de jesus freitas pereira (1).xlsx' (63 caracteres)
```

## Solução Aplicada

### 1. Alteração no Schema
- **Arquivo:** `bot_multidelivery/database.py`
- **Mudança:** `session_name` de `VARCHAR(50)` → `VARCHAR(200)`

### 2. Migração Alembic
- **Arquivo:** `alembic/versions/002_fix_session_name.py`
- Criada migração para alterar coluna existente

### 3. Auto-Migration no Startup
- **Arquivo:** `main_multidelivery.py`
- Adicionada execução automática de `alembic upgrade head` no startup

## Como Aplicar (Railway)

### Opção 1: Deploy Automático (Recomendado)
```bash
git push origin main
# Railway detecta mudanças e aplica automaticamente
```

### Opção 2: Manual via Railway CLI
```bash
# No terminal do Railway
alembic upgrade head
```

### Opção 3: SQL Direto (Emergência)
```sql
-- Conectar no PostgreSQL do Railway
ALTER TABLE sessions ALTER COLUMN session_name TYPE VARCHAR(200);
```

## Verificação

Após deploy, teste importando um arquivo com nome longo:
```bash
# Arquivo: "Romaneio 2026-02-01 Nome Muito Longo Para Testar (1).xlsx"
# Deve funcionar sem erros
```

## Impacto

- ✅ **Zero Breaking Changes**: Apenas aumenta limite
- ✅ **Backward Compatible**: Nomes curtos continuam funcionando
- ✅ **Zero Downtime**: Migração rápida (ALTER COLUMN)

## Próximos Passos

Se ainda houver erros, verificar:
1. Outros campos de texto que podem estar muito curtos
2. Tamanho máximo de JSON (romaneios_data)
3. Logs de erros específicos no Railway
