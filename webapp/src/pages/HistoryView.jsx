import React, { useState, useEffect } from 'react';
import { Archive, MapPin, Users, DollarSign, Calendar, ChevronDown, Download, Clock, Package, TrendingUp, ChevronRight, History, FolderOpen, Trash2 } from 'lucide-react';
import { fetchSafe } from '../api_client';

const HistoryView = () => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedSession, setExpandedSession] = useState(null);
  const [filter, setFilter] = useState('all');
  const [activeSession, setActiveSession] = useState(null);

  // Carregar histórico de sessões
  useEffect(() => {
    fetchHistory();
    fetchActiveSession();
  }, []);

  const fetchHistory = async () => {
    try {
      const { ok, json, error } = await fetchSafe('/history/sessions?limit=100');
      if (ok) setSessions(json.sessions || (Array.isArray(json) ? json : []));
      else {
        console.error('Erro ao carregar histórico:', error);
        setSessions([]);
      }
      setLoading(false);
    } catch (error) {
      console.error('Erro ao carregar histórico:', error);
      setLoading(false);
    }
  };

  const deleteSession = async (sessionId, e) => {
    e.stopPropagation();
    try {
      // Tenta exclusão normal
      let { ok, json, error } = await fetchSafe(`/session/${sessionId}`, { method: 'DELETE' });
      // Se falhou por sessão em uso, tenta forçar
      if (!ok || json.status !== 'success') {
        const msg = json?.detail || json?.message || error || '';
        if (msg.includes('Sessão em uso') && msg.includes('force=true')) {
          if (window.confirm('A sessão está em uso (rotas atribuídas ou não finalizadas).\nDeseja forçar a exclusão? Isso removerá todos os dados não finalizados.')) {
            ({ ok, json, error } = await fetchSafe(`/session/${sessionId}?force=true`, { method: 'DELETE' }));
            if (!ok || json.status !== 'success') {
              throw new Error(json?.detail || json?.message || error || 'Erro ao forçar exclusão');
            }
          } else {
            return;
          }
        } else {
          throw new Error(msg || 'Erro ao excluir sessão');
        }
      }
      // Remove da lista local instantaneamente
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (activeSession && activeSession.session_id === sessionId) {
        fetchActiveSession();
      }
      if (window.fetchDelivererRoutes) window.fetchDelivererRoutes();
      window.location.reload();
    } catch (error) {
      alert('Erro ao excluir sessão: ' + (error?.message || error));
    }
  };

  // Deleta diretamente com force após confirmação — usado pelo botão principal
  const handleDeleteClick = async (sessionId, e) => {
    e.stopPropagation();
    const ok = window.confirm('Essa ação removerá TODOS os dados financeiros, rotas e pacotes vinculados a essa sessão PERMANENTEMENTE.\n\nDeseja realmente continuar?');
    if (!ok) return;

    try {
      const { ok, json, error } = await fetchSafe(`/session/${sessionId}?force=true`, { method: 'DELETE' });
      if (!ok || json.status !== 'success') {
        throw new Error(json?.detail || json?.message || error || 'Erro ao excluir sessão');
      }

      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (activeSession && activeSession.session_id === sessionId) {
        fetchActiveSession();
      }
      if (window.fetchDelivererRoutes) window.fetchDelivererRoutes();
      window.location.reload();
    } catch (error) {
      alert('Erro ao excluir sessão: ' + (error?.message || error));
    }
  };

  const fetchActiveSession = async () => {
    try {
      const { ok, json, error } = await fetchSafe('/session/state');
      if (ok && json?.active) {
        setActiveSession(json);
      } else {
        setActiveSession(null);
      }
    } catch (error) {
      console.error('Erro ao carregar sessão ativa:', error);
      setActiveSession(null);
    }
  };

  // Retomar sessão - carregar estado completo
  const handleResumeSession = async (sessionId) => {
    try {
      const { ok, json, error } = await fetchSafe(`/session/${sessionId}/resume`);
      if (!ok) throw new Error(error || 'Erro ao carregar sessão');
      
      // Salva sessão no localStorage para recuperação
      localStorage.setItem('resuming_session', JSON.stringify(data));
      localStorage.setItem('current_session_id', sessionId);
      
      // ✅ SEMPRE vai para a aba 'map' para visualizar as rotas
      window.location.href = `/?tab=map&session_id=${sessionId}`;
    } catch (error) {
      console.error('Erro ao retomar sessão:', error);
      alert('Erro ao carregar sessão. Tente novamente.');
    }
  };

  // Formatar moeda
  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(value || 0);
  };

  // Formatar data
  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('pt-BR');
  };

  // Calcular duração
  const calculateDuration = (created, completed) => {
    if (!created || !completed) return '-';
    const start = new Date(created);
    const end = new Date(completed);
    const minutes = Math.round((end - start) / 60000);
    return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
  };

  // Baixar relatório CSV
  const handleDownloadReport = async (sessionId) => {
    try {
      // Implementar endpoint para export CSV
      window.open(`/api/session/${sessionId}/export`, '_blank');
    } catch (error) {
      console.error('Erro ao baixar relatório:', error);
    }
  };

  // Filtrar sessões
  const filteredSessions = filter === 'all' 
    ? sessions 
    : filter === 'active'
    ? sessions.filter(s => !s.is_completed && s.status !== 'completed')
    : filter === 'empty'
    ? sessions.filter(s => !s.is_completed && (s.addresses_count === 0 || !s.addresses_count))
    : sessions.filter(s => s.is_completed || s.status === 'completed');

  if (loading) {
    return (
      <div className="space-y-4 animate-fade-in p-6 container-responsive p-responsive">
        <div className="skeleton h-24 rounded-2xl" />
        <div className="skeleton h-16 rounded-xl" />
        <div className="skeleton h-32 rounded-2xl" />
        <div className="skeleton h-32 rounded-2xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in container-responsive p-responsive">
      {/* Header Premium */}
      <div className="card-premium p-6 container-responsive p-responsive">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center shadow-lg shadow-primary-500/30">
            <Archive className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              📚 Histórico de Sessões
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {filteredSessions.length} sessão(ões) finalizada(s)
            </p>
          </div>
        </div>
      </div>

      {/* Status da Sessão */}
      <div className="card-premium p-5 container-responsive p-responsive">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-gray-700 dark:text-gray-200">Status da Sessão</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Monitoramento em tempo real</p>
          </div>
          {activeSession?.active ? (
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-green-100 text-green-700">ATIVA</span>
          ) : (
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-gray-100 text-gray-600">INATIVA</span>
          )}
        </div>

        <div className="mt-4">
          {activeSession?.active ? (
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-green-50/70 border border-green-200 rounded-xl p-4">
              <div>
                <div className="text-sm font-semibold text-green-800">Sessão ativa: {activeSession.session_name || activeSession.session_id?.slice(0, 8)}</div>
                <div className="text-xs text-green-700 mt-1">
                  {activeSession.total_packages || 0} pacotes • {activeSession.num_deliverers || 0} entregadores
                </div>
              </div>
              <button
                onClick={() => handleResumeSession(activeSession.session_id)}
                className="px-4 py-2 rounded-lg bg-green-600 text-white text-sm font-semibold shadow-lg shadow-green-500/30"
              >
                Retomar sessão
              </button>
            </div>
          ) : (
            <div className="text-sm text-gray-500 dark:text-gray-400">Nenhuma sessão ativa</div>
          )}
        </div>
      </div>

      {/* Filtros Premium */}
      <div className="flex gap-2 flex-wrap container-responsive">
        {[
          { value: 'all', label: 'Todas', icon: FolderOpen },
          { value: 'active', label: 'Ativas', icon: Clock },
          { value: 'empty', label: 'Vazias', icon: Trash2 },
          { value: 'completed', label: 'Completas', icon: Archive }
        ].map(({ value, label, icon: Icon }) => (
          <button
            key={value}
            onClick={() => setFilter(value)}
            className={`px-4 py-2.5 rounded-xl font-semibold transition-all flex items-center gap-2 ${
              filter === value
                ? 'bg-primary-600 text-white shadow-lg shadow-primary-500/30'
                : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      {/* Botão de Limpeza em Massa (quando filtro = empty) */}
      {filter === 'empty' && filteredSessions.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 container-responsive p-responsive">
          <p className="text-sm text-red-700 dark:text-red-300 mb-3">
            🗑️ {filteredSessions.length} sessões vazias encontradas
          </p>
          <button
            onClick={async () => {
              if (!window.confirm(`Tem certeza? Vai deletar ${filteredSessions.length} sessões vazias.`)) return;
              setLoading(true);
              let deleted = 0;
              for (const s of filteredSessions) {
                try {
                  await fetch(`/api/session/${s.id}`, { method: 'DELETE' });
                  deleted++;
                } catch (e) {
                  console.error('Erro ao deletar:', e);
                }
              }
              alert(`✅ ${deleted} sessões deletadas`);
              fetchHistory();
              setLoading(false);
            }}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-semibold"
          >
            Deletar Tudo
          </button>
        </div>
      )}

      {/* Lista de Sessões ou Empty State */}
      {filteredSessions.length === 0 ? (
        <div className="card-premium container-responsive p-responsive">
          <div className="empty-state">
            <div className="empty-state-icon">
              <History className="w-10 h-10 text-gray-400" />
            </div>
            <h3 className="empty-state-title">Nenhuma sessão finalizada ainda</h3>
            <p className="empty-state-description">
              Suas sessões de entrega finalizadas aparecerão aqui. Importe um romaneio, distribua as rotas e finalize as entregas para começar.
            </p>
            
            {/* Quick Stats Placeholder */}
            <div className="grid grid-cols-3 gap-4 w-full max-w-md mt-2 table-responsive">
              <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4 text-center">
                <Package className="w-6 h-6 text-primary-500 mx-auto mb-2" />
                <p className="text-xs text-gray-500 dark:text-gray-400">Entregas</p>
                <p className="text-lg font-bold text-gray-900 dark:text-white">0</p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4 text-center">
                <TrendingUp className="w-6 h-6 text-green-500 mx-auto mb-2" />
                <p className="text-xs text-gray-500 dark:text-gray-400">Lucro Total</p>
                <p className="text-lg font-bold text-gray-900 dark:text-white">R$ 0</p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4 text-center">
                <Clock className="w-6 h-6 text-blue-500 mx-auto mb-2" />
                <p className="text-xs text-gray-500 dark:text-gray-400">Horas</p>
                <p className="text-lg font-bold text-gray-900 dark:text-white">0h</p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-3 list-responsive">
          {filteredSessions.map((session) => (
            <div
              key={session.id}
              className="card-premium overflow-hidden container-responsive p-responsive"
            >
                {/* Card Header - Clicável */}
                <div
                  onClick={() => setExpandedSession(expandedSession === session.id ? null : session.id)}
                  className="w-full p-6 hover:bg-gray-50 dark:hover:bg-gray-700 transition flex items-center justify-between"
                >
                  <div className="flex items-center gap-4 flex-1 text-left list-responsive">
                    <div className="flex-1">
                      <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2 text-responsive">
                        Sessão #{session.id.slice(0, 8)}
                      </h3>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm table-responsive">
                        <div>
                          <p className="text-gray-500 dark:text-gray-400 text-responsive">Criada</p>
                          <p className="text-gray-900 dark:text-white font-medium text-responsive">
                            {formatDate(session.created_at)}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500 dark:text-gray-400 text-responsive">Endereços</p>
                          <p className="text-gray-900 dark:text-white font-medium text-responsive">
                            {session.addresses_count || 0}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500 dark:text-gray-400 text-responsive">Entregadores</p>
                          <p className="text-gray-900 dark:text-white font-medium text-responsive">
                            {session.deliverers_count || 0}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500 dark:text-gray-400 text-responsive">Duração</p>
                          <p className="text-gray-900 dark:text-white font-medium text-responsive">
                            {calculateDuration(session.created_at, session.completed_at)}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 md:gap-3 justify-end">
                    {/* Botão Retomar */}
                    {!session.is_completed && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleResumeSession(session.id);
                        }}
                        className="px-3 py-1 md:px-4 md:py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg font-bold text-xs md:text-sm transition flex items-center gap-1 md:gap-2 whitespace-nowrap"
                      >
                        <span className="hidden md:inline">▶️ Retomar</span>
                        <span className="md:hidden">Retomar</span>
                      </button>
                    )}
                    
                    {/* Botão Excluir - VERMELHO e VISÍVEL */}
                    <button
                      onClick={(e) => handleDeleteClick(session.id, e)}
                      className="px-3 py-1 md:px-4 md:py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-bold text-xs md:text-sm transition flex items-center gap-1 md:gap-2 shadow-lg whitespace-nowrap"
                      title="Excluir sessão permanentemente"
                    >
                      <Trash2 size={16} className="md:w-[18px]" />
                      <span className="hidden md:inline">Excluir</span>
                      <span className="md:hidden">Del</span>
                    </button>

                    <ChevronDown
                      className={`w-5 h-5 md:w-6 md:h-6 text-gray-400 transition-transform flex-shrink-0 ${expandedSession === session.id ? 'transform rotate-180' : ''}`}
                    />
                  </div>
                </div>

                {/* Expanded Content */}
                {expandedSession === session.id && (
                  <div className="border-t dark:border-gray-700 p-6 bg-gray-50 dark:bg-gray-700/30">
                    {/* Estatísticas */}
                    {session.statistics && Object.keys(session.statistics).length > 0 && (
                      <div className="mb-6">
                        <h4 className="font-bold text-gray-900 dark:text-white mb-4">
                          📊 Estatísticas
                        </h4>
                        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg text-sm space-y-2 table-responsive">
                          {Object.entries(session.statistics).map(([key, value]) => (
                            <div key={key} className="flex justify-between">
                              <span className="text-gray-600 dark:text-gray-400 capitalize">
                                {key.replace(/_/g, ' ')}:
                              </span>
                              <span className="font-medium text-gray-900 dark:text-white">
                                {typeof value === 'number' ? value.toFixed(2) : value}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Meta */}
                    <div className="mb-6">
                      <h4 className="font-bold text-gray-900 dark:text-white mb-4">ℹ️ Informações</h4>
                      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg text-sm space-y-2 table-responsive">
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">ID</span>
                          <span className="font-mono text-gray-900 dark:text-white">{session.id}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Status</span>
                          <span className="px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded text-xs font-medium">
                            {session.status}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Atualizado</span>
                          <span className="text-gray-900 dark:text-white">
                            {formatDate(session.last_updated)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Botões de Ação */}
                    <div className="flex gap-2 container-responsive">
                      <button
                        onClick={() => handleDownloadReport(session.id)}
                        className="flex-1 btn-primary flex items-center justify-center gap-2"
                      >
                        <Download className="w-4 h-4" />
                        Exportar Relatório
                      </button>
                    </div>
                  </div>
                )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default HistoryView;
