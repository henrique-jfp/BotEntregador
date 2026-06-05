import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Variáveis de ambiente carregadas do .env")
except ImportError:
    pass

# Adiciona o diretório raiz ao path para importar os módulos do projeto
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot_multidelivery.database import db_manager, GeocodingCacheDB

def migrate():
    json_path = Path("data/geocoding_cache.json")
    if not json_path.exists():
        print("❌ Arquivo data/geocoding_cache.json não encontrado.")
        return

    print(f"📖 Lendo {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        cache_data = json.load(f)

    total_items = len(cache_data)
    print(f"📊 Encontrados {total_items} endereços no JSON.")

    if not db_manager.is_connected:
        print("❌ Banco de dados não está conectado. Verifique DATABASE_URL.")
        return

    migrated = 0
    skipped = 0
    errors = 0

    with db_manager.get_session() as session:
        for key, item in cache_data.items():
            address = item.get('address', '').lower().strip()
            if not address:
                continue

            try:
                # Verifica se já existe no banco
                exists = session.query(GeocodingCacheDB).filter_by(address=address).first()
                if exists:
                    skipped += 1
                    continue

                # Cria novo registro
                new_cache = GeocodingCacheDB(
                    address=address,
                    lat=item['lat'],
                    lng=item['lng'],
                    formatted_address=item.get('address'),
                    provider=item.get('provider', 'Legacy JSON'),
                    cached_at=datetime.fromisoformat(item['cached_at']) if item.get('cached_at') else datetime.now()
                )
                session.add(new_cache)
                migrated += 1

                # Commit parcial a cada 100 itens para não pesar
                if migrated % 100 == 0:
                    session.commit()
                    print(f"⏳ Processados {migrated + skipped}...")

            except Exception as e:
                print(f"⚠️ Erro ao processar '{address}': {e}")
                errors += 1
        
        session.commit()

    print("\n" + "="*40)
    print("✅ MIGRAÇÃO CONCLUÍDA")
    print(f"🚀 Migrados: {migrated}")
    print(f"⏩ Pulados (já existentes): {skipped}")
    print(f"❌ Erros: {errors}")
    print(f"🏠 Total final no Banco: {session.query(GeocodingCacheDB).count()}")
    print("="*40)

if __name__ == "__main__":
    migrate()
