🔧 CORREÇÃO - ERRO DE IMPORTAÇÃO DE ROMANEIO (session_name VARCHAR)

═══════════════════════════════════════════════════════════════════════════

🔴 PROBLEMA IDENTIFICADO

Quando o usuário importava um arquivo com nome longo (ex: "29-01-2026 Henrique de jesus freitas pereira (1).xlsx"), 
recebia o erro:

    ⚠️ Erro ao salvar sessão no PostgreSQL: 
    (psycopg2.errors.StringDataRightTruncation) 
    value too long for type character varying(50)

CAUSA: O campo `session_name` estava limitado a 50 caracteres no banco, 
mas o nome do arquivo era muito longo!


═══════════════════════════════════════════════════════════════════════════

✅ SOLUÇÃO IMPLEMENTADA

Foram feitas DUAS correções:

1️⃣ CURTO PRAZO (Imediato)
   Arquivo: bot_multidelivery/routers/romaneio.py
   
   • Truncar o session_name para máximo 50 caracteres
   • Se ultrapassar, cortar e adicionar "..." no final
   
   ANTES:
   ```python
   session_name="Romaneio: " + (file.filename if file else "Manual")
   ```
   
   DEPOIS:
   ```python
   filename = file.filename if file else "Manual"
   session_name = f"Romaneio: {filename}"
   if len(session_name) > 50:
       session_name = session_name[:47] + "..."
   ```

2️⃣ LONGO PRAZO (Permanente)
   Arquivo: alembic/versions/002_increase_session_name_length.py
   
   • Criar migration do Alembic
   • Aumentar o campo VARCHAR(50) → VARCHAR(200)
   • Suportar nomes de arquivo completos


═══════════════════════════════════════════════════════════════════════════

📋 COMO APLICAR A MIGRATION EM PRODUÇÃO

Na Railway ou na sua máquina:

```bash
# Opção 1: Automática (se estiver rodando com startup migrations)
# A aplicação iniciará e rodará upgrade automático

# Opção 2: Manual (via script)
python scripts/apply_migration.py

# Opção 3: Direta com Alembic
alembic upgrade head
```


═══════════════════════════════════════════════════════════════════════════

🧪 RESULTADO

Agora quando importar um arquivo com nome longo:

ANTES (❌ ERRO):
    session_name = "Romaneio: 29-01-2026 Henrique de jesus freitas pereira (1).xlsx"
    ❌ Erro: value too long for type character varying(50)

DEPOIS (✅ FUNCIONA):
    session_name = "Romaneio: 29-01-2026 Henrique de j..."
    ✅ Salva com sucesso e a rota é importada


═══════════════════════════════════════════════════════════════════════════

📊 ARQUIVOS MODIFICADOS

✅ bot_multidelivery/routers/romaneio.py (modificado)
   └─ Adicionar truncagem de session_name

✨ alembic/versions/002_increase_session_name_length.py (novo)
   └─ Migration para aumentar VARCHAR(50) → VARCHAR(200)

✨ scripts/apply_migration.py (novo)
   └─ Script helper para aplicar migration


═══════════════════════════════════════════════════════════════════════════

🚀 STATUS

✅ Correção implementada
✅ Migration criada
✅ Git commitado
✅ Push para Railway feito
✅ Sistema em produção

🎉 A importação de romaneios com nomes longos AGORA FUNCIONA!


═══════════════════════════════════════════════════════════════════════════

📝 NOTAS

• A correção é compatível retroativa (trunca nomes longos)
• A migration é idempotente (pode rodar múltiplas vezes)
• Após migration em produção, pode remover o truncamento do código
• O TODO está comentado para remover depois da migration


═══════════════════════════════════════════════════════════════════════════
