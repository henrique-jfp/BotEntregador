"""
✅ VALIDAÇÃO DE SETUP
Verifica se tudo está configurado corretamente
"""
import os
import sys

def check_env_vars():
    """Verifica variáveis de ambiente"""
    print("🔍 Verificando variáveis de ambiente...")
    
    required = ["TELEGRAM_BOT_TOKEN", "ADMIN_TELEGRAM_ID"]
    optional = ["GOOGLE_API_KEY"]
    
    missing = []
    for var in required:
        if not os.getenv(var):
            missing.append(var)
            print(f"   ❌ {var} não configurado")
        else:
            print(f"   ✅ {var} configurado")
    
    for var in optional:
        if os.getenv(var):
            print(f"   ✅ {var} configurado (opcional)")
        else:
            print(f"   ⚠️  {var} não configurado (opcional)")
    
    return len(missing) == 0


def check_modules():
    """Verifica módulos instalados"""
    print("\n📦 Verificando dependências...")
    
    required_modules = [
        ("telegram", "python-telegram-bot"),
        ("dotenv", "python-dotenv"),
    ]
    
    missing = []
    for module, package in required_modules:
        try:
            __import__(module)
            print(f"   ✅ {package} instalado")
        except ImportError:
            missing.append(package)
            print(f"   ❌ {package} NÃO instalado")
    
    return len(missing) == 0, missing


def check_config():
    """Verifica configuração de entregadores"""
    print("\n👥 Verificando cadastro de entregadores...")
    
    try:
        from bot_multidelivery.config import BotConfig
        
        print(f"   📊 Admin ID: {BotConfig.ADMIN_TELEGRAM_ID}")
        print(f"   👥 Entregadores cadastrados: {len(BotConfig.DELIVERY_PARTNERS)}")
        
        for partner in BotConfig.DELIVERY_PARTNERS:
            status = "Sócio" if partner.is_partner else f"R$ {partner.cost_per_package}/pacote"
            print(f"      • {partner.name} (ID: {partner.telegram_id}) - {status}")
        
        return True
    except Exception as e:
        print(f"   ❌ Erro ao carregar config: {e}")
        return False


def check_files():
    """Verifica arquivos essenciais"""
    print("\n📁 Verificando arquivos...")
    
    files = [
        "bot_multidelivery/__init__.py",
        "bot_multidelivery/config.py",
        "bot_multidelivery/clustering.py",
        "bot_multidelivery/session.py",
        "bot_multidelivery/bot.py",
        "main_multidelivery.py",
    ]
    
    missing = []
    for file in files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            missing.append(file)
            print(f"   ❌ {file} NÃO encontrado")
    
    return len(missing) == 0


def main():
    print("="*60)
    print("🔥 VALIDAÇÃO DE SETUP - Bot Multi-Entregador")
    print("="*60)
    print()
    
    # Carrega .env se existir
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
    
    # Checks
    checks = [
        ("Arquivos", check_files()),
        ("Variáveis de Ambiente", check_env_vars()),
        ("Configuração", check_config()),
    ]
    
    modules_ok, missing_modules = check_modules()
    checks.append(("Dependências", modules_ok))
    
    # Resultado
    print("\n" + "="*60)
    print("📊 RESULTADO")
    print("="*60)
    
    all_ok = all(result for _, result in checks)
    
    for name, result in checks:
        icon = "✅" if result else "❌"
        print(f"{icon} {name}")
    
    print()
    
    if all_ok:
        print("🎉 SETUP COMPLETO! Tudo pronto pra rodar.")
        print("\n💡 Próximo passo:")
        print("   python main_multidelivery.py")
    else:
        print("⚠️  SETUP INCOMPLETO. Corrija os problemas acima.")
        
        if not modules_ok:
            print("\n📦 Instale dependências faltando:")
            print(f"   pip install {' '.join(missing_modules)}")
        
        if not checks[1][1]:  # Env vars
            print("\n🔑 Configure variáveis de ambiente:")
            print("   1. Copie .env.example para .env")
            print("   2. Preencha TELEGRAM_BOT_TOKEN e ADMIN_TELEGRAM_ID")
    
    print("\n" + "="*60)
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
