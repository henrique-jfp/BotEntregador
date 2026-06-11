import React, { useState, useMemo, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Filter, MapPin, CheckSquare, Square, Save, Palette, Layers, PaintBucket } from 'lucide-react';
import { fetchWithAuth } from '../api_client';

// Palette Colors
const COLORS = [
  { id: 'blue', hex: '#3B82F6', label: '🔵 Azul' },
  { id: 'green', hex: '#10B981', label: '🟢 Verde' },
  { id: 'yellow', hex: '#F59E0B', label: '🟡 Amarelo' },
  { id: 'red', hex: '#EF4444', label: '🔴 Vermelho' },
  { id: 'purple', hex: '#8B5CF6', label: '🟣 Roxo' },
  { id: 'orange', hex: '#F97316', label: '🟠 Laranja' },
  { id: 'pink', hex: '#EC4899', label: '🦩 Rosa' },
  { id: 'teal', hex: '#14B8A6', label: '🩵 Turquesa' },
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
  
  // State: Filters & Grouping
  const [groupMode, setGroupMode] = useState('none'); // 'none', 'bairro', 'street', 'cep'
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
        const mapRes = await fetchWithAuth(`/map/realtime/${sessionId}`);
        const mapData = await mapRes.json();
        
        if (mapData.points) {
          const pkgs = mapData.points.map(p => {
             const addr = p.address || '';
             let street = addr;
             let number = null;
             let bairro = 'Desconhecido';
             let cep = 'Sem CEP';

             // Regex extractions
             const cepMatch = addr.match(/\b\d{5}-?\d{3}\b/);
             if (cepMatch) cep = cepMatch[0];

             const numMatch = addr.match(/\b\d+\b/);
             if (numMatch) number = parseInt(numMatch[0], 10);

             // Heuristic splitting
             const parts = addr.split(',');
             if (parts.length >= 3) {
                 street = parts[0].trim();
                 bairro = /\d/.test(parts[1]) && parts[2] ? parts[2].trim() : parts[1].trim();
                 bairro = bairro.split('-')[0].trim(); // Remove state if trailing
             } else if (parts.length === 2) {
                 street = parts[0].trim();
                 bairro = parts[1].replace(cep, '').trim() || 'Desconhecido';
             } else {
                 street = addr.replace(/\b\d+\b/g, '').replace(cep, '').trim();
             }

             if (street.length > 40) street = street.substring(0, 40) + '...';
             if (bairro.length > 25) bairro = bairro.substring(0, 25);

             return {
                 ...p,
                 street,
                 number,
                 bairro,
                 cep,
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
      // Even/Odd
      if (numberSideFilter !== 'all') {
        if (pkg.number === null || isNaN(pkg.number)) return false;
        const isEven = pkg.number % 2 === 0;
        if (numberSideFilter === 'even' && !isEven) return false;
        if (numberSideFilter === 'odd' && isEven) return false;
      }

      // Proximity
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
  }, [packages, numberSideFilter, anchorId, radiusFilter]);

  // --- Grouping Logic ---
  const groupedPackages = useMemo(() => {
    if (groupMode === 'none') return { 'Todos os Pacotes': filteredPackages };
    
    const groups = {};
    filteredPackages.forEach(pkg => {
        let key = 'Outros';
        if (groupMode === 'bairro') key = pkg.bairro || 'Desconhecido';
        if (groupMode === 'street') key = pkg.street || 'Rua Desconhecida';
        if (groupMode === 'cep') key = pkg.cep || 'Sem CEP';
        
        if (!groups[key]) groups[key] = [];
        groups[key].push(pkg);
    });
    
    // Sort alphabetically
    const sortedGroups = {};
    Object.keys(groups).sort().forEach(k => {
        sortedGroups[k] = groups[k];
    });
    return sortedGroups;
  }, [filteredPackages, groupMode]);

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

  const handleSelectGroup = (pkgsInGroup) => {
    const newSelected = new Set(selectedIds);
    let allSelected = true;
    for (const pkg of pkgsInGroup) {
      if (!newSelected.has(pkg.id)) {
        allSelected = false;
        break;
      }
    }

    if (allSelected) {
      pkgsInGroup.forEach(p => newSelected.delete(p.id));
    } else {
      pkgsInGroup.forEach(p => newSelected.add(p.id));
    }
    setSelectedIds(newSelected);
  };

  const handleColorClick = (hex) => {
    setActiveColor(hex);
    // Instant Paint!
    if (selectedIds.size > 0) {
        const newPackages = packages.map(pkg => {
          if (selectedIds.has(pkg.id)) {
            return { ...pkg, assignedColor: hex };
          }
          return pkg;
        });
        setPackages(newPackages);
        setSelectedIds(new Set()); // Auto clear after painting for rapid workflow
    }
  };

  const handleQuickPaint = (pkgId) => {
    const newPackages = packages.map(pkg => {
        if (pkg.id === pkgId) {
            return { ...pkg, assignedColor: activeColor };
        }
        return pkg;
    });
    setPackages(newPackages);
  };

  const handleSaveCreativeRoutes = async () => {
    setSaving(true);
    try {
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

        if (creativeRoutes.length === 0) {
            throw new Error("Nenhuma rota foi pintada! Associe cores aos pacotes antes de salvar.");
        }

        const res = await fetchWithAuth('/api/routes/creative/save', {
            method: 'POST',
            body: JSON.stringify({
                session_id: sessionId,
                routes: creativeRoutes
            })
        });

        if (!res.ok) throw new Error("Erro ao salvar rotas manuais.");
        
        alert("Rotas manuais consolidadas com sucesso!");
        if (onSaved) onSaved();

    } catch (e) {
        alert(e.message);
    } finally {
        setSaving(false);
    }
  };

  const handleMarkerClick = (id) => {
      handleToggleSelect(id);
      if (listRef.current[id]) {
          listRef.current[id].scrollIntoView({ behavior: 'smooth', block: 'center' });
          listRef.current[id].classList.add('bg-blue-100', 'dark:bg-blue-900/40');
          setTimeout(() => {
              if (listRef.current[id]) listRef.current[id].classList.remove('bg-blue-100', 'dark:bg-blue-900/40');
          }, 1500);
      }
  };

  if (loading) return <div className="p-8 text-center text-gray-500 font-semibold animate-pulse">Carregando mapa logístico...</div>;

  return (
    <div className="flex flex-col md:flex-row gap-6 h-[80vh]">
      {/* LEFT PANEL: Filters & List */}
      <div className="w-full md:w-1/3 flex flex-col bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden h-full">
        
        {/* Color Palette Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
           <div className="flex items-center justify-between mb-3">
               <span className="font-bold text-gray-700 dark:text-gray-300 text-sm flex items-center gap-2">
                   <Palette size={16}/> Paleta de Cores
               </span>
               <span className="text-xs text-gray-500">Selecione e clique na cor</span>
           </div>
           <div className="flex flex-wrap gap-2">
             {COLORS.map(c => (
                 <button
                    key={c.id}
                    onClick={() => handleColorClick(c.hex)}
                    className="w-10 h-10 rounded-full border-2 transition-transform relative group"
                    style={{ 
                        backgroundColor: c.hex, 
                        borderColor: activeColor === c.hex ? '#FFF' : 'transparent',
                        transform: activeColor === c.hex ? 'scale(1.15)' : 'scale(1)',
                        boxShadow: activeColor === c.hex ? '0 0 0 2px ' + c.hex : 'none'
                    }}
                    title={c.label}
                 >
                     {/* Indicator if active and packages are selected */}
                     {activeColor === c.hex && selectedIds.size > 0 && (
                         <span className="absolute -top-2 -right-2 bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full shadow-md animate-bounce">
                             Pintar
                         </span>
                     )}
                 </button>
             ))}
           </div>
        </div>

        {/* Grouping and Filters */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 space-y-4">
            <div className="flex items-center gap-2 text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">
                <Layers size={16}/> Agrupar Visualmente por:
            </div>
            
            <div className="grid grid-cols-4 gap-2">
                {['none', 'bairro', 'street', 'cep'].map(mode => (
                    <button
                        key={mode}
                        onClick={() => setGroupMode(mode)}
                        className={`text-xs py-2 px-1 rounded-lg font-bold transition-colors border ${
                            groupMode === mode 
                                ? 'bg-blue-100 border-blue-500 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 dark:border-blue-600' 
                                : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-300'
                        }`}
                    >
                        {mode === 'none' && 'Lista'}
                        {mode === 'bairro' && 'Bairro'}
                        {mode === 'street' && 'Rua'}
                        {mode === 'cep' && 'CEP'}
                    </button>
                ))}
            </div>

            <div className="grid grid-cols-2 gap-2 mt-2">
                <select 
                    value={numberSideFilter} onChange={e => setNumberSideFilter(e.target.value)}
                    className="w-full text-xs font-bold p-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                    <option value="all">Lado da Via (Todos)</option>
                    <option value="even">Apenas Par</option>
                    <option value="odd">Apenas Ímpar</option>
                </select>
                <div className="flex gap-2">
                    <input 
                        type="number" placeholder="Raio âncora (m)" value={radiusFilter} onChange={e => setRadiusFilter(e.target.value)}
                        className="w-full text-xs font-bold p-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        title="Distância máxima a partir do pacote âncora"
                    />
                </div>
            </div>
            {anchorId && (
                <div className="bg-blue-50 dark:bg-blue-900/30 p-2 rounded text-xs flex justify-between items-center text-blue-800 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                    <span>⚓ Âncora Ativa: {packages.find(p=>p.id === anchorId)?.street?.substring(0,20)}...</span>
                    <button onClick={() => setAnchorId(null)} className="font-bold hover:text-red-500">✕ Remover</button>
                </div>
            )}
        </div>

        {/* List Header */}
        <div className="px-4 py-2 bg-gray-100 dark:bg-gray-900 flex justify-between items-center border-b border-gray-200 dark:border-gray-700">
            <span className="text-xs font-bold text-gray-500 uppercase">{filteredPackages.length} Pacotes Exibidos</span>
            <button onClick={() => handleSelectGroup(filteredPackages)} className="text-blue-600 dark:text-blue-400 text-xs font-bold flex items-center gap-1 hover:underline">
                <CheckSquare size={14}/> Selecionar Exibidos
            </button>
        </div>

        {/* List (Grouped) */}
        <div className="flex-1 overflow-y-auto p-3 space-y-4 bg-gray-50 dark:bg-gray-800/20">
            {Object.entries(groupedPackages).map(([groupName, pkgs]) => (
                <div key={groupName} className="space-y-2">
                    {/* Group Header */}
                    {groupMode !== 'none' && (
                        <div className="sticky top-0 bg-gray-200/90 dark:bg-gray-700/90 backdrop-blur-sm px-3 py-2 font-bold text-sm text-gray-800 dark:text-gray-200 rounded-lg flex justify-between items-center shadow-sm z-10">
                           <span className="truncate pr-2">{groupName}</span>
                           <div className="flex items-center gap-3 shrink-0">
                               <span className="bg-white dark:bg-gray-800 px-2 py-0.5 rounded text-xs shadow-sm">{pkgs.length} pct</span>
                               <button onClick={() => handleSelectGroup(pkgs)} className="text-blue-600 hover:text-blue-800">
                                  <CheckSquare size={16}/>
                               </button>
                           </div>
                        </div>
                    )}
                    
                    {/* Packages in Group */}
                    {pkgs.map(pkg => (
                        <div 
                            key={pkg.id} 
                            ref={el => listRef.current[pkg.id] = el}
                            onClick={() => handleToggleSelect(pkg.id)}
                            className={`p-3 rounded-xl border transition-all cursor-pointer flex gap-3 items-center shadow-sm
                                ${selectedIds.has(pkg.id) ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-400' : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-gray-300'}
                            `}
                        >
                            <div className="flex-shrink-0 mt-1 self-start">
                               {selectedIds.has(pkg.id) ? <CheckSquare className="text-blue-600"/> : <Square className="text-gray-400"/>}
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-bold text-gray-900 dark:text-white leading-tight">{pkg.address}</p>
                                <div className="flex items-center gap-2 mt-1">
                                    <span className="text-xs text-gray-500 font-mono">#{pkg.id.substring(0,6)}</span>
                                    {pkg.cep && <span className="text-[10px] bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded text-gray-500">{pkg.cep}</span>}
                                    {pkg.number && <span className="text-[10px] bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-300 px-1.5 py-0.5 rounded border border-blue-100 dark:border-blue-800">Nº {pkg.number}</span>}
                                </div>
                            </div>
                            
                            {/* Ferramentas do Pacote: Âncora e Pintura Rápida */}
                            <div className="flex-shrink-0 flex flex-col items-center justify-between gap-2 h-full">
                                <button 
                                    onClick={(e) => { e.stopPropagation(); setAnchorId(pkg.id); }}
                                    className={`p-1.5 rounded-full transition-colors ${anchorId === pkg.id ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:bg-gray-100 hover:text-blue-600'}`}
                                    title="Usar como Ponto Âncora"
                                >
                                   <MapPin size={14}/>
                                </button>

                                <button 
                                    onClick={(e) => { e.stopPropagation(); handleQuickPaint(pkg.id); }}
                                    className="w-6 h-6 rounded-full border border-gray-300 hover:scale-110 transition-transform flex items-center justify-center relative overflow-hidden shadow-inner"
                                    style={{ backgroundColor: pkg.assignedColor || 'transparent' }}
                                    title="Pintar com a cor atual"
                                >
                                    {!pkg.assignedColor && <PaintBucket size={12} className="text-gray-300"/>}
                                </button>
                            </div>
                        </div>
                    ))}
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
               {saving ? 'Consolidando Rotas...' : <><Save size={20}/> Confirmar Manchas e Continuar</>}
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
                
                // Opacidade para destacar o que está no filtro atual
                const opacity = (isFiltered || pkg.assignedColor) ? 1.0 : 0.3;

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
                                <p className="text-xs text-gray-500 mb-2">ID: {pkg.id.substring(0,8)}... | {pkg.cep}</p>
                                <div className="flex gap-2">
                                    <button 
                                        onClick={() => handleToggleSelect(pkg.id)}
                                        className="bg-blue-100 text-blue-700 px-3 py-1.5 rounded text-xs font-bold"
                                    >
                                        {isSelected ? 'Desmarcar' : 'Selecionar'}
                                    </button>
                                    <button 
                                        onClick={() => handleQuickPaint(pkg.id)}
                                        className="text-white px-3 py-1.5 rounded text-xs font-bold flex items-center gap-1"
                                        style={{ backgroundColor: activeColor }}
                                    >
                                        <PaintBucket size={12} /> Pintar
                                    </button>
                                </div>
                            </div>
                        </Popup>
                    </Marker>
                );
            })}
        </MapContainer>
        
        {/* Floating Indicator */}
        <div className="absolute top-4 right-4 z-[1000] bg-white dark:bg-gray-800 p-3 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 pointer-events-none">
            <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full border-4 shadow-inner" style={{ borderColor: activeColor, backgroundColor: activeColor + '40' }}></div>
                <div>
                   <p className="text-xs text-gray-500 font-bold uppercase">Cor Ativa (Pincel)</p>
                   <p className="font-bold" style={{color: activeColor}}>{COLORS.find(c => c.hex === activeColor)?.label}</p>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
}