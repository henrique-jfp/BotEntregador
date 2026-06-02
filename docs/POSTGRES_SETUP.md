# 🗄️ CONFIGURAÇÃO DO POSTGRESQL NO RAILWAY

## ⚠️ PROBLEMA RESOLVIDO

O bot estava **perdendo todos os dados** (entregadores, rotas, sessões) toda vez que reiniciava porque o Railway **não persiste arquivos** entre deploys. Tudo que era salvo em `data/*.json` era apagado no próximo restart.

## ✅ SOLUÇÃO: PostgreSQL

Agora o bot usa **PostgreSQL** (banco de dados permanente) para guardar tudo:
- ✅ Entregadores cadastrados
- ✅ Sessões diárias com rotas
- ✅ Histórico de entregas
- ✅ Estatísticas e rankings

## 📋 PASSO A PASSO - CONFIGURAR NO RAILWAY

### 1️⃣ Criar Database no Railway

1. Acesse seu projeto no Railway
2. Clique em **"New"** → **"Database"** → **"Add PostgreSQL"**
3. O Railway vai criar o banco automaticamente
4. Aguarde a criação (leva ~30 segundos)

### 2️⃣ Conectar o Bot ao Database

1. No painel do Railway, clique no serviço **PostgreSQL** que você acabou de criar
2. Vá na aba **"Variables"**
3. Copie o valor da variável `DATABASE_URL` (algo como `postgresql://postgres:senha@hostname.railway.app:5432/railway`)

### 3️⃣ Configurar a Variável no Bot

1. Clique no serviço do **Bot** (não no PostgreSQL)
2. Vá na aba **"Variables"**
3. Clique em **"New Variable"**
4. Adicione:
   - **Nome**: `DATABASE_URL`
   - **Valor**: Cole a URL que você copiou do PostgreSQL

5. Clique em **"Add"**

### 4️⃣ Reiniciar o Bot

O bot vai reiniciar automaticamente quando você adicionar a variável. Você vai ver nos logs:

```
✅ PostgreSQL conectado com sucesso!
✅ DataStore usando PostgreSQL
✅ SessionStore usando PostgreSQL
```

## 🎯 VERIFICAR SE FUNCIONOU

Depois de configurar, teste:

1. `/add_entregador` - Cadastre um entregador
2. Reinicie o bot manualmente no Railway (Settings → Restart)
3. `/entregadores` - Deve mostrar o entregador que você cadastrou

Se aparecer o entregador, **FUNCIONOU!** 🎉

## 📝 NOTAS IMPORTANTES

### Fallback Automático
- Se `DATABASE_URL` não estiver configurada, o bot continua funcionando com JSON local
- Você verá nos logs: `📁 DataStore usando JSON local`
- **Mas os dados serão perdidos ao reiniciar**

### Migração dos Dados
- Os dados antigos em `data/deliverers.json` (se existirem) **NÃO são migrados automaticamente**
- Você precisará recadastrar os entregadores
- Ou posso criar um script de migração se necessário

### Custo
- PostgreSQL no Railway é **GRATUITO** no plano Hobby
- Limite: 1GB de storage (suficiente para milhares de entregas)

## 🆘 PROBLEMAS?

### "Database não está conectado"
- Verifique se a variável `DATABASE_URL` está correta
- Verifique se o serviço PostgreSQL está rodando no Railway

### "No module named 'psycopg2'"
- O requirements.txt já foi atualizado
- Força um redeploy: `git push` qualquer alteração

### Quer voltar para JSON?
- Remova a variável `DATABASE_URL` do Railway
- O bot volta automaticamente para o modo JSON

## 📊 PRÓXIMOS PASSOS OPCIONAIS

Se quiser, posso adicionar:
- ✨ Backup automático diário do banco
- 📈 Dashboard web para visualizar os dados
- 🔄 Script de migração dos dados antigos JSON → PostgreSQL
- 🧹 Limpeza automática de sessões antigas (> 30 dias)

Só me avisar! 🚀
