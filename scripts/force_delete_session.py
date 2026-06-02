#!/usr/bin/env python3
"""
Script de manutenção: força exclusão de uma sessão (com backup)

Uso:
  python scripts/force_delete_session.py --id 8b382c1f

Este script:
 - faz backup do arquivo JSON de sessão (se existir) em ./backups
 - tenta serializar a sessão do DB em JSON se não houver arquivo
 - chama `session_manager.delete_session(session_id, force=True)`

Risco: operação destrutiva. Execute apenas se tiver backup.
"""
import argparse
import os
import shutil
import json
from datetime import datetime

# Ajusta PYTHONPATH quando executado a partir da pasta scripts
import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from bot_multidelivery.session_persistence import session_store
from bot_multidelivery.session import session_manager


def make_backup(session_id: str, backups_dir: str = "backups") -> str:
    os.makedirs(backups_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_name = f"{session_id}_{timestamp}.json"
    backup_path = os.path.join(backups_dir, backup_name)

    # 1) se existir arquivo JSON local, copia
    try:
        file_path = session_store._session_file(session_id)
        if file_path.exists():
            shutil.copy2(file_path, backup_path)
            return backup_path
    except Exception:
        # ignora e tenta serializar via load_session
        pass

    # 2) tenta carregar via API de persistência e serializar
    try:
        sess = session_store.load_session(session_id)
        if sess:
            # serializar campos relevantes
            data = {
                'session_id': sess.session_id,
                'session_name': sess.session_name,
                'date': sess.date,
                'period': sess.period,
                'created_at': sess.created_at.isoformat() if getattr(sess, 'created_at', None) else None,
                'romaneios': [],
                'routes': []
            }

            for r in getattr(sess, 'romaneios', []):
                data['romaneios'].append({'id': r.id, 'filename': getattr(r, 'filename', '' )})

            for r in getattr(sess, 'routes', []):
                data['routes'].append({'id': r.id, 'assigned_to_telegram_id': r.assigned_to_telegram_id})

            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return backup_path
    except Exception:
        pass

    # sem backup possível
    return ""


def force_delete(session_id: str) -> bool:
    try:
        print(f"📌 Solicitando exclusão forçada da sessão {session_id}...")
        result = session_manager.delete_session(session_id, force=True)
        print(f"✅ delete_session returned: {result}")
        return True
    except Exception as e:
        print(f"❌ Erro ao forçar exclusão: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Força exclusão de sessão com backup")
    parser.add_argument('--id', '-i', required=True, help='session_id a ser excluído')
    parser.add_argument('--yes', '-y', action='store_true', help='Confirma sem prompt')
    parser.add_argument('--backups-dir', default='backups', help='Diretório onde salvar backup')
    args = parser.parse_args()

    session_id = args.id

    if not args.yes:
        confirm = input(f"Tem certeza que deseja forçar exclusão da sessão {session_id}? (digite 'sim' para confirmar): ")
        if confirm.strip().lower() != 'sim':
            print("Cancelado pelo usuário")
            return

    print("🔎 Fazendo backup antes de excluir...")
    backup_path = make_backup(session_id, backups_dir=args.backups_dir)
    if backup_path:
        print(f"💾 Backup criado em: {backup_path}")
    else:
        print("⚠️ Não foi possível criar backup (continuando mesmo assim)")

    success = force_delete(session_id)
    if success:
        print("✅ Operação concluída. Verifique logs do servidor para confirmar remoção.")
    else:
        print("❌ Falha ao excluir; verifique logs e backup no local.")


if __name__ == '__main__':
    main()
# EOF