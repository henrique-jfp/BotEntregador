# TROUBLESHOOTING - Telegram Bot Conflict

## Erro: "Conflict: terminated by other getUpdates request"

### O que significa?
Só **UMA** instância do bot pode rodar por vez. Você tem:
- Bot local rodando (seu computador)
- Bot no Render rodando
- OU webhook ativo (conflita com polling)

### Soluções (em ordem):

#### 1. PARE O BOT LOCAL
Se você iniciou o bot localmente para testar:

```powershell
# Procure processo Python rodando
Get-Process python | Where-Object {$_.Path -like "*BotEntregador*"}

# Mate o processo (substitua PID)
Stop-Process -Id <PID> -Force

# OU simplesmente feche o terminal que está rodando
```

#### 2. REMOVA WEBHOOK (se configurado)
Webhooks conflitam com polling (método do Render).

Execute este comando no Python:

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')

# Remove webhook
url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
params = {'drop_pending_updates': True}
response = requests.post(url, params=params)
print(response.json())
```

OU via curl/PowerShell:

```powershell
$TOKEN = "seu_token_aqui"
$url = "https://api.telegram.org/bot$TOKEN/deleteWebhook?drop_pending_updates=true"
Invoke-RestMethod -Uri $url -Method Post
```

#### 3. AGUARDE COOLDOWN (1-2 minutos)
Telegram API tem cooldown entre instâncias. Aguarde e Render vai reconectar automaticamente.

#### 4. REINICIE O SERVIÇO NO RENDER
Se nada funcionar:

1. Acesse: [Render Dashboard](https://dashboard.render.com)
2. Seu serviço → **Manual Deploy** → **Clear build cache & deploy**
3. Aguarde rebuild completo

### Como verificar se webhook está ativo?

```python
import requests
TOKEN = "seu_token"
url = f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
response = requests.get(url)
print(response.json())
```

Se retornar `"url": ""` → Sem webhook (OK para polling)  
Se retornar `"url": "https://..."` → Webhook ativo (CONFLITO)

### Modo correto no Render:
O bot deve usar **POLLING** (não webhook):

```python
# main_multidelivery.py
app.run_polling()  # ✅ Correto
# app.run_webhook()  # ❌ Não use no Render
```

### Checklist final:
- [ ] Bot local **não está rodando** (verifique Task Manager)
- [ ] Webhook **removido** (getWebhookInfo retorna url vazio)
- [ ] Aguardou **1-2 minutos** após parar bot local
- [ ] Render **redeployou** automaticamente
- [ ] Logs do Render mostram `Application started` sem erros

### Status do seu deploy ATUAL:
✅ Build: **SUCESSO**  
✅ Dependências: **Instaladas (aiohttp, openpyxl)**  
✅ Bot iniciado: **SIM**  
❌ Polling: **CONFLITO (outra instância)**

**Ação necessária:** Pare bot local ou remova webhook.

### Logs esperados após resolver:
```
INFO:bot_multidelivery.bot:🚀 Bot iniciado!
INFO:telegram.ext.Application:Application started
INFO:httpx:HTTP Request: POST https://api.telegram.org/.../getUpdates "HTTP/1.1 200 OK"
```

Se ver `200 OK` no getUpdates → **RESOLVIDO!**
