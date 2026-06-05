import { useState, useEffect } from 'react'
import { LayoutDashboard, Package, Map as MapIcon, Users, RefreshCw, Navigation, Sparkles, Zap, TrendingUp, Award, Moon, Sun, Archive, Trash2, Laptop } from 'lucide-react'
import MapCircuitPremium from './pages/MapCircuitPremium.jsx'
import MapRealtimeView from './components/MapRealtimeView'
import TeamView from './TeamView'
import RouteAnalysisView from './RouteAnalysisView'
import SeparationMode from './SeparationMode'
import HistoryView from './pages/HistoryView'
import AnalyticsPage from './pages/AnalyticsPage'
import HeatmapView from './HeatmapView'
import MapsView from './pages/MapsView'
import DelivererPublicView from './pages/DelivererPublicView'
import ProgressBar from './components/ProgressBar'
import OfflineIndicator from './components/OfflineIndicator'
import ZonaSulWarMap from './components/ZonaSulWarMap'
import { useResponsive } from './hooks/useResponsive'
import offlineSync from './services/offlineSync'

import { fetchWithAuth, fetchJsonWithAuth } from './api_client'

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [tgUser, setTgUser] = useState(null)
  const [roleInfo, setRoleInfo] = useState({ role: 'loading' })
  const [routeInfo, setRouteInfo] = useState(null)
  const [adminStats, setAdminStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [darkMode, setDarkMode] = useState(false)
  const [loadingProgress, setLoadingProgress] = useState(0)
  const [teamMembers, setTeamMembers] = useState([])
  const [zonalMapData, setZonalMapData] = useState({})
  const responsive = useResponsive()
  const [forceDesktop, setForceDesktop] = useState(localStorage.getItem('forceDesktop') === '1');

  const toggleForceDesktop = () => {
    const isForcing = localStorage.getItem('forceDesktop') === '1';
    if (isForcing) {
      localStorage.removeItem('forceDesktop');
    } else {
      localStorage.setItem('forceDesktop', '1');
    }
    window.location.reload();
  };


  // 1. Inicialização e Auth
  useEffect(() => {
    let userId = null;

    // Detectar dark mode automático
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    setDarkMode(prefersDark);
    if (prefersDark) {
      document.documentElement.classList.add('dark')
    }

    // Listener para mudanças de dark mode
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleDarkModeChange = (e) => {
      setDarkMode(e.matches);
      if (e.matches) {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    };
    mediaQuery.addEventListener('change', handleDarkModeChange);

    // Verifica query param ?tab= para navegação direta
    const params = new URLSearchParams(window.location.search);
    if (params.get('tab')) {
      // Mapear tabs legados/alias para os nomes corretos
      const tabMap = {
        'myroute': 'routes',  // Entregador abrindo rota via Telegram
        'route': 'routes',    // Alias
      };
      const requestedTab = params.get('tab');
      setActiveTab(tabMap[requestedTab] || requestedTab);
    }

    // Tenta pegar do Telegram WebApp
    if (window.Telegram && window.Telegram.WebApp) {
      const tg = window.Telegram.WebApp
      tg.ready()
      tg.expand()
      
      if (tg.initDataUnsafe?.user) {
        setTgUser(tg.initDataUnsafe.user)
        userId = tg.initDataUnsafe.user.id
      }
    }

    // Fallback para Dev
    if (!userId) {
      const params = new URLSearchParams(window.location.search);
      if (params.get('user_id')) {
        userId = parseInt(params.get('user_id'));
        setTgUser({ id: userId, first_name: 'Dev User' });
      }
    }

    if (userId) {
      fetchUserData(userId);
    } else {
      setRoleInfo({ role: 'guest' });
    }

    return () => mediaQuery.removeEventListener('change', handleDarkModeChange);
  }, [])

  // 2. Fetch de Dados
  const fetchUserData = async (id) => {
    setLoading(true)
    try {
      // Auth (usa helper que valida JSON e fornece erro legível)
      const authData = await fetchJsonWithAuth(`/auth/me?user_id=${id}`)
      setRoleInfo(authData)

      // Fetch paralelo dependendo da role
      const promises = []
      

      if (authData.role === 'admin') {
        promises.push(
            fetchWithAuth(`/admin/stats`)
                .then(r => r.json())
                .then(data => setAdminStats(data))
        )
        // Buscar equipe para o dashboard
        promises.push(
            fetchWithAuth(`/admin/team`)
                .then(r => r.json())
                .then(data => setTeamMembers(data || []))
                .catch(() => setTeamMembers([]))
        )
        // Buscar dados do mapa zonal (se disponível)
        promises.push(
            fetchWithAuth(`/analytics/neighborhood-stats?days=7`)
                .then(r => r.json())
                .then(data => {
                  // Converter para formato do mapa
                  const mapData = {};
                  (data.neighborhoods || []).forEach(n => {
                    mapData[n.name] = { volume: n.total_deliveries || 0, status: n.success_rate > 90 ? 'bom' : n.success_rate > 70 ? 'medio' : 'ruim' };
                  });
                  setZonalMapData(mapData);
                })
                .catch(() => setZonalMapData({}))
        )
      } else if (authData.role === 'deliverer') {
        promises.push(
            fetchWithAuth(`/api/deliverer/route?user_id=${id}`)
                .then(r => r.json())
                .then(data => setRouteInfo(data))
        )
      }
      
      await Promise.all(promises)

    } catch (e) {
      console.error("Erro fetching data", e)
      // Em caso de erro de rede ou auth, evita splash eterno definindo acesso como guest
      setRoleInfo({ role: 'guest' })
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = () => {
    if (tgUser?.id) {
      setLoadingProgress(0);
      setLoading(true);
      
      // Simular progresso
      const interval = setInterval(() => {
        setLoadingProgress(prev => {
          if (prev >= 80) {
            clearInterval(interval);
            return prev;
          }
          return prev + Math.random() * 40;
        });
      }, 300);

      fetchUserData(tgUser.id).finally(() => {
        setLoadingProgress(100);
        setTimeout(() => setLoadingProgress(0), 500);
      });
    }
  }

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    if (newDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }

  const handleDeleteSession = async () => {
    if (!adminStats?.active_session) return;

    const sessionId = adminStats.session_id;
    // Se houver sessão ativa, oferecer liberar da análise antes de excluir
    if (adminStats?.active_session && adminStats.session_id === sessionId) {
      if (confirm('⚠️ A sessão atual está ATIVA. Clique OK para LIBERAR a aba Análise (recomendado) ou Cancel para EXCLUIR permanentemente.')) {
        setLoading(true);
        try {
          const res = await fetchWithAuth(`/api/session/${sessionId}/release`, { method: 'POST' });
          if (res.ok) {
            alert('Sessão liberada da Análise — permanece ativa para mapa/separação.');
            // Atualiza estado local
            setAdminStats(prev => ({ ...prev, active_session: false, session_id: null, session_name: null }));
            return;
          } else {
            const body = await res.json().catch(() => ({}));
            alert(body.message || 'Falha ao liberar sessão');
            return;
          }
        } catch (err) {
          console.error('Erro ao liberar sessão:', err);
          alert('Erro ao liberar sessão');
          return;
        } finally {
          setLoading(false);
        }
      }
      // Se o usuário escolher Cancel no diálogo, prossegue para exclusão
    }

    // Pergunta de segurança dupla para exclusão permanente
    if (!window.confirm("⚠️ ATENÇÃO: Tem certeza que deseja excluir esta sessão?")) return;
    if (!window.confirm("❗Essa ação removerá TODOS os dados financeiros, rotas e pacotes vinculados a essa sessão PERMANENTEMENTE.\n\nDeseja realmente continuar?")) return;

    setLoading(true);
    try {
      const response = await fetchWithAuth(`/api/session/${sessionId}`, { 
        method: 'DELETE' 
      });
      const data = await response.json();

      if (response.ok) {
        // ⚡ LIMPAR IMEDIATAMENTE O ESTADO
        setAdminStats(prev => ({
          ...prev,
          active_session: false,
          session_id: null,
          session_name: null
        }));

        alert("✅ Sessão excluída com sucesso!");
        
        // Aguardar sincronização do banco de dados (aumentado para 1s)
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Refazer fetch completo para garantir sincronização
        if (tgUser?.id) {
          console.log('🔄 Refazendo fetch após deletar sessão...');
          await fetchUserData(tgUser.id);
          console.log('✅ Dashboard atualizado');
        }
      } else {
        alert(data.message || "❌ Erro ao excluir sessão");
      }
    } catch (error) {
      console.error('Erro ao excluir sessão:', error);
      alert("❌ Erro de conexão ao tentar excluir sessão");
    } finally {
      setLoading(false);
    }
  }

  // --- RENDERS ---

  // Rota pública minimalista para entregador (acesso via token)
  if (typeof window !== 'undefined' && window.location.pathname && window.location.pathname.startsWith('/public/deliverer')) {
    return <DelivererPublicView />;
  }

  const renderAdminDashboard = () => {
    
    return (
    <div className={`${responsive.isDesktop ? 'space-y-6' : 'space-y-4'} animate-fade-in`}>
      {/* Hero Stats Card - Compacto */}
      <div className="relative overflow-hidden gradient-primary rounded-3xl p-5 text-white shadow-glass">
        <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full blur-3xl -mr-16 -mt-16" />
        <div className="relative z-10">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-sm font-medium text-white/80">Painel Administrativo</p>
              <h2 className={`font-bold ${responsive.isDesktop ? 'text-2xl' : 'text-xl'}`}>Visão Geral 🚀</h2>
            </div>
            <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
              <Sparkles className="w-5 h-5" />
            </div>
          </div>
          
          <div className={`grid gap-2 ${responsive.isDesktop ? 'grid-cols-4' : 'grid-cols-2'}`}>
            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-3 border border-white/20">
              <div className="flex items-center gap-1.5 text-white/70 text-xs mb-1">
                <Package className="w-3 h-3" />
                <span>Pacotes</span>
              </div>
              <p className="text-2xl font-black">{adminStats?.packages_total || 0}</p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-3 border border-white/20">
              <div className="flex items-center gap-1.5 text-white/70 text-xs mb-1">
                <Zap className="w-3 h-3" />
                <span>Entregues</span>
              </div>
              <p className="text-2xl font-black text-green-300">{adminStats?.delivered || 0}</p>
            </div>
            {responsive.isDesktop && (
              <>
                <div className="bg-white/10 backdrop-blur-sm rounded-lg p-3 border border-white/20">
                  <div className="flex items-center gap-1.5 text-white/70 text-xs mb-1">
                    <Users className="w-3 h-3" />
                    <span>Entregadores</span>
                  </div>
                  <p className="text-2xl font-black text-blue-300">{adminStats?.active_deliverers || 0}</p>
                </div>
                <div className="bg-white/10 backdrop-blur-sm rounded-lg p-3 border border-white/20">
                  <div className="flex items-center gap-1.5 text-white/70 text-xs mb-1">
                    <TrendingUp className="w-3 h-3" />
                    <span>Pendentes</span>
                  </div>
                  <p className="text-2xl font-black text-yellow-300">{adminStats?.pending || 0}</p>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Grid Principal - 2 colunas em desktop */}
      <div className={`grid gap-4 ${responsive.isDesktop ? 'grid-cols-2' : 'grid-cols-1'}`}>
        
        {/* Card da Equipe */}
        <div className="card-premium p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <Users className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              </div>
              <h3 className="font-bold text-gray-900 dark:text-white text-sm">Equipe</h3>
            </div>
            <button 
              onClick={() => setActiveTab('team')}
              className="text-xs text-primary-600 dark:text-primary-400 hover:underline font-medium"
            >
              Gerenciar →
            </button>
          </div>
          
          {teamMembers.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {teamMembers.slice(0, 6).map((member, idx) => (
                <div 
                  key={member.id || idx}
                  className="flex items-center gap-2 bg-gray-50 dark:bg-gray-800 rounded-full px-3 py-1.5"
                >
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold ${
                    ['bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500', 'bg-pink-500', 'bg-cyan-500'][idx % 6]
                  }`}>
                    {member.name?.charAt(0)?.toUpperCase() || '?'}
                  </div>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {member.name?.split(' ')[0] || 'Entregador'}
                  </span>
                  {member.is_partner && <span className="text-xs">⭐</span>}
                </div>
              ))}
              {teamMembers.length > 6 && (
                <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 px-2">
                  +{teamMembers.length - 6} mais
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400">Nenhum entregador cadastrado</p>
          )}
        </div>
      </div>

      {/* Cérebro Geográfico - Mapa SVG */}
      <div className="card-premium p-4">
        <ZonaSulWarMap 
          data={zonalMapData}
          compact={true}
          onBairroClick={(bairro) => {
            console.log('Bairro clicado:', bairro);
            // Pode abrir detalhes do bairro no futuro
          }}
        />
      </div>

      {/* Status da Sessão - Compacto */}
      <div className="card-premium p-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
            <RefreshCw className={`w-4 h-4 text-white ${loading ? 'animate-spin' : ''}`} />
          </div>
          <div>
            <h3 className="font-bold text-gray-900 dark:text-white text-sm">Status da Sessão</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Monitoramento em tempo real</p>
          </div>
        </div>
        
        {adminStats?.active_session ? (
          <div className="space-y-3">
            <button
              onClick={() => {
                const resumeTab = localStorage.getItem('resume_tab') || 'analysis';
                setActiveTab(resumeTab);
              }}
              className="w-full flex items-center gap-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-xl border border-green-200 dark:border-green-800 hover:bg-green-100 dark:hover:bg-green-900/40 transition cursor-pointer"
            >
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse-soft" />
              <div className="flex-1 text-left">
                <p className="font-semibold text-green-700 dark:text-green-400 text-sm">Sessão Ativa</p>
                <p className="text-xs text-green-600 dark:text-green-500">{adminStats.session_name}</p>
              </div>
              <div className="text-green-600 dark:text-green-400 text-lg">→</div>
            </button>
            <button
              onClick={handleDeleteSession}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/40 transition cursor-pointer disabled:opacity-50"
            >
              <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />
              <span className="font-semibold text-red-700 dark:text-red-400 text-sm">Remover Sessão</span>
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
            <div className="w-2 h-2 bg-gray-400 rounded-full" />
            <p className="text-sm text-gray-600 dark:text-gray-400 font-medium">Nenhuma sessão ativa</p>
          </div>
        )}
      </div>
    </div>
    );
  }

  const renderDelivererDashboard = () => (
    <div className="space-y-5 animate-fade-in">
      {/* Hero Greeting Card */}
      <div className="relative overflow-hidden gradient-success rounded-3xl p-6 text-white shadow-glass">
        <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full blur-2xl" />
        <div className="absolute bottom-0 left-0 w-24 h-24 bg-white/10 rounded-full blur-2xl" />
        
        <div className="relative z-10">
          <div className="flex justify-between items-start mb-3">
            <div>
              <p className="text-sm font-medium text-white/80 mb-1">Bem-vindo de volta 👋</p>
              <h2 className="text-2xl font-black">{roleInfo.name?.split(' ')[0]}</h2>
            </div>
            <div className="flex flex-col items-end gap-2">
              <div className="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center">
                <Package className="w-6 h-6" />
              </div>
              {roleInfo.is_partner && (
                <span className="badge bg-yellow-400/30 text-yellow-100 border-yellow-400/50 text-[10px] px-2 py-0.5">
                  <Award className="w-3 h-3" /> SÓCIO
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard 
          icon={<MapIcon className="w-5 h-5" />}
          label="Mapa / Rota"
          value={routeInfo?.has_route ? 'Rota Ativa' : 'Abrir Mapa'}
          color="blue"
          isDisabled={false}
          onClick={() => setActiveTab(routeInfo?.has_route ? 'routes' : 'map')}
        />
      </div>

      {/* Active Route Details */}
      {routeInfo?.has_route && (
        <div className="card-premium overflow-hidden animate-slide-up">
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 px-5 py-3 border-b border-gray-100 dark:border-gray-700/50">
            <div className="flex justify-between items-center">
              <h3 className="font-bold text-gray-900 dark:text-white text-sm">Rota em Andamento</h3>
              <span className="badge badge-info">
                <Package className="w-3 h-3" />
                {routeInfo.summary.total_packages} volumes
              </span>
            </div>
          </div>
          
          <div className="grid grid-cols-3 divide-x divide-gray-100 dark:divide-gray-700/50">
            <RouteMetric 
              icon={<Navigation className="w-4 h-4" />}
              value={routeInfo.summary.total_stops}
              label="Paradas"
            />
            <RouteMetric 
              icon={<TrendingUp className="w-4 h-4" />}
              value={`${routeInfo.summary.distance_km} km`}
              label="Distância"
            />
            <RouteMetric 
              icon={<Zap className="w-4 h-4" />}
              value={`${routeInfo.summary.estimated_time_min}m`}
              label="Tempo"
            />
          </div>

          <div className="p-4">
            <button 
              onClick={() => setActiveTab('routes')}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              <Navigation className="w-5 h-5" />
              <span>Abrir Navegação</span>
            </button>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!routeInfo?.has_route && (
        <div className="card-premium p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
            <MapIcon className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="font-bold text-gray-900 dark:text-white mb-2">Nenhuma rota ativa</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">Aguardando designação de entregas</p>
        </div>
      )}
    </div>
  )

  const renderContent = () => {
    // Tela de Loading Inicial - SPLASH SCREEN PREMIUM
    if (roleInfo.role === 'loading') {
        return (
            <div className="h-full w-full flex flex-col items-center justify-center bg-gradient-to-br from-gray-50 via-white to-gray-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
              {/* Logo Grande */}
              <div className="mb-8 animate-fade-in">
                <div className="w-24 h-24 rounded-2xl shadow-2xl shadow-primary-500/30 overflow-hidden border-4 border-white dark:border-gray-800 mx-auto">
                  <img src="/logoMiniApp.jpg" alt="Bot Entregador" className="w-full h-full object-cover" />
                </div>
              </div>

              {/* Título */}
              <div className="text-center mb-12 animate-slide-up">
                <h1 className="text-4xl font-black text-gray-900 dark:text-white mb-2">Bot Entregador</h1>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Sistema de Rotas Inteligente</p>
              </div>

              {/* Loading Animation */}
              <div className="mb-12 animate-fade-in">
                <div className="relative w-16 h-16">
                  <div className="absolute inset-0 border-4 border-primary-200 dark:border-primary-900 rounded-full" />
                  <div className="absolute inset-0 border-4 border-transparent border-t-primary-600 border-r-primary-500 rounded-full animate-spin" />
                </div>
              </div>

              {/* Status Text */}
              <div className="text-center mb-8 space-y-2">
                <p className="text-sm font-semibold text-gray-900 dark:text-white">Preparando seu ambiente</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Carregando dados e sincronizando rotas...</p>
              </div>

              {/* Progress Bar */}
              <div className="w-48 h-2 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden shadow-inner">
                <div className="h-full bg-gradient-to-r from-primary-500 via-purple-500 to-primary-500 animate-shimmer" style={{
                  backgroundSize: '200% 100%',
                  animation: 'shimmer 2s infinite'
                }} />
              </div>

              {/* Footer */}
              <div className="absolute bottom-8 text-center">
                <p className="text-xs text-gray-400 dark:text-gray-600">
                  Versão 3.0 • Sistema Hybrid
                </p>
              </div>
            </div>
        )
    }

    if (activeTab === 'dashboard') {
        if (roleInfo.role === 'admin') return renderAdminDashboard()
        if (roleInfo.role === 'deliverer') return renderDelivererDashboard()
        // Guest ou role desconhecido - mostra tela de boas-vindas
        return (
          <div className="space-y-6 animate-fade-in">
            {/* Hero Card */}
            <div className="relative overflow-hidden gradient-primary rounded-3xl p-8 text-white shadow-glass">
              <div className="absolute top-0 right-0 w-40 h-40 bg-white/10 rounded-full blur-3xl -mr-20 -mt-20" />
              <div className="relative z-10">
                <h2 className="text-3xl font-black mb-2">Bem-vindo! 👋</h2>
                <p className="text-white/80">Sistema de Gestão de Entregas Inteligente</p>
              </div>
            </div>
            
            {/* Info Card */}
            <div className="card-premium p-6 text-center">
              <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                <Sparkles className="w-10 h-10 text-primary-500" />
              </div>
              <h3 className="font-bold text-gray-900 dark:text-white text-xl mb-2">Acesso de Visitante</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                Você está acessando como visitante. Para funcionalidades completas, 
                cadastre-se como entregador ou entre em contato com o administrador.
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-500">
                ID: {tgUser?.id || 'Não identificado'}
              </p>
            </div>
          </div>
        )
    }

    if (activeTab === 'analysis') {
        return (
             <div className="h-full overflow-y-auto">
                 <RouteAnalysisView />
             </div>
        )
    }

    if (activeTab === 'analytics') {
      return (
         <div className="h-full overflow-y-auto">
           <AnalyticsPage />
         </div>
      )
    }

    if (activeTab === 'separation') {
        return (
             <div className="h-full overflow-y-auto">
                 <SeparationMode />
             </div>
        )
    }

    if (activeTab === 'routes') {
        if (roleInfo.role === 'deliverer' && routeInfo?.has_route) {
            return (
                <div className="h-[calc(100vh-140px)] w-full rounded-2xl overflow-hidden shadow-glass border border-gray-200 dark:border-gray-700 relative">
                    <MapCircuitPremium stops={routeInfo?.stops || []} />
                    {/* Floating Info Overlay */}
                    <div className="absolute top-3 left-3 right-3 glass-strong p-3 rounded-xl shadow-lg z-[1000] flex justify-between items-center">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse-soft" />
                          <span className="text-sm font-semibold text-gray-900 dark:text-white">Modo Navegação</span>
                        </div>
                        <span className="badge badge-info text-[10px]">{routeInfo.stops.length} pontos</span>
                    </div>
                </div>
            )
        }
        return (
          <div className="card-premium p-10 text-center">
            <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
              <MapIcon className="w-10 h-10 text-gray-400" />
            </div>
            <h3 className="font-bold text-gray-900 dark:text-white mb-2">Nenhuma rota disponível</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">Não há rotas para exibir no mapa</p>
          </div>
        )
    }

    if (activeTab === 'map') {
      // 🗺️ REGRA DE OURO: Mostrar mapa global se for admin OU se não tiver rota específica (pré-separação)
      if (roleInfo.role === 'admin' || !routeInfo?.has_route) {
        return (
          <div className="h-full overflow-y-auto">
            <MapRealtimeView />
          </div>
        )
      }

      if (roleInfo.role === 'deliverer' && routeInfo?.has_route) {
        return (
          <div className="h-[calc(100vh-140px)] w-full rounded-2xl overflow-hidden shadow-glass border border-gray-200 dark:border-gray-700 relative">
            <MapCircuitPremium stops={routeInfo?.stops || []} />
          </div>
        )
      }

      return (
        <div className="card-premium">
          <div className="empty-state">
            <div className="empty-state-icon">
              <MapIcon className="w-10 h-10 text-gray-400" />
            </div>
            <h3 className="empty-state-title">Mapa em tempo real</h3>
            <p className="empty-state-description">
              O mapa fica disponível quando houver uma sessão ativa com rotas otimizadas (não depende da separação).
            </p>
            <div className="flex flex-col gap-2 w-full max-w-xs">
              <button 
                onClick={() => setActiveTab('analysis')}
                className="btn-primary flex items-center justify-center gap-2"
              >
                <Sparkles size={18} />
                Criar Nova Sessão
              </button>
            </div>
          </div>
        </div>
      )
    }
    
    if (activeTab === 'team') {
        return <TeamView />;
    }

    if (activeTab === 'history') {
        return <HistoryView />;
    }
    
    if (activeTab === 'heatmap') {
        return <HeatmapView />;
    }
    
    if (activeTab === 'map') {
        return <MapsView />;
    }

    return (
      <div className="card-premium">
        <div className="empty-state">
          <div className="empty-state-icon">
            <Zap className="w-10 h-10 text-primary-500" />
          </div>
          <h3 className="empty-state-title">Em Desenvolvimento</h3>
          <p className="empty-state-description">
            Esta funcionalidade está sendo preparada e estará disponível em breve. 🚧
          </p>
          <button 
            onClick={() => setActiveTab('dashboard')}
            className="btn-secondary flex items-center justify-center gap-2"
          >
            <LayoutDashboard size={18} />
            Voltar ao Dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950 text-gray-900 dark:text-gray-100 flex flex-col font-sans">
      {/* Indicador Offline/Online - DESABILITADO POR ENQUANTO */}
      {/* <OfflineIndicator /> */}
      
      {/* LAYOUT RESPONSIVO */}
      <div className={responsive.isDesktop ? 'flex h-screen overflow-hidden' : 'flex flex-col h-screen'}>
        
        {/* DESKTOP SIDEBAR */}
        {responsive.isDesktop && (
          <aside className="w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col shadow-lg">
            {/* Header Sidebar */}
            <div className="p-6 border-b border-gray-200 dark:border-gray-800">
              <div className="flex items-center gap-4">
                <div className="relative">
                  <div className="w-16 h-16 rounded-xl shadow-lg shadow-primary-500/30 overflow-hidden border-2 border-primary-500">
                    <img src="/logoMiniApp.jpg" alt="Bot Entregador" className="w-full h-full object-cover" />
                  </div>
                  <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white dark:border-gray-900 animate-pulse-soft" />
                </div>
                <div>
                  <h1 className="text-xl font-black text-gray-900 dark:text-white">Bot Entregador</h1>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Sistema de Rotas IA</p>
                </div>
              </div>
            </div>

            {/* Desktop Navigation */}
            <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-1">
              {[
                { id: 'dashboard', icon: <LayoutDashboard size={20} />, label: 'Dashboard' },
                { id: 'analysis', icon: <Sparkles size={20} />, label: 'Roteirização' },
                { id: 'heatmap', icon: <TrendingUp size={20} />, label: 'Cérebro Geográfico' },
                { id: 'separation', icon: <Navigation size={20} />, label: 'Separação' },
                { id: 'map', icon: <MapIcon size={20} />, label: 'Mapa' },
                { id: 'team', icon: <Users size={20} />, label: 'Equipe' },
                { id: 'history', icon: <Archive size={20} />, label: 'Histórico' },
              ].map(item => (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full px-4 py-3.5 rounded-xl transition-all flex items-center gap-3 font-medium text-sm group min-h-[48px] ${
                    activeTab === item.id
                      ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 shadow-sm'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  <div className={`flex-shrink-0 ${activeTab === item.id ? 'text-primary-600 dark:text-primary-400' : ''}`}>{item.icon}</div>
                  <span className="flex-1 text-left">{item.label}</span>
                  {activeTab === item.id && <div className="w-1 h-6 bg-primary-600 rounded-full" />}
                </button>
              ))}
            </nav>

            {/* Sidebar Footer */}
            <div className="p-4 border-t border-gray-200 dark:border-gray-800 space-y-3">
              <button 
                onClick={toggleDarkMode}
                className="w-full px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center justify-center gap-2 transition-colors"
              >
                {darkMode ? (
                  <>
                    <Sun size={16} /> Claro
                  </>
                ) : (
                  <>
                    <Moon size={16} /> Escuro
                  </>
                )}
              </button>
              <button 
                onClick={handleRefresh}
                className="w-full px-4 py-2 rounded-lg bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 hover:bg-primary-200 dark:hover:bg-primary-900/50 flex items-center justify-center gap-2 transition-colors font-medium"
              >
                <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Atualizar
              </button>
            </div>
          </aside>
        )}

        {/* MAIN CONTENT AREA - RESPONSIVE */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* MOBILE HEADER */}
          {responsive.isMobile && (
            <header className="glass-strong sticky top-0 z-20 border-b border-gray-200/50 dark:border-gray-700/50 pt-safe">
              <div className="px-5 py-4 flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="w-12 h-12 rounded-xl shadow-lg shadow-primary-500/30 overflow-hidden flex-shrink-0 border-2 border-white dark:border-gray-700">
                      <img src="/logoMiniApp.jpg" alt="Bot Entregador" className="w-full h-full object-cover" />
                    </div>
                    <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white dark:border-gray-900 animate-pulse-soft" />
                  </div>
                  <div>
                    <h1 className="text-lg font-black text-gray-900 dark:text-white leading-none">Bot Entregador</h1>
                    <p className="text-[10px] text-gray-500 dark:text-gray-400 font-medium">Sistema de Rotas</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button 
                    onClick={toggleDarkMode}
                    className="relative w-10 h-10 rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center justify-center transition-all active:scale-90 group"
                  >
                    {darkMode ? (
                      <Sun size={18} className="text-gray-500 dark:text-gray-400 group-hover:text-primary-600" />
                    ) : (
                      <Moon size={18} className="text-gray-500 dark:text-gray-400 group-hover:text-primary-600" />
                    )}
                  </button>
                  <button 
                    onClick={handleRefresh} 
                    className="relative w-10 h-10 rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center justify-center transition-all active:scale-90 group"
                  >
                    <RefreshCw 
                      size={18} 
                      className={`${loading ? 'animate-spin text-primary-600' : 'text-gray-500 dark:text-gray-400 group-hover:text-primary-600'} transition-colors`} 
                    />
                  </button>
                  {roleInfo.role === 'admin' && (
                    <button
                      onClick={toggleForceDesktop}
                      className="relative w-10 h-10 rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center justify-center transition-all active:scale-90 group"
                    >
                      <Laptop size={18} className={`${forceDesktop ? 'text-primary-600' : 'text-gray-500 dark:text-gray-400 group-hover:text-primary-600'}`} />
                    </button>
                  )}
                </div>
              </div>
              <ProgressBar visible={loadingProgress > 0} percentage={loadingProgress} />
            </header>
          )}

          {/* TABLET/DESKTOP HEADER */}
          {responsive.isTablet && (
            <header className="glass-strong sticky top-0 z-20 border-b border-gray-200/50 dark:border-gray-700/50 pt-safe">
              <div className="px-6 py-4 flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="w-14 h-14 rounded-xl shadow-lg shadow-primary-500/30 overflow-hidden flex-shrink-0 border-2 border-white dark:border-gray-700">
                      <img src="/logoMiniApp.jpg" alt="Bot Entregador" className="w-full h-full object-cover" />
                    </div>
                    <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white dark:border-gray-900 animate-pulse-soft" />
                  </div>
                  <div>
                    <h1 className="text-xl font-black text-gray-900 dark:text-white leading-none">Bot Entregador</h1>
                    <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">Sistema de Rotas</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button 
                    onClick={toggleDarkMode}
                    className="relative w-12 h-12 rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center justify-center transition-all active:scale-90 group"
                  >
                    {darkMode ? (
                      <Sun size={20} className="text-gray-500 dark:text-gray-400 group-hover:text-primary-600" />
                    ) : (
                      <Moon size={20} className="text-gray-500 dark:text-gray-400 group-hover:text-primary-600" />
                    )}
                  </button>
                  <button 
                    onClick={handleRefresh} 
                    className="relative w-12 h-12 rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center justify-center transition-all active:scale-90 group"
                  >
                    <RefreshCw 
                      size={20} 
                      className={`${loading ? 'animate-spin text-primary-600' : 'text-gray-500 dark:text-gray-400 group-hover:text-primary-600'} transition-colors`} 
                    />
                  </button>
                  {roleInfo.role === 'admin' && (
                    <button
                      onClick={toggleForceDesktop}
                      className="relative w-12 h-12 rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center justify-center transition-all active:scale-90 group"
                    >
                      <Laptop size={20} className={`${forceDesktop ? 'text-primary-600' : 'text-gray-500 dark:text-gray-400 group-hover:text-primary-600'}`} />
                    </button>
                  )}
                </div>
              </div>
              <ProgressBar visible={loadingProgress > 0} percentage={loadingProgress} />
            </header>
          )}

          {/* Content */}
          <main className="flex-1 overflow-auto">
            <div className={`mx-auto ${
              responsive.isDesktop ? 'px-8 py-8 max-w-7xl' : 
              responsive.isTablet ? 'px-6 py-6 max-w-4xl' : 
              'px-4 py-5 pb-24'
            }`}>
              {renderContent()}
            </div>
          </main>
        </div>
      </div>

      {/* MOBILE BOTTOM NAVIGATION */}
      {responsive.isMobile && (
        <nav className="fixed bottom-0 left-0 right-0 glass-strong border-t border-gray-200/50 dark:border-gray-700/50 pb-safe z-30 shadow-glass">
          <div className="max-w-lg mx-auto">
            <div className="flex justify-around items-center h-16 px-2">
              <TabButton 
                icon={<LayoutDashboard size={22} />} 
                label="Início" 
                isActive={activeTab === 'dashboard'} 
                onClick={() => setActiveTab('dashboard')} 
              />
              <TabButton 
                icon={<Sparkles size={22} />} 
                label="Análise" 
                isActive={activeTab === 'analysis'} 
                onClick={() => setActiveTab('analysis')} 
              />
              <TabButton 
                icon={<TrendingUp size={22} />} 
                label="Cérebro" 
                isActive={activeTab === 'heatmap'} 
                onClick={() => setActiveTab('heatmap')} 
              />
              <TabButton 
                icon={<MapIcon size={22} />} 
                label="Mapas" 
                isActive={activeTab === 'map'} 
                onClick={() => setActiveTab('map')} 
              />
              <TabButton 
                icon={<Navigation size={22} />} 
                label="Separação" 
                isActive={activeTab === 'separation'} 
                onClick={() => setActiveTab('separation')} 
              />
              <TabButton 
                icon={<Archive size={22} />} 
                label="Histórico" 
                isActive={activeTab === 'history'} 
                onClick={() => setActiveTab('history')}
              />
            </div>
          </div>
        </nav>
      )}
    </div>
  )
}

function TabButton({ icon, label, isActive, onClick }) {
  return (
    <button 
      onClick={onClick}
      className={`relative flex flex-col items-center justify-center w-full h-full transition-all duration-300 ${
        isActive 
          ? 'text-primary-600 dark:text-primary-400' 
          : 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'
      }`}
    >
      {/* Active Indicator */}
      {isActive && (
        <>
          <div className="absolute -top-[1px] left-1/2 -translate-x-1/2 w-12 h-1 gradient-primary rounded-b-full shadow-lg shadow-primary-500/30" />
          <div className="absolute inset-0 bg-primary-50/50 dark:bg-primary-900/10 rounded-2xl mx-2" />
        </>
      )}
      
      {/* Icon Container */}
      <div className={`relative z-10 transition-all duration-300 ${isActive ? 'scale-110 -translate-y-0.5' : ''}`}>
        <div className={`p-1.5 rounded-xl transition-all ${isActive ? 'bg-primary-100 dark:bg-primary-900/30' : ''}`}>
          {icon}
        </div>
      </div>
      
      {/* Label */}
      <span className={`relative z-10 text-[10px] font-semibold mt-1 transition-all ${isActive ? 'font-bold' : ''}`}>
        {label}
      </span>
    </button>
  )
}

// Helper Components
function ActionCard({ icon, label, sublabel, color, onClick }) {
  const colorClasses = {
    green: 'from-green-500 to-emerald-600 shadow-green-500/30',
    blue: 'from-blue-500 to-indigo-600 shadow-blue-500/30',
    purple: 'from-purple-500 to-indigo-600 shadow-purple-500/30',
  }

  return (
    <button 
      onClick={onClick}
      className="group relative overflow-hidden"
    >
      <div className={`absolute inset-0 bg-gradient-to-br ${colorClasses[color]} rounded-2xl shadow-lg transition-all group-hover:shadow-xl group-active:scale-95`} />
      <div className="relative p-4 flex flex-col items-center text-center text-white">
        <div className="w-10 h-10 mb-2 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
          {icon}
        </div>
        <p className="font-bold text-sm">{label}</p>
        <p className="text-[10px] text-white/70 font-medium">{sublabel}</p>
      </div>
    </button>
  )
}

function StatCard({ icon, label, value, color, isDisabled, onClick }) {
  const colorClasses = {
    green: 'from-green-500 to-emerald-600 text-green-700 dark:text-green-400 bg-green-100 dark:bg-green-900/30',
    blue: 'from-blue-500 to-indigo-600 text-blue-700 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/30',
  }

  return (
    <button 
      onClick={onClick}
      disabled={isDisabled}
      className={`card-premium p-4 flex items-center gap-3 text-left transition-all active:scale-95 ${isDisabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${colorClasses[color].split('text-')[1]}`}>
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-500 dark:text-gray-400 font-medium mb-0.5">{label}</p>
        <p className="font-bold text-lg text-gray-900 dark:text-white truncate">{value}</p>
      </div>
    </button>
  )
}

function RouteMetric({ icon, value, label }) {
  return (
    <div className="py-4 text-center">
      <div className="flex items-center justify-center gap-1 text-gray-400 dark:text-gray-500 mb-2">
        {icon}
        <span className="text-xs font-medium">{label}</span>
      </div>
      <p className="text-xl font-black text-gray-900 dark:text-white">{value}</p>
    </div>
  )
}

export default App
