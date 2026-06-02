
import React, { useState, useEffect } from 'react';
import { MapIcon, Navigation, Package, Users } from 'lucide-react';
import MapCircuitPremium from './MapCircuitPremium.jsx';

export default function MapsView() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedSession, setSelectedSession] = useState(null);

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      const { ok, json, error } = await fetchSafe('/session/list/all');
      if (ok) {
        // Filtrar apenas sessões com rotas criadas (routes_count > 0)
        const withRoutes = (json.sessions || []).filter(s => (s.routes_count || 0) > 0);
        setSessions(withRoutes);
      } else {
        console.error('Erro ao carregar sessões:', error);
        setSessions([]);
      }
      // Filtrar apenas sessões com rotas criadas (routes_count > 0)
      const withRoutes = (data.sessions || []).filter(s => (s.routes_count || 0) > 0);
      setSessions(withRoutes);
    } catch (error) {
      console.error('Erro ao carregar sessões:', error);
      setSessions([]);
    } finally {
      setLoading(false);
    }
  };


  if (loading) {
    return (
      <div className="flex items-center justify-center h-full container-responsive p-responsive">
        <div className="animate-spin">
          <MapIcon className="w-8 h-8 text-primary-500" />
        </div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="card-premium p-10 text-center container-responsive p-responsive">
        <MapIcon className="w-16 h-16 mx-auto text-gray-400 mb-4" />
        <h3 className="text-xl font-bold mb-2 text-responsive">Nenhuma rota disponível</h3>
        <p className="text-gray-600 dark:text-gray-400 mb-6 text-responsive">
          Importe um arquivo de romaneio e crie rotas para visualizar no mapa.
        </p>
        <button 
          onClick={() => window.location.href = '/?tab=analysis'}
          className="btn-primary"
        >
          Ir para Roteirização
        </button>
      </div>
    );
  }

  if (selectedSession) {
    return (
      <div className="flex flex-col h-full gap-4 container-responsive p-responsive">
        <button 
          onClick={() => setSelectedSession(null)}
          className="btn-secondary self-start"
        >
          ← Voltar
        </button>
        <div className="flex-1 rounded-2xl overflow-hidden shadow-glass border border-gray-200 dark:border-gray-700">
          {selectedSession.routes && selectedSession.routes.length > 0 ? (
            <MapCircuitPremium stops={selectedSession.routes.flatMap(r => r.stops || [])} />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gray-100 dark:bg-gray-800">
              <p className="text-gray-500 text-responsive">Nenhuma parada nesta rota</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto space-y-4 pb-24 container-responsive p-responsive">
      <div className="sticky top-0 bg-white dark:bg-gray-900 p-4 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 z-10">
        <h2 className="text-lg font-bold flex items-center gap-2 text-responsive">
          <MapIcon className="w-5 h-5 text-primary-500" />
          Sessões com Rotas ({sessions.length})
        </h2>
      </div>

      <div className="grid gap-3 px-1">
        {sessions.map(session => {
          return (
            <div 
              key={session.id}
              className="card-premium p-4 cursor-pointer hover:shadow-lg transition-all list-responsive"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <h3 className="font-bold text-gray-900 dark:text-white truncate text-responsive">{session.name || session.id.slice(0, 8)}</h3>
                  <p className="text-xs text-gray-500 text-responsive">{session.date}</p>
                </div>
                <span className={`badge badge-${session.is_finalized ? 'warning' : 'success'} text-xs ml-2 flex-shrink-0`}>
                  {session.is_finalized ? 'Finalizada' : 'Ativa'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-3">
                <div className="flex items-center gap-2 text-sm">
                  <Package className="w-4 h-4 text-primary-500 flex-shrink-0" />
                  <span>{session.total_packages || 0} entregas</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Users className="w-4 h-4 text-primary-500 flex-shrink-0" />
                  <span>{session.routes_count || 0} rotas</span>
                </div>
              </div>

              <button 
                onClick={() => setSelectedSession(session)}
                className="w-full btn-primary flex items-center justify-center gap-2 py-2"
              >
                <Navigation className="w-4 h-4" />
                Ver Mapa
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
