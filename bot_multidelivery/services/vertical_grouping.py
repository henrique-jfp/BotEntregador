from collections import defaultdict
from typing import List, Dict, Any

def group_by_cep_condominio(points: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Agrupa pontos por CEP e, se disponível, por nome de condomínio.
    Cada grupo vira um "super-ponto" para clusterização.
    """
    groups = defaultdict(list)
    for p in points:
        key = (p.get('cep'), p.get('condominio') or p.get('building') or p.get('address'))
        groups[key].append(p)
    return list(groups.values())
