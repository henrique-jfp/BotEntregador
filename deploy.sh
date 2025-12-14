#!/data/data/com.termux/files/usr/bin/bash
# 🤖 Script de Deploy Automático - Bot Entregas no M21s
# Execute: bash deploy.sh

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     🤖 Deploy Automático - Bot de Entregas              ║"
echo "║     Servidor: M21s (Termux)                              ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Diretório do projeto
PROJECT_DIR="$HOME/BotEntregador"
BOT_NAME="bot-entregas"

# Função de log
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar se já existe instalação
if [ -d "$PROJECT_DIR" ]; then
    log_warn "Diretório $PROJECT_DIR já existe!"
    read -p "Deseja reinstalar? (s/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        log_info "Removendo instalação antiga..."
        pm2 delete $BOT_NAME 2>/dev/null
        rm -rf $PROJECT_DIR
    else
        log_info "Abortado pelo usuário."
        exit 0
    fi
fi

# 1. Clonar repositório
log_info "Clonando repositório..."
cd ~
git clone https://github.com/henrique-jfp/BotEntregador.git
if [ $? -ne 0 ]; then
    log_error "Falha ao clonar repositório!"
    exit 1
fi
cd $PROJECT_DIR

# 2. Criar ambiente virtual
log_info "Criando ambiente virtual Python..."
python -m venv .venv
if [ $? -ne 0 ]; then
    log_error "Falha ao criar venv!"
    exit 1
fi

# 3. Ativar venv e instalar dependências
log_info "Instalando dependências..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    log_warn "Algumas dependências falharam. Tentando com pacotes Termux..."
    pkg install python-pillow python-numpy -y
    pip install -r requirements.txt --no-build-isolation
fi

# 4. Configurar variáveis de ambiente
log_info "Configurando variáveis de ambiente..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 CONFIGURAÇÃO DE CREDENCIAIS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ ! -f .env ]; then
    echo "🔑 Configure suas credenciais:"
    echo ""
    read -p "TELEGRAM_BOT_TOKEN (do @BotFather): " BOT_TOKEN
    read -p "ADMIN_TELEGRAM_ID (seu ID do @userinfobot): " ADMIN_ID
    read -p "GOOGLE_API_KEY (opcional, Enter para pular): " GOOGLE_KEY
    
    cat > .env << EOF
TELEGRAM_BOT_TOKEN=$BOT_TOKEN
ADMIN_TELEGRAM_ID=$ADMIN_ID
GOOGLE_API_KEY=$GOOGLE_KEY
EOF
    
    chmod 600 .env
    log_info "Arquivo .env criado com sucesso!"
else
    log_info "Arquivo .env já existe, mantendo configuração atual."
fi

# 5. Criar diretório de logs
mkdir -p ~/logs

# 6. Criar script de inicialização
log_info "Criando script de inicialização..."
cat > start_bot.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd ~/BotEntregador
source .venv/bin/activate
python main_multidelivery.py
EOF

chmod +x start_bot.sh

# 7. Testar bot
echo ""
log_info "Testando bot (5 segundos)..."
source .venv/bin/activate
timeout 5 python main_multidelivery.py &
PID=$!
sleep 6
kill $PID 2>/dev/null

if [ $? -eq 0 ]; then
    log_info "✅ Bot iniciou com sucesso!"
else
    log_warn "⚠️  Não foi possível testar o bot. Continuando..."
fi

# 8. Configurar PM2
log_info "Configurando PM2..."
deactivate

# Parar instâncias antigas se existirem
pm2 delete $BOT_NAME 2>/dev/null

# Iniciar com PM2
pm2 start start_bot.sh \
  --name $BOT_NAME \
  --interpreter bash \
  --log ~/logs/$BOT_NAME.log \
  --error ~/logs/$BOT_NAME-error.log \
  --max-restarts 10 \
  --min-uptime 5000

if [ $? -ne 0 ]; then
    log_error "Falha ao iniciar com PM2!"
    exit 1
fi

# Salvar configuração PM2
pm2 save

# 9. Configurar boot automático
log_info "Configurando boot automático..."
mkdir -p ~/.termux/boot

if [ ! -f ~/.termux/boot/start-server.sh ]; then
    cat > ~/.termux/boot/start-server.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash

# Wake Lock (impede CPU dormir)
termux-wake-lock

# SSH
sshd

# PM2 - Restaurar processos
pm2 resurrect
EOF
    chmod +x ~/.termux/boot/start-server.sh
    log_info "Script de boot criado!"
else
    # Adicionar pm2 resurrect se não existir
    if ! grep -q "pm2 resurrect" ~/.termux/boot/start-server.sh; then
        echo "pm2 resurrect" >> ~/.termux/boot/start-server.sh
        log_info "pm2 resurrect adicionado ao boot!"
    else
        log_info "Boot já configurado!"
    fi
fi

# 10. Status final
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DEPLOY CONCLUÍDO COM SUCESSO!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
pm2 list
echo ""
echo "📋 PRÓXIMOS PASSOS:"
echo ""
echo "1. Verificar logs:"
echo "   pm2 logs $BOT_NAME"
echo ""
echo "2. Testar no Telegram:"
echo "   Envie /start para o bot"
echo ""
echo "3. Monitorar status:"
echo "   pm2 monit"
echo ""
echo "4. Ver informações:"
echo "   pm2 info $BOT_NAME"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Bot rodando 24/7 no servidor M21s!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Mostrar logs por 10 segundos
log_info "Mostrando logs (CTRL+C para sair)..."
sleep 2
pm2 logs $BOT_NAME
