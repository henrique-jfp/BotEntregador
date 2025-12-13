# 🚀 DEPLOY NO RENDER - Bot Multi-Entregador

## ✅ Código enviado para GitHub!

**Commit**: `feat: Sistema multi-entregador com suporte a CSV, PDF e texto`
**Branch**: `main`
**Status**: Pushed ✅

---

## 🔧 CONFIGURAR NO RENDER

### Passo 1: Conectar Repositório

1. Acesse: https://dashboard.render.com
2. **New +** → **Web Service**
3. Conecte seu repositório: `henrique-jfp/BotEntregador`
4. Clique em **Connect**

### Passo 2: Configurações Básicas

```yaml
Name: bot-multidelivery
Region: Oregon (US West) ou São Paulo (mais próximo)
Branch: main
Runtime: Python 3
```

### Passo 3: Build & Start Commands

```bash
# Build Command
pip install -r requirements.txt

# Start Command
python main_multidelivery.py
```

### Passo 4: Plan

- Escolha: **Free** (suficiente para bot)
- Nota: Free tier dorme após 15 min de inatividade
  - Acorda automaticamente ao receber mensagem

### Passo 5: Environment Variables (OBRIGATÓRIO!)

Adicione estas variáveis em **Environment**:

```env
TELEGRAM_BOT_TOKEN=seu_token_aqui
ADMIN_TELEGRAM_ID=seu_telegram_id_aqui
GOOGLE_API_KEY=opcional
```

**Como obter:**
- `TELEGRAM_BOT_TOKEN`: Fale com @BotFather → `/newbot`
- `ADMIN_TELEGRAM_ID`: Fale com @userinfobot
- `GOOGLE_API_KEY`: Opcional (para geocoding futuro)

### Passo 6: Deploy

1. Clique **Create Web Service**
2. Aguarde build (~2-3 minutos)
3. Veja logs: "🚀 Bot iniciado! Suporta: texto, CSV, PDF"

---

## 🎯 VERIFICAR SE ESTÁ FUNCIONANDO

### No Telegram:

1. Abra chat com seu bot
2. Digite `/start`
3. Deve receber menu admin:

```
🔥 BOT ADMIN - Multi-Entregador

Bem-vindo, chefe! Escolha uma opção:

📦 Nova Sessão do Dia
📊 Status Atual
💰 Relatório Financeiro
```

### Nos Logs do Render:

Procure por:
```
🚀 Bot iniciado! Suporta: texto, CSV, PDF
```

---

## ⚙️ CONFIGURAÇÕES ADICIONAIS (Opcional)

### Auto-Deploy (Recomendado)

Em **Settings** → **Build & Deploy**:
- ✅ **Auto-Deploy**: Yes
  - Toda vez que fizer push, Render atualiza automaticamente

### Health Check

Em **Settings** → **Health & Alerts**:
- **Health Check Path**: Deixe vazio (não é web app HTTP)

### Notifications

Em **Settings** → **Notifications**:
- Configure email para alertas de deploy

---

## 🔍 TROUBLESHOOTING

### Bot não responde?

**1. Verifique variáveis de ambiente:**
```bash
# No dashboard Render → Environment
TELEGRAM_BOT_TOKEN=presente ✅
ADMIN_TELEGRAM_ID=presente ✅
```

**2. Veja logs:**
- Dashboard → Logs
- Procure por erros:
  ```
  ❌ TELEGRAM_BOT_TOKEN não configurado
  ❌ Invalid token
  ```

**3. Redeploy:**
- Manual Redeploy → **Clear build cache & deploy**

### Dependências faltando?

Se aparecer erro:
```
ModuleNotFoundError: No module named 'pdfplumber'
```

**Solução:**
1. Verifique `requirements.txt` tem:
   ```
   pdfplumber==0.11.0
   PyPDF2==3.0.1
   pytesseract==0.3.10
   pdf2image==1.17.0
   ```
2. Redeploy

### OCR não funciona (PDF escaneado)?

**Limitação**: Tesseract não está disponível no Render Free tier.

**Solução**:
- Use PDFs digitais (texto selecionável)
- Ou upgrade para plan pago + adicionar buildpack Tesseract

**Workaround atual**:
- Bot funciona 100% com texto manual e CSV
- PDFs digitais funcionam
- PDFs escaneados precisam Tesseract local

---

## 📊 MONITORAMENTO

### Logs em Tempo Real

```bash
# Dashboard → Logs
# Ou via CLI:
render logs -s bot-multidelivery --tail
```

### Métricas

- Dashboard → Metrics
- Veja:
  - CPU usage
  - Memory usage
  - Restarts

---

## 🔄 ATUALIZAR BOT (Futuro)

```bash
# Local
git add .
git commit -m "feat: nova funcionalidade"
git push origin main

# Render
# Se auto-deploy ativado: atualiza automaticamente
# Se não: Manual Deploy no dashboard
```

---

## 💰 CUSTOS

### Free Tier (Atual)

- ✅ **750 horas/mês grátis**
- ✅ Suficiente para 1 bot
- ⚠️ Dorme após 15 min inativo (acorda em ~30 segundos)
- ⚠️ 500 MB RAM limit

### Paid Plans (Opcional)

- **Starter ($7/mês)**:
  - Sem sleep
  - 512 MB RAM
  - Custom domains

- **Standard ($25/mês)**:
  - 2 GB RAM
  - Priority support

**Recomendação**: Comece com Free, upgrade se necessário.

---

## 🎯 PRÓXIMOS PASSOS

### 1. Teste Completo

```
1. /start
2. "📦 Nova Sessão do Dia"
3. Define base
4. Envia romaneios (texto/CSV/PDF)
5. /fechar_rota
6. Atribui rotas
7. Testa entregadores
```

### 2. Adicione Entregadores

Em `bot_multidelivery/config.py`:
```python
DELIVERY_PARTNERS = [
    DeliveryPartner(
        telegram_id=123456789,  # Telegram ID real
        name="João",
        is_partner=True
    ),
    # Adicione mais...
]
```

### 3. Configure Webhook (Opcional, mais eficiente)

Alternativa ao polling:
```python
# Adicione ao bot.py:
app.run_webhook(
    listen="0.0.0.0",
    port=int(os.getenv("PORT", 10000)),
    url_path=BotConfig.TELEGRAM_TOKEN,
    webhook_url=f"https://seu-app.onrender.com/{BotConfig.TELEGRAM_TOKEN}"
)
```

---

## 📚 DOCUMENTAÇÃO COMPLETA

- [MANUAL_COMPLETO.md](MANUAL_COMPLETO.md) - Manual de uso
- [FORMATOS_ROMANEIO.md](FORMATOS_ROMANEIO.md) - Formatos aceitos
- [QUICKSTART.md](QUICKSTART.md) - Setup rápido

---

## ✅ CHECKLIST DE DEPLOY

- [x] Código commitado
- [x] Push para GitHub
- [ ] Conectado no Render
- [ ] Variáveis de ambiente configuradas
- [ ] Build bem-sucedido
- [ ] Bot respondendo no Telegram
- [ ] Entregadores cadastrados
- [ ] Teste completo realizado

---

🚀 **Deploy pronto! Configure as variáveis no Render e teste!**
