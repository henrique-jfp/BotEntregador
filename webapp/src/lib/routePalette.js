export const ROUTE_COLORS = [
  { id: 'blue', hex: '#3B82F6', label: 'Azul' },
  { id: 'green', hex: '#10B981', label: 'Verde' },
  { id: 'yellow', hex: '#F59E0B', label: 'Amarelo' },
  { id: 'red', hex: '#EF4444', label: 'Vermelho' },
  { id: 'purple', hex: '#8B5CF6', label: 'Roxo' },
  { id: 'orange', hex: '#F97316', label: 'Laranja' },
  { id: 'pink', hex: '#EC4899', label: 'Rosa' },
  { id: 'teal', hex: '#14B8A6', label: 'Turquesa' },
];

export const normalizeRouteColor = (color) => {
  if (!color) return null;
  const match = ROUTE_COLORS.find((item) => item.hex.toLowerCase() === String(color).toLowerCase());
  return match ? match.hex : color;
};
