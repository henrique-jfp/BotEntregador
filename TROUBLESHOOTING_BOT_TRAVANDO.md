# 🔧 TROUBLESHOOTING - BOT PARANDO DE RESPONDER

## ⚠️ Problema: Bot Para de Responder

### Causas Comuns

1. **Arquivos HTML Muito Grandes**
   - Os mapas HTML podem ficar muito grandes (>20MB)
   - Telegram tem limite de 50MB para uploads
   - Solução: Reduzir quantidade de pacotes por rota

2. **Timeout na Rede**
   - Conexão lenta ou instável
   - Servidor Telegram sobrecarregado
   - Solução: Implementado retry automático

3. **Rate Limiting do Telegram**
   - Muitas mensagens enviadas rapidamente
   - Limite: ~30 mensagens/segundo
   - Solução: Adicionado delay de 0.5s entre envios

4. **Múltiplas Instâncias**
   - Conflito quando bot roda em 2+ lugares
   - Erro: `telegram.error.Conflict`
   - Solução: Pare todas instâncias e inicie apenas uma

## ✅ Soluções Implementadas

### 1. Timeouts Configurados
```python
- read_timeout=30s
- write_timeout=30s  
- connect_timeout=30s
- pool_timeout=30s
```

### 2. Verificação de Tamanho
- Arquivos >20MB não são enviados
- Fallback para mensagem com link local

### 3. Retry Automático
- Até 5 tentativas de reconexão
- Espera progressiva: 5s → 10s → 15s → 20s → 25s

### 4. Logging Detalhado
- Todos erros logados com contexto
- Fácil identificar onde travou

## 🔍 Como Diagnosticar

### 1. Verificar Status do Bot
```powershell
python monitor_bot.py
```

### 2. Enviar Mensagem de Teste
```powershell
python monitor_bot.py --test
```

### 3. Ver Logs em Tempo Real
```powershell
python main_multidelivery.py
# Observe os logs no console
```

### 4. Verificar Processos Python
```powershell
# Windows
Get-Process python

# Matar processo específico se necessário
Stop-Process -Id <PID>
```

## 🚀 Passos para Resolver

### Se o Bot Travou:

1. **Pare o bot** (CTRL+C)

2. **Verifique se há outras instâncias rodando:**
   ```powershell
   Get-Process python | Where-Object {$_.CommandLine -like "*main_multidelivery*"}
   ```

3. **Limpe mapas antigos (opcional):**
   ```powershell
   Remove-Item map_*.html -Force
   ```

4. **Reinicie o bot:**
   ```powershell
   python main_multidelivery.py
   ```

5. **Monitore os logs** para ver se está enviando mensagens

### Se Continuar Travando:

1. **Reduza o tamanho das rotas:**
   - Divida em mais rotas com menos pacotes
   - Menos pacotes = mapas HTML menores

2. **Verifique sua conexão:**
   ```powershell
   Test-Connection telegram.org
   ```

3. **Teste com importação menor:**
   - Use arquivo CSV com apenas 10-20 entregas
   - Verifique se funciona com poucos dados

4. **Verifique variáveis de ambiente:**
   ```powershell
   $env:TELEGRAM_BOT_TOKEN
   $env:ADMIN_TELEGRAM_ID
   ```

## 📊 Monitoramento Contínuo

### Script de Health Check
Crie um arquivo `health_check.ps1`:
```powershell
while ($true) {
    $date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$date] Verificando bot..."
    
    python monitor_bot.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Bot OK" -ForegroundColor Green
    } else {
        Write-Host "❌ Bot com problemas" -ForegroundColor Red
        # Opcional: reiniciar bot automaticamente
    }
    
    Start-Sleep -Seconds 60
}
```

## 🐛 Debug Avançado

### Ativar Modo Debug
Edite `bot_multidelivery/bot.py`:
```python
# Linha 17
logging.basicConfig(level=logging.DEBUG)  # Era INFO
```

### Testar Envio de Documento Manualmente
```python
import asyncio
from telegram import Bot

async def test():
    bot = Bot("SEU_TOKEN")
    with open("map_ROTA_1.html", "rb") as f:
        await bot.send_document(
            chat_id=123456789,  # Seu ID
            document=f,
            filename="teste.html",
            read_timeout=30,
            write_timeout=30
        )

asyncio.run(test())
```

## 📞 Suporte

Se o problema persistir:

1. Capture os últimos logs
2. Anote quando/como o bot travou
3. Verifique o tamanho dos arquivos HTML gerados
4. Teste com dados menores

## 🔄 Manutenção Preventiva

### Diariamente:
- Limpar mapas antigos: `Remove-Item map_*.html -Force`
- Verificar logs de erro
- Monitorar uso de memória

### Semanalmente:
- Atualizar dependências: `pip install -r requirements.txt --upgrade`
- Verificar espaço em disco
- Testar com dados reais

### Mensalmente:
- Revisar e otimizar código
- Atualizar bibliotecas
- Backup de dados
