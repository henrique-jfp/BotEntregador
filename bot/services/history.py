import json
from pathlib import Path
from datetime import datetime
from bot.models.core import UserSession

HISTORY_DIR = Path('history')
HISTORY_DIR.mkdir(exist_ok=True)

def append_route_history(session: UserSession):
    try:
        rec = {
            'ts': datetime.utcnow().isoformat(),
            'entregas_total': len(session.completed_deliveries),
            'receita': session.config.get('valor_entrega',0)*len(session.completed_deliveries) if session.config else 0,
            'duracao_min': int((datetime.now()-session.start_time).total_seconds()/60)
        }
        with open(HISTORY_DIR / f'history_{session.user_id}.jsonl','a',encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False)+'\n')
    except Exception:
        pass
