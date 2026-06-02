import React, { useState, useRef, useEffect } from 'react';
import { FileUp, Sparkles, MapPin, AlertCircle, Users, Send, Map, TrendingUp, Navigation } from 'lucide-react';
import { useResponsive } from './hooks/useResponsive';
import BarcodeScanner from './components/BarcodeScanner';
import RoutePreviewMap from './components/RoutePreviewMap';
import BaseLocationSelector from './components/BaseLocationSelector';
import { fetchWithAuth } from './api_client';

export default function RouteAnalysisView() {
  const responsive = useResponsive();
  
  
  // ===== ANÁLISE SIMPLES (por lista de endereços) =====
  const [viewMode, setViewMode] = useState('simple');  // 'simple' ou 'import'
  
  // Simple Analysis
  const [addressesText, setAddressesText] = useState('');
  const [simpleRouteValue, setSimpleRouteValue] = useState('');
  const [simpleAnalysis, setSimpleAnalysis] = useState(null);
  const [simpleLoading, setSimpleLoading] = useState(false);
  const [mapUrl, setMapUrl] = useState(null);
  const [mapLoading, setMapLoading] = useState(false);
  
  // ===== IMPORTAÇÃO ROMANEIO (fluxo multi-import) =====
  const [file, setFile] = useState(null);
  const [importAddressesText, setImportAddressesText] = useState('');
  const [importRouteValue, setImportRouteValue] = useState('');
  const [hasRomaneio, setHasRomaneio] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [importAnalysis, setImportAnalysis] = useState(null);
  const [numDeliverers, setNumDeliverers] = useState(2);
  const [routes, setRoutes] = useState([]);
  const [assignments, setAssignments] = useState({});
  const [autoOptimizeAfterImport, setAutoOptimizeAfterImport] = useState(false);
  
  // ===== LOCALIZAÇÃO DA BASE =====
  const [baseAddress, setBaseAddress] = useState('');
  const [baseLat, setBaseLat] = useState(-22.9068);
  const [baseLng, setBaseLng] = useState(-43.1729);
  const [showBaseMap, setShowBaseMap] = useState(false);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [deliverers, setDeliverers] = useState([]);
  const fileInputRef = useRef(null);
  const [showScanner, setShowScanner] = useState(false);

  useEffect(() => {
    // 1. Carregar Entregadores
    fetchWithAuth(`/admin/team`)
      .then(r => r.json())
      .then(data => setDeliverers(data))
      .catch(() => setDeliverers([]));

    // 2. Restaurar Estado da Sessão (Cross-Device)
    fetchWithAuth(`${import.meta.env.VITE_API_URL}/session/state`)
      .then(r => r.json())
      .then(data => {
        if (data.active) {
          console.log("Restaurando sessão:", data);
          if (data.has_romaneio) {
            setViewMode('import');
            setHasRomaneio(true);
            setSessionId(data.session_id);
            if (data.route_value) setImportRouteValue(data.route_value);
            if (data.num_deliverers) setNumDeliverers(data.num_deliverers);
            
            // Restaura rotas se houver
            if (data.routes && data.routes.length > 0) {
              setRoutes(data.routes);
              setAssignments(data.assignments || {});
            }
            
            // Recarrega relatório visual
            fetchWithAuth(`${import.meta.env.VITE_API_URL}/session/report`)
               .then(r => r.json())
               .then(data => setImportAnalysis(data))
               .catch(e => console.error("Erro recarregar report", e));
          }
        }
      })
      .catch(e => console.error("Erro ao checar estado", e));
  }, []);

  // ====== ABA 1: ANÁLISE SIMPLES POR ENDEREÇOS ======
  
  const handleAnalyzeAddresses = async () => {
    if (!addressesText.trim() || !simpleRouteValue) {
      setError('Preencha os endereços e o valor total');
      return;
    }

    setSimpleLoading(true);
    setError(null);
    setSimpleAnalysis(null);

    const formData = new FormData();
    formData.append('addresses_text', addressesText);
    formData.append('route_value', parseFloat(simpleRouteValue));

    try {
      const res = await fetchWithAuth('/api/routes/analyze-addresses', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Falha ao analisar');
      }

      const data = await res.json();
      setSimpleAnalysis(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setSimpleLoading(false);
    }
  };

  const handleClearSimple = () => {
    setAddressesText('');
    setSimpleRouteValue('');
    setSimpleAnalysis(null);
    setMapUrl(null);
    setError(null);
  };

  const handleGenerateMap = async () => {
    if (!addressesText.trim()) {
      setError('Cole os endereços primeiro');
      return;
    }

    setMapLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('addresses_text', addressesText);

    try {
      const res = await fetchWithAuth('/api/routes/generate-map', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Falha ao gerar mapa');
      }

      const data = await res.json();
      setMapUrl(data.map_url);
    } catch (err) {
      setError(err.message);
    } finally {
      setMapLoading(false);
    }
  };

  // ====== ABA 2: IMPORTAR ROMANEIO =====

  const handleFileChange = (e) => {
    if (e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleImport = async () => {
    if (!file && !importAddressesText.trim()) {
      setError('Selecione arquivo ou cole endereços para importar');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    if (file) formData.append('file', file);
    if (importAddressesText.trim()) formData.append('manual_addresses', importAddressesText.trim());

    try {
      const res = await fetchWithAuth('/api/romaneio/import', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Falha ao importar romaneio');
      }

      const data = await res.json();
      
      // Atualizar estados imediatamente
      setHasRomaneio(true);
      setViewMode('import');
      if (data.session_id) setSessionId(data.session_id);
      
      // Mostrar feedback imediato com dados do response
      setImportAnalysis({
        total_romaneios: data.imported_romaneios || 1,
        total_packages: data.session_total_packages || data.total_addresses,
        romaneios: [{
          id: data.romaneio_id,
          filename: file.name,
          uploaded_at: new Date().toISOString(),
          package_count: data.total_addresses
        }]
      });
      
      // Limpar arquivo
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      
      // Atualizar valor inicial se ainda não definido
      if (!importRouteValue && data.route_value) {
        setImportRouteValue(data.route_value.toString());
      }
      // sinaliza que devemos rodar otimização automaticamente (se possível)
      setAutoOptimizeAfterImport(true);

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleImportAdditional = async () => {
    if (!file && !importAddressesText.trim()) {
      setError('Selecione arquivo ou cole endereços para importar');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    if (file) formData.append('file', file);
    if (importAddressesText.trim()) formData.append('manual_addresses', importAddressesText.trim());

    try {
      const res = await fetchWithAuth('/api/romaneio/import', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Falha ao importar adicional');
      }

      const data = await res.json();
      if (data.session_id) setSessionId(data.session_id);
      
      // Atualizar lista de romaneios localmente
      setImportAnalysis(prev => ({
        ...prev,
        total_romaneios: data.imported_romaneios || (prev?.total_romaneios || 0) + 1,
        total_packages: data.session_total_packages || (prev?.total_packages || 0) + data.total_addresses,
        romaneios: [
          ...(prev?.romaneios || []),
          {
            id: data.romaneio_id,
            filename: file.name,
            uploaded_at: new Date().toISOString(),
            package_count: data.total_addresses
          }
        ]
      }));
      
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSessionReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchWithAuth('/api/session/report');
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Falha ao gerar relatório');
      }
      const data = await res.json();
      setImportAnalysis(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleOptimize = async () => {
    if (!sessionId) {
      setError('Nenhuma sessão ativa. Importe um romaneio primeiro.');
      return;
    }

    if (!importRouteValue) {
      setError('Informe o valor total da sessão antes de otimizar');
      return;
    }

    setLoading(true);
    setError(null);
    setRoutes([]);

    try {
      // 1. Salvar valor da rota na sessão
      await fetchWithAuth('/api/session/route-value', {
        method: 'POST',
        body: JSON.stringify({
          value: Number(importRouteValue),
          session_id: sessionId
        })
      });

      // 2. Chamar endpoint CORRETO de divisão de rotas (com base location)
      const res = await fetchWithAuth('/api/routes/divide-and-assign', {
        method: 'POST',
        body: JSON.stringify({ 
          session_id: sessionId,
          num_deliverers: Number(numDeliverers),
          deliverer_ids: [],
          base_lat: baseLat,
          base_lng: baseLng
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Falha ao otimizar rotas');
      }

      const data = await res.json();
      
      // Mapear retorno do backend para formato esperado pelo frontend
      const totalPackages = (data.routes || []).reduce((sum, rt) => sum + (rt.total_packages || rt.total_points || 0), 0) || 1;
      const mappedRoutes = (data.routes || []).map(r => ({
        route_id: r.route_id,
        total_stops: r.total_stops ?? r.total_points,
        total_packages: r.total_packages ?? r.total_points,
        percentage_load: Math.round((r.total_packages || r.total_points || 0) / totalPackages * 100),
        color: r.color,
        map_url: r.map_url || null,  // Usar map_url do backend
        points_sample: r.points_sample || []
      }));
      
      setRoutes(mappedRoutes);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAssign = async (routeId, delivererId) => {
    // Se vazio, apenas remove a atribuição localmente
    if (!delivererId) {
      setAssignments(prev => {
        const next = { ...prev };
        delete next[routeId];
        return next;
      });
      return;
    }

    // Atualiza UI imediatamente (optimistic update) - mantém como string para consistência com select
    const delivererIdStr = String(delivererId);
    setAssignments(prev => ({ ...prev, [routeId]: delivererIdStr }));

    try {
      console.log(`🚀 Atribuindo rota ${routeId} ao entregador ${delivererIdStr}`);
      const res = await fetchWithAuth('/api/routes/assign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ route_id: routeId, deliverer_id: Number(delivererIdStr) })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: 'Erro desconhecido' }));
        console.error('❌ Erro na atribuição:', errData);
        // NÃO reverter - mantém a seleção local para o usuário continuar
        // A atribuição será enviada novamente quando clicar em "Confirmar e Enviar"
        console.warn('⚠️ Atribuição local mantida, será sincronizada ao enviar rotas');
        return; // Não lança erro - permite continuar
      }

      const result = await res.json();
      console.log('✅ Atribuição confirmada:', result);
    } catch (err) {
      // Em caso de erro de rede, mantém a atribuição local
      console.error('❌ Erro handleAssign (rede?):', err);
      console.warn('⚠️ Atribuição salva localmente, será sincronizada ao enviar');
      // Não reverte e não mostra erro - permite o usuário continuar
    }
  };

  const handleCancelSession = async () => {
    // Se já existirem rotas geradas e/ou atribuídas, NÃO limpar a sessão completamente
    // — ao invés disso apenas libera a aba Análise para permitir novo romaneio.
    const hasRoutes = routes && routes.length > 0;
    const hasAssignments = assignments && Object.keys(assignments).length > 0;

    if (hasRoutes || hasAssignments) {
      if (!confirm('🟡 Existem rotas/atribuições geradas. Deseja LIBERAR a aba Análise (recomendado) em vez de apagar tudo?\n\nOK = Liberar Análise • Cancel = Apagar tudo')) return;

      setLoading(true);
      try {
        // Chama endpoint que apenas desassocia a sessão do foco (mantém ativa para mapa/separação)
        const res = await fetchWithAuth(`/api/session/${sessionId}/release`, { method: 'POST' });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || 'Falha ao liberar sessão');
        }

        // Atualiza estado local: libera a tela de Análise sem apagar a sessão
        setHasRomaneio(false);
        setSessionId(null);
        setImportAnalysis(null);
        setRoutes([]);
        setAssignments({});
        setImportRouteValue('');
        setFile(null);
        setViewMode('simple');
      } catch (err) {
        setError('Erro ao liberar: ' + err.message);
      } finally {
        setLoading(false);
      }

      return;
    }

    // Caso não haja rotas/atribuições, manter comportamento antigo: limpar import
    if (!confirm('🛑 Tem certeza? Isso apagará todos os romaneios e rotas atuais.')) return;

    setLoading(true);
    try {
      await fetchWithAuth('/api/session/cancel-import', { method: 'POST' });
      // Reset local state
      setHasRomaneio(false);
      setSessionId(null);
      setImportAnalysis(null);
      setRoutes([]);
      setAssignments({});
      setImportRouteValue('');
      setFile(null);
      setViewMode('simple'); // Volta por padrão
    } catch (err) {
      setError('Erro ao cancelar: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStartRoutes = async () => {
    const allAssigned = routes.length > 0 && routes.every(r => assignments[r.route_id]);
    if (!allAssigned) {
      setError('Selecione um entregador para cada rota antes de iniciar.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // Converte assignments para formato {route_id: deliverer_telegram_id (number)}
      const assignmentsPayload = {};
      for (const [routeId, delivererId] of Object.entries(assignments)) {
        assignmentsPayload[routeId] = Number(delivererId);
      }
      
      console.log('📤 Enviando atribuições:', { session_id: sessionId, assignments: assignmentsPayload });
      
      const res = await fetchWithAuth(`${import.meta.env.VITE_API_URL}/routes/assign-multiple`, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          assignments: assignmentsPayload
        })
      });
      
      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: 'Erro desconhecido' }));
        throw new Error(errData.detail || 'Falha ao enviar rotas');
      }
      
      const result = await res.json();
      console.log('✅ Rotas enviadas com sucesso:', result);
      
      // Sucesso! Permite usuário escolher próximo passo
      alert('🚀 Rotas enviadas com sucesso! Entregadores foram notificados.');

      // Liberar automaticamente a aba Análise para permitir novo romaneio
      try {
        const rel = await fetchWithAuth(`/api/session/${sessionId}/release`, { method: 'POST' });
        if (rel.ok) {
          // Limpa interface de análise para permitir novo fluxo
          setHasRomaneio(false);
          setSessionId(null);
          setImportAnalysis(null);
          setRoutes([]);
          setAssignments({});
          setImportRouteValue('');
          setFile(null);
          setViewMode('simple');
          console.log('✅ Aba Análise liberada automaticamente após envio de rotas');
        } else {
          console.warn('⚠️ Falha ao liberar sessão automaticamente:', await rel.text().catch(() => ''));
        }
      } catch (e) {
        console.warn('⚠️ Erro ao chamar release after assign:', e);
      }
      // Não força redirecionamento - deixa usuário escolher entre mapa ou separação
    } catch (err) {
      console.error('❌ Erro ao enviar rotas:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Se uma importação acabou de ocorrer, dispara otimização automaticamente
  useEffect(() => {
    if (autoOptimizeAfterImport && sessionId) {
      // reset flag para evitar loops
      setAutoOptimizeAfterImport(false);
      // chama otimização (usa valor atual de numDeliverers/base)
      // Aguardamos um tick para garantir que o estado UI foi atualizado
      setTimeout(() => {
        handleOptimize().catch(e => console.error('Auto-optimize falhou', e));
      }, 200);
    }
  }, [autoOptimizeAfterImport, sessionId]);

  const allAssigned = routes.length > 0 && routes.every((r) => assignments[r.route_id]);

  return (
    <div className="space-y-6 animate-fade-in pb-20">
      {/* Header Premium */}
      <div className={`rounded-3xl p-6 shadow-lg text-white bg-gradient-to-r from-purple-600 to-blue-600 ${responsive.isDesktop ? 'mb-8' : 'mb-5'}`}>
        <h2 className={`font-bold flex items-center gap-2 mb-2 ${responsive.isDesktop ? 'text-3xl' : 'text-2xl'}`}>
          <Sparkles size={responsive.isDesktop ? 36 : 32} /> Análise de Rota com IA
        </h2>
        <p className={`${responsive.isDesktop ? 'text-base' : 'text-purple-100'} opacity-90`}>
          Cole endereços ou importe romaneio. A IA te diz se vale a pena.
        </p>
        
      </div>

      {/* Abas Principais */}
      <div className={`grid gap-3 ${responsive.isDesktop ? 'grid-cols-4' : 'grid-cols-2'}`}>
        <button
          onClick={() => setViewMode('simple')}
          className={`${responsive.isDesktop ? 'py-4 px-6' : 'py-3 px-4'} rounded-xl font-bold transition-all flex items-center justify-center ${
            viewMode === 'simple'
              ? 'bg-purple-600 text-white shadow-lg scale-105'
              : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
          }`}
        >
          <Sparkles size={responsive.isDesktop ? 20 : 18} className="mr-2" />
          {responsive.isDesktop ? 'Análise Manual' : 'Colar'}
        </button>
        <button
          onClick={() => setViewMode('import')}
          className={`${responsive.isDesktop ? 'py-4 px-6' : 'py-3 px-4'} rounded-xl font-bold transition-all flex items-center justify-center ${
            viewMode === 'import'
              ? 'bg-blue-600 text-white shadow-lg scale-105'
              : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
          }`}
        >
          <FileUp size={responsive.isDesktop ? 20 : 18} className="mr-2" />
          {responsive.isDesktop ? 'Importar Arquivo' : 'Importar'}
        </button>
      </div>

      {/* ERRO GLOBAL */}
      {error && (
        <div className={`bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 flex gap-3 ${responsive.isDesktop ? 'text-base' : 'text-sm'}`}>
          <AlertCircle className="text-red-600 flex-shrink-0" size={responsive.isDesktop ? 24 : 20} />
          <div className="flex-1">
            <p className="font-bold text-red-800 dark:text-red-300">Erro detectado</p>
            <p className="text-red-700 dark:text-red-400 mt-1">{error}</p>
          </div>

          {/* Pasted Addresses (optional for import) */}
          <div className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 ${responsive.isDesktop ? 'p-4' : 'p-3'}`}>
            <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">📋 Cole lista de endereços para importar (opcional)</label>
            <textarea
              value={importAddressesText}
              onChange={(e) => setImportAddressesText(e.target.value)}
              placeholder={`Bairro\tEndereço completo\nIPANEMA\tEpitácio Pessoa, 2030 202\nLEBLON\tAvenida General San Martin 900\n...`}
              className={`w-full border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none resize-none ${responsive.isDesktop ? 'h-28 p-3' : 'h-20 p-2'}`}
            />
            <p className="text-xs text-gray-400 mt-2">Aceita linhas no formato "Bairro[TAB]Endereço" ou apenas endereço por linha. Isso será importado como romaneio e criará uma sessão.</p>
          </div>
          
          <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">✕</button>
        </div>
      )}

      {/* ===== ABA 1: COLAR ENDEREÇOS ===== */}
      {viewMode === 'simple' && (
        <div className="space-y-4">
          {/* Input Area */}
          <div className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 ${responsive.isDesktop ? 'p-6' : 'p-4'}`}>
            <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2 flex justify-between">
              <span>📝 Cola os Endereços (um por linha)</span>
              <span className="text-xs font-normal text-gray-400">{addressesText.trim() ? addressesText.trim().split('\n').length : 0} linhas</span>
            </label>
            <textarea
              value={addressesText}
              onChange={(e) => setAddressesText(e.target.value)}
              placeholder={`Rua Principado de Mônaco, 37, Apt 501
Rua Mena Barreto, 161, Loja BMRIO
Rua General Polidoro, 322, 301
...`}
              className={`w-full border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none resize-none ${responsive.isDesktop ? 'h-48 p-4' : 'h-40 p-3'}`}
            />
          </div>

          {/* Value Input e Ações */}
          <div className={`grid gap-4 ${responsive.isDesktop ? 'grid-cols-2' : 'grid-cols-1'}`}>
            <div className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 ${responsive.isDesktop ? 'p-6' : 'p-4'}`}>
              <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">
                💰 Valor Total da Rota (R$)
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 font-bold">R$</span>
                <input
                  type="number"
                  value={simpleRouteValue}
                  onChange={(e) => setSimpleRouteValue(e.target.value)}
                  placeholder="150.00"
                  className="w-full pl-10 p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-bold text-lg outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={handleAnalyzeAddresses}
                disabled={simpleLoading || !addressesText.trim() || !simpleRouteValue}
                className="col-span-1 btn-primary flex flex-col items-center justify-center gap-1 !py-4"
              >
                {simpleLoading ? (
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
                ) : (
                  <>
                    <Sparkles size={24} />
                    <span>Analisar</span>
                  </>
                )}
              </button>
              
              <button
                onClick={handleClearSimple}
                className="col-span-1 btn-secondary flex flex-col items-center justify-center gap-1 !py-4"
              >
                <FileUp size={24} className="rotate-180" /> 
                <span>Limpar</span>
              </button>
            </div>
          </div>
          {/* Resultado */}
          {simpleAnalysis && (
            <div className="space-y-4">
              {/* Header com destaque */}
              <div className={`bg-gradient-to-r rounded-xl p-6 text-white ${
                simpleAnalysis.header?.['📊 SCORE'] >= 7
                  ? 'from-green-500 to-emerald-600'
                  : simpleAnalysis.header?.['📊 SCORE'] >= 5
                  ? 'from-yellow-500 to-orange-600'
                  : 'from-red-500 to-pink-600'
              }`}>
                <div className={`grid gap-4 ${responsive.isDesktop ? 'grid-cols-4' : 'grid-cols-2'}`}>
                  <div>
                    <p className="text-sm opacity-80">Valor</p>
                    <p className="text-2xl font-bold">{simpleAnalysis.header?.['💰 VALOR']}</p>
                  </div>
                  <div>
                    <p className="text-sm opacity-80">Tipo</p>
                    <p className={`font-bold ${String(simpleAnalysis.header?.['⭐ TIPO'] || '').length > 10 ? 'text-xl' : 'text-2xl'}`}>{simpleAnalysis.header?.['⭐ TIPO']}</p>
                  </div>
                  <div>
                    <p className="text-sm opacity-80">Score</p>
                    <p className="text-3xl font-bold">{simpleAnalysis.header?.['📊 SCORE']}</p>
                  </div>
                  <div>
                    <p className="text-sm opacity-80">Ganho/hora</p>
                    <p className="text-2xl font-bold">{simpleAnalysis.financial?.hourly}</p>
                  </div>
                </div>
                <p className="mt-4 text-sm font-semibold">{simpleAnalysis.header?.['✅ RECOMENDAÇÃO']}</p>
              </div>

              {/* Top Drops - Estilo Melhorado */}
              {simpleAnalysis.top_drops && simpleAnalysis.top_drops.length > 0 && (
                <div className="bg-gradient-to-br from-orange-50 to-red-50 dark:from-orange-900/20 dark:to-red-900/20 rounded-xl p-5 border-2 border-orange-200 dark:border-orange-700">
                  <h4 className="font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2 text-lg">
                    <TrendingUp size={22} className="text-orange-600" />
                    🔥 Top Drops (Ruas com Maior Concentração)
                  </h4>
                  <div className="space-y-3">
                    {simpleAnalysis.top_drops.map((drop, i) => (
                      <div 
                        key={i} 
                        className={`flex items-center justify-between p-4 rounded-lg border-2 transition-all transform hover:scale-102 ${
                          i === 0 
                            ? 'bg-gradient-to-r from-yellow-100 to-orange-100 dark:from-yellow-900/30 dark:to-orange-900/30 border-yellow-300 dark:border-yellow-600 shadow-md' 
                            : i === 1
                            ? 'bg-gradient-to-r from-blue-100 to-purple-100 dark:from-blue-900/30 dark:to-purple-900/30 border-blue-300 dark:border-blue-600'
                            : 'bg-gradient-to-r from-gray-100 to-slate-100 dark:from-gray-700 dark:to-slate-700 border-gray-300 dark:border-gray-600'
                        }`}
                      >
                        <div className="flex items-center gap-4">
                          <span className="text-4xl">{drop.emoji}</span>
                          <div>
                            <p className="font-bold text-gray-900 dark:text-white text-lg">{drop.street}</p>
                            <p className="text-xs text-gray-600 dark:text-gray-400 font-semibold">{drop.count} endereços</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold text-orange-600 dark:text-orange-400">{drop.percentage}</p>
                          <p className="text-xs text-gray-500">concentração</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Perfil da Rota - Expandido */}
              <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
                <h4 className="font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  📊 Perfil Detalhado da Rota
                </h4>
                <div className={`grid gap-3 ${responsive.isDesktop ? 'grid-cols-6' : 'grid-cols-3'}`}>
                  <div className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/30 dark:to-purple-800/30 p-3 rounded-xl border border-purple-200 dark:border-purple-700">
                    <p className="text-xs text-purple-600 dark:text-purple-400 font-semibold">Tipo</p>
                    <p className="font-bold text-purple-900 dark:text-purple-200 text-sm">{simpleAnalysis.profile?.type || '---'}</p>
                  </div>
                  <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30 p-3 rounded-xl border border-blue-200 dark:border-blue-700">
                    <p className="text-xs text-blue-600 dark:text-blue-400 font-semibold">Pacotes</p>
                    <p className="font-bold text-blue-900 dark:text-blue-200 text-lg">{simpleAnalysis.profile?.total_packages || 0}</p>
                  </div>
                  <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/30 dark:to-green-800/30 p-3 rounded-xl border border-green-200 dark:border-green-700">
                    <p className="text-xs text-green-600 dark:text-green-400 font-semibold">Paradas</p>
                    <p className="font-bold text-green-900 dark:text-green-200 text-lg">{simpleAnalysis.profile?.unique_stops || 0}</p>
                  </div>
                  <div className="bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-900/30 dark:to-orange-800/30 p-3 rounded-xl border border-orange-200 dark:border-orange-700">
                    <p className="text-xs text-orange-600 dark:text-orange-400 font-semibold">Comercial</p>
                    <p className="font-bold text-orange-900 dark:text-orange-200 text-sm">{simpleAnalysis.profile?.commercial_pct || '0%'}</p>
                  </div>
                  <div className="bg-gradient-to-br from-cyan-50 to-cyan-100 dark:from-cyan-900/30 dark:to-cyan-800/30 p-3 rounded-xl border border-cyan-200 dark:border-cyan-700">
                    <p className="text-xs text-cyan-600 dark:text-cyan-400 font-semibold">Tempo Est.</p>
                    <p className="font-bold text-cyan-900 dark:text-cyan-200 text-sm">{simpleAnalysis.metrics?.estimated_time || '---'}</p>
                  </div>
                  <div className="bg-gradient-to-br from-pink-50 to-pink-100 dark:from-pink-900/30 dark:to-pink-800/30 p-3 rounded-xl border border-pink-200 dark:border-pink-700">
                    <p className="text-xs text-pink-600 dark:text-pink-400 font-semibold">Aptos</p>
                    <p className="font-bold text-pink-900 dark:text-pink-200 text-lg">{simpleAnalysis.metrics?.vertical_count || 0}</p>
                  </div>
                </div>
              </div>

              {/* Análise Qualitativa - Prós e Contras lado a lado */}
              <div className={`grid gap-4 ${responsive.isDesktop ? 'grid-cols-2' : 'grid-cols-1'}`}>
                {/* PRÓS */}
                <div className="bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl p-5 border-2 border-green-200 dark:border-green-700">
                  <h4 className="font-bold text-green-800 dark:text-green-300 mb-4 flex items-center gap-2 text-lg">
                    ✅ Pontos Positivos
                  </h4>
                  <ul className="space-y-3">
                    {(simpleAnalysis.analysis?.pros || []).map((pro, i) => (
                      <li key={i} className="flex items-start gap-3 text-sm text-green-800 dark:text-green-300 bg-white/50 dark:bg-green-900/30 p-3 rounded-lg border border-green-100 dark:border-green-800">
                        <span className="text-green-500 font-bold text-lg">✓</span>
                        <span className="flex-1">{pro}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* CONTRAS */}
                <div className="bg-gradient-to-br from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 rounded-xl p-5 border-2 border-red-200 dark:border-red-700">
                  <h4 className="font-bold text-red-800 dark:text-red-300 mb-4 flex items-center gap-2 text-lg">
                    ⚠️ Pontos de Atenção
                  </h4>
                  <ul className="space-y-3">
                    {(simpleAnalysis.analysis?.cons || []).map((con, i) => (
                      <li key={i} className="flex items-start gap-3 text-sm text-red-800 dark:text-red-300 bg-white/50 dark:bg-red-900/30 p-3 rounded-lg border border-red-100 dark:border-red-800">
                        <span className="text-red-500 font-bold text-lg">!</span>
                        <span className="flex-1">{con}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Comentário IA - Com formatação Markdown */}
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/30 dark:to-indigo-900/30 border-2 border-blue-200 dark:border-blue-700 rounded-xl p-5 shadow-sm">
                <h4 className="font-bold text-blue-900 dark:text-blue-300 mb-3 flex items-center gap-2 text-lg">
                  🤖 Análise Inteligente
                </h4>
                <div className="text-sm text-blue-900 dark:text-blue-200 leading-relaxed space-y-3">
                  {simpleAnalysis.ai_comment?.split('\n\n').map((paragraph, i) => (
                    <p key={i} className="text-blue-800 dark:text-blue-300" 
                       dangerouslySetInnerHTML={{ 
                         __html: paragraph
                           .replace(/\*\*(.*?)\*\*/g, '<strong class="text-blue-900 dark:text-blue-100">$1</strong>')
                           .replace(/\n/g, '<br/>')
                       }} 
                    />
                  ))}
                </div>
              </div>

              {/* MAPA - Lazy Load */}
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                <div className="bg-gradient-to-r from-purple-500 to-pink-500 p-4 text-white font-bold flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Map size={20} />
                    🗺️ Minimapa da Rota
                  </div>
                  {mapLoading && <span className="text-sm">⏳ Gerando...</span>}
                </div>
                
                {mapUrl ? (
                  <iframe
                    src={mapUrl}
                    className="w-full h-96 border-0"
                    title="Mapa da Rota"
                    allowFullScreen=""
                  />
                ) : (
                  <div className="p-6 text-center">
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                      ⚠️ Geocodificação lenta (3-5 seg por endereço)
                    </p>
                    <button
                      onClick={handleGenerateMap}
                      disabled={mapLoading}
                      className="bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white font-bold py-2 px-6 rounded-lg transition-colors"
                    >
                      {mapLoading ? '⏳ Gerando Mapa...' : '🗺️ Gerar Mapa'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===== ABA 2: IMPORTAR ROMANEIO ===== */}
      {viewMode === 'import' && (
        <div className="space-y-4">
          {/* Upload File */}
          <div className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 ${responsive.isDesktop ? 'p-6' : 'p-4'}`}>
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl p-8 text-center cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".xlsx,.xls"
                className="hidden"
              />
              <FileUp size={48} className="mx-auto text-gray-400 mb-4" />
              {file ? (
                <div>
                  <p className="font-bold text-green-600 text-lg">{file.name}</p>
                  <p className="text-sm text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
              ) : (
                <div>
                  <p className="font-bold text-gray-700 dark:text-gray-300 text-lg">Clique ou arraste arquivo Excel</p>
                  <p className="text-sm text-gray-500">Suporta .xlsx ou .xls (Shopee)</p>
                </div>
              )}
            </div>
          </div>

          {/* Botões Import */}
          {!hasRomaneio ? (
            <button
              onClick={handleImport}
                disabled={loading || (!file && !importAddressesText.trim())}
              className={`w-full btn-primary flex items-center justify-center gap-2 ${responsive.isDesktop ? 'py-4 text-lg' : 'py-3'} ${!file ? '!bg-gray-300 dark:!bg-gray-700 !shadow-none cursor-not-allowed' : ''}`}
            >
              {loading ? (
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
              ) : (
                <>
                  <FileUp size={24} />
                  <span>Importar Romaneio</span>
                </>
              )}
            </button>
          ) : (
            <div className="space-y-4">
              {/* Value Input (antes de otimizar) */}
              <div className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 ${responsive.isDesktop ? 'p-6' : 'p-4'}`}>
                <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">
                  💰 Valor Inicial da Sessão (R$)
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 font-bold">R$</span>
                  <input
                    type="number"
                    value={importRouteValue}
                    onChange={(e) => setImportRouteValue(e.target.value)}
                    placeholder="500.00"
                    className="input-premium !pl-10"
                  />
                </div>
              </div>

              {/* Seção: Romaneios Importados */}
              <div className={`bg-gradient-to-br from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20 border-2 border-blue-200 dark:border-blue-800 rounded-xl p-4`}>
                <h4 className="font-bold text-blue-900 dark:text-blue-300 mb-3 flex items-center gap-2">
                  📂 Romaneios Importados ({sessionId && importAnalysis?.total_romaneios ? importAnalysis.total_romaneios : '0'})
                </h4>
                
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {importAnalysis?.romaneios && importAnalysis.romaneios.length > 0 ? (
                    importAnalysis.romaneios.map((rom, idx) => (
                      <div key={rom.id} className="bg-white dark:bg-gray-800 p-3 rounded-lg flex items-start justify-between border border-blue-200 dark:border-blue-700 hover:shadow-md transition-shadow">
                        <div className="flex-1">
                          <p className="font-bold text-gray-900 dark:text-white text-sm">{idx + 1}. {rom.filename || 'Sem nome'}</p>
                          <p className="text-xs text-gray-600 dark:text-gray-400">
                            {rom.package_count} pacotes • {new Date(rom.uploaded_at).toLocaleTimeString()}
                          </p>
                        </div>
                        <button
                          onClick={() => {
                            if (confirm(`❌ Remover "${rom.filename}"?`)) {
                              fetchWithAuth(`/api/romaneio/romaneio/${sessionId}/${rom.id}`, { method: 'DELETE' })
                                .then(() => handleSessionReport())
                                .catch(e => setError(`Erro ao remover: ${e.message}`));
                            }
                          }}
                          className="text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/30 p-1 rounded ml-2"
                          title="Remover romaneio"
                        >
                          ✕
                        </button>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-gray-500 italic">Nenhum romaneio listado</p>
                  )}
                </div>
              </div>

              {/* Botões: + Add / Relatório / Cancelar */}
              <div className={`grid gap-3 ${responsive.isDesktop ? 'grid-cols-2' : 'grid-cols-1'}`}>
                <button
                  onClick={handleImportAdditional}
                    disabled={loading || (!file && !importAddressesText.trim())}
                  className="btn-secondary flex items-center justify-center gap-2 !border-blue-300 dark:!border-blue-700 !text-blue-700 dark:!text-blue-300 hover:!bg-blue-50 dark:hover:!bg-blue-900/30"
                >
                  <FileUp size={20} />
                  {loading ? 'Importando...' : '+ Add Outro Romaneio'}
                </button>
                <button
                  onClick={handleSessionReport}
                  disabled={loading}
                  className="btn-primary flex items-center justify-center gap-2"
                >
                  <Sparkles size={20} />
                  {loading ? 'Carregando...' : '✨ Gerar Relatório Completo'}
                </button>
              </div>
              
              {/* Botão Cancelar separado */}
              <button
                onClick={handleCancelSession}
                disabled={loading}
                className="w-full btn-danger-outline flex items-center justify-center gap-2"
              >
                ● Cancelar Sessão (Limpar tudo)
              </button>
            </div>
          )}

          {/* Resultado da Importação */}
          {importAnalysis && (
            <div className="space-y-4 animate-fade-in">
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-4 flex items-center gap-3">
                <div className="bg-green-100 p-2 rounded-full text-green-600">
                  <Sparkles size={24} />
                </div>
                <div>
                  <p className="font-bold text-green-900 dark:text-green-300">Sessão Gerada!</p>
                  <p className="text-sm text-green-800 dark:text-green-400">Próximo: Otimizar e distribuir entregadores</p>
                </div>
              </div>

              {importAnalysis.formatted && (
                <div className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 space-y-4 ${responsive.isDesktop ? 'p-6' : 'p-4'}`}>
                  <h4 className="font-bold text-gray-900 dark:text-white flex items-center gap-2">
                    <TrendingUp size={20} className="text-blue-600" />
                    Análise da Sessão
                  </h4>

                  <div className={`grid gap-3 ${responsive.isDesktop ? 'grid-cols-4' : 'grid-cols-2'}`}>
                    <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg text-center">
                      <p className="text-xs text-gray-500 uppercase">Valor</p>
                      <p className="font-bold text-gray-900 dark:text-white text-lg">{importAnalysis.formatted.header?.value}</p>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg text-center">
                      <p className="text-xs text-gray-500 uppercase">Tipo</p>
                      <p className="font-bold text-gray-900 dark:text-white text-lg">{importAnalysis.formatted.header?.type}</p>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg text-center">
                      <p className="text-xs text-gray-500 uppercase">Score</p>
                      <p className="font-bold text-gray-900 dark:text-white text-2xl text-blue-600">{importAnalysis.formatted.header?.score}</p>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg text-center">
                      <p className="text-xs text-gray-500 uppercase">Status</p>
                      <p className="font-bold text-gray-900 dark:text-white text-sm">{importAnalysis.formatted.header?.recommendation}</p>
                    </div>
                  </div>

                  <div className={`grid gap-3 ${responsive.isDesktop ? 'grid-cols-4' : 'grid-cols-2'}`}>
                    <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
                      <p className="text-xs text-blue-600 font-bold">Ganho/Hora</p>
                      <p className="font-bold text-gray-900 dark:text-white">{importAnalysis.formatted.earnings?.hourly}</p>
                    </div>
                    <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
                      <p className="text-xs text-blue-600 font-bold">Ganho/Pct</p>
                      <p className="font-bold text-gray-900 dark:text-white">{importAnalysis.formatted.earnings?.package}</p>
                    </div>
                    <div className={`bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg ${responsive.isDesktop ? 'col-span-2' : 'col-span-2'}`}>
                      <p className="text-xs text-blue-600 font-bold">Tempo Total Est.</p>
                      <p className="font-bold text-gray-900 dark:text-white">{importAnalysis.formatted.earnings?.time_estimate}</p>
                    </div>
                  </div>

                  {importAnalysis.formatted.top_drops?.length > 0 && (
                    <div>
                      <p className="text-sm font-bold text-gray-900 dark:text-white mb-2">🔥 Top Drops</p>
                      <div className="grid gap-2 grid-cols-1 md:grid-cols-2">
                        {importAnalysis.formatted.top_drops.map((drop, i) => (
                          <div key={i} className="flex items-center justify-between bg-gray-50 dark:bg-gray-700 rounded-lg p-3 border border-gray-100 dark:border-gray-600">
                            <div className="flex items-center gap-3">
                              <span className="text-2xl">{drop.emoji}</span>
                              <span className="font-semibold text-gray-900 dark:text-white">{drop.street}</span>
                            </div>
                            <span className="text-xs font-bold bg-white dark:bg-gray-600 px-2 py-1 rounded text-gray-600 dark:text-gray-300">{drop.count} entregas</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {importAnalysis.minimap_url && (
                <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                  <div className="bg-gradient-to-r from-purple-500 to-pink-500 p-4 text-white font-bold flex items-center gap-2">
                    <Map size={20} /> Minimapa da Sessão
                  </div>
                  <iframe
                    src={importAnalysis.minimap_url}
                    className="w-full h-96 border-0"
                    title="Minimapa da Sessão"
                    allowFullScreen=""
                  />
                </div>
              )}
            </div>
          )}

          {/* Configuração da Base + Otimize Section */}
          {hasRomaneio && (
            <div className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 ${responsive.isDesktop ? 'p-6' : 'p-4'} space-y-4`}>
              
              {/* Localização da Base */}
              <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4 border border-orange-200 dark:border-orange-800">
                <label className="block text-sm font-bold text-orange-700 dark:text-orange-300 mb-2">
                  🏠 Localização da Base (ponto de partida das rotas)
                </label>
                <div className="grid gap-3 md:grid-cols-3">
                  <div>
                    <input
                      type="text"
                      placeholder="Endereço da base (opcional)"
                      value={baseAddress}
                      onChange={(e) => setBaseAddress(e.target.value)}
                      className="input-premium text-sm"
                    />
                  </div>
                  <div className="flex gap-2">
                    <div className="flex-1">
                      <label className="text-xs text-gray-500">Latitude</label>
                      <input
                        type="number"
                        step="0.0001"
                        value={baseLat}
                        onChange={(e) => setBaseLat(parseFloat(e.target.value))}
                        className="input-premium text-sm"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="text-xs text-gray-500">Longitude</label>
                      <input
                        type="number"
                        step="0.0001"
                        value={baseLng}
                        onChange={(e) => setBaseLng(parseFloat(e.target.value))}
                        className="input-premium text-sm"
                      />
                    </div>
                  </div>
                  <button
                    onClick={() => setShowBaseMap(!showBaseMap)}
                    className="btn-secondary text-sm flex items-center justify-center gap-1"
                  >
                    <MapPin size={16} /> {showBaseMap ? 'Ocultar Mapa' : 'Selecionar no Mapa'}
                  </button>
                </div>
                
                {showBaseMap && (
                  <div className="mt-3">
                    <BaseLocationSelector
                      lat={baseLat}
                      lng={baseLng}
                      onLocationChange={(lat, lng) => {
                        setBaseLat(lat);
                        setBaseLng(lng);
                      }}
                      height="256px"
                    />
                  </div>
                )}
              </div>
              
              {/* Quantidade de Entregadores */}
              <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">
                📍 Quantos Entregadores para dividir?
              </label>
              <div className={`flex gap-3 ${responsive.isDesktop ? 'flex-row items-center' : 'flex-col'}`}>
                <div className="relative flex-1">
                   <Users className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20}/>
                   <input
                    type="number"
                    min="1"
                    max="10"
                    value={numDeliverers}
                    onChange={(e) => setNumDeliverers(e.target.value)}
                    className="input-premium !pl-10"
                  />
                </div>
                <button
                  onClick={handleOptimize}
                  disabled={loading || !hasRomaneio}
                  className={`btn-success flex items-center justify-center gap-2 ${responsive.isDesktop ? '' : 'w-full'}`}
                >
                  {loading ? 'Processando...' : '🚀 Otimizar Rotas'}
                </button>
              </div>
            </div>
          )}

          {/* Routes & Assignment */}
          {routes.length > 0 && (
            <div className="space-y-4 animate-fade-in-up">
              <h3 className="font-bold text-xl text-gray-900 dark:text-white flex items-center gap-2">
                <Users size={24} className="text-purple-600" />
                Atribuição de Entregadores
              </h3>
              
              <div className={`grid gap-4 ${responsive.isDesktop ? 'grid-cols-2' : 'grid-cols-1'}`}>
                {routes.map((route, idx) => (
                  <div 
                    key={route.route_id} 
                    className="bg-white dark:bg-gray-800 rounded-xl p-5 border-2 border-gray-100 dark:border-gray-700 hover:border-purple-200 dark:hover:border-purple-900 transition-all shadow-sm"
                    style={{ borderLeftColor: route.color, borderLeftWidth: '4px' }}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex items-center gap-2">
                        <div 
                          className="w-4 h-4 rounded-full flex-shrink-0" 
                          style={{ backgroundColor: route.color }}
                        />
                        <div>
                          <p className="font-bold text-lg text-gray-900 dark:text-white">Rota {idx + 1}</p>
                          <p className="text-sm text-gray-500">{route.total_stops ?? '-'} paradas • {route.total_packages ?? '-'} pacotes</p>
                        </div>
                      </div>
                      <div className="bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 px-3 py-1 rounded-full text-xs font-bold">
                        {route.percentage_load ? `${route.percentage_load}% volume` : 'Auto'}
                      </div>
                    </div>

                    {/* MAPA VISUAL DA ROTA - mesmo que o entregador recebe */}
                    {route.points_sample && route.points_sample.length > 0 && (
                      <div className="mb-4">
                        <RoutePreviewMap
                          points={route.points_sample}
                          baseLat={baseLat}
                          baseLng={baseLng}
                          color={route.color}
                          routeIndex={idx}
                          height="200px"
                          geometry={route.geometry || route.route_geometry || null}
                        />
                        <div className="bg-gray-50 dark:bg-gray-700 p-2 rounded-b-lg text-xs text-gray-600 dark:text-gray-300 flex justify-between items-center">
                          <span>📍 {route.total_stops} paradas partindo da base</span>
                          <span style={{color: route.color}} className="font-bold">● Rota {idx + 1}</span>
                        </div>
                      </div>
                    )}

                    {/* Botão Ver Mapa */}
                    <div className="mb-4">
                      <a
                        href={route.map_url || `https://www.google.com/maps/search/?api=1&query=${route.points_sample?.[0]?.lat || 0},${route.points_sample?.[0]?.lng || 0}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-2 text-sm font-bold text-green-600 dark:text-green-400 hover:underline bg-green-50 dark:bg-green-900/20 px-3 py-2 rounded-lg w-full justify-center transition-colors hover:bg-green-100"
                      >
                        <Map size={16} /> 🗺️ Ver Rota no Google Maps
                      </a>
                    </div>
                    
                    <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Entregador Responsável</label>
                    <select
                      value={String(assignments[route.route_id] || '')}
                      onChange={(e) => {
                        const value = e.target.value;
                        console.log('📋 Select onChange:', route.route_id, value);
                        handleAssign(route.route_id, value);
                      }}
                      className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white font-medium focus:ring-2 focus:ring-purple-500 outline-none cursor-pointer"
                    >
                      <option value="">-- Selecione --</option>
                      {deliverers.map(d => (
                        <option key={d.id} value={String(d.id)}>{d.name}</option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>

              <div className="space-y-3 pt-4">
                <button
                  onClick={handleStartRoutes}
                  disabled={!allAssigned || loading}
                  className={`w-full flex items-center justify-center gap-2 text-lg ${allAssigned ? 'btn-success' : 'btn-secondary !cursor-not-allowed !opacity-50'}`}
                >
                  {loading ? 'Enviando...' : (
                    <>
                      <Send size={24} />
                      Confirmar e Enviar Rotas
                    </>
                  )}
                </button>
                
                <button
                  onClick={() => {
                    alert('✅ Rotas enviadas! Agora vá para a aba MAPAS para visualizar ou inicie a Separação.');
                  }}
                  className="w-full btn-secondary flex items-center justify-center gap-2"
                >
                  <Map size={20} />
                  Ver Rotas no Mapa
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* BarcodeScanner Modal */}
      {showScanner && (
        <BarcodeScanner 
          onScan={(codes) => {
            if (codes && codes.length > 0) {
              // Adicionar códigos escaneados ao campo de endereços
              const newCodes = codes.join('\n');
              setAddressesText(prev => prev ? prev + '\n' + newCodes : newCodes);
            }
          }}
          onClose={() => setShowScanner(false)}
        />
      )}
    </div>
  );
}
