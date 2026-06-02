import React, { useState, useEffect } from 'react';
import { DollarSign, TrendingDown, TrendingUp, Fuel, Receipt, Users, CheckCircle, XCircle } from 'lucide-react';
import { fetchSafe } from '../api_client';
import FullscreenToggle from '../components/FullscreenToggle';

export default function FinancialClosureView() {
  const [activeSession, setActiveSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deliverers, setDeliverers] = useState([]);
  
  // Formulário de custos
  const [fuel, setFuel] = useState('');
  const [otherCosts, setOtherCosts] = useState('');
  const [extraRevenue, setExtraRevenue] = useState('');
  const [salaries, setSalaries] = useState({});
  
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    loadActiveSession();
    loadDeliverers();
  }, []);

  const loadActiveSession = async () => {
    try {
      const { ok, json, error } = await fetchSafe('/session/state');
      if (ok && json?.active) {
        setActiveSession(json);
      }
      setLoading(false);
    } catch (error) {
      console.error('Erro ao carregar sessão:', error);
      setLoading(false);
    }
  };

  const loadDeliverers = async () => {
    try {
      const response = await fetchWithAuth('/api/admin/team');
      const data = await response.json();
      setDeliverers(data.deliverers || []);
    } catch (error) {
      console.error('Erro ao carregar entregadores:', error);
    }
  };

  const handleSalaryChange = (delivererId, value) => {
    setSalaries(prev => ({
      ...prev,
      [delivererId]: parseFloat(value) || 0
    }));
  };

  const calculateTotals = () => {
    const totalRevenue = (activeSession?.route_value || 0) + (parseFloat(extraRevenue) || 0);
    const totalSalaries = Object.values(salaries).reduce((sum, val) => sum + val, 0);
    const totalCosts = (parseFloat(fuel) || 0) + (parseFloat(otherCosts) || 0) + totalSalaries;
    const netProfit = totalRevenue - totalCosts;

    return {
      totalRevenue,
      totalSalaries,
      totalCosts,
      netProfit
    };
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    const totals = calculateTotals();

    try {
      // 1. Salvar fechamento financeiro
      const financialResponse = await fetchWithAuth('/api/financial/daily-closure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: activeSession.session_id,
          date: new Date().toISOString().split('T')[0],
          revenue: totals.totalRevenue,
          delivery_costs: totals.totalSalaries,
          other_costs: (parseFloat(fuel) || 0) + (parseFloat(otherCosts) || 0),
          net_profit: totals.netProfit,
          total_packages: activeSession.total_packages,
          total_deliveries: activeSession.total_packages,
          deliverer_breakdown: salaries,
          expenses: [
            { type: 'Combustível', value: parseFloat(fuel) || 0, desc: 'Abastecimento do dia' },
            { type: 'Outros', value: parseFloat(otherCosts) || 0, desc: 'Custos operacionais' }
          ]
        })
      });

      if (!financialResponse.ok) throw new Error('Erro ao salvar financeiro');

      // 2. Finalizar sessão
      const completeResponse = await fetchWithAuth(`/api/session/${activeSession.session_id}/complete`, {
        method: 'POST'
      });

      if (!completeResponse.ok) throw new Error('Erro ao finalizar sessão');

      setSuccess(true);
      setTimeout(() => {
        window.location.href = '/?tab=history';
      }, 2000);

    } catch (error) {
      console.error('Erro ao finalizar rota:', error);
      alert('Erro ao processar fechamento. Tente novamente.');
    } finally {
      setSubmitting(false);
    }
  };

  const totals = calculateTotals();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Carregando...</p>
        </div>
      </div>
    );
  }

  if (!activeSession) {
    return (
      <div className="card-premium p-8 text-center">
        <XCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h3 className="text-xl font-bold text-gray-700 mb-2">Nenhuma sessão ativa</h3>
          <FullscreenToggle isFullscreen={isFullscreen} onToggle={() => setIsFullscreen(f => !f)} />
        <p className="text-gray-500">Não há sessão para finalizar no momento.</p>
      </div>
    );
  }

  if (success) {
    return (
      <div className="card-premium p-8 text-center">
        <CheckCircle className="w-20 h-20 text-green-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Fechamento Concluído!</h2>
        <p className="text-gray-600">Redirecionando para o histórico...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="card-premium p-6">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-green-500/30">
            <DollarSign className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">💰 Fechamento Diário</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Sessão: {activeSession.session_name || activeSession.session_id?.slice(0, 8)}
            </p>
          </div>
        </div>
      </div>

      {/* Info da Sessão */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card-premium p-4">
          <p className="text-sm text-gray-600 mb-1">Total de Pacotes</p>
          <p className="text-2xl font-bold text-blue-600">{activeSession.total_packages}</p>
        </div>
        <div className="card-premium p-4">
          <p className="text-sm text-gray-600 mb-1">Valor da Rota</p>
          <p className="text-2xl font-bold text-green-600">
            R$ {(activeSession.route_value || 0).toFixed(2)}
          </p>
        </div>
        <div className="card-premium p-4">
          <p className="text-sm text-gray-600 mb-1">Entregadores</p>
          <p className="text-2xl font-bold text-purple-600">{activeSession.num_deliverers}</p>
        </div>
      </div>

      {/* Formulário de Fechamento */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Custos Operacionais */}
        <div className="card-premium p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-red-500" />
            Custos Operacionais
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                <Fuel className="w-4 h-4 inline mr-1" />
                Combustível (R$)
              </label>
              <input
                type="number"
                step="0.01"
                value={fuel}
                onChange={(e) => setFuel(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="0.00"
              />
            </div>
            
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                <Receipt className="w-4 h-4 inline mr-1" />
                Outros Custos (R$)
              </label>
              <input
                type="number"
                step="0.01"
                value={otherCosts}
                onChange={(e) => setOtherCosts(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="0.00"
              />
            </div>
          </div>
        </div>

        {/* Receitas Extras */}
        <div className="card-premium p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-green-500" />
            Receitas Extras
          </h3>
          
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Lucros Adicionais (R$)
            </label>
            <input
              type="number"
              step="0.01"
              value={extraRevenue}
              onChange={(e) => setExtraRevenue(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="0.00"
            />
            <p className="text-xs text-gray-500 mt-1">Ex: gorjetas, taxa extra de urgência, etc.</p>
          </div>
        </div>

        {/* Salários dos Entregadores */}
        <div className="card-premium p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-blue-500" />
            Salário dos Entregadores
          </h3>
          
          <div className="space-y-3">
            {deliverers.filter(d => !d.is_partner).map(deliverer => (
              <div key={deliverer.telegram_id} className="flex items-center gap-4">
                <div className="flex-1">
                  <p className="font-semibold text-gray-900">{deliverer.name}</p>
                  <p className="text-xs text-gray-500">ID: {deliverer.telegram_id}</p>
                </div>
                <input
                  type="number"
                  step="0.01"
                  value={salaries[deliverer.telegram_id] || ''}
                  onChange={(e) => handleSalaryChange(deliverer.telegram_id, e.target.value)}
                  className="w-32 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="0.00"
                />
                <span className="text-sm text-gray-600">R$</span>
              </div>
            ))}
          </div>
        </div>

        {/* Resumo Financeiro */}
        <div className="card-premium p-6 bg-gradient-to-br from-blue-50 to-purple-50">
          <h3 className="text-lg font-bold text-gray-900 mb-4">📊 Resumo Financeiro</h3>
          
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-gray-700">Receita Total:</span>
              <span className="font-bold text-green-600">+ R$ {totals.totalRevenue.toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-700">Salários:</span>
              <span className="font-bold text-red-600">- R$ {totals.totalSalaries.toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-700">Combustível + Outros:</span>
              <span className="font-bold text-red-600">
                - R$ {((parseFloat(fuel) || 0) + (parseFloat(otherCosts) || 0)).toFixed(2)}
              </span>
            </div>
            <hr className="border-gray-300" />
            <div className="flex justify-between items-center">
          <style>{`
            .financial-closure-root.fullscreen {
              position: fixed !important;
              top: 0; left: 0; right: 0; bottom: 0;
              background: #f7f7fa;
              z-index: 9999;
              border-radius: 0;
              box-shadow: none;
              padding: 32px 0 0 0 !important;
              min-height: 100vh;
              max-width: 100vw;
              overflow-y: auto;
              transition: all 0.3s;
            }
            .financial-closure-root.fullscreen .card-premium {
              box-shadow: none !important;
            }
            .financial-closure-root.fullscreen .fullscreen-btn {
              background: #6C63FF !important;
            }
          `}</style>
              <span className="text-lg font-bold text-gray-900">Lucro Líquido:</span>
              <span className={`text-2xl font-black ${totals.netProfit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                R$ {totals.netProfit.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        {/* Botão de Finalizar */}
        <button
          type="submit"
          disabled={submitting}
          className="w-full py-4 rounded-xl font-bold text-lg bg-gradient-to-r from-green-600 to-emerald-600 text-white shadow-xl shadow-green-500/30 hover:shadow-2xl hover:scale-[1.02] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? '⏳ Processando...' : '✅ Finalizar Sessão e Salvar'}
        </button>
      </form>
    </div>
  );
}
