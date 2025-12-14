# 🚚 Bot de Otimização de Rotas - Telegram

## 🎯 Visão Geral

Bot inteligente para entregadores que utiliza IA para otimizar rotas de entrega através de análise de imagens, extração de endereços via OCR e navegação GPS integrada.

### ✨ Funcionalidades Principais

- 📸 **Upload múltiplo de imagens** (até 8 fotos por sessão)
- 🔍 **OCR avançado** com Google Cloud Vision
- 🤖 **IA generativa** para limpeza e otimização (Google Gemini Pro)
- 🗺️ **Navegação GPS integrada** (Waze, Google Maps)
- 💾 **Persistência de dados** com recuperação de sessão
- ⚡ **Interface assíncrona** de alta performance
- 🔒 **Validações de segurança** e rate limiting

## 🛠️ Stack Tecnológico

- **Python** 3.10+ com type hints
- **python-telegram-bot** 20.7 (arquitetura assíncrona)
- **Google Cloud Vision API** para OCR
- **Google Gemini Pro** para processamento de IA
- **Pillow** para manipulação de imagens
- **aiohttp** para requisições assíncronas

## 🚀 Instalação e Configuração

### 1. Pré-requisitos

```bash
Python 3.10+
Conta no Google Cloud Platform
Bot do Telegram (via @BotFather)
```

### 2. Clone e Setup

**Opção A: Deploy Local (Windows/Mac/Linux)**
```bash
git clone https://github.com/henrique-jfp/BotEntregador.git
cd BotEntregador
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Opção B: Deploy 24/7 no Servidor Termux (M21s) - Deploy Automático**
```bash
cd ~
curl -O https://raw.githubusercontent.com/henrique-jfp/BotEntregador/main/deploy.sh
bash deploy.sh
```
📖 Guia completo: [DEPLOY_M21S_TERMUX.md](DEPLOY_M21S_TERMUX.md)

**Opção C: Deploy no Render**  
📖 Veja: [DEPLOY_RENDER.md](DEPLOY_RENDER.md)

### 3. Configuração de Ambiente

Copie o arquivo de exemplo e configure suas credenciais:

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN="seu_token_aqui"

# Google Cloud APIs
GOOGLE_API_KEY="sua_chave_gemini_aqui"
GOOGLE_VISION_CREDENTIALS_JSON_BASE64="credenciais_base64_aqui"

# Bot Configuration
MAX_PHOTOS_PER_REQUEST=8
MAX_ADDRESSES_PER_ROUTE=20
DEBUG_MODE=False
```

### 4. Configuração do Google Cloud

#### Google Cloud Vision API:
1. Acesse [Google Cloud Console](https://console.cloud.google.com)
2. Crie um novo projeto ou selecione um existente
3. Ative a API "Cloud Vision API"
4. Crie uma conta de serviço em "IAM & Admin" > "Service Accounts"
5. Baixe o arquivo JSON das credenciais
6. Converta para Base64:
   ```bash
   # Windows PowerShell
   [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Content 'credenciais.json' -Raw)))
   
   # Linux/Mac
   base64 -i credenciais.json
   ```

#### Google Gemini Pro API:
1. Acesse [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Crie uma nova API Key
3. Adicione a chave no arquivo `.env`

### 5. Execução Local

```bash
python main.py
```

## 🌐 Deploy no Render

### 1. Preparação

Certifique-se que tem os arquivos:
- `main.py` (código principal)
- `requirements.txt` (dependências)
- `Procfile` (configuração do Render)

### 2. Criar Procfile

```
web: python main.py
```

### 3. Deploy

1. Conecte seu repositório GitHub ao Render
2. Configure as variáveis de ambiente no dashboard
3. Deploy automático será executado

### 4. Variáveis de Ambiente no Render

```
TELEGRAM_BOT_TOKEN=seu_token
GOOGLE_API_KEY=sua_chave_gemini
GOOGLE_VISION_CREDENTIALS_JSON_BASE64=credenciais_base64
PORT=8000
```

## 📱 Como Usar

### 1. Iniciar Conversa
- Encontre seu bot no Telegram
- Digite `/start`
- Clique em "📸 Enviar Fotos do Roteiro"

### 2. Enviar Fotos
- Envie até 8 fotos do seu roteiro de entregas
- Fotos de apps como iFood, Rappi, Uber Eats
- Clique em "✅ Processar Fotos"

### 3. Rota Otimizada
- Aguarde o processamento da IA
- Revise a rota otimizada apresentada
- Clique em "🚀 Começar Navegação"

### 4. Navegação
- Siga as entregas passo a passo
- Use os botões de navegação (Waze/Google Maps)
- Marque entregas como concluídas
- Acompanhe progresso em tempo real

## 🔧 Comandos Disponíveis

- `/start` - Iniciar nova sessão
- `/help` - Manual de uso
- `/status` - Ver status atual
- `/cancel` - Cancelar operação

## 📊 Recursos Avançados

### Rate Limiting
- Máximo 50 requisições por usuário/hora
- Proteção contra spam e abuso

### Persistência de Dados
- Sessões salvas automaticamente
- Recuperação após reinicialização
- Histórico de entregas

### Validações de Segurança
- Verificação de formato de imagem
- Limite de tamanho (20MB por foto)
- Sanitização de inputs

### Logging Detalhado
- Logs separados por tipo (geral, erro, API)
- Rotação automática de arquivos
- Métricas de performance

## 🐛 Troubleshooting

### Erro "No module named..."
```bash
pip install -r requirements.txt
```

### Erro de credenciais Google
- Verifique se as APIs estão ativadas
- Confirme que o Base64 está correto
- Teste com um projeto novo no Google Cloud

### Bot não responde
- Verifique o token do Telegram
- Confirme que o bot está ativo no @BotFather
- Check logs para erros específicos

### OCR não funciona
- Certifique-se que as fotos têm texto legível
- Verifique iluminação e qualidade da imagem
- Teste com imagens mais simples

## 📈 Métricas e Analytics

O bot coleta automaticamente:
- Número de sessões por usuário
- Taxa de sucesso do OCR
- Tempo médio de processamento
- Eficiência da otimização de rota

## 🔐 Segurança e Privacidade

- Imagens processadas são temporárias
- Não armazenamos dados pessoais
- Comunicação criptografada (Telegram)
- Rate limiting para prevenção de abuso

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para detalhes.

## 🆘 Suporte

Para suporte e dúvidas:
- Abra uma issue no GitHub
- Entre em contato via Telegram: @seu_usuario

---

**🚚 Desenvolvido para otimizar a vida dos entregadores brasileiros!**
