# 🤖 Deploy do Bot no Servidor M21s (Termux)

## 🎯 Objetivo
Rodar o Bot de Entregas 24/7 no seu servidor caseiro Samsung M21s usando PM2 para alta disponibilidade.

---

## 📋 Pré-requisitos no Servidor

Verifique se já tem instalado (segundo sua doc, você já tem):
- ✅ Python 3.x
- ✅ Git
- ✅ PM2 (Node.js)
- ✅ Termux:Boot (para iniciar após reboot)

---

## 🚀 Passo a Passo do Deploy

### 1. Conectar ao Servidor

**Via Browser:**
```
https://terminal.henriquedejesus.dev
```

**Ou via SSH Local:**
```bash
ssh -p 8022 u0_a123@192.168.x.x
```

---

### 2. Clonar o Repositório

```bash
cd ~
git clone https://github.com/henrique-jfp/BotEntregador.git
cd BotEntregador
```

---

### 3. Criar Ambiente Virtual Python

```bash
# Instalar virtualenv se não tiver
pip install virtualenv

# Criar venv
python -m venv .venv

# Ativar (Termux)
source .venv/bin/activate
```

---

### 4. Instalar Dependências

```bash
pip install -r requirements.txt
```

**⚠️ Possíveis Problemas no Termux ARM64:**

Se alguma lib falhar (ex: Pillow, numpy), instale via apt primeiro:
```bash
pkg install python-pillow python-numpy
pip install -r requirements.txt --no-build-isolation
```

---

### 5. Configurar Variáveis de Ambiente

**Opção A: Arquivo .env (Recomendado)**

```bash
nano .env
```

Cole e configure:
```bash
TELEGRAM_BOT_TOKEN=seu_token_aqui
ADMIN_TELEGRAM_ID=seu_id_aqui
GOOGLE_API_KEY=sua_chave_google_opcional
```

Salve: `CTRL+X` → `Y` → `ENTER`

**Opção B: Variáveis no Shell (Temporário)**

```bash
export TELEGRAM_BOT_TOKEN="seu_token"
export ADMIN_TELEGRAM_ID="seu_id"
```

---

### 6. Testar o Bot Manualmente

```bash
# Com venv ativado
python main_multidelivery.py
```

Deve aparecer:
```
🚀 Bot iniciado! (Tentativa 1/5)
✅ Admin ID configurado: xxxxx
✅ Token presente: 1234567890...
INFO: Application started
```

Teste no Telegram: `/start`

Se funcionar, **CTRL+C** para parar.

---

### 7. Configurar PM2 para Rodar 24/7

#### A. Desativar venv (PM2 não funciona bem com venv ativado)

```bash
deactivate
```

#### B. Criar Script Wrapper

Crie um script que ativa o venv automaticamente:

```bash
nano start_bot.sh
```

Cole:
```bash
#!/data/data/com.termux/files/usr/bin/bash
cd ~/BotEntregador
source .venv/bin/activate
python main_multidelivery.py
```

Torne executável:
```bash
chmod +x start_bot.sh
```

#### C. Iniciar com PM2

```bash
pm2 start start_bot.sh \
  --name "bot-entregas" \
  --interpreter bash \
  --log ~/logs/bot-entregas.log \
  --error ~/logs/bot-entregas-error.log
```

**Ou usando Python diretamente (recomendado):**

```bash
pm2 start ~/BotEntregador/.venv/bin/python \
  --name "bot-entregas" \
  --interpreter none \
  -- ~/BotEntregador/main_multidelivery.py
```

---

### 8. Verificar Status

```bash
pm2 list
```

Deve aparecer:
```
┌─────┬──────────────────┬─────────┬─────────┬─────────┬──────────┐
│ id  │ name             │ status  │ restart │ uptime  │ cpu      │
├─────┼──────────────────┼─────────┼─────────┼─────────┼──────────┤
│ 0   │ bot-entregas     │ online  │ 0       │ 5m      │ 0%       │
└─────┴──────────────────┴─────────┴─────────┴─────────┴──────────┘
```

**Status:** `online` ✅

---

### 9. Ver Logs em Tempo Real

```bash
# Todos os logs
pm2 logs

# Só do bot
pm2 logs bot-entregas

# Últimas 100 linhas
pm2 logs bot-entregas --lines 100
```

---

### 10. Salvar Configuração (Boot Automático)

**ESSENCIAL** para o bot voltar após reboot:

```bash
pm2 save
```

Isso salva a lista de processos em `~/.pm2/dump.pm2`

---

### 11. Configurar Boot Automático

#### A. Editar Script de Boot

```bash
nano ~/.termux/boot/start-server.sh
```

Adicione no final (se ainda não tiver):
```bash
# Restaurar processos PM2
pm2 resurrect
```

#### B. Testar (Reinicie o celular)

1. Reinicie o celular
2. Aguarde 2-3 minutos
3. Verifique: `pm2 list`

O bot deve estar `online` automaticamente!

---

## 🎛️ Comandos de Gerenciamento

### Controle do Bot
```bash
pm2 restart bot-entregas    # Reiniciar
pm2 stop bot-entregas        # Parar
pm2 start bot-entregas       # Iniciar
pm2 delete bot-entregas      # Remover (cuidado!)
```

### Monitoramento
```bash
pm2 monit                    # Dashboard interativo
pm2 logs bot-entregas        # Logs em tempo real
pm2 info bot-entregas        # Informações detalhadas
```

### Atualizar Bot
```bash
cd ~/BotEntregador
pm2 stop bot-entregas
git pull origin main
pip install -r requirements.txt
pm2 restart bot-entregas
pm2 save
```

---

## 🔧 Configurações Avançadas

### 1. Auto-Restart em Caso de Crash

PM2 já faz isso por padrão! Mas você pode configurar:

```bash
pm2 start start_bot.sh \
  --name "bot-entregas" \
  --max-restarts 10 \
  --min-uptime 5000
```

### 2. Configuração via Ecosystem File

Crie `ecosystem.config.js`:

```bash
nano ~/BotEntregador/ecosystem.config.js
```

Cole:
```javascript
module.exports = {
  apps: [{
    name: 'bot-entregas',
    script: './main_multidelivery.py',
    interpreter: './.venv/bin/python',
    cwd: '/data/data/com.termux/files/home/BotEntregador',
    instances: 1,
    autorestart: true,
    watch: false,
    max_restarts: 10,
    min_uptime: 5000,
    env: {
      NODE_ENV: 'production'
    },
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    error_file: '~/logs/bot-entregas-error.log',
    out_file: '~/logs/bot-entregas-out.log',
    merge_logs: true
  }]
};
```

Inicie com:
```bash
pm2 start ecosystem.config.js
pm2 save
```

### 3. Limite de Memória

Se o bot usar muita RAM:

```bash
pm2 start main_multidelivery.py \
  --name "bot-entregas" \
  --max-memory-restart 500M
```

### 4. Rotação de Logs

Evita que logs fiquem gigantes:

```bash
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
```

---

## 📊 Monitoramento e Alertas

### 1. Status via Telegram

Adicione este comando no bot para você verificar status:

```bash
# No seu PC/celular
ssh -p 8022 henrique@terminal.henriquedejesus.dev "pm2 jlist"
```

### 2. Webhook de Status (Opcional)

Crie um script de monitoramento:

```bash
nano ~/monitor_bot.sh
```

```bash
#!/data/data/com.termux/files/usr/bin/bash

STATUS=$(pm2 jlist | jq '.[0].pm2_env.status' -r)

if [ "$STATUS" != "online" ]; then
    # Enviar alerta para você
    curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
        -d "chat_id=$ADMIN_TELEGRAM_ID" \
        -d "text=⚠️ Bot de Entregas OFFLINE no servidor M21s!"
fi
```

Execute via cron (Termux):
```bash
pkg install cronie
crontab -e

# Adicione:
*/5 * * * * ~/monitor_bot.sh
```

---

## ⚡ Otimizações para ARM64

### 1. Bibliotecas Pesadas

Se alguma lib estiver lenta (ex: numpy, pandas):

```bash
# Use versões otimizadas para ARM
pkg install openblas
pip install numpy --no-binary numpy
```

### 2. Geocoding Cache

O bot já tem cache, mas garanta que está ativo:
- Arquivo: `data/geocoding_cache.json`
- Benefício: Economiza API calls e RAM

### 3. Limpeza de Mapas

Adicione ao cron para limpar mapas antigos:

```bash
crontab -e

# Todo dia às 3h da manhã
0 3 * * * cd ~/BotEntregador && rm -f map_*.html
```

---

## 🐛 Troubleshooting

### Bot não inicia no PM2
```bash
# Verifique o erro
pm2 logs bot-entregas --err

# Teste manualmente
cd ~/BotEntregador
source .venv/bin/activate
python main_multidelivery.py
```

### Bot trava após algumas horas
```bash
# Pode ser falta de memória
pm2 restart bot-entregas --update-env --max-memory-restart 400M
```

### Conflito de múltiplas instâncias
```bash
# Mate todos os processos Python
pkill -9 python
pm2 delete all
pm2 start ecosystem.config.js
pm2 save
```

### Variáveis de ambiente não carregam
```bash
# Adicione ao ecosystem.config.js na seção env:
env: {
  TELEGRAM_BOT_TOKEN: 'seu_token',
  ADMIN_TELEGRAM_ID: 'seu_id'
}
```

### Bot não volta após reboot
```bash
# Verifique se pm2 resurrect está no boot
cat ~/.termux/boot/start-server.sh | grep resurrect

# Se não estiver, adicione
echo "pm2 resurrect" >> ~/.termux/boot/start-server.sh
```

---

## 📱 Acesso Remoto ao Bot

### Via Cloudflare Tunnel (Já configurado)

1. Acesse: `https://terminal.henriquedejesus.dev`
2. Faça login (GitHub OAuth)
3. Execute: `pm2 monit`

### Via App de Terminal (Android)

Use **Termux:Widget** para criar atalhos:

```bash
mkdir -p ~/.shortcuts
nano ~/.shortcuts/bot-status.sh
```

Cole:
```bash
#!/data/data/com.termux/files/usr/bin/bash
pm2 list
```

Agora você pode ver o status direto da tela inicial!

---

## 🔐 Segurança

### 1. Proteger .env
```bash
chmod 600 .env
```

### 2. Backup Automático

```bash
nano ~/backup_bot.sh
```

```bash
#!/data/data/com.termux/files/usr/bin/bash
cd ~
tar -czf bot-backup-$(date +%Y%m%d).tar.gz BotEntregador/data
# Manter só últimos 7 dias
find . -name "bot-backup-*.tar.gz" -mtime +7 -delete
```

Agende:
```bash
crontab -e
0 2 * * * ~/backup_bot.sh
```

---

## 📈 Consumo de Recursos

### Estimativa no M21s

| Recurso | Consumo Esperado |
|---------|------------------|
| RAM | ~150-250 MB |
| CPU | 1-5% (ocioso) / 15-30% (processando) |
| Bateria | ~3-5%/dia (com tela desligada) |
| Dados | ~50-200 MB/dia (depende do uso) |

### Verificar Uso Atual

```bash
# RAM
pm2 info bot-entregas | grep memory

# CPU
top -n 1 | grep python
```

---

## ✅ Checklist Final

- [ ] Bot clonado em `~/BotEntregador`
- [ ] Dependências instaladas (`.venv`)
- [ ] `.env` configurado com tokens
- [ ] Bot testado manualmente
- [ ] PM2 iniciado e `online`
- [ ] `pm2 save` executado
- [ ] Boot automático configurado (`pm2 resurrect`)
- [ ] Teste de reboot realizado
- [ ] Logs funcionando (`pm2 logs`)
- [ ] Monitor configurado (opcional)

---

## 🎉 Pronto!

Seu bot agora roda 24/7 no servidor M21s com:
- ✅ Auto-restart em caso de crash
- ✅ Reinício automático após reboot
- ✅ Logs persistentes
- ✅ Baixo consumo (3-5% bateria/dia)
- ✅ Monitoramento via PM2
- ✅ Acesso remoto via Cloudflare

**Uptime esperado:** 99.9%+ 🚀

---

## 📞 Suporte Rápido

### Ver se bot está rodando:
```bash
pm2 list
```

### Ver últimos logs:
```bash
pm2 logs bot-entregas --lines 50
```

### Reiniciar bot:
```bash
pm2 restart bot-entregas
```

### Atualizar código:
```bash
cd ~/BotEntregador && git pull && pm2 restart bot-entregas
```

---

**Última Atualização:** 14/12/2025  
**Versão do Guia:** 1.0  
**Servidor:** M21s (Termux)  
**Status:** ✅ Testado e Funcional
