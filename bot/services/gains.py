import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

GAINS_FILE = Path('gains.jsonl')
DEFAULT_APPS = ["iFood", "Rappi", "Uber Eats", "Loggi", "Outro"]

def append_gain(rec: Dict):
    try:
        with open(GAINS_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False)+'\n')
    except Exception:
        pass

def load_gains(user_id: int, start: datetime, end: datetime) -> List[Dict]:
    if not GAINS_FILE.exists():
        return []
    out = []
    try:
        with open(GAINS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    j = json.loads(line)
                    if j.get('user') != user_id:
                        continue
                    d = datetime.fromisoformat(j.get('date'))
                    if start.date() <= d.date() <= end.date():
                        out.append(j)
                except Exception:
                    pass
    except Exception:
        return out
    return out

def summarize_gains(gains: List[Dict]) -> str:
    if not gains:
        return "Nenhum registro."
    by_app = {}
    total = 0.0
    for g in gains:
        v = float(g.get('valor', 0))
        app = g.get('app', 'Outro')
        by_app[app] = by_app.get(app, 0.0) + v
        total += v
    lines = [f"{app}: R$ {val:.2f}" for app,val in sorted(by_app.items(), key=lambda x:-x[1])]
    lines.append(f"Total: R$ {total:.2f}")
    return '\n'.join(lines)
