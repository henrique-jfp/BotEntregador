import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, GeoJSON, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { fetchWithAuth } from '../api_client';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { MapPin, TrendingUp, Users, AlertCircle, CheckCircle, Clock } from 'lucide-react';

/**
 * HEATMAP DASHBOARD - Zona Sul Rio de Janeiro
 * Análise geográfica de entregas por bairro com mapa interativo
 */
export default function HeatmapDashboard() {
  const [neighborhoodsData, setNeighborhoodsData] = useState({});
  const [heatmapData, setHeatmapData] = useState([]);
  const [geoJsonData, setGeoJsonData] = useState(null);
  const [selectedBairro, setSelectedBairro] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mapRef, setMapRef] = useState(null);

  // Carregar dados ao montar
  useEffect(() => {
    loadData();
  }, []);

  // Função para carregar dados da API
  const loadData = async () => {
    setLoading(true);
    try {
      // Buscar estatísticas por bairro
      const statsRes = await fetchWithAuth('/api/stats/neighborhoods');
      setNeighborhoodsData(statsRes);

      // Buscar dados de heatmap (falhas)
      const heatmapRes = await fetchWithAuth('/api/stats/neighborhoods/heatmap?status=failed');
      setHeatmapData(heatmapRes);

      // Carregar GeoJSON
      const geoRes = await fetch('/geojson/zona_sul_rio.json');
      const geo = await geoRes.json();
      setGeoJsonData(geo);

      setError(null);
    } catch (err) {
      console.error('Erro ao carregar dados:', err);
      setError('Erro ao carregar dados do mapa');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Função para determinar cor do bairro baseado em volume de entregas
   */
  const getColor = (totalPackages) => {
    if (!totalPackages) return '#ccc';
    if (totalPackages < 10) return '#e3f2fd'; // Azul muito claro
    if (totalPackages < 30) return '#bbdefb'; // Azul claro
    if (totalPackages < 60) return '#90caf9'; // Azul médio
    if (totalPackages < 100) return '#64b5f6'; // Azul
    if (totalPackages < 150) return '#42a5f5'; // Azul escuro
    return '#2196f3'; // Azul muito escuro
  };

  /**
   * Função para estilizar polígonos GeoJSON
   */
  const onEachFeature = (feature, layer) => {
    const bairroName = feature.properties.name;
    const bairroStats = neighborhoodsData[bairroName] || {};

    // Estilo padrão
    const baseStyle = {
      color: '#333',
      weight: 2,
      opacity: 0.8,
      fillOpacity: 0.6,
      fillColor: getColor(bairroStats.total_packages)
    };

    layer.setStyle(baseStyle);

    // Hover effect
    layer.on('mouseover', () => {
      layer.setStyle({
        ...baseStyle,
        weight: 3,
        opacity: 1,
        fillOpacity: 0.8
      });
      layer.bringToFront();
    });

    layer.on('mouseout', () => {
      layer.setStyle(baseStyle);
    });

    // Click para abrir modal
    layer.on('click', () => {
      setSelectedBairro({
        name: bairroName,
        ...bairroStats
      });
    });

    // Popup ao passar mouse
    const popupContent = `
      <div class="p-2 text-sm">
        <p class="font-bold">${bairroName}</p>
        <p>Total: ${bairroStats.total_packages || 0}</p>
        <p>Taxa: ${bairroStats.success_rate || 0}%</p>
      </div>
    `;

    layer.bindPopup(popupContent);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-lg p-6 text-white shadow-lg">
        <div className="flex items-center gap-3 mb-2">
          <MapPin size={28} />
          <h1 className="text-3xl font-bold">Mapa de Entregas - Zona Sul Rio de Janeiro</h1>
        </div>
        <p className="text-blue-100">Análise geográfica de desempenho por bairro</p>
      </div>

      {/* Mapa */}
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        <MapContainer
          center={[-22.98, -43.21]}
          zoom={13}
          style={{ height: '600px', width: '100%' }}
          ref={setMapRef}
        >
          {/* Tile Layer OpenStreetMap */}
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; OpenStreetMap contributors'
          />

          {/* GeoJSON com estilo coroplético */}
          {geoJsonData && (
            <GeoJSON
              data={geoJsonData}
              onEachFeature={onEachFeature}
              style={() => ({
                color: '#333',
                weight: 2,
                opacity: 0.8,
                fillOpacity: 0.6
              })}
            />
          )}
        </MapContainer>
      </div>

      {/* Legenda */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="font-bold text-lg mb-4">Legenda de Cores</h3>
        <div className="grid grid-cols-6 gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded" style={{ backgroundColor: '#e3f2fd' }}></div>
            <span className="text-sm">0-10</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded" style={{ backgroundColor: '#bbdefb' }}></div>
            <span className="text-sm">10-30</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded" style={{ backgroundColor: '#90caf9' }}></div>
            <span className="text-sm">30-60</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded" style={{ backgroundColor: '#64b5f6' }}></div>
            <span className="text-sm">60-100</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded" style={{ backgroundColor: '#42a5f5' }}></div>
            <span className="text-sm">100-150</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded" style={{ backgroundColor: '#2196f3' }}></div>
            <span className="text-sm">150+</span>
          </div>
        </div>
        <p className="text-xs text-gray-600 mt-4">Volume de pacotes por bairro</p>
      </div>

      {/* Cards de Resumo */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-blue-50 rounded-lg p-4 border-l-4 border-blue-600">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Total de Pacotes</p>
              <p className="text-2xl font-bold text-blue-600">
                {Object.values(neighborhoodsData).reduce((sum, b) => sum + (b.total_packages || 0), 0)}
              </p>
            </div>
            <MapPin size={32} className="text-blue-400" />
          </div>
        </div>

        <div className="bg-green-50 rounded-lg p-4 border-l-4 border-green-600">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Entregas Sucesso</p>
              <p className="text-2xl font-bold text-green-600">
                {Object.values(neighborhoodsData).reduce((sum, b) => sum + (b.success_count || 0), 0)}
              </p>
            </div>
            <CheckCircle size={32} className="text-green-400" />
          </div>
        </div>

        <div className="bg-red-50 rounded-lg p-4 border-l-4 border-red-600">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Entregas Falhadas</p>
              <p className="text-2xl font-bold text-red-600">
                {Object.values(neighborhoodsData).reduce((sum, b) => sum + (b.failed_count || 0), 0)}
              </p>
            </div>
            <AlertCircle size={32} className="text-red-400" />
          </div>
        </div>

        <div className="bg-purple-50 rounded-lg p-4 border-l-4 border-purple-600">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Taxa Média de Sucesso</p>
              <p className="text-2xl font-bold text-purple-600">
                {(
                  Object.values(neighborhoodsData).reduce((sum, b) => sum + (b.success_rate || 0), 0) /
                  Object.keys(neighborhoodsData).length
                ).toFixed(1)}
                %
              </p>
            </div>
            <TrendingUp size={32} className="text-purple-400" />
          </div>
        </div>
      </div>

      {/* Tabela de Bairros */}
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        <div className="p-6 border-b border-gray-200">
          <h3 className="font-bold text-lg">Resumo por Bairro</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-100 border-b">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-bold">Bairro</th>
                <th className="px-6 py-3 text-left text-sm font-bold">Total</th>
                <th className="px-6 py-3 text-left text-sm font-bold">Sucessos</th>
                <th className="px-6 py-3 text-left text-sm font-bold">Falhas</th>
                <th className="px-6 py-3 text-left text-sm font-bold">Taxa Sucesso</th>
                <th className="px-6 py-3 text-left text-sm font-bold">Top Entregador</th>
                <th className="px-6 py-3 text-left text-sm font-bold">Ação</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(neighborhoodsData).map(([bairro, stats]) => (
                <tr key={bairro} className="border-b hover:bg-gray-50 cursor-pointer">
                  <td className="px-6 py-4 font-medium">{bairro}</td>
                  <td className="px-6 py-4 text-blue-600 font-semibold">{stats.total_packages}</td>
                  <td className="px-6 py-4 text-green-600 font-semibold">{stats.success_count}</td>
                  <td className="px-6 py-4 text-red-600 font-semibold">{stats.failed_count}</td>
                  <td className="px-6 py-4">
                    <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                      stats.success_rate >= 90 ? 'bg-green-100 text-green-700' :
                      stats.success_rate >= 70 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {stats.success_rate}%
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1">
                      <Users size={16} className="text-purple-600" />
                      {stats.top_deliverer}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <button
                      onClick={() => setSelectedBairro({ name: bairro, ...stats })}
                      className="text-blue-600 hover:text-blue-800 font-semibold text-sm"
                    >
                      Detalhes
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal de Detalhe do Bairro */}
      {selectedBairro && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full max-h-96 overflow-y-auto">
            {/* Header Modal */}
            <div className="bg-gradient-to-r from-blue-600 to-blue-800 text-white p-6 flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold">{selectedBairro.name}</h2>
                <p className="text-blue-100">Análise Detalhada</p>
              </div>
              <button
                onClick={() => setSelectedBairro(null)}
                className="text-white hover:bg-blue-700 rounded-full p-2 transition-all"
              >
                ✕
              </button>
            </div>

            {/* Conteúdo Modal */}
            <div className="p-6">
              {/* Stats Grid */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-gray-600 text-sm mb-1">Total de Pacotes</p>
                  <p className="text-3xl font-bold text-blue-600">{selectedBairro.total_packages}</p>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <p className="text-gray-600 text-sm mb-1">Entregas Sucesso</p>
                  <p className="text-3xl font-bold text-green-600">{selectedBairro.success_count}</p>
                </div>
                <div className="bg-red-50 p-4 rounded-lg">
                  <p className="text-gray-600 text-sm mb-1">Entregas Falhadas</p>
                  <p className="text-3xl font-bold text-red-600">{selectedBairro.failed_count}</p>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <p className="text-gray-600 text-sm mb-1">Taxa de Sucesso</p>
                  <p className="text-3xl font-bold text-purple-600">{selectedBairro.success_rate}%</p>
                </div>
              </div>

              {/* Top Entregador */}
              <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 rounded-lg mb-6">
                <div className="flex items-center gap-3">
                  <Users size={24} className="text-purple-600" />
                  <div>
                    <p className="text-gray-600 text-sm">Top Entregador</p>
                    <p className="text-xl font-bold text-purple-700">{selectedBairro.top_deliverer}</p>
                  </div>
                </div>
              </div>

              {/* Mini Gráfico */}
              <div className="h-64 mb-4">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Sucesso', value: selectedBairro.success_count },
                        { name: 'Falha', value: selectedBairro.failed_count }
                      ]}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, value }) => `${name}: ${value}`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      <Cell fill="#22c55e" />
                      <Cell fill="#ef4444" />
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Botão Fechar */}
              <button
                onClick={() => setSelectedBairro(null)}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg transition-all"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Botão para Atualizar Dados */}
      <div className="text-center">
        <button
          onClick={loadData}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded-lg transition-all"
        >
          🔄 Atualizar Dados
        </button>
      </div>
    </div>
  );
}
