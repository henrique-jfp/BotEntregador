/**
 * 🧠 Cérebro Geográfico
 * 
 * - Mapa SVG estilo WAR/RISK (bordas curvas, cores por zona)
 * - UI Premium Moderna (cards, stats, sidebar)
 */
import React, { useState, useEffect, useRef } from 'react';
import { MapPin, TrendingUp, AlertTriangle, Award, RefreshCw, Target, Zap, X, Users, ChevronRight } from 'lucide-react';
import { fetchWithAuth } from './api_client';
import ZonaSulWarMap from './components/ZonaSulWarMap';

export default function HeatmapView() {
  const [data, setData] = useState(null);
  const [selectedBairro, setSelectedBairro] = useState(null);
  const [bairroDetail, setBairroDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [days, setDays] = useState(7);
  const [hoveredBairro, setHoveredBairro] = useState(null);

  // Carregar dados
  const loadData = async () => {
    setLoading(true);
    try {
      const response = await fetchWithAuth(`/api/analytics/neighborhood-stats?days=${days}`);
      const result = await response.json();
      
      const mapData = {};
      let totalDeliveries = 0;
      let totalSuccess = 0;
      
      (result.neighborhoods || []).forEach(n => {
        mapData[n.name] = {
          volume: n.total_deliveries || 0,
          success_rate: n.success_rate || 0,
          avg_time: n.avg_delivery_time || 0,
        };
        totalDeliveries += n.total_deliveries || 0;
        if (n.success_rate) totalSuccess += n.success_rate;
      });

      setData({
        neighborhoods: mapData,
        total_deliveries: totalDeliveries,
        avg_success: result.neighborhoods?.length > 0 
          ? Math.round(totalSuccess / result.neighborhoods.length) 
          : 0,
        active_bairros: Object.keys(mapData).filter(k => mapData[k].volume > 0).length,
      });
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      setData({
        neighborhoods: {
          'Leblon': { volume: 45, success_rate: 94 },
          'Ipanema': { volume: 62, success_rate: 92 },
          'Copacabana': { volume: 78, success_rate: 89 },
          'Botafogo': { volume: 54, success_rate: 91 },
          'Flamengo': { volume: 41, success_rate: 88 },
          'Lagoa': { volume: 23, success_rate: 95 },
          'Leme': { volume: 18, success_rate: 90 },
          'Urca': { volume: 12, success_rate: 96 },
          'Gávea': { volume: 28, success_rate: 93 },
          'Jardim Botânico': { volume: 19, success_rate: 94 },
          'Humaitá': { volume: 31, success_rate: 91 },
          'Laranjeiras': { volume: 25, success_rate: 90 },
        },
        total_deliveries: 436,
        avg_success: 92,
        active_bairros: 12,
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [days]);

  // Carregar detalhes do bairro
  const loadBairroDetail = async (bairro) => {
    setSelectedBairro(bairro);
    setDetailLoading(true);
    try {
      const response = await fetchWithAuth(`/api/analytics/neighborhood/${encodeURIComponent(bairro)}?days=${days}`);
      const detail = await response.json();
      setBairroDetail(detail);
    } catch (error) {
      console.error('Erro ao carregar detalhes:', error);
      setBairroDetail({
        total_deliveries: data?.neighborhoods?.[bairro]?.volume || 0,
        success_rate: data?.neighborhoods?.[bairro]?.success_rate || 0,
        top_deliverers: [
          { name: 'Carlos Silva', total_deliveries: 28, success_rate: 96 },
          { name: 'Maria Santos', total_deliveries: 22, success_rate: 94 },
          { name: 'João Pereira', total_deliveries: 18, success_rate: 92 },
        ],
        failure_breakdown: [
          { reason: 'Cliente ausente', count: 5 },
          { reason: 'Endereço incorreto', count: 3 },
        ],
      });
    } finally {
      setDetailLoading(false);
    }
  };

  // Loading state
  if (loading && !data) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-4">
            <div className="absolute inset-0 rounded-full border-4 border-purple-200 dark:border-purple-900"></div>
            <div className="absolute inset-0 rounded-full border-4 border-purple-600 border-t-transparent animate-spin"></div>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Carregando mapa...</h3>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div className="max-w-7xl mx-auto px-3 sm:px-4 py-4 sm:py-6">
        
        {/* Header Premium */}
        <div className="mb-4 sm:mb-6">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-purple-500/25">
                <MapPin className="w-6 h-6 sm:w-7 sm:h-7 text-white" />
              </div>
              <div>
                <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                  Cérebro Geográfico
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                </h1>
                <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">Inteligência de entregas • Zona Sul RJ</p>
              </div>
            </div>
            
            {/* Controles */}
            <div className="flex items-center gap-2">
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="h-9 sm:h-10 px-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm font-medium text-gray-700 dark:text-gray-300 shadow-sm"
              >
                <option value={7}>7 dias</option>
                <option value={15}>15 dias</option>
                <option value={30}>30 dias</option>
              </select>
              
              <button
                onClick={loadData}
                disabled={loading}
                className="h-9 w-9 sm:h-10 sm:w-10 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 flex items-center justify-center hover:bg-gray-50 dark:hover:bg-gray-700 shadow-sm transition-colors"
              >
                <RefreshCw className={`w-4 h-4 text-gray-600 dark:text-gray-400 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>

        {/* Stats Cards - Design Premium Moderno */}
        <div className="grid grid-cols-3 gap-2 sm:gap-4 mb-4 sm:mb-6">
          <div className="bg-white dark:bg-gray-800 rounded-xl sm:rounded-2xl p-3 sm:p-5 shadow-lg border border-gray-100 dark:border-gray-700">
            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
              <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg sm:rounded-xl bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                <Target className="w-4 h-4 sm:w-5 sm:h-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <p className="text-lg sm:text-2xl font-bold text-gray-900 dark:text-white">{data?.total_deliveries || 0}</p>
                <p className="text-[10px] sm:text-xs text-gray-500 dark:text-gray-400">Entregas</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-xl sm:rounded-2xl p-3 sm:p-5 shadow-lg border border-gray-100 dark:border-gray-700">
            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
              <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg sm:rounded-xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                <Zap className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <p className="text-lg sm:text-2xl font-bold text-gray-900 dark:text-white">{data?.avg_success || 0}%</p>
                <p className="text-[10px] sm:text-xs text-gray-500 dark:text-gray-400">Sucesso</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-xl sm:rounded-2xl p-3 sm:p-5 shadow-lg border border-gray-100 dark:border-gray-700">
            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
              <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg sm:rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <MapPin className="w-4 h-4 sm:w-5 sm:h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-lg sm:text-2xl font-bold text-gray-900 dark:text-white">{data?.active_bairros || 0}</p>
                <p className="text-[10px] sm:text-xs text-gray-500 dark:text-gray-400">Bairros</p>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content: Mapa + Sidebar */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
          
          {/* =====================================================
              🗺️ MAPA SVG - ESTILO WAR/RISK
              ===================================================== */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-100 dark:border-gray-700 overflow-hidden">
              {/* Container do Mapa */}
              <div className="relative bg-white p-2">
                <ZonaSulWarMap
                  data={data}
                  onBairroClick={loadBairroDetail}
                  hoveredBairro={hoveredBairro}
                  onHoverChange={setHoveredBairro}
                />
              </div>
            </div>
          </div>

          {/* =====================================================
              📊 SIDEBAR - PREMIUM MODERNA (sem estilo jogo)
              ===================================================== */}
          <div className="lg:col-span-1">
            {selectedBairro ? (
              <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-100 dark:border-gray-700 overflow-hidden sticky top-4">
                {/* Header Premium */}
                <div className="p-5 bg-gradient-to-r from-purple-600 to-indigo-600">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xl font-bold text-white">{selectedBairro}</h3>
                      <p className="text-sm text-purple-200">Zona Sul • Rio de Janeiro</p>
                    </div>
                    <button 
                      onClick={() => setSelectedBairro(null)}
                      className="w-8 h-8 rounded-full bg-white/20 hover:bg-white/30 flex items-center justify-center transition-colors"
                    >
                      <X className="w-4 h-4 text-white" />
                    </button>
                  </div>
                </div>

                {detailLoading ? (
                  <div className="p-8 text-center">
                    <RefreshCw className="w-8 h-8 text-purple-600 mx-auto mb-3 animate-spin" />
                    <p className="text-sm text-gray-500 dark:text-gray-400">Carregando...</p>
                  </div>
                ) : bairroDetail && (
                  <div className="p-5 space-y-5">
                    {/* Métricas Premium */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-purple-50 dark:bg-purple-900/20 rounded-xl p-4">
                        <TrendingUp className="w-5 h-5 text-purple-600 mb-2" />
                        <p className="text-xl font-bold text-gray-900 dark:text-white">{bairroDetail.total_deliveries}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Entregas</p>
                      </div>
                      <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl p-4">
                        <Award className="w-5 h-5 text-emerald-600 mb-2" />
                        <p className="text-xl font-bold text-gray-900 dark:text-white">{bairroDetail.success_rate}%</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Sucesso</p>
                      </div>
                    </div>

                    {/* Top Entregadores */}
                    <div>
                      <h4 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                        <Users className="w-4 h-4 text-purple-500" />
                        Top Entregadores
                      </h4>
                      <div className="space-y-2">
                        {(bairroDetail.top_deliverers || []).slice(0, 3).map((d, idx) => (
                          <div 
                            key={idx} 
                            className="flex items-center justify-between p-3 rounded-xl bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20"
                          >
                            <div className="flex items-center gap-3">
                              <span className={`w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center ${
                                idx === 0 ? 'bg-yellow-400 text-yellow-900' :
                                idx === 1 ? 'bg-gray-300 text-gray-700' :
                                'bg-amber-600 text-white'
                              }`}>
                                {idx + 1}
                              </span>
                              <span className="text-sm font-medium text-gray-900 dark:text-white">{d.name}</span>
                            </div>
                            <div className="text-right">
                              <p className="text-sm font-bold text-gray-900 dark:text-white">{d.total_deliveries}</p>
                              <p className="text-xs text-emerald-600 dark:text-emerald-400">{d.success_rate}%</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Problemas */}
                    {bairroDetail.failure_breakdown?.length > 0 && (
                      <div>
                        <h4 className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-amber-500" />
                          Principais Problemas
                        </h4>
                        <div className="space-y-2">
                          {bairroDetail.failure_breakdown.map((f, idx) => (
                            <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-amber-50 dark:bg-amber-900/20">
                              <span className="text-sm text-gray-700 dark:text-gray-300">{f.reason}</span>
                              <span className="text-sm font-bold text-amber-700 dark:text-amber-400">{f.count}x</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              /* Estado vazio Premium */
              <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-100 dark:border-gray-700 p-8 text-center sticky top-4">
                <div className="w-16 h-16 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center mx-auto mb-4">
                  <MapPin className="w-8 h-8 text-purple-600 dark:text-purple-400" />
                </div>
                <h3 className="font-semibold text-gray-900 dark:text-white mb-2">Selecione um Território</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">Clique em um bairro no mapa para ver estatísticas detalhadas de entregas.</p>
              </div>
            )}

            {/* Ranking Premium */}
            <div className="mt-4 bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-100 dark:border-gray-700 p-5">
              <h4 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-purple-500" />
                Top 5 Territórios
              </h4>
              <div className="space-y-2">
                {Object.entries(data?.neighborhoods || {})
                  .sort((a, b) => (b[1].volume || 0) - (a[1].volume || 0))
                  .slice(0, 5)
                  .map(([nome, stats], idx) => (
                    <div 
                      key={nome}
                      onClick={() => loadBairroDetail(nome)}
                      className="flex items-center justify-between p-3 rounded-xl bg-gray-50 dark:bg-gray-700/50 hover:bg-purple-50 dark:hover:bg-purple-900/20 cursor-pointer transition-colors group"
                    >
                      <div className="flex items-center gap-3">
                        <span className={`w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center ${
                          idx === 0 ? 'bg-yellow-400 text-yellow-900' :
                          idx === 1 ? 'bg-gray-300 text-gray-700' :
                          idx === 2 ? 'bg-amber-600 text-white' :
                          'bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300'
                        }`}>
                          {idx + 1}
                        </span>
                        <span className="text-sm font-medium text-gray-900 dark:text-white">{nome}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="text-right">
                          <p className="text-sm font-bold text-gray-900 dark:text-white">{stats.volume}</p>
                          <p className="text-xs text-emerald-600 dark:text-emerald-400">{stats.success_rate}%</p>
                        </div>
                        <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-purple-600 transition-colors" />
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
