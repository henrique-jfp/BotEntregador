"""
🚀 MAIN RUNNER
Ponto de entrada do bot multi-entregador
"""
import sys
import os

# Adiciona diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot_multidelivery.bot import run_bot

if __name__ == "__main__":
    print("🔥 Iniciando Bot Multi-Entregador...")
    print("🎯 Pressione CTRL+C para parar\n")
    
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n⚠️ Bot interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
