import React, { useState, useMemo } from 'react';
import { zonaSulGeoData } from '../data/zonaSulGeoData';

/**
 * ZonaSulWarMap - Mapa oficial da Zona Sul do Rio de Janeiro
 * Dados GeoJSON do OpenStreetMap (100% fiel aos limites reais)
 * 18 bairros: Botafogo, Humaitá, Copacabana, Lagoa, Ipanema, Leblon,
 * Jardim Botânico, São Conrado, Flamengo, Glória, Catete, Cosme Velho,
 * Gávea, Laranjeiras, Leme, Rocinha, Urca, Vidigal
 */

const ZonaSulWarMap = ({ 
  data = {}, 
  onBairroClick = () => {}, 
  hoveredBairro = null,
  onHoverChange = () => {},
  compact = false,
  showTitle = false
}) => {
  const [internalHover, setInternalHover] = useState(null);
  const activeHover = hoveredBairro || internalHover;

  // Cores sofisticadas para cada bairro
  const CORES_BAIRROS = {
    'Botafogo': '#E8B4B8',
    'Humaitá': '#A8D5BA', 
    'Copacabana': '#F5D6A8',
    'Lagoa': '#89CFF0',
    'Ipanema': '#C3B1E1',
    'Leblon': '#FFDAB9',
    'Jardim Botânico': '#90EE90',
    'São Conrado': '#DEB887',
    'Flamengo': '#FFB6C1',
    'Glória': '#FFE4B5',
    'Catete': '#B0E0E6',
    'Cosme Velho': '#D4A574',
    'Gávea': '#98FB98',
    'Laranjeiras': '#F0E68C',
    'Leme': '#FFA07A',
    'Rocinha': '#DDA0DD',
    'Urca': '#87CEEB',
    'Vidigal': '#F4A460'
  };

  // Calcula bounds do mapa
  const bounds = useMemo(() => {
    let minLng = Infinity, maxLng = -Infinity;
    let minLat = Infinity, maxLat = -Infinity;
    
    zonaSulGeoData.features.forEach(feature => {
      const coords = feature.geometry.coordinates[0];
      if (!coords) return;
      coords.forEach(coord => {
        if (Array.isArray(coord) && coord.length >= 2) {
          minLng = Math.min(minLng, coord[0]);
          maxLng = Math.max(maxLng, coord[0]);
          minLat = Math.min(minLat, coord[1]);
          maxLat = Math.max(maxLat, coord[1]);
        }
      });
    });
    
    // Adiciona padding
    const lngPad = (maxLng - minLng) * 0.05;
    const latPad = (maxLat - minLat) * 0.05;
    
    return { 
      minLng: minLng - lngPad, 
      maxLng: maxLng + lngPad, 
      minLat: minLat - latPad, 
      maxLat: maxLat + latPad 
    };
  }, []);

  // Dimensões do SVG
  const svgWidth = 800;
  const svgHeight = compact ? 450 : 550;
  const padding = 15;

  // Converte coordenadas geo para SVG
  const geoToSvg = (lng, lat) => {
    const { minLng, maxLng, minLat, maxLat } = bounds;
    const x = padding + ((lng - minLng) / (maxLng - minLng)) * (svgWidth - 2 * padding);
    const y = padding + ((maxLat - lat) / (maxLat - minLat)) * (svgHeight - 2 * padding);
    return { x, y };
  };

  // Converte polygon para path SVG
  const polygonToPath = (coordinates) => {
    if (!coordinates || !coordinates[0]) return '';
    const ring = coordinates[0];
    if (ring.length < 3) return '';
    
    const points = ring.map(coord => {
      if (!Array.isArray(coord) || coord.length < 2) return null;
      const { x, y } = geoToSvg(coord[0], coord[1]);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).filter(Boolean);
    
    if (points.length < 3) return '';
    return `M ${points.join(' L ')} Z`;
  };

  // Calcula centroide do polígono
  const getCentroid = (coordinates) => {
    if (!coordinates || !coordinates[0]) return { x: 0, y: 0 };
    const ring = coordinates[0];
    if (ring.length === 0) return { x: 0, y: 0 };
    
    let sumX = 0, sumY = 0, count = 0;
    ring.forEach(coord => {
      if (Array.isArray(coord) && coord.length >= 2) {
        const { x, y } = geoToSvg(coord[0], coord[1]);
        sumX += x;
        sumY += y;
        count++;
      }
    });
    
    return count > 0 ? { x: sumX / count, y: sumY / count } : { x: 0, y: 0 };
  };

  const handleMouseEnter = (nome) => {
    setInternalHover(nome);
    onHoverChange(nome);
  };

  const handleMouseLeave = () => {
    setInternalHover(null);
    onHoverChange(null);
  };

  return (
    <svg
      viewBox={`0 0 ${svgWidth} ${svgHeight}`}
      className="w-full h-auto"
      style={{ 
        minHeight: compact ? '300px' : '400px', 
        maxHeight: compact ? '450px' : '600px',
        background: 'linear-gradient(145deg, #f8fafc 0%, #e2e8f0 100%)'
      }}
      preserveAspectRatio="xMidYMid meet"
    >
      {/* Definições de filtros */}
      <defs>
        <filter id="dropShadow" x="-10%" y="-10%" width="120%" height="120%">
          <feDropShadow dx="1" dy="1" stdDeviation="1.5" floodOpacity="0.2"/>
        </filter>
        <filter id="hoverShadow" x="-15%" y="-15%" width="130%" height="130%">
          <feDropShadow dx="2" dy="2" stdDeviation="3" floodOpacity="0.35"/>
        </filter>
        <linearGradient id="oceanGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#e0f2fe" />
          <stop offset="100%" stopColor="#bae6fd" />
        </linearGradient>
      </defs>

      {/* Background - Oceano */}
      <rect 
        x="0" 
        y="0" 
        width={svgWidth} 
        height={svgHeight} 
        fill="url(#oceanGradient)"
        rx="8"
      />

      {/* Título opcional */}
      {showTitle && (
        <text
          x={svgWidth / 2}
          y={25}
          textAnchor="middle"
          fontSize="16"
          fontWeight="700"
          fill="#1e293b"
          style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}
        >
          Zona Sul • Rio de Janeiro
        </text>
      )}

      {/* Bairros */}
      <g>
        {zonaSulGeoData.features.map((feature, index) => {
          const nome = feature.properties.name;
          const isHovered = activeHover === nome;
          const bairroData = data?.neighborhoods?.[nome] || {};
          const cor = CORES_BAIRROS[nome] || '#E5E7EB';
          const path = polygonToPath(feature.geometry.coordinates);
          const centroid = getCentroid(feature.geometry.coordinates);
          
          if (!path) return null;

          // Ajuste de posição do label para bairros específicos
          let labelOffset = { x: 0, y: 0 };
          if (nome === 'Lagoa') labelOffset = { x: 0, y: 10 };
          if (nome === 'Jardim Botânico') labelOffset = { x: 0, y: -5 };
          if (nome === 'Gávea') labelOffset = { x: 5, y: 0 };
          
          return (
            <g key={nome || index} className="cursor-pointer">
              {/* Polígono do bairro */}
              <path
                d={path}
                fill={cor}
                stroke={isHovered ? '#1e40af' : '#475569'}
                strokeWidth={isHovered ? 2 : 0.8}
                strokeLinejoin="round"
                style={{ 
                  transition: 'all 150ms ease-out',
                  filter: isHovered ? 'url(#hoverShadow) brightness(1.08)' : 'url(#dropShadow)',
                  transform: isHovered ? 'scale(1.01)' : 'scale(1)',
                  transformOrigin: `${centroid.x}px ${centroid.y}px`
                }}
                onMouseEnter={() => handleMouseEnter(nome)}
                onMouseLeave={handleMouseLeave}
                onClick={() => onBairroClick(nome)}
              />
              
              {/* Nome do bairro */}
              <text
                x={centroid.x + labelOffset.x}
                y={centroid.y + labelOffset.y}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={nome.length > 13 ? "7" : nome.length > 9 ? "8" : "9"}
                fontWeight="600"
                fill="#1e293b"
                className="pointer-events-none select-none"
                style={{ 
                  fontFamily: 'system-ui, -apple-system, sans-serif',
                  textShadow: '1px 1px 0 rgba(255,255,255,0.9), -1px -1px 0 rgba(255,255,255,0.9), 1px -1px 0 rgba(255,255,255,0.9), -1px 1px 0 rgba(255,255,255,0.9)',
                  opacity: isHovered ? 1 : 0.9
                }}
              >
                {nome}
              </text>

              {/* Badge de volume de entregas */}
              {bairroData.volume > 0 && (
                <g className="pointer-events-none">
                  <circle 
                    cx={centroid.x + 20} 
                    cy={centroid.y - 12} 
                    r="9" 
                    fill="#dc2626" 
                    stroke="#fff" 
                    strokeWidth="1.5"
                    style={{ filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.3))' }}
                  />
                  <text 
                    x={centroid.x + 20} 
                    y={centroid.y - 11} 
                    textAnchor="middle" 
                    dominantBaseline="middle" 
                    fontSize="7" 
                    fill="white" 
                    fontWeight="700"
                  >
                    {bairroData.volume > 99 ? '99+' : bairroData.volume}
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </g>

      {/* Indicador de hover */}
      {activeHover && (
        <g className="pointer-events-none">
          <rect
            x={svgWidth - 150}
            y={svgHeight - 40}
            width="140"
            height="30"
            rx="6"
            fill="rgba(30, 41, 59, 0.95)"
          />
          <text
            x={svgWidth - 80}
            y={svgHeight - 22}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="11"
            fontWeight="600"
            fill="white"
            style={{ fontFamily: 'system-ui, sans-serif' }}
          >
            {activeHover}
          </text>
        </g>
      )}
    </svg>
  );
};

export default ZonaSulWarMap;
