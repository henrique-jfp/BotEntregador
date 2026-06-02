import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import HeatmapDashboard from '../components/HeatmapDashboard';
import { Activity, Map, TrendingUp } from 'lucide-react';

/**
 * Analytics Page - Integra HeatmapDashboard com outras visualizações
 */
export default function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState('heatmap');

  return (
    <div className="space-y-6 pb-20 container-responsive p-responsive">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg p-8 text-white shadow-lg container-responsive p-responsive">
        <div className="flex items-center gap-4 mb-4">
          <Activity size={40} />
          <div>
            <h1 className="text-4xl font-bold text-responsive">Centro de Análise</h1>
            <p className="text-blue-100 text-responsive">Visualize o desempenho de entregas por região</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 bg-white rounded-lg p-2 shadow container-responsive">
        <button
          onClick={() => setActiveTab('heatmap')}
          className={`flex-1 py-2 px-4 rounded-lg font-bold transition-all flex items-center justify-center gap-2 ${
            activeTab === 'heatmap'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          } text-responsive`}
        >
          <Map size={20} />
          Mapa de Calor
        </button>
        <button
          onClick={() => setActiveTab('trends')}
          className={`flex-1 py-2 px-4 rounded-lg font-bold transition-all flex items-center justify-center gap-2 ${
            activeTab === 'trends'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          } text-responsive`}
        >
          <TrendingUp size={20} />
          Tendências
        </button>
      </div>

      {/* Content */}
      {activeTab === 'heatmap' && <HeatmapDashboard />}
      
      {activeTab === 'trends' && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-lg p-6 table-responsive">
            <h2 className="text-2xl font-bold mb-4 text-responsive">Tendências de Desempenho</h2>
            <p className="text-gray-600 text-sm mb-4 text-responsive">Análise temporal de entregas por bairro</p>
            <div className="h-96 bg-gray-100 rounded-lg flex items-center justify-center">
              <p className="text-gray-500 text-responsive">Gráfico de tendências em desenvolvimento</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
