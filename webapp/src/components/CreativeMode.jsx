import React, { useState, useMemo, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, LayersControl } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Filter, MapPin, CheckSquare, Square, Save, Palette, Layers, PaintBucket, Eye, EyeOff, Navigation2, Crosshair, ChevronDown, ChevronRight, List as ListIcon, Map as MapIcon, Search, Eraser } from 'lucide-react';
import { fetchWithAuth } from '../api_client';
import { ROUTE_COLORS, normalizeRouteColor } from '../lib/routePalette';

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
    
    // 1. Normalização básica e remoção de acentos inicial
    let s = street.toUpperCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .trim();
    
    // 2. Remove parênteses e conteúdo (e.g., "(PORTARIA)")
    s = s.replace(/\s*\(.*?\)/g, '').replace(/\(+/g, '');
    
    // 3. Remove prefixos comuns (Rua, Av, etc)
    s = s.replace(/^(RUA|R\.|R\s+|AVENIDA|AV\.|AV\s+|TRAVESSA|TRV\.|TRV\s+|PRACA|PRC\.|PRC\s+|ALAMEDA|AL\.|AL\s+|LADEIRA|ESTRADA|EST\.|EST\s+|BECO|VILA|RODOVIA|ROD\.|ROD\s+)\s+/i, '');
    
    // 4. Remove preposições de início (DO, DA, DOS, DAS, DE)
    s = s.replace(/^(DO|DA|DE|DOS|DAS)\s+/i, '');
    
    // 5. Remove indicadores de número e variações no fim da string
    s = s.replace(/\s+(Nº|N°|N\.|NUMERO|NO|N\s*|NUM|NR\.?)$/i, '');
    s = s.replace(/,\s*S\/N\.?$/i, ''); // Sem número
    
    // 6. Remove números soltos que sobraram no final (leaks de endereço)
    s = s.replace(/\s+\d+.*$/, '');
    
    // 7. Limpeza final de caracteres não alfanuméricos extras
    s = s.replace(/[^\w\s]/gi, '').trim();
    
    return s || 'RUA DESCONHECIDA';
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

export default function CreativeMode({ sessionId, sessionBase, onSaved, initialBlank = false }) {
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // State: Tools
  const [activeColor, setActiveColor] = useState(ROUTE_COLORS[0].hex);
  const [selectedIds, setSelectedIds] = useState(new Set());
  
  // State: Filters & Grouping
  const [groupMode, setGroupMode] = useState('bairro'); // Default to bairro grouping
  const [searchTerm, setSearchTerm] = useState('');
  const [colorFilter, setColorFilter] = useState('all');
  const [hiddenGroups, setHiddenGroups] = useState(new Set());
  const [collapsedGroups, setCollapsedGroups] = useState(new Set());
  const [numberSideFilter, setNumberSideFilter] = useState('all'); // 'all', 'even', 'odd'
  const [anchorId, setAnchorId] = useState(null);
  const [radiusFilter, setRadiusFilter] = useState('');
  const [proximityMode, setGroupProximityMode] = useState('anchor'); // 'anchor' or 'selection'

  // State: Mobile View Control
  const [mobileView, setMobileView] = useState('list'); // 'list' or 'map'

  // Refs for scrolling
  const listRef = useRef({});

  useEffect(() => {
    if (sessionId) {
      loadPackages();
    }
  }, [sessionId, initialBlank]);

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
             let bairro = (p.bairro || 'Desconhecido').toUpperCase();
             let cep = p.cep || 'Sem CEP';

             // 1. Extract CEP (fallback)
             if (cep === 'Sem CEP') {
                const cepMatch = addr.match(/\b\d{5}-?\d{3}\b/);
                if (cepMatch) cep = cepMatch[0];
             }

             // 2. Extract House Number
             const numberAfterComma = addr.match(/,\s*(\d+)/);
             if (numberAfterComma) {
                 number = parseInt(numberAfterComma[1], 10);
             } else {
                 const firstPart = addr.split('-')[0].split('(')[0];
                 const allNums = firstPart.match(/\b\d+\b/g);
                 if (allNums) number = parseInt(allNums[allNums.length - 1], 10);
             }

             // 3. Street Extraction
             const parts = addr.split(',');
             if (parts.length >= 2) {
                 street = parts[0].trim();
             } else {
                 street = addr.replace(/\s+\d+.*$/, '').trim();
             }

             const cleanStreet = normalizeStreet(street);

             return {
                 ...p,
                 package_id: p.package_id || p.id,
                 street: cleanStreet,
                 number,
                 bairro,
                 cep,
                 assignedColor: !initialBlank && p.route_id !== 'unassigned' ? normalizeRouteColor(p.route_color) : null,
                 assignedRouteId: !initialBlank && p.route_id !== 'unassigned' ? p.route_id : null
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

  // --- Filtering & Grouping Logic ---
  const filteredPackages = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toUpperCase();
    return packages.filter(pkg => {
      if (normalizedSearch) {
        const haystack = [
          pkg.address,
          pkg.street,
          pkg.bairro,
          pkg.cep,
          pkg.id,
          pkg.package_id,
        ].filter(Boolean).join(' ').toUpperCase();
        if (!haystack.includes(normalizedSearch)) return false;
      }

      if (colorFilter === 'unassigned' && pkg.assignedColor) return false;
      if (colorFilter === 'assigned' && !pkg.assignedColor) return false;
      if (colorFilter.startsWith('#') && normalizeRouteColor(pkg.assignedColor) !== colorFilter) return false;

      if (numberSideFilter !== 'all') {
        if (pkg.number === null || isNaN(pkg.number)) return false;
        const isEven = pkg.number % 2 === 0;
        if (numberSideFilter === 'even' && !isEven) return false;
        if (numberSideFilter === 'odd' && isEven) return false;
      }
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
              const isNearAny = selectedPkgs.some(sp => haversineDistance(sp, pkg) <= radius);
              if (!isNearAny) return false;
          }
      }
      return true;
    });
  }, [packages, searchTerm, colorFilter, numberSideFilter, anchorId, radiusFilter, proximityMode, selectedIds]);

  const filteredIds = useMemo(() => new Set(filteredPackages.map(pkg => pkg.id)), [filteredPackages]);

  const routeStats = useMemo(() => {
    const stats = {
      total: packages.length,
      filtered: filteredPackages.length,
      selected: selectedIds.size,
      unassigned: packages.filter(pkg => !pkg.assignedColor).length,
      byColor: {}
    };
    ROUTE_COLORS.forEach(color => {
      stats.byColor[color.hex] = packages.filter(pkg => normalizeRouteColor(pkg.assignedColor) === color.hex).length;
    });
    return stats;
  }, [packages, filteredPackages.length, selectedIds.size]);

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
    Object.keys(groups).sort().forEach(k => { sortedGroups[k] = groups[k]; });
    return sortedGroups;
  }, [filteredPackages, groupMode]);

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
    if (sessionBase?.lat && sessionBase?.lng) return [sessionBase.lat, sessionBase.lng];
    return [-22.9068, -43.1729];
  }, [sessionBase]);

  // --- Actions ---
  const handleToggleSelect = (id) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) newSelected.delete(id);
    else newSelected.add(id);
    setSelectedIds(newSelected);
  };

  const handleSelectGroup = (pkgs) => {
    const newSelected = new Set(selectedIds);
    const allInGroupSelected = pkgs.every(p => selectedIds.has(p.id));
    pkgs.forEach(p => {
        if (allInGroupSelected) newSelected.delete(p.id);
        else newSelected.add(p.id);
    });
    setSelectedIds(newSelected);
  };

  const handleColorClick = (hex) => {
    setActiveColor(hex);
    if (selectedIds.size > 0) {
        const newPkgs = packages.map(p => {
            if (selectedIds.has(p.id)) return { ...p, assignedColor: hex, assignedRouteId: null };
            return p;
        });
        setPackages(newPkgs);
        setSelectedIds(new Set());
    }
  };

  const handleSelectFiltered = () => {
      setSelectedIds(prev => {
          const allFilteredSelected = filteredPackages.length > 0 && filteredPackages.every(pkg => prev.has(pkg.id));
          const next = new Set(prev);
          filteredPackages.forEach(pkg => {
              if (allFilteredSelected) next.delete(pkg.id);
              else next.add(pkg.id);
          });
          return next;
      });
  };

  const handlePaintFiltered = () => {
      if (filteredPackages.length === 0) return;
      setPackages(prev => prev.map(pkg => (
          filteredIds.has(pkg.id) ? { ...pkg, assignedColor: activeColor, assignedRouteId: null } : pkg
      )));
      setSelectedIds(new Set());
  };

  const handleClearFiltered = () => {
      if (filteredPackages.length === 0) return;
      setPackages(prev => prev.map(pkg => (
          filteredIds.has(pkg.id) ? { ...pkg, assignedColor: null, assignedRouteId: null } : pkg
      )));
      setSelectedIds(new Set());
  };

  const handlePaintSelected = () => {
      if (selectedIds.size === 0) return;
      setPackages(prev => prev.map(pkg => (
          selectedIds.has(pkg.id) ? { ...pkg, assignedColor: activeColor, assignedRouteId: null } : pkg
      )));
      setSelectedIds(new Set());
  };

  const handleClearFilters = () => {
      setSearchTerm('');
      setColorFilter('all');
      setNumberSideFilter('all');
      setRadiusFilter('');
      setAnchorId(null);
      setHiddenGroups(new Set());
  };

  const handleQuickPaint = (id) => {
      const newPkgs = packages.map(p => {
          if (p.id === id) return { ...p, assignedColor: activeColor, assignedRouteId: null };
          return p;
      });
      setPackages(newPkgs);
  };

  const toggleGroupVisibility = (groupName) => {
      const newHidden = new Set(hiddenGroups);
      if (newHidden.has(groupName)) newHidden.delete(groupName);
      else newHidden.add(groupName);
      setHiddenGroups(newHidden);
  };

  const toggleGroupCollapse = (groupName) => {
      const newCollapsed = new Set(collapsedGroups);
      if (newCollapsed.has(groupName)) newCollapsed.delete(groupName);
      else newCollapsed.add(groupName);
      setCollapsedGroups(newCollapsed);
  };

  const handleSaveCreativeRoutes = async () => {
    setSaving(true);
    try {
        const coloredPackages = packages.filter(p => p.assignedColor);
        const routesMap = {};
        coloredPackages.forEach(p => {
            if (!routesMap[p.assignedColor]) routesMap[p.assignedColor] = [];
            // Força a conversão para string, pois o backend (List[str]) exige string
            routesMap[p.assignedColor].push(String(p.package_id || p.id));
        });
        const creativeRoutes = Object.entries(routesMap).map(([color, ids], idx) => ({
            id: `CREATIVE_${idx + 1}`,
            color: color,
            package_ids: ids
            // Removidos campos null explícitos que podem falhar na validação
        }));
        
        console.log("Enviando rotas criativas:", { session_id: sessionId, routes: creativeRoutes });
        
        const res = await fetchWithAuth('/api/routes/creative/save', {
            method: 'POST',
            body: JSON.stringify({ session_id: String(sessionId), routes: creativeRoutes })
        });
        
        if (!res.ok) {
           const errText = await res.text();
           console.error("Erro 422 do backend:", errText);
           throw new Error(`Erro ao salvar rotas: ${errText.slice(0,100)}`);
        }
        const savedRoutes = await res.json();
        alert("Rotas salvas com sucesso!");
        if (onSaved) onSaved(savedRoutes);
    } catch (e) { alert(e.message); } finally { setSaving(false); }
  };

  const handleMarkerClick = (id) => {
      handleToggleSelect(id);
      if (listRef.current[id]) {
          listRef.current[id].scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      if (window.innerWidth < 768) { setMobileView('list'); }
  };

  if (loading) return <div className="p-8 text-center text-gray-500 font-semibold animate-pulse">Carregando painel criativo...</div>;

  return (
    <div className="flex flex-col md:flex-row gap-4 h-[85vh] relative">
      
      {/* MOBILE TOGGLE (Floating) */}
      <div className="md:hidden flex bg-white dark:bg-gray-800 p-1 rounded-full shadow-xl border border-gray-200 dark:border-gray-700 absolute bottom-24 left-1/2 -translate-x-1/2 z-[1001] w-48">
          <button 
              onClick={() => setMobileView('list')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-full text-xs font-bold transition-all ${mobileView === 'list' ? 'bg-blue-600 text-white shadow-md' : 'text-gray-500'}`}
          >
              <ListIcon size={16}/> Lista
          </button>
          <button 
              onClick={() => setMobileView('map')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-full text-xs font-bold transition-all ${mobileView === 'map' ? 'bg-blue-600 text-white shadow-md' : 'text-gray-500'}`}
          >
              <MapIcon size={16}/> Mapa
          </button>
      </div>

      {/* LEFT PANEL - LIST */}
      <div className={`w-full md:w-1/3 flex flex-col bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden h-full ${mobileView === 'map' ? 'hidden md:flex' : 'flex'}`}>
        
        {/* Palette */}
        <div className="p-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
           <div className="flex items-center justify-between mb-2">
               <span className="font-bold text-gray-700 dark:text-gray-300 text-[10px] md:text-xs flex items-center gap-1 uppercase tracking-wider">
                   <Palette size={14}/> Pincel de Rotas
               </span>
               {selectedIds.size > 0 && (
                   <span className="bg-blue-600 text-white text-[10px] px-2 py-0.5 rounded-full font-bold animate-bounce">
                       {selectedIds.size} selecionados
                   </span>
               )}
           </div>
           <div className="flex flex-wrap gap-2">
             {ROUTE_COLORS.map(c => (
                 <button
                    key={c.id}
                    onClick={() => handleColorClick(c.hex)}
                    className="w-8 h-8 md:w-9 md:h-9 rounded-full border-2 transition-all relative"
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
           <div className="grid grid-cols-4 gap-2 mt-3 text-center">
             <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 py-1">
               <p className="text-[9px] text-gray-400 font-bold uppercase">Total</p>
               <p className="text-xs font-black text-gray-700 dark:text-gray-200">{routeStats.total}</p>
             </div>
             <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 py-1">
               <p className="text-[9px] text-gray-400 font-bold uppercase">Filtro</p>
               <p className="text-xs font-black text-blue-600">{routeStats.filtered}</p>
             </div>
             <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 py-1">
               <p className="text-[9px] text-gray-400 font-bold uppercase">Sem rota</p>
               <p className="text-xs font-black text-amber-600">{routeStats.unassigned}</p>
             </div>
             <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 py-1">
               <p className="text-[9px] text-gray-400 font-bold uppercase">Selecion.</p>
               <p className="text-xs font-black text-purple-600">{routeStats.selected}</p>
             </div>
           </div>
        </div>

        {/* Filters */}
        <div className="p-3 border-b border-gray-200 dark:border-gray-700 space-y-3 bg-white dark:bg-gray-800">
            <div>
                <p className="text-[10px] font-bold text-gray-400 uppercase mb-1 flex items-center gap-1"><Search size={12}/> Buscar</p>
                <input
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                    placeholder="Endereço, rua, bairro, CEP ou pacote"
                    className="w-full text-xs font-semibold p-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700"
                />
            </div>

            <div>
                <p className="text-[10px] font-bold text-gray-400 uppercase mb-1 flex items-center gap-1"><Filter size={12}/> Cor</p>
                <select
                    value={colorFilter}
                    onChange={e => setColorFilter(e.target.value)}
                    className="w-full text-xs font-bold p-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700"
                >
                    <option value="all">Todas as cores</option>
                    <option value="unassigned">Sem rota</option>
                    <option value="assigned">Com rota</option>
                    {ROUTE_COLORS.map(color => (
                        <option key={color.hex} value={color.hex}>{color.label} ({routeStats.byColor[color.hex] || 0})</option>
                    ))}
                </select>
            </div>

            <div>
                <p className="text-[10px] font-bold text-gray-400 uppercase mb-2 flex items-center gap-1"><Layers size={12}/> Agrupar por:</p>
                <div className="grid grid-cols-4 gap-1 bg-gray-100 dark:bg-gray-700 p-1 rounded-lg">
                    {['bairro', 'street', 'cep', 'none'].map(mode => (
                        <button
                            key={mode}
                            onClick={() => setGroupMode(mode)}
                            className={`text-[9px] md:text-[10px] py-1.5 rounded-md font-bold transition-all ${
                                groupMode === mode 
                                    ? 'bg-white dark:bg-gray-600 shadow-sm text-blue-600 dark:text-blue-300' 
                                    : 'text-gray-500 hover:text-gray-700'
                            }`}
                        >
                            {mode === 'bairro' ? 'Bairro' : mode === 'street' ? 'Rua' : mode === 'cep' ? 'CEP' : 'Tudo'}
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
                        <option value="all">Ambos</option>
                        <option value="even">Pares</option>
                        <option value="odd">Ímpares</option>
                    </select>
                </div>
                <div>
                    <p className="text-[10px] font-bold text-gray-400 uppercase mb-1">Raio (m)</p>
                    <div className="relative">
                        <input 
                            type="number" placeholder="Metros..." value={radiusFilter} onChange={e => setRadiusFilter(e.target.value)}
                            className="w-full text-xs font-bold p-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 pr-8"
                        />
                        <button 
                            onClick={() => setGroupProximityMode(proximityMode === 'anchor' ? 'selection' : 'anchor')}
                            className={`absolute right-2 top-1/2 -translate-y-1/2 ${proximityMode === 'selection' ? 'text-purple-600' : 'text-gray-400'}`}
                        >
                            {proximityMode === 'selection' ? <Crosshair size={14}/> : <MapPin size={14}/>}
                        </button>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
                <button
                    onClick={handleSelectFiltered}
                    disabled={filteredPackages.length === 0}
                    className="text-[10px] font-black rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 py-2 flex items-center justify-center gap-1 disabled:opacity-40"
                >
                    <CheckSquare size={14}/> Selecionar filtro
                </button>
                <button
                    onClick={handlePaintFiltered}
                    disabled={filteredPackages.length === 0}
                    className="text-[10px] font-black rounded-lg border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 py-2 flex items-center justify-center gap-1 disabled:opacity-40"
                >
                    <PaintBucket size={14}/> Pintar filtro
                </button>
                <button
                    onClick={handlePaintSelected}
                    disabled={selectedIds.size === 0}
                    className="text-[10px] font-black rounded-lg border border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 py-2 flex items-center justify-center gap-1 disabled:opacity-40"
                >
                    <Palette size={14}/> Pintar seleção
                </button>
                <button
                    onClick={handleClearFiltered}
                    disabled={filteredPackages.length === 0}
                    className="text-[10px] font-black rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 py-2 flex items-center justify-center gap-1 disabled:opacity-40"
                >
                    <Eraser size={14}/> Limpar filtro
                </button>
            </div>

            <button
                onClick={handleClearFilters}
                className="w-full text-[10px] font-black rounded-lg border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-300 py-2 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
                Resetar filtros
            </button>
            
            {anchorId && proximityMode === 'anchor' && (
                <div className="bg-blue-50 dark:bg-blue-900/20 p-2 rounded flex justify-between items-center text-[10px] text-blue-700 dark:text-blue-300 border border-blue-100 dark:border-blue-800">
                    <span className="truncate">⚓ Âncora: {packages.find(p=>p.id === anchorId)?.address}</span>
                    <button onClick={() => setAnchorId(null)} className="font-bold hover:text-red-500 px-1">✕</button>
                </div>
            )}
        </div>

        {/* List Content */}
        <div className="flex-1 overflow-y-auto p-2 space-y-3 bg-gray-50/50 dark:bg-gray-900/40">
            {Object.entries(groupedPackages).map(([groupName, pkgs]) => (
                <div key={groupName} className="space-y-1">
                    {groupMode !== 'none' && (
                        <div className="sticky top-0 z-20 flex items-center justify-between bg-white/90 dark:bg-gray-800/90 backdrop-blur-md px-3 py-2 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 mb-2">
                           <div className="flex items-center gap-2 overflow-hidden flex-1">
                               <button onClick={() => toggleGroupCollapse(groupName)} className="text-gray-500">
                                   {collapsedGroups.has(groupName) ? <ChevronRight size={16}/> : <ChevronDown size={16}/>}
                               </button>
                               <button onClick={() => toggleGroupVisibility(groupName)} className={`${hiddenGroups.has(groupName) ? 'text-red-400' : 'text-blue-400'}`}>
                                   {hiddenGroups.has(groupName) ? <EyeOff size={14}/> : <Eye size={14}/>}
                               </button>
                               <span className={`text-[11px] font-black truncate uppercase ${hiddenGroups.has(groupName) ? 'text-gray-400 line-through' : 'text-gray-700 dark:text-gray-100'}`}>
                                   {groupName}
                               </span>
                               <span className="text-[10px] text-gray-400 font-bold bg-gray-100 dark:bg-gray-700 px-1.5 rounded-full">{pkgs.length}</span>
                           </div>
                           <button onClick={() => handleSelectGroup(pkgs)} className="text-blue-600 hover:scale-110 transition-transform ml-2">
                              <CheckSquare size={18}/>
                           </button>
                        </div>
                    )}
                    
                    {!collapsedGroups.has(groupName) && pkgs.map(pkg => (
                        <div 
                            key={pkg.id} 
                            ref={el => listRef.current[pkg.id] = el}
                            onClick={() => handleToggleSelect(pkg.id)}
                            className={`group p-2.5 rounded-xl border transition-all cursor-pointer flex gap-3 items-center
                                ${selectedIds.has(pkg.id) ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-400' : 'bg-white dark:bg-gray-800 border-gray-100 dark:border-gray-700 hover:border-gray-300'}
                            `}
                        >
                            <div className="flex-shrink-0">
                               {selectedIds.has(pkg.id) ? <CheckSquare size={20} className="text-blue-600"/> : <Square size={20} className="text-gray-300 dark:text-gray-600"/>}
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-[11px] font-bold text-gray-800 dark:text-gray-100 truncate">{pkg.address}</p>
                                <div className="flex items-center gap-2 mt-1">
                                    {pkg.number && <span className="text-[9px] font-bold text-blue-500 bg-blue-50 dark:bg-blue-900/50 px-1.5 rounded-full border border-blue-100 dark:border-blue-800">Nº {pkg.number}</span>}
                                    <span className="text-[9px] text-gray-400 dark:text-gray-500 font-medium">{pkg.cep}</span>
                                </div>
                            </div>
                            <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity md:opacity-100">
                                <button onClick={(e) => { e.stopPropagation(); setAnchorId(pkg.id); setGroupProximityMode('anchor'); }} className="p-1 hover:text-blue-600 text-gray-400"><MapPin size={16}/></button>
                                <button onClick={(e) => { e.stopPropagation(); handleQuickPaint(pkg.id); }} className="w-6 h-6 rounded-full border-2 border-white dark:border-gray-700 shadow-sm" style={{ backgroundColor: pkg.assignedColor || '#f3f4f6' }}></button>
                            </div>
                        </div>
                    ))}
                </div>
            ))}
        </div>
        
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
           <div className="mb-2 text-center">
               <p className="text-[10px] text-blue-500 font-bold flex items-center justify-center gap-1">
                   <Navigation2 size={10}/> O Bot irá sequenciar as entregas automaticamente
               </p>
           </div>
           <button 
               onClick={handleSaveCreativeRoutes}
               disabled={saving || !packages.some(p => p.assignedColor)}
               className="w-full btn-success flex items-center justify-center gap-2 py-3 text-sm font-bold shadow-xl active:scale-95 transition-transform"
           >
               {saving ? 'Processando...' : <><Save size={20}/> Finalizar Rotas</>}
           </button>
        </div>
      </div>

      {/* RIGHT PANEL - MAP */}
      <div className={`w-full md:w-2/3 bg-gray-100 dark:bg-gray-900 rounded-xl overflow-hidden relative shadow-inner border border-gray-200 dark:border-gray-700 h-full ${mobileView === 'list' ? 'hidden md:block' : 'block'}`}>
        <MapContainer center={mapCenter} zoom={13} style={{ height: '100%', width: '100%', zIndex: 10 }}>
            <LayersControl position="topright">
                <LayersControl.BaseLayer name="Mapa Suave" checked>
                    <TileLayer url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png" />
                </LayersControl.BaseLayer>
                <LayersControl.BaseLayer name="Satélite">
                    <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />
                </LayersControl.BaseLayer>
                <LayersControl.Overlay name="Sentido das Vias" checked>
                    <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" opacity={0.3} />
                </LayersControl.Overlay>
            </LayersControl>

            <MapUpdater center={mapCenter} zoom={13} bounds={mapBounds} />

            {packages.map(pkg => {
                let groupKey = 'none';
                if (groupMode === 'bairro') groupKey = pkg.bairro;
                if (groupMode === 'street') groupKey = pkg.street;
                if (groupMode === 'cep') groupKey = pkg.cep;
                
                if (hiddenGroups.has(groupKey)) return null;

                const isFiltered = filteredPackages.some(fp => fp.id === pkg.id);
                const isSelected = selectedIds.has(pkg.id);
                const color = pkg.assignedColor || (isFiltered ? '#3B82F6' : '#9CA3AF');
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
                            <div className="p-2 min-w-[180px]">
                                <p className="font-bold text-xs text-gray-800 mb-2">{pkg.address}</p>
                                <div className="grid grid-cols-2 gap-2">
                                    <button 
                                        onClick={() => handleToggleSelect(pkg.id)}
                                        className={`px-2 py-1.5 rounded-lg text-[10px] font-bold ${isSelected ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600'}`}
                                    >
                                        {isSelected ? 'Remover' : 'Selecionar'}
                                    </button>
                                    <button 
                                        onClick={() => handleQuickPaint(pkg.id)}
                                        className="text-white px-2 py-1.5 rounded-lg text-[10px] font-bold flex items-center justify-center gap-1"
                                        style={{ backgroundColor: activeColor }}
                                    >
                                        Pintar
                                    </button>
                                </div>
                            </div>
                        </Popup>
                    </Marker>
                );
            })}
        </MapContainer>
        
        {/* Help Overlay (Desktop Only) */}
        <div className="hidden md:block absolute bottom-4 left-4 z-[1000] bg-white/95 dark:bg-gray-800/95 p-3 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 text-[10px] pointer-events-none">
            <p className="font-black text-gray-400 mb-1 flex items-center gap-1 tracking-tighter uppercase"><Navigation2 size={10}/> Navegação Inteligente</p>
            <p className="text-gray-500 font-medium">Use as camadas no topo para alternar entre Satélite e Mapa Suave.</p>
        </div>
      </div>
    </div>
  );
}
