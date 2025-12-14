# 🚀 GUIA RÁPIDO - SE O BOT PAROU DE RESPONDER

## ⚡ Solução Rápida (1 minuto)

### Passo 1: Pare o Bot
```powershell
# Pressione CTRL+C no terminal onde o bot está rodando
```

### Passo 2: Verifique Status
```powershell
python monitor_bot.py
```

### Passo 3: Reinicie
```powershell
python main_multidelivery.py
```

## 🔍 O Que Foi Corrigido?

### ✅ Problemas Resolvidos:

1. **Timeouts ao enviar mapas HTML**
   - Adicionado timeout de 45s para envio de arquivos
   - Fallback automático para mensagem de texto se falhar
   - Verificação de tamanho (limite 20MB)

2. **Bot trava ao enviar múltiplos arquivos**
   - Adicionado delay de 0.5s entre envios
   - Evita rate limiting do Telegram
   - Melhor tratamento de erros de rede

3. **Sem retry automático**
   - Bot agora tenta reconectar até 5x
   - Espera progressiva: 5s, 10s, 15s, 20s, 25s
   - Logs detalhados de cada tentativa

4. **Logs confusos**
   - Emojis e mensagens claras
   - Indica sucesso (✅) ou falha (❌) de cada operação
   - Fácil identificar onde travou

## 📋 Checklist de Verificação

Antes de reiniciar o bot, verifique:

- [ ] ✅ Variáveis de ambiente configuradas
  ```powershell
  $env:TELEGRAM_BOT_TOKEN
  $env:ADMIN_TELEGRAM_ID
  ```

- [ ] ✅ Apenas uma instância do bot rodando
  ```powershell
  Get-Process python
  ```

- [ ] ✅ Conexão com internet OK
  ```powershell
  Test-Connection telegram.org
  ```

- [ ] ✅ Espaço em disco disponível
  ```powershell
  Get-PSDrive C
  ```

## 🎯 Comportamento Esperado Agora

### Quando funciona corretamente:

```
🚀 Bot iniciado! (Tentativa 1/5)
INFO:bot_multidelivery.bot:🚀 Bot iniciado! Suporta: texto, CSV, PDF + Deliverer Management
INFO:telegram.ext._application:Application started
```

### Ao enviar rotas:

```
INFO:bot_multidelivery.bot:✅ Mapa ROTA_1 enviado com sucesso
INFO:bot_multidelivery.bot:✅ Mapa ROTA_2 enviado com sucesso
```

### Se der timeout:

```
WARNING:bot_multidelivery.bot:⚠️ Timeout ao enviar mapa ROTA_1: Timeout. Enviando só texto...
```

### Se der erro de rede:

```
WARNING:bot_multidelivery.bot:⚠️ Erro de rede/timeout: Network Error
🔄 Tentando reconectar em 5 segundos... (Tentativa 1/5)
```

## 💡 Dicas Importantes

### 1. Arquivos HTML Grandes
Se os mapas estão muito grandes:
- **Divida em mais rotas** com menos pacotes
- Menos pacotes = mapa menor = envia mais rápido
- Recomendado: máximo 50-60 pacotes por rota

### 2. Conexão Lenta
Se sua internet está lenta:
- Bot vai tentar 5x antes de desistir
- Seja paciente, pode demorar 1-2 minutos
- Veja os logs para acompanhar progresso

### 3. Múltiplas Instâncias
Se aparecer erro `Conflict`:
- **PARE TODAS as instâncias do bot**
- Aguarde 1-2 minutos
- Inicie apenas uma nova instância

### 4. Rate Limiting
Se enviar muitas mensagens rápido:
- Bot agora espera 0.5s entre envios
- Evita ser bloqueado pelo Telegram
- Mais lento, mas mais confiável

## 🛠️ Ferramentas Disponíveis

### 1. Monitor de Status
```powershell
# Verifica se bot está online
python monitor_bot.py

# Envia mensagem de teste
python monitor_bot.py --test
```

### 2. Limpar Mapas Antigos
```powershell
# Remove todos mapas HTML
Remove-Item map_*.html -Force
```

### 3. Ver Processos Python
```powershell
# Lista todos processos Python
Get-Process python

# Matar processo específico
Stop-Process -Id 12345
```

## 📞 Quando Pedir Ajuda

Relate o problema com estas informações:

1. **Último log antes de travar:**
   ```
   [Cole aqui as últimas 10-20 linhas do log]
   ```

2. **Quantos pacotes estava processando:**
   - Total de entregas: ___
   - Número de rotas: ___

3. **Tamanho dos arquivos HTML:**
   ```powershell
   Get-ChildItem map_*.html | Select Name, @{N='Size(MB)';E={[math]::Round($_.Length/1MB,2)}}
   ```

4. **Status da conexão:**
   ```powershell
   Test-Connection telegram.org -Count 5
   ```

## 🎉 Próximos Passos

1. **Reinicie o bot** com as melhorias
2. **Teste com poucos dados** primeiro
3. **Monitore os logs** atentamente
4. **Reporte qualquer problema** com logs

## 📚 Documentação Completa

Para mais detalhes, consulte:
- [TROUBLESHOOTING_BOT_TRAVANDO.md](TROUBLESHOOTING_BOT_TRAVANDO.md) - Guia completo
- [MANUAL_COMPLETO.md](MANUAL_COMPLETO.md) - Manual do sistema
- [QUICKSTART.md](QUICKSTART.md) - Início rápido
