"""
🚀 CONFIGURADOR INTERATIVO
Setup guiado passo a passo
"""
import os
from pathlib import Path

def print_header(text):
    print("\n" + "="*60)
    print(f"🔥 {text}")
    print("="*60)

def print_step(num, text):
    print(f"\n📌 PASSO {num}: {text}")

def get_input(prompt, default=None):
    if default:
        response = input(f"{prompt} [{default}]: ").strip()
        return response if response else default
    return input(f"{prompt}: ").strip()

def main():
    print_header("CONFIGURADOR INTERATIVO - Bot Multi-Entregador")
    
    print("\n👋 Vou te ajudar a configurar tudo em 5 minutos!")
    print("\n⚠️  Você JÁ criou o bot no @BotFather?")
    print("   Se não, siga: https://t.me/BotFather")
    print("   Comando: /newbot")
    
    input("\n➡️  Pressione ENTER quando tiver o TOKEN do bot...")
    
    # Coleta dados
    print_step(1, "Configuração do Bot")
    token = get_input("🤖 Cole o TELEGRAM_BOT_TOKEN")
    
    while not token or ':' not in token:
        print("   ❌ Token inválido. Deve ser tipo: 123456789:ABCdef...")
        token = get_input("🤖 Cole o TELEGRAM_BOT_TOKEN")
    
    print("\n✅ Token válido!")
    
    print("\n📱 Agora preciso do SEU Telegram ID")
    print("   Fale com @userinfobot no Telegram e copie seu ID")
    
    admin_id = get_input("👤 Seu TELEGRAM_ID (apenas números)")
    
    while not admin_id.isdigit():
        print("   ❌ ID inválido. Deve ser apenas números")
        admin_id = get_input("👤 Seu TELEGRAM_ID")
    
    print("\n✅ ID válido!")
    
    # Salva .env
    print_step(2, "Salvando configurações")
    
    env_content = f"""# Bot Multi-Entregador - Configurações
# Gerado automaticamente em {Path.cwd()}

# Token do bot (obtido com @BotFather)
TELEGRAM_BOT_TOKEN={token}

# Seu Telegram ID (obtido com @userinfobot)
ADMIN_TELEGRAM_ID={admin_id}

# Google API Key (opcional - descomente quando tiver)
# GOOGLE_API_KEY=sua_chave_aqui
"""
    
    env_path = Path('.env')
    env_path.write_text(env_content, encoding='utf-8')
    
    print(f"   ✅ Arquivo .env criado em: {env_path.absolute()}")
    
    # Cadastro de entregadores
    print_step(3, "Cadastro de Entregadores")
    
    print("\n👥 Agora vamos cadastrar os entregadores")
    print("   Cada um precisa falar com @userinfobot pra pegar o ID")
    
    partners = []
    
    add_more = True
    while add_more:
        print(f"\n🚴 Entregador #{len(partners) + 1}")
        
        name = get_input("   Nome")
        if not name:
            break
        
        e_id = get_input("   Telegram ID")
        if not e_id.isdigit():
            print("   ⚠️  ID inválido, pulando...")
            continue
        
        is_partner = get_input("   É sócio? (s/n)", "n").lower() == 's'
        
        partners.append({
            'id': e_id,
            'name': name,
            'is_partner': is_partner
        })
        
        print(f"   ✅ {name} cadastrado!")
        
        cont = get_input("\n   Adicionar mais? (s/n)", "n")
        add_more = cont.lower() == 's'
    
    if partners:
        # Atualiza config.py
        config_path = Path('bot_multidelivery/config.py')
        
        if config_path.exists():
            config_content = config_path.read_text(encoding='utf-8')
            
            # Gera lista de partners
            partners_code = "    DELIVERY_PARTNERS: List[DeliveryPartner] = [\n"
            for p in partners:
                status = "Sócio" if p['is_partner'] else ""
                partners_code += f"        DeliveryPartner(telegram_id={p['id']}, name=\"{p['name']}{' ('+status+')' if status else ''}\", is_partner={p['is_partner']}),\n"
            partners_code += "    ]"
            
            # Substitui no arquivo
            import re
            pattern = r'DELIVERY_PARTNERS: List\[DeliveryPartner\] = \[.*?\]'
            config_content = re.sub(pattern, partners_code, config_content, flags=re.DOTALL)
            
            config_path.write_text(config_content, encoding='utf-8')
            print(f"\n   ✅ {len(partners)} entregadores salvos em config.py")
        else:
            print(f"\n   ⚠️  Arquivo config.py não encontrado")
    
    # Resumo
    print_header("CONFIGURAÇÃO COMPLETA! 🎉")
    
    print(f"\n📊 RESUMO:")
    print(f"   🤖 Bot configurado: ✅")
    print(f"   👤 Admin ID: {admin_id}")
    print(f"   👥 Entregadores: {len(partners)}")
    
    if partners:
        for p in partners:
            cost = "R$ 0 (Sócio)" if p['is_partner'] else "R$ 1/pacote"
            print(f"      • {p['name']} - {cost}")
    
    print(f"\n🚀 PRÓXIMOS PASSOS:")
    print(f"   1. pip install python-telegram-bot python-dotenv")
    print(f"   2. python validate_setup.py (valida tudo)")
    print(f"   3. python main_multidelivery.py (inicia bot)")
    print(f"   4. Abra o bot no Telegram e envie /start")
    
    print(f"\n📱 Procure seu bot no Telegram:")
    print(f"   O username deve terminar com 'bot'")
    print(f"   Ex: @meuEntregadorBot")
    
    print("\n" + "="*60)
    print("✅ Setup concluído! Boa sorte nas entregas! 🚀")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Configuração cancelada pelo usuário")
    except Exception as e:
        print(f"\n\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
