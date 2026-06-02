# 🎨 PALETA DE CORES PARA ENTREGADORES
# Cores usadas nos mapas, adesivos e separação
DELIVERER_COLORS = [
    '#FF4444',  # Vermelho
    '#44FF44',  # Verde
    '#4444FF',  # Azul
    '#FFD700',  # Amarelo/Ouro
    '#FF69B4',  # Rosa
    '#9370DB',  # Roxo
    '#FF8C00',  # Laranja
    '#00CED1',  # Ciano
    '#32CD32',  # Verde-lima
    '#FF1493',  # Rosa-escuro
]

COLOR_NAMES = {
    '#FF4444': '🔴 VERMELHO',
    '#44FF44': '🟢 VERDE',
    '#4444FF': '🔵 AZUL',
    '#FFD700': '🟡 AMARELO',
    '#FF69B4': '🌸 ROSA',
    '#9370DB': '🟣 ROXO',
    '#FF8C00': '🟠 LARANJA',
    '#00CED1': '💎 CIANO',
    '#32CD32': '🍏 VERDE-LIMA',
    '#FF1493': '💗 ROSA-ESCURO',
}

def get_color_for_index(idx: int) -> str:
    """Retorna cor baseada no índice do entregador"""
    return DELIVERER_COLORS[idx % len(DELIVERER_COLORS)]

def get_color_name(hex_color: str) -> str:
    """Retorna nome amigável da cor"""
    return COLOR_NAMES.get(hex_color, hex_color)
