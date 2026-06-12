import React, { useState, useMemo, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, LayersControl } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Filter, MapPin, CheckSquare, Square, Save, Palette, Layers, PaintBucket, Eye, EyeOff, Navigation2, Crosshair, ChevronDown, ChevronRight } from 'lucide-react';
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

function normalizeStreet(street) {
    if (!street) return 'RUA DESCONHECIDA';
    let s = street.toUpperCase().trim();
    // Remove prefixes
    s = s.replace(/^(RUA|R\.|R\s|AVENIDA|AV\.|AV\s|TRAVESSA|TRV\.|TRV\s|PRAÇA|PRC\.|PRC\s|ALAMEDA|AL\.|AL\s)\s+/i, '');
    // Remove trailing numbers that might be leaked
    s = s.replace(/\s+\d+.*$/, '');
    return s.trim() || 'RUA DESCONHECIDA';
}

function MapUpdater({ center, zoom, bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds && bounds.isValid()) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
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
  const [groupMode, setGroupMode] = useState('bairro'); // Default to bairro grouping as requested
  const [hiddenGroups, setHiddenGroups] = useState(new Set());
  const [collapsedGroups, setCollapsedGroups] = useState(new Set());
  const [numberSideFilter, setNumberSideFilter] = useState('all'); // 'all', 'even', 'odd'
  const [anchorId, setAnchorId] = useState(null);
  const [radiusFilter, setRadiusFilter] = useState('');
  const [proximityMode, setGroupProximityMode] = useState('anchor'); // 'anchor' or 'selection'

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
             let bairro = p.bairro || 'Desconhecido';
             let cep = p.cep || 'Sem CEP';

             // 1. Extract CEP (fallback if not in backend)
             if (cep === 'Sem CEP') {
                const cepMatch = addr.match(/\b\d{5}-?\d{3}\b/);
                if (cepMatch) cep = cepMatch[0];
             }

             // 2. Extract House Number - BETTER HEURISTIC
             const numberAfterComma = addr.match(/,\s*(\d+)/);
             if (numberAfterComma) {
                 number = parseInt(numberAfterComma[1], 10);
             } else {
                 const firstPart = addr.split('-')[0].split('(')[0];
                 const allNums = firstPart.match(/\b\d+\b/g);
                 if (allNums) number = parseInt(allNums[allNums.length - 1], 10);
             }

             // 3. Heuristic splitting for Street (fallback)
             const parts = addr.split(',');
             if (parts.length >= 2) {
                 street = parts[0].trim();
             } else {
                 street = addr.replace(/\s+\d+.*$/, '').trim();
             }

             // Final Normalization
             const cleanStreet = normalizeStreet(street);
             const cleanBairro = (bairro || 'Desconhecido').toUpperCase();

             return {
                 ...p,
                 street: cleanStreet,
                 number,
                 bairro: cleanBairro,
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

  // --- Filtering Logic (Cumulative) ---
  const filteredPackages = useMemo(() => {
    return packages.filter(pkg => {
      // 1. Even/Odd Side
      if (numberSideFilter !== 'all') {
        if (pkg.number === null || isNaN(pkg.number)) return false;
        const isEven = pkg.number % 2 === 0;
        if (numberSideFilter === 'even' && !isEven) return false;
        if (numberSideFilter === 'odd' && isEven) return false;
      }

      // 2. Proximity (Anchor or Selection)
      if (radiusFilter) {
          const radius = parseFloat(radiusFilter);
          if (proximityMode === 'anchor' && anchorId) {
              const anchorPkg = packages.find(p => p.id === anchorId);
              if (anchorPkg && anchorPkg.lat && pkg.lat) {
                  const dist = haversineDistance(anchorPkg, pkg);
                  if (dist > radius) return false;
              }
          } else if (proximityMode === 'selection' && selectedIds.size > 0) {
              const selectedPkgs = packages.filter(p => selectedIds.has(p.id));
              const isNearAny = selectedPkgs.some(sp => {
                  const dist = haversineDistance(sp, pkg);
                  return dist <= radius;
              });
              if (!isNearAny) return false;
          }
      }

      return true;
    });
  }, [packages, numberSideFilter, anchorId, radiusFilter, proximityMode, selectedIds]);

  // --- Grouping Logic ---
  const groupedPackages = useMemo(() => {
    if (groupMode === 'none') return { 'Todos os Pacotes': filteredPackages };
    
    const groups = {};
    filteredPackages.forEach(pkg => {
        let key = 'Outros';
        if (groupMode === 'bairro') key = pkg.bairro || 'Desconhecido';
        if (groupMode === 'street') key = pkg.street || 'RUA DESCONHECIDA';
        if (groupMode === 'cep') key = pkg.cep || 'Sem CEP';
        
        if (!groups[key]) groups[key] = [];
        groups[key].push(pkg);
    });
    
    const sortedGroups = {};
    Object.keys(groups).sort().forEach(k => {
        sortedGroups[k] = groups[k];
    });
    return sortedGroups;
  }, [filteredPackages, groupMode]);

  // --- Map Bounds Calculation ---
  const mapBounds = useMemo(() => {
    const pointsWithCoords = filteredPackages.filter(p => p.lat && p.lng);
    const visiblePoints = pointsWithCoords.filter(pkg => {
        let groupKey = 'none';
        if (groupMode === 'bairro') groupKey = pkg.bairro;
        if (groupMode === 'street') groupKey = pkg.street;
        if (groupMode === 'cep') groupKey = pkg.cep;
        return !hiddenGroups.has(groupKey);
    });

    if (visiblePoints.length === 0) return null;
    return L.latLngBounds(visiblePoints.map(p => [p.lat, p.lng]));
  }, [filteredPackages, groupMode, hiddenGroups]);

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
    const allInGroupSelected = pkgsInGroup.every(p => newSelected.has(p.id));

    if (allInGroupSelected) {
      pkgsInGroup.forEach(p => newSelected.delete(p.id));
    } else {
      pkgsInGroup.forEach(p => newSelected.add(p.id));
    }
    setSelectedIds(newSelected);
  };

  const toggleGroupVisibility = (groupKey) => {
      const newHidden = new Set(hiddenGroups);
      if (newHidden.has(groupKey)) {
          newHidden.delete(groupKey);
      } else {
          newHidden.add(groupKey);
      }
      setHiddenGroups(newHidden);
  };

  const toggleGroupCollapse = (groupKey) => {
      const newCollapsed = new Set(collapsedGroups);
      if (newCollapsed.has(groupKey)) {
          newCollapsed.delete(groupKey);
      } else {
          newCollapsed.add(groupKey);
      }
      setCollapsedGroups(newCollapsed);
  };

  const handleColorClick = (hex) => {
    setActiveColor(hex);
    if (selectedIds.size > 0) {
        const newPackages = packages.map(pkg => {
          if (selectedIds.has(pkg.id)) {
            return { ...pkg, assignedColor: hex };
          }
          return pkg;
        });
        setPackages(newPackages);
        setSelectedIds(new Set()); 
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
            throw new Error("Pinte as rotas no mapa antes de salvar!");
        }

        const res = await fetchWithAuth('/api/routes/creative/save', {
            method: 'POST',
            body: JSON.stringify({
                session_id: sessionId,
                routes: creativeRoutes
            })
        });

        if (!res.ok) throw new Error("Erro ao salvar rotas.");
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
      if (listRef.current[id]) {
          listRef.current[id].scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
  };

  if (loading) return <div className="p-8 text-center text-gray-500 font-semibold animate-pulse">Carregando painel criativo...</div>;

  return (
    <div className="flex flex-col md:flex-row gap-4 h-[85vh]">
      {/* LEFT PANEL */}
      <div className="w-full md:w-1/3 flex flex-col bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden h-full">
        
        {/* Palette */}
        <div className="p-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
           <div className="flex items-center justify-between mb-2">
               <span className="font-bold text-gray-700 dark:text-gray-300 text-xs flex items-center gap-1">
                   <Palette size={14}/> PINCEL DE ROTAS
               </span>
               {selectedIds.size > 0 && (
                   <span className="bg-blue-600 text-white text-[10px] px-2 py-0.5 rounded-full font-bold">
                       {selectedIds.size} selecionados
                   </span>
               )}
           </div>
           <div className="flex flex-wrap gap-1.5">
             {COLORS.map(c => (
                 <button
                    key={c.id}
                    onClick={() => handleColorClick(c.hex)}
                    className="w-8 h-8 rounded-full border-2 transition-all relative"
                    style={{ 
                        backgroundColor: c.hex, 
                        borderColor: activeColor === c.hex ? '#FFF' : 'transparent',
                        transform: activeColor === c.hex ? 'scale(1.1)' : 'scale(1)',
                        boxShadow: activeColor === c.hex ? '0 0 0 2px ' + c.hex : 'none'
                    }}
                    title={c.label}
                 />
             ))}
           </div>
        </div>

        {/* Advanced Filters */}
        <div className="p-3 border-b border-gray-200 dark:border-gray-700 space-y-3">
            <div>
                <p className="text-[10px] font-bold text-gray-400 uppercase mb-2 flex items-center gap-1"><Layers size={12}/> Agrupamento Visual</p>
                <div className="flex bg-gray-100 dark:bg-gray-700 p-1 rounded-lg">
                    {['bairro', 'street', 'cep', 'none'].map(mode => (
                        <button
                            key={mode}
                            onClick={() => setGroupMode(mode)}
                            className={`flex-1 text-[10px] py-1.5 rounded-md font-bold transition-all ${
                                groupMode === mode 
                                    ? 'bg-white dark:bg-gray-600 shadow-sm text-blue-600 dark:text-blue-300' 
                                    : 'text-gray-500 hover:text-gray-700'
                            }`}
                        >
                            {mode === 'bairro' ? 'Bairro' : mode === 'street' ? 'Rua' : mode === 'cep' ? 'CEP' : 'Lista'}
                        </button>
                    ))}
                </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
                <div>
                    <p className="text-[10px] font-bold text-gray-400 uppercase mb-1">Lado da Via</p>
                    <select 
                        value={numberSideFilter} onChange={e => setNumberSideFilter(e.target.value)}
                        className="w-full text-xs font-bold p-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700"
                    >
                        <option value="all">Ambos os Lados</option>
                        <option value="even">Lado PAR</option>
                        <option value="odd">Lado ÍMPAR</option>
                    </select>
                </div>
                <div>
                    <p className="text-[10px] font-bold text-gray-400 uppercase mb-1">Raio de Busca (m)</p>
                    <div className="relative">
                        <input 
                            type="number" placeholder="Distância..." value={radiusFilter} onChange={e => setRadiusFilter(e.target.value)}
                            className="w-full text-xs font-bold p-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 pr-8"
                        />
                        <button 
                            onClick={() => setGroupProximityMode(proximityMode === 'anchor' ? 'selection' : 'anchor')}
                            className={`absolute right-2 top-1/2 -translate-y-1/2 ${proximityMode === 'selection' ? 'text-purple-600' : 'text-gray-400'}`}
                            title={proximityMode === 'selection' ? 'Buscando vizinhos da seleção' : 'Buscando vizinhos da âncora'}
                        >
                            {proximityMode === 'selection' ? <Crosshair size={14}/> : <MapPin size={14}/>}
                        </button>
                    </div>
                </div>
            </div>
            
            {anchorId && proximityMode === 'anchor' && (
                <div className="bg-blue-50 dark:bg-blue-900/20 p-2 rounded flex justify-between items-center text-[10px] text-blue-700 dark:text-blue-300 border border-blue-100 dark:border-blue-800">
                    <span className="truncate">⚓ Âncora: {packages.find(p=>p.id === anchorId)?.address}</span>
                    <button onClick={() => setAnchorId(null)} className="font-bold hover:text-red-500">✕</button>
                </div>
            )}
            {proximityMode === 'selection' && selectedIds.size > 0 && (
                <div className="bg-purple-50 dark:bg-purple-900/20 p-2 rounded flex justify-between items-center text-[10px] text-purple-700 dark:text-purple-300 border border-purple-100 dark:border-purple-800">
                    <span>🎯 Buscando vizinhos de {selectedIds.size} pacotes</span>
                    <button onClick={() => setSelectedIds(new Set())} className="font-bold">Limpar</button>
                </div>
            )}
        </div>

        {/* Package List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-4 bg-gray-50/50 dark:bg-gray-900/20">
            {Object.entries(groupedPackages).map(([groupName, pkgs]) => (
                <div key={groupName} className="space-y-1">
                    {groupMode !== 'none' && (
                        <div className="sticky top-0 z-20 flex items-center justify-between bg-white/80 dark:bg-gray-800/80 backdrop-blur-md px-2 py-1.5 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700 mb-2">
                           <div className="flex items-center gap-2 overflow-hidden flex-1">
                               <button 
                                   onClick={() => toggleGroupCollapse(groupName)} 
                                   className="text-gray-500 hover:text-blue-600 transition-colors"
                               >
                                   {collapsedGroups.has(groupName) ? <ChevronRight size={16}/> : <ChevronDown size={16}/>}
                               </button>
                               <button 
                                   onClick={() => toggleGroupVisibility(groupName)} 
                                   className={`${hiddenGroups.has(groupName) ? 'text-red-400' : 'text-blue-400'} hover:scale-110 transition-transform`}
                                   title={hiddenGroups.has(groupName) ? "Mostrar no mapa" : "Esconder do mapa"}
                               >
                                   {hiddenGroups.has(groupName) ? <EyeOff size={14}/> : <Eye size={14}/>}
                               </button>
                               <span className={`text-xs font-bold truncate ${hiddenGroups.has(groupName) ? 'text-gray-400 line-through' : 'text-gray-700 dark:text-gray-200'}`}>
                                   {groupName}
                               </span>
                               <span className="text-[10px] text-gray-400 font-bold bg-gray-100 dark:bg-gray-700 px-1.5 rounded">{pkgs.length}</span>
                           </div>
                           <button onClick={() => handleSelectGroup(pkgs)} className="text-blue-600 hover:scale-110 transition-transform ml-2">
                              <CheckSquare size={16}/>
                           </button>
                        </div>
                    )}
                    
                    {!collapsedGroups.has(groupName) && pkgs.map(pkg => (
                        <div 
                            key={pkg.id} 
                            ref={el => listRef.current[pkg.id] = el}
                            onClick={() => handleToggleSelect(pkg.id)}
                            className={`group p-2 rounded-lg border transition-all cursor-pointer flex gap-3 items-center
                                ${selectedIds.has(pkg.id) ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-400' : 'bg-white dark:bg-gray-800 border-gray-100 dark:border-gray-700 hover:border-gray-300'}
                            `}
                        >
                            <div className="flex-shrink-0">
                               {selectedIds.has(pkg.id) ? <CheckSquare size={18} className="text-blue-600"/> : <Square size={18} className="text-gray-300"/>}
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-xs font-bold text-gray-800 dark:text-gray-100 truncate">{pkg.address}</p>
                                <div className="flex items-center gap-1.5 mt-0.5">
                                    {pkg.number && <span className="text-[9px] font-bold text-blue-500 bg-blue-50 dark:bg-blue-900/30 px-1 rounded">Nº {pkg.number}</span>}
                                    <span className="text-[9px] text-gray-400">{pkg.cep}</span>
                                </div>
                            </div>
                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button onClick={(e) => { e.stopPropagation(); setAnchorId(pkg.id); setGroupProximityMode('anchor'); }} className="p-1 hover:text-blue-600 text-gray-400"><MapPin size={14}/></button>
                                <button onClick={(e) => { e.stopPropagation(); handleQuickPaint(pkg.id); }} className="w-5 h-5 rounded-full border shadow-sm" style={{ backgroundColor: pkg.assignedColor || '#eee' }}></button>
                            </div>
                        </div>
                    ))}
                </div>
            ))}
        </div>
        
        <div className="p-3 border-t border-gray-200 dark:border-gray-700">
           <button 
               onClick={handleSaveCreativeRoutes}
               disabled={saving || !packages.some(p => p.assignedColor)}
               className="w-full btn-success flex items-center justify-center gap-2 py-2.5 text-sm font-bold shadow-lg"
           >
               {saving ? 'Salvando...' : <><Save size={18}/> Finalizar e Roteirizar</>}
           </button>
        </div>
      </div>

      {/* RIGHT PANEL - MAP */}
      <div className="w-full md:w-2/3 bg-gray-100 dark:bg-gray-900 rounded-xl overflow-hidden relative shadow-inner border border-gray-200 dark:border-gray-700">
        <MapContainer center={mapCenter} zoom={13} style={{ height: '100%', width: '100%' }}>
            <LayersControl position="topright">
                <LayersControl.BaseLayer name="Mapa Suave (Voyager)" checked>
                    <TileLayer url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png" />
                </LayersControl.BaseLayer>
                <LayersControl.BaseLayer name="Mapa Detalhado (OSM - Direções)">
                    <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                </LayersControl.BaseLayer>
                <LayersControl.BaseLayer name="Satélite">
                    <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />
                </LayersControl.BaseLayer>
                <LayersControl.Overlay name="Sentido das Vias" checked>
                    <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" opacity={0.4} />
                </LayersControl.Overlay>
            </LayersControl>

            <MapUpdater center={mapCenter} zoom={13} bounds={mapBounds} />

            {packages.map(pkg => {
                // Determine if markers should be hidden based on group
                let groupKey = 'none';
                if (groupMode === 'bairro') groupKey = pkg.bairro;
                if (groupMode === 'street') groupKey = pkg.street;
                if (groupMode === 'cep') groupKey = pkg.cep;
                
                const isHiddenByGroup = hiddenGroups.has(groupKey);
                if (isHiddenByGroup) return null;

                const isFiltered = filteredPackages.some(fp => fp.id === pkg.id);
                const isSelected = selectedIds.has(pkg.id);
                const color = pkg.assignedColor || (isFiltered ? '#3B82F6' : '#E5E7EB');
                const opacity = (isFiltered || pkg.assignedColor) ? 1.0 : 0.2;

                if (!pkg.lat || !pkg.lng) return null;

                return (
                    <Marker 
                        key={pkg.id}
                        position={[pkg.lat, pkg.lng]}
                        icon={createMarkerIcon(color, isSelected)}
                        opacity={opacity}
                        eventHandlers={{ click: () => handleMarkerClick(pkg.id) }}
                    >
                        <Popup>
                            <div className="p-1 min-w-[150px]">
                                <p className="font-bold text-xs mb-1">{pkg.address}</p>
                                <div className="flex gap-1.5 mt-2">
                                    <button 
                                        onClick={() => handleToggleSelect(pkg.id)}
                                        className="flex-1 bg-gray-100 text-gray-700 px-2 py-1 rounded text-[10px] font-bold"
                                    >
                                        {isSelected ? 'Desmarcar' : 'Selecionar'}
                                    </button>
                                    <button 
                                        onClick={() => handleQuickPaint(pkg.id)}
                                        className="flex-1 text-white px-2 py-1 rounded text-[10px] font-bold flex items-center justify-center gap-1"
                                        style={{ backgroundColor: activeColor }}
                                    >
                                        <PaintBucket size={10} /> Pintar
                                    </button>
                                </div>
                            </div>
                        </Popup>
                    </Marker>
                );
            })}
        </MapContainer>
        
        {/* Help Overlay */}
        <div className="absolute bottom-4 left-4 z-[1000] bg-white/90 dark:bg-gray-800/90 p-2 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 text-[10px] pointer-events-none">
            <p className="font-bold text-gray-500 mb-1 flex items-center gap-1"><Navigation2 size={10}/> DICA LOGÍSTICA</p>
            <p className="text-gray-400">Use o mapa **OSM** para ver setas de sentido único em zoom alto.</p>
        </div>
      </div>
    </div>
  );
}
