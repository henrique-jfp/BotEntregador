import React, { useState, useMemo, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Filter, Search, MapPin, CheckSquare, Square, Save, Palette, Navigation } from 'lucide-react';
import { fetchWithAuth } from '../api_client';

// Palette Colors
const COLORS = [
  { id: 'blue', hex: '#3B82F6', label: '🔵 Azul' },
  { id: 'green', hex: '#10B981', label: '🟢 Verde' },
  { id: 'yellow', hex: '#F59E0B', label: '🟡 Amarelo' },
  { id: 'red', hex: '#EF4444', label: '🔴 Vermelho' },
  { id: 'purple', hex: '#8B5CF6', label: '🟣 Roxo' },
  { id: 'orange', hex: '#F97316', label: '🟠 Laranja' },
];

const createMarkerIcon = (color, isSelected, number = '') => {
  return L.divIcon({
    html: `<div style="
      background-color: ${color || '#9CA3AF'};
      border: ${isSelected ? '3px solid #FFF' : '2px solid #FFF'};
      box-shadow: ${isSelected ? '0 0 10px rgba(0,0,0,0.8)' : '0 2px 4px rgba(0,0,0,0.4)'};
      border-radius: 50%;
      width: ${isSelected ? '28px' : '24px'};
      height: ${isSelected ? '28px' : '24px'};
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: bold;
      font-size: 10px;
      transform: ${isSelected ? 'scale(1.2)' : 'scale(1)'};
      transition: transform 0.2s;
    ">${number}</div>`,
    className: 'custom-marker',
    iconSize: isSelected ? [28, 28] : [24, 24],
    iconAnchor: isSelected ? [14, 14] : [12, 12],
  });
};

function haversineDistance(coords1, coords2) {
  const R = 6371; // km
  const dLat = (coords2.lat - coords1.lat) * Math.PI / 180;
  const dLon = (coords2.lng - coords1.lng) * Math.PI / 180;
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(coords1.lat * Math.PI / 180) * Math.cos(coords2.lat * Math.PI / 180) *
    Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c * 1000; // meters
}

function MapUpdater({ center, zoom, bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds && bounds.isValid()) {
      map.fitBounds(bounds, { padding: [20, 20], maxZoom: 16 });
    } else if (center) {
      map.setView(center, zoom);
    }
  }, [center, zoom, bounds, map]);
  return null;
}

export default function CreativeMode({ sessionId, sessionBase, onSaved }) {
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // State: Tools
  const [activeColor, setActiveColor] = useState(COLORS[0].hex);
  const [selectedIds, setSelectedIds] = useState(new Set());
  
  // State: Filters
  const [bairroFilter, setBairroFilter] = useState('');
  const [streetFilter, setStreetFilter] = useState('');
  const [numberSideFilter, setNumberSideFilter] = useState('all'); // 'all', 'even', 'odd'
  const [anchorId, setAnchorId] = useState(null);
  const [radiusFilter, setRadiusFilter] = useState('');

  // Refs for scrolling
  const listRef = useRef({});

  useEffect(() => {
    if (sessionId) {
      loadPackages();
    }
  }, [sessionId]);

  const loadPackages = async () => {
    setLoading(true);
    try {
      const res = await fetchWithAuth(`/session/state`);
      const data = await res.json();
      if (data.active && data.session_id === sessionId) {
        // We need to fetch the actual packages. We can use the /map/realtime/{sessionId} endpoint which returns all points
        const mapRes = await fetchWithAuth(`/map/realtime/${sessionId}`);
        const mapData = await mapRes.json();
        
        if (mapData.points) {
          // Normalize points
          const pkgs = mapData.points.map(p => {
             // Extract street and number for filters
             let street = p.address;
             let number = null;
             const parts = p.address.split(',');
             if (parts.length > 1) {
                 street = parts[0].trim();
                 const numMatch = parts[1].trim().match(/^(\\d+)/);
                 if (numMatch) number = parseInt(numMatch[1], 10);
             }

             return {
                 ...p,
                 street: street,
                 number: number,
                 assignedColor: p.route_id !== 'unassigned' ? p.route_color : null,
                 assignedRouteId: p.route_id !== 'unassigned' ? p.route_id : null
             };
          });
          setPackages(pkgs);
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // --- Filtering Logic ---
  const filteredPackages = useMemo(() => {
    return packages.filter(pkg => {
      // 1. Bairro (simple search in address for now)
      if (bairroFilter && !pkg.address.toLowerCase().includes(bairroFilter.toLowerCase())) return false;
      
      // 2. Street
      if (streetFilter && !pkg.street.toLowerCase().includes(streetFilter.toLowerCase())) return false;

      // 3. Even/Odd
      if (numberSideFilter !== 'all') {
        if (pkg.number === null) return false; // Exclude those without number if filtering
        const isEven = pkg.number % 2 === 0;
        if (numberSideFilter === 'even' && !isEven) return false;
        if (numberSideFilter === 'odd' && isEven) return false;
      }

      // 4. Proximity
      if (anchorId && radiusFilter) {
        const anchorPkg = packages.find(p => p.id === anchorId);
        if (anchorPkg && anchorPkg.lat && pkg.lat) {
          const dist = haversineDistance(
            { lat: anchorPkg.lat, lng: anchorPkg.lng },
            { lat: pkg.lat, lng: pkg.lng }
          );
          if (dist > parseFloat(radiusFilter)) return false;
        }
      }

      return true;
    });
  }, [packages, bairroFilter, streetFilter, numberSideFilter, anchorId, radiusFilter]);

  // --- Map Bounds Calculation ---
  const mapBounds = useMemo(() => {
    const pointsWithCoords = filteredPackages.filter(p => p.lat && p.lng);
    if (pointsWithCoords.length === 0) return null;
    
    const bounds = L.latLngBounds(pointsWithCoords.map(p => [p.lat, p.lng]));
    return bounds;
  }, [filteredPackages]);

  const mapCenter = useMemo(() => {
      if (sessionBase && sessionBase.lat) return [sessionBase.lat, sessionBase.lng];
      return [-22.9068, -43.1729];
  }, [sessionBase]);

  // --- Actions ---
  const handleToggleSelect = (id) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const handleSelectAllFiltered = () => {
    const newSelected = new Set(selectedIds);
    let allSelected = true;
    for (const pkg of filteredPackages) {
      if (!newSelected.has(pkg.id)) {
        allSelected = false;
        break;
      }
    }

    if (allSelected) {
      filteredPackages.forEach(p => newSelected.delete(p.id));
    } else {
      filteredPackages.forEach(p => newSelected.add(p.id));
    }
    setSelectedIds(newSelected);
  };

  const handlePaintSelected = () => {
    if (selectedIds.size === 0) return;
    
    const newPackages = packages.map(pkg => {
      if (selectedIds.has(pkg.id)) {
        return { ...pkg, assignedColor: activeColor };
      }
      return pkg;
    });
    
    setPackages(newPackages);
    setSelectedIds(new Set()); // clear selection after painting
  };

  const handleSaveCreativeRoutes = async () => {
    setSaving(true);
    try {
        // Group by color
        const colorGroups = {};
        packages.forEach(p => {
            if (p.assignedColor) {
                if (!colorGroups[p.assignedColor]) colorGroups[p.assignedColor] = [];
                colorGroups[p.assignedColor].push(p.id);
            }
        });

        const creativeRoutes = Object.keys(colorGroups).map((color, idx) => ({
            id: `creative_route_${idx+1}`,
            color: color,
            package_ids: colorGroups[color]
        }));

        const res = await fetchWithAuth('/api/routes/creative/save', {
            method: 'POST',
            body: JSON.stringify({
                session_id: sessionId,
                routes: creativeRoutes
            })
        });

        if (!res.ok) throw new Error("Erro ao salvar rotas manuais.");
        
        alert("Rotas salvas com sucesso!");
        if (onSaved) onSaved();

    } catch (e) {
        alert(e.message);
    } finally {
        setSaving(false);
    }
  };

  const handleMarkerClick = (id) => {
      handleToggleSelect(id);
      // Scroll to list item
      if (listRef.current[id]) {
          listRef.current[id].scrollIntoView({ behavior: 'smooth', block: 'center' });
          // Highlight temporarily
          listRef.current[id].classList.add('bg-blue-100', 'dark:bg-blue-900/40');
          setTimeout(() => {
              if (listRef.current[id]) listRef.current[id].classList.remove('bg-blue-100', 'dark:bg-blue-900/40');
          }, 1500);
      }
  };

  if (loading) return <div className="p-8 text-center text-gray-500 font-semibold animate-pulse">Carregando pacotes...</div>;

  return (
    <div className="flex flex-col md:flex-row gap-6 h-[80vh]">
      {/* LEFT PANEL: Filters & List */}
      <div className="w-full md:w-1/3 flex flex-col bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden h-full">
        
        {/* Color Palette Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
           <div className="flex items-center justify-between mb-3">
               <span className="font-bold text-gray-700 dark:text-gray-300 text-sm flex items-center gap-2"><Palette size={16}/> Paleta de Rotas</span>
               <button 
                  onClick={handlePaintSelected}
                  disabled={selectedIds.size === 0}
                  className="bg-gray-900 dark:bg-white text-white dark:text-gray-900 px-3 py-1.5 rounded-lg text-xs font-bold disabled:opacity-50 hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors"
               >
                   Pintar Selecionados ({selectedIds.size})
               </button>
           </div>
           <div className="flex flex-wrap gap-2">
             {COLORS.map(c => (
                 <button
                    key={c.id}
                    onClick={() => setActiveColor(c.hex)}
                    className="w-10 h-10 rounded-full border-2 transition-transform"
                    style={{ 
                        backgroundColor: c.hex, 
                        borderColor: activeColor === c.hex ? '#FFF' : 'transparent',
                        transform: activeColor === c.hex ? 'scale(1.15)' : 'scale(1)',
                        boxShadow: activeColor === c.hex ? '0 0 0 2px ' + c.hex : 'none'
                    }}
                    title={c.label}
                 />
             ))}
           </div>
        </div>

        {/* Filters */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 space-y-3">
            <div className="flex items-center gap-2 text-sm font-bold text-gray-700 dark:text-gray-300 mb-1">
                <Filter size={16}/> Filtros Cascata
            </div>
            
            <div className="grid grid-cols-2 gap-2">
                <input 
                    type="text" placeholder="Bairro..." value={bairroFilter} onChange={e => setBairroFilter(e.target.value)}
                    className="w-full text-sm p-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
                <input 
                    type="text" placeholder="Nome da Rua..." value={streetFilter} onChange={e => setStreetFilter(e.target.value)}
                    className="w-full text-sm p-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
            </div>
            <div className="grid grid-cols-2 gap-2">
                <select 
                    value={numberSideFilter} onChange={e => setNumberSideFilter(e.target.value)}
                    className="w-full text-sm p-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                    <option value="all">Sentido (Todos)</option>
                    <option value="even">Lado Par</option>
                    <option value="odd">Lado Ímpar</option>
                </select>
                <div className="flex gap-2">
                    <input 
                        type="number" placeholder="Raio (m)" value={radiusFilter} onChange={e => setRadiusFilter(e.target.value)}
                        className="w-full text-sm p-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                </div>
            </div>
            {anchorId && (
                <div className="bg-blue-50 dark:bg-blue-900/30 p-2 rounded text-xs flex justify-between items-center text-blue-800 dark:text-blue-300">
                    <span>⚓ Âncora: {packages.find(p=>p.id === anchorId)?.address?.substring(0,25)}...</span>
                    <button onClick={() => setAnchorId(null)} className="font-bold hover:text-red-500">✕</button>
                </div>
            )}
        </div>

        {/* List Header */}
        <div className="px-4 py-2 bg-gray-100 dark:bg-gray-900 flex justify-between items-center border-b border-gray-200 dark:border-gray-700">
            <span className="text-xs font-bold text-gray-500 uppercase">{filteredPackages.length} Pacotes Filtrados</span>
            <button onClick={handleSelectAllFiltered} className="text-blue-600 dark:text-blue-400 text-sm font-bold flex items-center gap-1 hover:underline">
                <CheckSquare size={16}/> Selecionar Todos
            </button>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {filteredPackages.map(pkg => (
                <div 
                    key={pkg.id} 
                    ref={el => listRef.current[pkg.id] = el}
                    onClick={() => handleToggleSelect(pkg.id)}
                    className={`p-3 rounded-xl border transition-all cursor-pointer flex gap-3 items-center
                        ${selectedIds.has(pkg.id) ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-400 shadow-sm' : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-blue-300'}
                    `}
                >
                    <div className="flex-shrink-0">
                       {selectedIds.has(pkg.id) ? <CheckSquare className="text-blue-600"/> : <Square className="text-gray-400"/>}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-bold text-gray-900 dark:text-white truncate">{pkg.address}</p>
                        <p className="text-xs text-gray-500">ID: {pkg.id}</p>
                    </div>
                    {/* Indicador de cor associada */}
                    <div className="flex-shrink-0 flex items-center gap-2">
                        {pkg.assignedColor && (
                           <div className="w-4 h-4 rounded-full shadow-sm" style={{ backgroundColor: pkg.assignedColor }} />
                        )}
                        <button 
                            onClick={(e) => { e.stopPropagation(); setAnchorId(pkg.id); }}
                            className="text-gray-400 hover:text-blue-600" title="Usar como âncora"
                        >
                           <MapPin size={16}/>
                        </button>
                    </div>
                </div>
            ))}
            {filteredPackages.length === 0 && (
                <div className="text-center p-8 text-gray-500">Nenhum pacote corresponde aos filtros.</div>
            )}
        </div>
        
        {/* Footer Actions */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
           <button 
               onClick={handleSaveCreativeRoutes}
               disabled={saving || !packages.some(p => p.assignedColor)}
               className="w-full btn-success flex items-center justify-center gap-2 py-3"
           >
               {saving ? 'Salvando...' : <><Save size={20}/> Confirmar Rotas e Continuar</>}
           </button>
        </div>
      </div>

      {/* RIGHT PANEL: Map */}
      <div className="w-full md:w-2/3 h-[50vh] md:h-full bg-gray-100 rounded-xl overflow-hidden shadow-inner relative border border-gray-200 dark:border-gray-700">
        <MapContainer center={mapCenter} zoom={13} style={{ height: '100%', width: '100%' }}>
            <TileLayer
                url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />
            <MapUpdater center={mapCenter} zoom={13} bounds={mapBounds} />

            {/* Render all points, highlight filtered, colorize assigned */}
            {packages.filter(p => p.lat && p.lng).map(pkg => {
                const isFiltered = filteredPackages.some(fp => fp.id === pkg.id);
                const isSelected = selectedIds.has(pkg.id);
                const color = pkg.assignedColor || (isFiltered ? '#9CA3AF' : '#E5E7EB');
                // Se não está no filtro e não foi pintado, fica quase transparente
                const opacity = (isFiltered || pkg.assignedColor) ? 1.0 : 0.4;

                return (
                    <Marker 
                        key={pkg.id}
                        position={[pkg.lat, pkg.lng]}
                        icon={createMarkerIcon(color, isSelected)}
                        opacity={opacity}
                        eventHandlers={{
                            click: () => handleMarkerClick(pkg.id)
                        }}
                    >
                        <Popup>
                            <div className="p-1">
                                <p className="font-bold text-sm mb-1">{pkg.address}</p>
                                <p className="text-xs text-gray-500 mb-2">ID: {pkg.id}</p>
                                <div className="flex gap-2">
                                    <button 
                                        onClick={() => handleToggleSelect(pkg.id)}
                                        className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs font-bold"
                                    >
                                        {isSelected ? 'Desmarcar' : 'Selecionar'}
                                    </button>
                                    <button 
                                        onClick={() => setAnchorId(pkg.id)}
                                        className="bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs"
                                    >
                                        Usar Âncora
                                    </button>
                                </div>
                            </div>
                        </Popup>
                    </Marker>
                );
            })}
        </MapContainer>
        
        {/* Floating Indicator */}
        <div className="absolute top-4 right-4 z-[1000] bg-white dark:bg-gray-800 p-3 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full border-4 shadow-inner" style={{ borderColor: activeColor, backgroundColor: activeColor + '40' }}></div>
                <div>
                   <p className="text-xs text-gray-500 font-bold uppercase">Cor Ativa</p>
                   <p className="font-bold" style={{color: activeColor}}>{COLORS.find(c => c.hex === activeColor)?.label}</p>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
}
