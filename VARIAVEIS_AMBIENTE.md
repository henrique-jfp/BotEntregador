# VARIAVEIS DE AMBIENTE - BOT ENTREGADOR

## Obrigatorias (Sistema nao funciona sem elas)

```env
# Telegram Bot Token
# Onde pegar: https://t.me/BotFather
# Como: /newbot -> segue instrucoes -> copia token
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# ID do Admin (seu Telegram ID numerico)
# Onde pegar: https://t.me/userinfobot
# Mande qualquer mensagem pro bot, ele retorna seu ID
ADMIN_TELEGRAM_ID=123456789
```

## Opcionais (Sistema funciona sem, mas com funcionalidades limitadas)

```env
# Google Cloud Vision API (OCR para PDFs escaneados)
# Onde pegar: https://console.cloud.google.com/apis/credentials
# 1. Crie projeto
# 2. Ative "Cloud Vision API"
# 3. Crie Service Account
# 4. Baixe JSON credentials
# 5. Coloque caminho aqui
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-vision.json

# Gemini AI (Previsao de tempo com IA generativa)
# Onde pegar: https://aistudio.google.com/app/apikey
# Opcional: sistema usa heuristica se nao tiver
GEMINI_API_KEY=AIzaSy...

# Porta do Dashboard WebSocket (padrao: 8765)
# Mudar se porta em uso
DASHBOARD_PORT=8765

# Ambiente (producao/desenvolvimento)
# Padrao: production
ENVIRONMENT=production
```

## Estrutura do .env (exemplo completo)

```env
# === OBRIGATORIO ===
TELEGRAM_TOKEN=6234567890:AAHdqTcvbXYqZ-xhmy0OffdV1LsO2vB9aaa
ADMIN_TELEGRAM_ID=987654321

# === OPCIONAL - APIs Externas ===
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-cloud-vision.json
GEMINI_API_KEY=AIzaSyBkXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# === OPCIONAL - Configuracoes ===
DASHBOARD_PORT=8765
ENVIRONMENT=production
DEBUG=false
```

## Como configurar no Render.com (Deploy)

1. Acesse: Dashboard -> Service -> Environment
2. Clique em "Add Environment Variable"
3. Adicione cada variavel:
   - Key: TELEGRAM_TOKEN
   - Value: seu_token_aqui
4. IMPORTANTE: Arquivos JSON (credentials) precisam ser:
   - Commitados no repo (nao recomendado)
   - OU configurados via Secret Files do Render
   - OU usar Service Account via variable de ambiente (conteudo JSON inline)

### Alternativa para GOOGLE_APPLICATION_CREDENTIALS no Render:

```env
# Cole o conteudo JSON completo em uma unica linha
GOOGLE_CLOUD_CREDENTIALS={"type":"service_account","project_id":"..."}
```

Depois no codigo Python:
```python
import json
import os
from google.oauth2 import service_account

# Le credentials da variavel de ambiente
creds_json = os.getenv('GOOGLE_CLOUD_CREDENTIALS')
if creds_json:
    creds_dict = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
```

## Como testar localmente

1. Copie `.env.example` para `.env`
2. Preencha com suas keys
3. Execute: `python main_multidelivery.py`
4. Bot deve iniciar sem erros

## Troubleshooting

### Erro: "TELEGRAM_TOKEN not found"
- Verifique se `.env` existe na raiz do projeto
- Verifique se python-dotenv esta instalado: `pip install python-dotenv`
- Verifique se `load_dotenv()` esta sendo chamado antes de `os.getenv()`

### Erro: "ModuleNotFoundError: No module named 'aiohttp'"
- Instale: `pip install aiohttp aiohttp-cors`
- Ou adicione ao requirements.txt

### Erro: Google Cloud Vision API
- Verifique se JSON credentials e valido
- Verifique se API esta ativada no console Google
- Verifique se billing esta configurado (API requer cartao)

### Dashboard nao abre
- Verifique se porta 8765 esta livre: `netstat -ano | findstr 8765`
- Tente mudar DASHBOARD_PORT para 8080 ou 3000
- Verifique firewall/antivirus

## Permissoes necessarias (Telegram Bot)

No BotFather, configure:
```
/setcommands
start - Menu principal
help - Ajuda completa
add_entregador - Cadastra novo entregador
entregadores - Lista entregadores
distribuir - Divide romaneio entre entregadores
ranking - Ranking de gamificacao
prever - Previsao de tempo com IA
fechar_rota - Fecha e divide rotas (legado)
```

## Seguranca

- NUNCA commite .env no Git
- Adicione `.env` no `.gitignore`
- Use secrets do Render para producao
- Rotacione tokens periodicamente
- Restrinja ADMIN_TELEGRAM_ID (apenas seu ID)

## Checklist pre-deploy

- [ ] TELEGRAM_TOKEN configurado
- [ ] ADMIN_TELEGRAM_ID configurado
- [ ] requirements.txt atualizado (aiohttp, openpyxl)
- [ ] .env no .gitignore
- [ ] Entregadores cadastrados: /add_entregador
- [ ] Testado localmente
- [ ] Dashboard acessivel em localhost:8765
- [ ] Bot responde a /start

## Suporte

Duvidas? Abra issue no GitHub ou contate o desenvolvedor.
