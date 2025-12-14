"""
RESET BOT - Remove webhook e limpa conflitos
Execute isso para resolver erro "Conflict: terminated by other getUpdates"
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def delete_webhook():
    """Remove webhook (se configurado)"""
    url = f"{BASE_URL}/deleteWebhook"
    params = {'drop_pending_updates': True}
    
    response = requests.post(url, params=params)
    result = response.json()
    
    if result.get('ok'):
        print("[OK] Webhook removido com sucesso")
        print(f"Descricao: {result.get('description')}")
    else:
        print(f"[ERRO] {result}")

def get_webhook_info():
    """Verifica se tem webhook configurado"""
    url = f"{BASE_URL}/getWebhookInfo"
    response = requests.get(url)
    result = response.json()
    
    if result.get('ok'):
        info = result.get('result', {})
        webhook_url = info.get('url')
        
        if webhook_url:
            print(f"[!] Webhook ATIVO: {webhook_url}")
            print(f"Pending updates: {info.get('pending_update_count', 0)}")
            print(f"Last error: {info.get('last_error_message', 'None')}")
            return True
        else:
            print("[OK] Nenhum webhook configurado")
            return False

def get_me():
    """Testa conexao com bot"""
    url = f"{BASE_URL}/getMe"
    response = requests.get(url)
    result = response.json()
    
    if result.get('ok'):
        bot = result.get('result', {})
        print(f"\n[BOT INFO]")
        print(f"Username: @{bot.get('username')}")
        print(f"ID: {bot.get('id')}")
        print(f"Nome: {bot.get('first_name')}")
    else:
        print(f"[ERRO] Nao conseguiu conectar: {result}")

if __name__ == "__main__":
    print("=" * 60)
    print("TELEGRAM BOT - RESET DE CONFLITOS")
    print("=" * 60)
    
    # Testa conexao
    get_me()
    
    print("\n" + "=" * 60)
    print("VERIFICANDO WEBHOOK...")
    print("=" * 60)
    
    # Verifica webhook
    has_webhook = get_webhook_info()
    
    if has_webhook:
        print("\n[!] ENCONTRADO WEBHOOK ATIVO!")
        print("\nDeseja remover? (s/n): ", end="")
        choice = input().lower()
        
        if choice == 's':
            print("\nRemovendo webhook...")
            delete_webhook()
            print("\n[OK] Agora o bot pode usar polling no Render!")
    else:
        print("\n[OK] Bot configurado corretamente para polling")
    
    print("\n" + "=" * 60)
    print("INSTRUCOES:")
    print("=" * 60)
    print("1. Se bot local estiver rodando: PARE-O (Ctrl+C)")
    print("2. Se erro persistir: Aguarde 1-2 minutos (cooldown Telegram)")
    print("3. Render vai reconectar automaticamente")
    print("\n[OK] Tudo certo! Bot no Render deve funcionar agora.")
