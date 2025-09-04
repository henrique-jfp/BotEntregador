import re
from typing import List
from bot.models.core import DeliveryAddress
from bot.config import Config

ABBREV_MAP = [
    (r'^(r)\b\.?', 'Rua'),
    (r'^(av)\b\.?', 'Avenida'),
]
CEP_REGEX = re.compile(r'\b\d{5}-?\d{3}\b')

def normalize_address(original: str) -> str:
    line = original.strip()
    if not line:
        return line
    parts = line.split(maxsplit=1)
    first = parts[0]
    rest = parts[1] if len(parts) > 1 else ''
    for pattern, repl in ABBREV_MAP:
        if re.match(pattern, first, flags=re.IGNORECASE):
            first = repl
            break
    rebuilt = (first + (' ' + rest if rest else '')).strip()
    cep_match = CEP_REGEX.search(original)
    if cep_match and cep_match.group(0) not in rebuilt:
        rebuilt += f' CEP {cep_match.group(0)}'
    return rebuilt

ADDRESS_TYPE = re.compile(r'^(rua|r\.|avenida|av\.|travessa|tv\.|alameda|praça|praca|rodovia|estrada|beco)\b', re.IGNORECASE)
CITY_OR_CEP = re.compile(r'(\b(rj|sp|mg|es|ba|rs|sc|pr|go|df|pe|ce)\b|\b\d{5}-?\d{3}\b)', re.IGNORECASE)

def extract_addresses(raw_text: str) -> List[DeliveryAddress]:
    lines = [l.strip() for l in raw_text.splitlines()]
    cleaned = [l for l in lines if l and len(re.sub(r'[^\w]', '', l)) >= 3]
    merged = []
    i = 0
    while i < len(cleaned):
        cur = cleaned[i]
        nxt = cleaned[i+1] if i+1 < len(cleaned) else ''
        if nxt and not ADDRESS_TYPE.search(nxt) and CITY_OR_CEP.search(nxt) and re.search(r'\d', cur) and len(cur) < 120:
            merged.append(cur.rstrip(',') + ', ' + nxt)
            i += 2
            continue
        merged.append(cur)
        i += 1
    seen = set(); results = []
    for line in merged:
        if re.search(r'\d', line) and re.search(r'[A-Za-zÀ-ÖØ-öø-ÿ]', line):
            norm = normalize_address(line)
            key = norm.lower()
            if key not in seen:
                seen.add(key)
                results.append(DeliveryAddress(original_text=line, cleaned_address=norm))
        if len(results) >= Config.MAX_ADDRESSES_PER_ROUTE:
            break
    return results
