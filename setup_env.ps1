# 🔑 CONFIGURAR VARIÁVEIS DE AMBIENTE
# Execute este script no PowerShell

Write-Host "🔑 CONFIGURAÇÃO DO BOT - Variáveis de Ambiente" -ForegroundColor Cyan
Write-Host "=" * 60
Write-Host ""

# Verifica se já existem
$existingToken = $env:TELEGRAM_BOT_TOKEN
$existingAdmin = $env:ADMIN_TELEGRAM_ID

if ($existingToken) {
    Write-Host "✅ TELEGRAM_BOT_TOKEN já configurado: $($existingToken.Substring(0,10))..." -ForegroundColor Green
} else {
    Write-Host "❌ TELEGRAM_BOT_TOKEN não configurado" -ForegroundColor Yellow
}

if ($existingAdmin) {
    Write-Host "✅ ADMIN_TELEGRAM_ID já configurado: $existingAdmin" -ForegroundColor Green
} else {
    Write-Host "❌ ADMIN_TELEGRAM_ID não configurado" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=" * 60
Write-Host ""

# Pergunta se quer configurar
$configurar = Read-Host "Deseja configurar/reconfigurar as variáveis? (S/N)"

if ($configurar -eq "S" -or $configurar -eq "s") {
    Write-Host ""
    
    # Token do Bot
    Write-Host "📱 TELEGRAM_BOT_TOKEN" -ForegroundColor Cyan
    Write-Host "   Obtenha em: https://t.me/BotFather"
    Write-Host "   Formato: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
    $token = Read-Host "   Digite o token"
    
    Write-Host ""
    
    # ID do Admin
    Write-Host "👤 ADMIN_TELEGRAM_ID" -ForegroundColor Cyan
    Write-Host "   Obtenha em: https://t.me/userinfobot"
    Write-Host "   Formato: 123456789 (apenas números)"
    $adminId = Read-Host "   Digite seu ID do Telegram"
    
    Write-Host ""
    Write-Host "=" * 60
    Write-Host ""
    
    # Pergunta se quer salvar permanentemente
    Write-Host "💾 COMO SALVAR?" -ForegroundColor Yellow
    Write-Host "1. Apenas nesta sessão (temporário)"
    Write-Host "2. Permanentemente para este usuário"
    Write-Host "3. Permanentemente para todo o sistema"
    $opcao = Read-Host "Escolha (1/2/3)"
    
    Write-Host ""
    
    switch ($opcao) {
        "1" {
            # Temporário
            $env:TELEGRAM_BOT_TOKEN = $token
            $env:ADMIN_TELEGRAM_ID = $adminId
            Write-Host "✅ Variáveis configuradas para esta sessão!" -ForegroundColor Green
            Write-Host "⚠️  Elas serão perdidas ao fechar o terminal" -ForegroundColor Yellow
        }
        "2" {
            # Usuário
            [System.Environment]::SetEnvironmentVariable("TELEGRAM_BOT_TOKEN", $token, "User")
            [System.Environment]::SetEnvironmentVariable("ADMIN_TELEGRAM_ID", $adminId, "User")
            $env:TELEGRAM_BOT_TOKEN = $token
            $env:ADMIN_TELEGRAM_ID = $adminId
            Write-Host "✅ Variáveis salvas permanentemente para seu usuário!" -ForegroundColor Green
            Write-Host "⚠️  Abra um novo terminal ou execute: refreshenv" -ForegroundColor Yellow
        }
        "3" {
            # Sistema (requer admin)
            try {
                [System.Environment]::SetEnvironmentVariable("TELEGRAM_BOT_TOKEN", $token, "Machine")
                [System.Environment]::SetEnvironmentVariable("ADMIN_TELEGRAM_ID", $adminId, "Machine")
                $env:TELEGRAM_BOT_TOKEN = $token
                $env:ADMIN_TELEGRAM_ID = $adminId
                Write-Host "✅ Variáveis salvas permanentemente no sistema!" -ForegroundColor Green
                Write-Host "⚠️  Abra um novo terminal ou execute: refreshenv" -ForegroundColor Yellow
            }
            catch {
                Write-Host "❌ Erro: Execute o PowerShell como Administrador" -ForegroundColor Red
                # Fallback para usuário
                [System.Environment]::SetEnvironmentVariable("TELEGRAM_BOT_TOKEN", $token, "User")
                [System.Environment]::SetEnvironmentVariable("ADMIN_TELEGRAM_ID", $adminId, "User")
                $env:TELEGRAM_BOT_TOKEN = $token
                $env:ADMIN_TELEGRAM_ID = $adminId
                Write-Host "✅ Salvo para seu usuário como alternativa" -ForegroundColor Green
            }
        }
        default {
            Write-Host "❌ Opção inválida" -ForegroundColor Red
            exit
        }
    }
    
    Write-Host ""
    Write-Host "=" * 60
    Write-Host ""
    Write-Host "🎉 CONFIGURAÇÃO CONCLUÍDA!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📝 PRÓXIMOS PASSOS:" -ForegroundColor Cyan
    Write-Host "1. Teste a conexão: python monitor_bot.py"
    Write-Host "2. Inicie o bot: python main_multidelivery.py"
    Write-Host ""
}
else {
    Write-Host "❌ Configuração cancelada" -ForegroundColor Red
}

Write-Host ""
Write-Host "💡 DICA: Para verificar as variáveis depois, execute:" -ForegroundColor Cyan
Write-Host "   `$env:TELEGRAM_BOT_TOKEN"
Write-Host "   `$env:ADMIN_TELEGRAM_ID"
Write-Host ""
