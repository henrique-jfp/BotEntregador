import React, { useState, useEffect } from 'react';
import { Users, UserPlus, Trash2, Shield, Truck, AlertCircle, CheckCircle, XCircle, ChevronDown, Phone, MapPin, Clock, ChevronRight, Edit2, Star, BarChart2, X } from 'lucide-react';
import { fetchSafe } from './api_client';

export default function TeamView() {
  const [team, setTeam] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showMemberModal, setShowMemberModal] = useState(null);
  const [newMember, setNewMember] = useState({ name: '', telegram_id: '', is_partner: false });
  const [pendingTransfers, setPendingTransfers] = useState([]);

  // Fetch Team
  const refreshTeam = () => {
    setLoading(true);
    fetchSafe('/admin/team')
      .then(res => {
        if (res.ok) setTeam(res.json);
        else alert(res.error || 'Erro ao buscar equipe');
        setLoading(false);
      });
  };

  useEffect(() => {
    refreshTeam();
  }, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!newMember.name || !newMember.telegram_id) return;

    const res = await fetchSafe('/admin/team', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...newMember,
        telegram_id: parseInt(newMember.telegram_id)
      })
    });
    if (res.ok) {
      setShowModal(false);
      setNewMember({ name: '', telegram_id: '', is_partner: false });
      refreshTeam();
    } else {
      alert(res.error || "Erro ao adicionar member");
    }
  };

  const handleRemove = async (id) => {
    if (!confirm('Tem certeza que deseja remover este entregador?')) return;
    
    await fetchSafe(`/admin/team/${id}`, { method: 'DELETE' });
    setShowMemberModal(null);
    refreshTeam();
  };

  // Função para abrir modal do membro
  const handleMemberClick = (member) => {
    setShowMemberModal(member);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header Premium */}
      <div className="card-premium p-6 flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2 text-gray-900 dark:text-white">
            <Users className="text-primary-500" /> Gestão de Equipe
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Gerencie seus entregadores e parceiros</p>
        </div>
        <button 
          onClick={() => setShowModal(true)}
          className="btn-primary flex items-center justify-center gap-2 !px-4"
        >
          <UserPlus size={20} />
        </button>
      </div>

      {/* Lista de Membros */}
      <div className="space-y-3">
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="skeleton h-20 rounded-xl" />
            ))}
          </div>
        ) : team.length === 0 ? (
          <div className="card-premium">
            <div className="empty-state">
              <div className="empty-state-icon">
                <Users className="w-10 h-10 text-gray-400" />
              </div>
              <h3 className="empty-state-title">Nenhum membro na equipe</h3>
              <p className="empty-state-description">
                Adicione entregadores para começar a distribuir rotas e gerenciar entregas.
              </p>
              <button 
                onClick={() => setShowModal(true)}
                className="btn-primary flex items-center gap-2"
              >
                <UserPlus size={18} />
                Adicionar Primeiro Entregador
              </button>
            </div>
          </div>
        ) : (
          team.map(member => (
            <div 
              key={member.id} 
              className="list-item-interactive"
              onClick={() => handleMemberClick(member)}
            >
              {/* Avatar */}
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-lg flex-shrink-0 ${
                member.is_partner 
                  ? 'bg-gradient-to-br from-purple-500 to-indigo-600 text-white shadow-lg shadow-purple-500/30' 
                  : 'bg-gradient-to-br from-primary-500 to-purple-600 text-white shadow-lg shadow-primary-500/30'
              }`}>
                {member.name.substring(0, 1).toUpperCase()}
              </div>
              
              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-bold text-gray-900 dark:text-white truncate">{member.name}</h3>
                  {member.is_partner && (
                    <span className="badge bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 border-purple-200 dark:border-purple-700 text-[10px] px-2">
                      <Star size={10} className="fill-current" /> SÓCIO
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                  <span className="flex items-center gap-1">
                    <Truck size={12} /> {member.deliveries || 0} entregas
                  </span>
                  <span className="font-mono">ID: {member.id}</span>
                </div>
              </div>
              
              <ChevronRight size={20} className="list-item-arrow flex-shrink-0" />
            </div>
          ))
        )}
      </div>

      {/* Modal de Detalhes do Membro */}
      {showMemberModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm animate-fade-in">
          <div className="bg-white dark:bg-gray-900 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
            {/* Header do Modal */}
            <div className={`p-6 text-white ${showMemberModal.is_partner ? 'bg-gradient-to-r from-purple-600 to-indigo-600' : 'bg-gradient-to-r from-primary-600 to-purple-600'}`}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center font-bold text-2xl">
                    {showMemberModal.name.substring(0, 1).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="text-xl font-bold">{showMemberModal.name}</h3>
                    <p className="text-white/80 text-sm flex items-center gap-2 mt-1">
                      {showMemberModal.is_partner ? (
                        <><Star size={14} className="fill-current" /> Sócio</>
                      ) : (
                        <><Truck size={14} /> Entregador</>
                      )}
                    </p>
                  </div>
                </div>
                <button 
                  onClick={() => setShowMemberModal(null)}
                  className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                >
                  <X size={20} />
                </button>
              </div>
            </div>
            
            {/* Conteúdo */}
            <div className="p-6 space-y-4">
              {/* Stats Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-xl">
                  <p className="text-xs text-gray-500 dark:text-gray-400 uppercase font-medium mb-1">Telegram ID</p>
                  <p className="font-mono font-bold text-gray-900 dark:text-white">{showMemberModal.id}</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-xl">
                  <p className="text-xs text-gray-500 dark:text-gray-400 uppercase font-medium mb-1">Entregas</p>
                  <p className="font-bold text-green-600 dark:text-green-400 text-xl">{showMemberModal.deliveries || 0}</p>
                </div>
              </div>
              
              {/* Ações */}
              <div className="space-y-2 pt-2">
                <button 
                  onClick={() => window.open(`https://t.me/${showMemberModal.id}`, '_blank')}
                  className="w-full btn-primary flex items-center justify-center gap-2"
                >
                  <Phone size={18} /> Contatar no Telegram
                </button>
                <button 
                  onClick={() => handleRemove(showMemberModal.id)}
                  className="w-full btn-danger-outline flex items-center justify-center gap-2"
                >
                  <Trash2 size={18} /> Remover da Equipe
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Add */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 w-full max-w-sm shadow-2xl animate-fade-in">
            <h3 className="text-lg font-bold mb-4 text-gray-900 dark:text-white">Novo Entregador</h3>
            <form onSubmit={handleAdd} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-500 dark:text-gray-400 mb-1 font-medium">Nome</label>
                <input 
                  type="text" 
                  required
                  className="input-premium"
                  placeholder="Ex: João Silva"
                  value={newMember.name}
                  onChange={e => setNewMember({...newMember, name: e.target.value})}
                />
              </div>
              
              <div>
                <label className="block text-sm text-gray-500 dark:text-gray-400 mb-1 font-medium">Telegram ID</label>
                <input 
                  type="number" 
                  required
                  className="input-premium"
                  placeholder="Ex: 123456789"
                  value={newMember.telegram_id}
                  onChange={e => setNewMember({...newMember, telegram_id: e.target.value})}
                />
                <p className="text-[10px] text-gray-400 mt-1">Peça pro entregador enviar /id para o bot.</p>
              </div>

              <div className="flex items-center gap-3 pt-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                <input 
                  type="checkbox" 
                  id="is_partner"
                  className="w-5 h-5 rounded text-primary-600 focus:ring-primary-500 border-gray-300 cursor-pointer"
                  checked={newMember.is_partner}
                  onChange={e => setNewMember({...newMember, is_partner: e.target.checked})}
                />
                <label htmlFor="is_partner" className="text-sm font-medium text-gray-700 dark:text-gray-300 cursor-pointer">
                  Sócio (Não recebe por pacote)
                </label>
              </div>

              <div className="flex gap-3 pt-4">
                <button 
                  type="button" 
                  onClick={() => setShowModal(false)}
                  className="flex-1 btn-ghost"
                >
                  Cancelar
                </button>
                <button 
                  type="submit" 
                  className="flex-1 btn-primary"
                >
                  Salvar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
