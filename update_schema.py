import logging
from sqlalchemy import text
from bot_multidelivery.database import db_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_schema():
    print("🚀 Iniciando verificação do schema do banco de dados...")
    
    if not db_manager.is_connected:
        print("❌ Database não está conectado. Verifique a variável DATABASE_URL.")
        return

    engine = db_manager.engine
    
    try:
        with engine.connect() as conn:
            print("🔍 Verificando tabela 'sessions'...")
            
            # Check existing columns
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='sessions'"))
            columns = [row[0] for row in result.fetchall()]
            
            print(f"📋 Colunas atuais: {columns}")
            
            # Add session_name if missing
            if 'session_name' not in columns:
                print("🛠️ Adicionando coluna 'session_name'...")
                conn.execute(text("ALTER TABLE sessions ADD COLUMN session_name VARCHAR(50)"))
                print("✅ Coluna 'session_name' adicionada.")
            else:
                print("✅ Coluna 'session_name' já existe.")

            # Add period if missing
            if 'period' not in columns:
                print("🛠️ Adicionando coluna 'period'...")
                conn.execute(text("ALTER TABLE sessions ADD COLUMN period VARCHAR(10)"))
                print("✅ Coluna 'period' adicionada.")
            else:
                print("✅ Coluna 'period' já existe.")
                
            conn.commit()
        
        print("\n🎉 Schema do banco de dados atualizado com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao atualizar schema: {e}")

if __name__ == "__main__":
    fix_schema()
