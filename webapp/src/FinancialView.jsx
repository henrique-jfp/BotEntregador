import React, { useState } from 'react';
import { TrendingUp, TrendingDown, DollarSign, Wallet, Calendar, CreditCard, ArrowUpRight, ArrowDownRight, Users as UsersIcon, BarChart3, PieChart, Activity } from 'lucide-react';

export default function FinancialView({ data, adminStats }) {
  // Loading State
  if (!data) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="skeleton h-48 rounded-3xl" />
        <div className="skeleton h-32 rounded-2xl" />
        <div className="skeleton h-40 rounded-2xl" />
      </div>
    )
  }

  // Verificar se é view pessoal
  if (data.view === 'personal') {
    return <PersonalFinancialView data={data} />;
  }

  // Verificar se é view company
  if (data.view === 'company') {
    return <CompanyFinancialView data={data} adminStats={adminStats} />;
  }

  // 🔧 CORREÇÃO: Fallback inteligente baseado nos dados disponíveis
  // Se tem company_stats, é view de empresa
  if (data.company_stats) {
    return <CompanyFinancialView data={data} adminStats={adminStats} />;
  }
  
  // Se tem balance, é view pessoal
  if (data.balance !== undefined) {
    return <PersonalFinancialView data={data} />;
  }

  // Estado vazio elegante quando não há dados
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="relative overflow-hidden gradient-primary rounded-3xl p-6 text-white">
        <div className="absolute top-0 right-0 w-40 h-40 bg-white/10 rounded-full blur-3xl -mr-20 -mt-20" />
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center">
              <DollarSign className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-2xl font-bold">Financeiro</h2>
              <p className="text-white/70 text-sm">Gestão de receitas e custos</p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Empty State Premium */}
      <div className="card-premium">
        <div className="empty-state">
          <div className="empty-state-icon">
            <BarChart3 className="w-10 h-10 text-gray-400" />
          </div>
          <h3 className="empty-state-title">Nenhum dado financeiro disponível</h3>
          <p className="empty-state-description">
            Os dados financeiros aparecerão aqui assim que houver sessões finalizadas com entregas processadas.
          </p>
          
          {/* Quick Info Cards */}
          <div className="grid grid-cols-3 gap-4 w-full max-w-md mt-4">
            <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4 text-center">
              <Activity className="w-6 h-6 text-primary-500 mx-auto mb-2" />
              <p className="text-xs text-gray-500 dark:text-gray-400">Receitas</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">R$ 0</p>
            </div>
            <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4 text-center">
              <TrendingDown className="w-6 h-6 text-red-500 mx-auto mb-2" />
              <p className="text-xs text-gray-500 dark:text-gray-400">Custos</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">R$ 0</p>
            </div>
            <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4 text-center">
              <PieChart className="w-6 h-6 text-green-500 mx-auto mb-2" />
              <p className="text-xs text-gray-500 dark:text-gray-400">Lucro</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">R$ 0</p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Dica */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4">
        <p className="text-sm text-blue-800 dark:text-blue-300 flex items-start gap-2">
          <span className="text-lg">💡</span>
          <span>
            <strong>Dica:</strong> Importe um romaneio na aba "Roteirização" e finalize as entregas para começar a ver os dados financeiros aqui.
          </span>
        </p>
      </div>
    </div>
  );
}

function PersonalFinancialView({ data }) {
  const balanceFormatted = data.balance.toFixed(2).replace('.', ',')
  const mainValue = balanceFormatted.split(',')[0]
  const cents = balanceFormatted.split(',')[1]

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Balance Hero Card */}
      <div className="relative overflow-hidden gradient-success rounded-3xl p-6 text-white shadow-glass">
        <div className="absolute top-0 right-0 w-40 h-40 bg-white/10 rounded-full blur-3xl -mr-20 -mt-20" />
        <div className="absolute bottom-0 left-0 w-32 h-32 bg-white/10 rounded-full blur-3xl -ml-16 -mb-16" />
        
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center">
              <Wallet className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-white/70">Seus Ganhos</p>
              <p className="text-xs font-bold text-white/90">{data.period}</p>
            </div>
          </div>
          
          <div className="mb-6">
            <div className="flex items-baseline gap-1">
              <span className="text-xl font-bold opacity-80">R$</span>
              <span className="text-5xl font-black tracking-tight">{mainValue}</span>
              <span className="text-2xl font-bold opacity-80">,{cents}</span>
            </div>
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-white/20">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-white/70" />
              <span className="text-xs font-medium text-white/90">Próximo pagamento: Sexta</span>
            </div>
            <span className="badge bg-yellow-400/30 text-yellow-100 border-yellow-400/50 text-[10px]">
              A RECEBER
            </span>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 gap-3">
        <StatMiniCard 
          label="Entregas"
          value="--"
          icon={<TrendingUp className="w-4 h-4" />}
          trend="positive"
        />
        <StatMiniCard 
          label="Média/Dia"
          value={`R$ ${(data.balance / 5).toFixed(0)}`}
          icon={<DollarSign className="w-4 h-4" />}
          trend="neutral"
        />
      </div>

      {/* Transaction History Card */}
      <div className="card-premium overflow-hidden">
        <div className="bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-800/50 px-5 py-3 border-b border-gray-100 dark:border-gray-700/50">
          <h3 className="font-bold text-gray-900 dark:text-white text-sm flex items-center gap-2">
            <CreditCard className="w-4 h-4" />
            Extrato Recente
          </h3>
        </div>
        
        <div className="divide-y divide-gray-100 dark:divide-gray-700/50">
          <TransactionItem 
            title="Rota de Hoje"
            subtitle="Processando..."
            value="--"
            status="pending"
          />
          <TransactionItem 
            title="Rota Ontem"
            subtitle="Concluída"
            value={`+ R$ ${((data.balance > 0 ? data.balance : 50) * 0.4).toFixed(2).replace('.', ',')}`}
            status="completed"
          />
          <TransactionItem 
            title="Bônus Meta Semanal"
            subtitle="Extra conquistado"
            value={`+ R$ ${((data.balance > 0 ? data.balance : 50) * 0.1).toFixed(2).replace('.', ',')}`}
            status="bonus"
          />
        </div>
      </div>
    </div>
  );
}

function CompanyFinancialView({ data, adminStats }) {
  // 🔧 CORREÇÃO: Usar dados diretamente do backend (não company_stats)
  const revenue = data.company_stats?.revenue ?? data.revenue ?? 0;
  const costs = data.company_stats?.costs ?? data.costs ?? 0;
  const profit = data.company_stats?.profit ?? data.balance ?? (revenue - costs);
  
  const [extraRevenue, setExtraRevenue] = useState('');
  const [extraCosts, setExtraCosts] = useState('');
  const [closing, setClosing] = useState(false);
  const [closeMsg, setCloseMsg] = useState(null);
  const profitFormatted = profit.toFixed(2).replace('.', ',')
  const profitIsPositive = profit >= 0
  const canClose = adminStats?.active_session && adminStats?.pending === 0;

  const handleCloseDay = async () => {
    setClosing(true);
    setCloseMsg(null);
    try {
      const res = await fetch('/api/session/finalize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          extra_revenue: extraRevenue ? parseFloat(extraRevenue) : 0,
          other_costs: extraCosts ? parseFloat(extraCosts) : 0
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Falha ao fechar dia');

      setCloseMsg('✅ Dia fechado com sucesso.');
    } catch (err) {
      setCloseMsg(err.message);
    } finally {
      setClosing(false);
    }
  };

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Profit Overview Card */}
      <div className="relative overflow-hidden gradient-dark rounded-3xl p-6 text-white shadow-glass">
        <div className="absolute top-0 right-0 opacity-10">
          <DollarSign size={120} strokeWidth={1} />
        </div>
        
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-10 h-10 bg-white/10 backdrop-blur-sm rounded-2xl flex items-center justify-center">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-gray-400">Lucro Líquido</p>
              <p className="text-xs font-bold text-gray-300">{data.period}</p>
            </div>
          </div>
          
          <div className="mb-6">
            <div className={`text-5xl font-black ${profitIsPositive ? 'text-green-400' : 'text-red-400'}`}>
              R$ {profitFormatted}
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white/5 backdrop-blur-sm p-4 rounded-xl border border-white/10">
              <div className="flex items-center gap-1.5 text-green-300 text-xs mb-2 font-medium">
                <ArrowUpRight className="w-3.5 h-3.5" /> Receita
              </div>
              <div className="text-2xl font-black text-white">R$ {revenue.toFixed(0)}</div>
            </div>
            <div className="bg-white/5 backdrop-blur-sm p-4 rounded-xl border border-white/10">
              <div className="flex items-center gap-1.5 text-red-300 text-xs mb-2 font-medium">
                <ArrowDownRight className="w-3.5 h-3.5" /> Custos
              </div>
              <div className="text-2xl font-black text-white">R$ {costs.toFixed(0)}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Deliverers Payout Card */}
      <div className="card-premium overflow-hidden">
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 px-5 py-3 border-b border-gray-100 dark:border-gray-700/50">
          <h3 className="font-bold text-gray-900 dark:text-white text-sm flex items-center gap-2">
            <UsersIcon className="w-4 h-4" />
            Repasse aos Entregadores
          </h3>
        </div>
        
        <div className="p-5 space-y-4">
          {data.deliverers_stats && Object.entries(data.deliverers_stats).length > 0 ? (
            Object.entries(data.deliverers_stats).map(([name, val], idx) => (
              <div key={idx} className="flex items-center justify-between group hover:bg-gray-50 dark:hover:bg-gray-800/50 p-3 rounded-xl transition-all">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-black text-xs shadow-lg shadow-blue-500/30">
                    {name.substring(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <p className="font-bold text-sm text-gray-900 dark:text-white">{name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Colaborador</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-black text-lg text-gray-900 dark:text-white">
                    R$ {val.toFixed(2).replace('.', ',')}
                  </p>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-8">
              <div className="w-16 h-16 mx-auto mb-3 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                <UsersIcon className="w-8 h-8 text-gray-400" />
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">Nenhum repasse registrado</p>
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Os valores aparecerão aqui</p>
            </div>
          )}
        </div>
      </div>

      {canClose && (
        <div className="card-premium p-5 space-y-3">
          <h3 className="font-bold text-gray-900 dark:text-white">✅ Fechar Dia</h3>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Todos os pacotes foram finalizados. Informe custos e lucros extras para fechar a sessão.
          </p>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="number"
              placeholder="Lucro extra"
              value={extraRevenue}
              onChange={(e) => setExtraRevenue(e.target.value)}
              className="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
            />
            <input
              type="number"
              placeholder="Custos extras"
              value={extraCosts}
              onChange={(e) => setExtraCosts(e.target.value)}
              className="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
            />
          </div>
          <button
            onClick={handleCloseDay}
            disabled={closing}
            className={`w-full py-3 rounded-lg text-sm font-semibold ${closing ? 'bg-gray-400 text-white' : 'bg-emerald-600 text-white'}`}
          >
            {closing ? 'Fechando...' : 'Fechar Dia'}
          </button>
          {closeMsg && (
            <div className="text-sm text-gray-600 dark:text-gray-300">{closeMsg}</div>
          )}
        </div>
      )}
    </div>
  );
}

// Helper Components
function StatMiniCard({ label, value, icon, trend }) {
  const trendColors = {
    positive: 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30',
    negative: 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30',
    neutral: 'text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/30',
  }

  return (
    <div className="card-premium p-4">
      <div className={`w-8 h-8 rounded-xl flex items-center justify-center mb-3 ${trendColors[trend]}`}>
        {icon}
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400 font-medium mb-1">{label}</p>
      <p className="text-lg font-black text-gray-900 dark:text-white">{value}</p>
    </div>
  )
}

function TransactionItem({ title, subtitle, value, status }) {
  const statusConfig = {
    pending: { color: 'text-gray-400', bg: 'bg-gray-100 dark:bg-gray-800' },
    completed: { color: 'text-green-600 dark:text-green-400', bg: 'bg-green-50 dark:bg-green-900/20' },
    bonus: { color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-900/20' },
  }

  return (
    <div className="flex justify-between items-center p-4 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-all">
      <div className="flex-1">
        <p className="font-bold text-sm text-gray-900 dark:text-white mb-0.5">{title}</p>
        <p className={`text-xs font-semibold ${statusConfig[status].color}`}>{subtitle}</p>
      </div>
      <div className={`text-sm font-black font-mono ${statusConfig[status].color}`}>
        {value}
      </div>
    </div>
  )
}
