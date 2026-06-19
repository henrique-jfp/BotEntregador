# 🎨 PALETA DE CORES PARA ENTREGADORES
# Cores usadas nos mapas, adesivos e separação
DELIVERER_COLORS = [
    '#3B82F6',  # Azul
    '#10B981',  # Verde
    '#F59E0B',  # Amarelo
    '#EF4444',  # Vermelho
    '#8B5CF6',  # Roxo
    '#F97316',  # Laranja
    '#EC4899',  # Rosa
    '#14B8A6',  # Turquesa
]

COLOR_NAMES = {
    '#3B82F6': '🔵 AZUL',
    '#10B981': '🟢 VERDE',
    '#F59E0B': '🟡 AMARELO',
    '#EF4444': '🔴 VERMELHO',
    '#8B5CF6': '🟣 ROXO',
    '#F97316': '🟠 LARANJA',
    '#EC4899': '🌸 ROSA',
    '#14B8A6': '💎 TURQUESA',
}

def get_color_for_index(idx: int) -> str:
    """Retorna cor baseada no índice do entregador"""
    return DELIVERER_COLORS[idx % len(DELIVERER_COLORS)]

def get_color_name(hex_color: str) -> str:
    """Retorna nome amigável da cor"""
    return COLOR_NAMES.get(hex_color, hex_color)
