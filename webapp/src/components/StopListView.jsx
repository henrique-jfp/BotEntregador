import React from 'react';
import { CheckCircle2, XCircle, Package, Info } from 'lucide-react';

/**
 * StopListView - Lista de paradas/endereço para entregador
 * Props:
 *   stops: array de paradas (cada parada tem address, status, packages, note)
 *   currentStopIndex: índice da parada atual
 *   onStopSelect: função para selecionar parada
 */
export default function StopListView({ stops, currentStopIndex, onStopSelect }) {
  if (!stops || stops.length === 0) {
    return (
      <div className="p-6 text-center text-gray-500">Nenhuma parada na rota.</div>
    );
  }

  return (
    <div className="divide-y divide-gray-200">
      {stops.map((stop, idx) => (
        <button
          key={idx}
          onClick={() => onStopSelect(idx)}
          className={`w-full text-left px-4 py-4 flex items-center gap-4 bg-white hover:bg-blue-50 transition rounded-xl mb-2 border border-gray-100 shadow-sm ${idx === currentStopIndex ? 'ring-2 ring-blue-500' : ''}`}
        >
          {/* Badge de status */}
          <div className="flex flex-col items-center justify-center">
            {stop.status === 'delivered' ? (
              <CheckCircle2 className="w-6 h-6 text-emerald-500" />
            ) : stop.status === 'failed' ? (
              <XCircle className="w-6 h-6 text-red-500" />
            ) : (
              <Package className="w-6 h-6 text-blue-400" />
            )}
            <span className="text-xs font-bold mt-1 text-gray-600">{idx + 1}</span>
          </div>

          {/* Endereço e info */}
          <div className="flex-1">
            <div className="font-black text-lg text-gray-900 mb-1">{stop.address}</div>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span>{stop.packages?.length || 1} {stop.packages?.length === 1 ? 'unidade' : 'unidades'}</span>
              {stop.note && (
                <span className="flex items-center gap-1 text-amber-600"><Info className="w-4 h-4" />{stop.note}</span>
              )}
            </div>
          </div>

          {/* Status badge */}
          <div className="min-w-[80px] text-center">
            {stop.status === 'delivered' && <span className="bg-emerald-100 text-emerald-700 px-2 py-1 rounded-full text-xs font-bold">Entregue</span>}
            {stop.status === 'failed' && <span className="bg-red-100 text-red-700 px-2 py-1 rounded-full text-xs font-bold">Insucesso</span>}
            {!stop.status && <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded-full text-xs font-bold">Pendente</span>}
          </div>
        </button>
      ))}
    </div>
  );
}
