# ========================================
# 🚀 SCRIPT DE PUSH PARA GITHUB
# ========================================

Write-Host "`n🔗 CONFIGURAÇÃO DO GITHUB" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Cyan

# Verifica se já tem remote configurado
$hasRemote = git remote get-url origin 2>$null

if ($hasRemote) {
    Write-Host "✅ Remote já configurado: $hasRemote`n" -ForegroundColor Green
    
    # Faz push direto
    Write-Host "🚀 Fazendo push para o GitHub...`n" -ForegroundColor Cyan
    git push origin main
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ PUSH REALIZADO COM SUCESSO!" -ForegroundColor Green
        Write-Host "🔗 Acesse: $hasRemote`n" -ForegroundColor Cyan
    } else {
        Write-Host "`n⚠️  Erro no push. Execute:`n" -ForegroundColor Yellow
        Write-Host "   git push -u origin main`n" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠️  Remote não configurado`n" -ForegroundColor Yellow
    Write-Host "📝 CONFIGURE ASSIM:`n" -ForegroundColor Cyan
    Write-Host "1️⃣  Crie repositório: https://github.com/new" -ForegroundColor White
    Write-Host "    Nome sugerido: BotEntregador`n" -ForegroundColor Gray
    
    Write-Host "2️⃣  Execute os comandos:`n" -ForegroundColor White
    Write-Host "   git remote add origin https://github.com/SEU_USUARIO/BotEntregador.git" -ForegroundColor Cyan
    Write-Host "   git branch -M main" -ForegroundColor Cyan
    Write-Host "   git push -u origin main`n" -ForegroundColor Cyan
    
    Write-Host "💡 Ou cole a URL do repositório agora:" -ForegroundColor Yellow
    $url = Read-Host "   URL (ou Enter para pular)"
    
    if ($url) {
        git remote add origin $url
        git branch -M main
        git push -u origin main
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n✅ PUSH REALIZADO COM SUCESSO!" -ForegroundColor Green
        }
    }
}
