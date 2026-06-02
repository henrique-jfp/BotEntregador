# 🚀 Script de Execução Local do Mini App (Windows)
# Garante ambiente configurado e rodando suave.

Write-Host "🚀 Iniciando setup local do Bot Entregador..." -ForegroundColor Cyan

# 1. Verifica Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "❌ Python não encontrado! Instale Python 3.10+."
    exit 1
}

# 2. Cria/Ativa Ambiente Virtual
if (-not (Test-Path ".venv")) {
    Write-Host "📦 Criando ambiente virtual..." -ForegroundColor Yellow
    python -m venv .venv
}
Write-Host "🔌 Ativando virtualenv..." -ForegroundColor Green
& .\.venv\Scripts\Activate.ps1

# 3. Instala Dependências Python
Write-Host "⬇️ Instalando dependências do Python..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Falha ao instalar requirements.txt"
    exit 1
}

# 4. Configura Frontend
if (Test-Path "webapp") {
    Push-Location "webapp"
    if (-not (Test-Path "node_modules")) {
        Write-Host "📦 Instalando dependências do Frontend..." -ForegroundColor Yellow
        npm install
    }
    
    if (-not (Test-Path "dist")) {
        Write-Host "🏗️ Buildando Frontend..." -ForegroundColor Yellow
        npm run build
    }
    Pop-Location
} else {
    Write-Host "⚠️ Pasta webapp não encontrada. Rodando apenas API." -ForegroundColor Yellow
}

# 5. Verifica .env
if (-not (Test-Path ".env")) {
    Write-Host "⚠️ Arquivo .env não encontrado!" -ForegroundColor Red
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "✅ Criado .env a partir do exemplo. EDITE-O AGORA COM SEUS DADOS!" -ForegroundColor Magenta
        notepad .env
        Read-Host "Pressione Enter após salvar o .env"
    }
}

# 6. Executa
Write-Host "🔥 Iniciando Servidor e Bot..." -ForegroundColor Cyan
Write-Host "🌐 API: http://localhost:8000"
Write-Host "📱 Scanner: http://localhost:8000/scanner"
Write-Host "⌨️ Pressione CTRL+C para parar"

python main_multidelivery.py
