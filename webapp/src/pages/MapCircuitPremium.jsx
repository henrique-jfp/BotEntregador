// Utilitário para extrair assignments dos selects de entregador
function getAssignmentsFromUI(routes, deliverers) {
  // Exemplo: busca selects pelo DOM (ajuste conforme estrutura real)
  const assignments = {};
  routes.forEach((route, idx) => {
    const select = document.getElementById(`deliverer-select-${route.id}`);
    if (select) {
      assignments[route.id] = parseInt(select.value, 10);
    }
  });
  return assignments;
}
  // Função para enviar rotas aos entregadores (batch)
  const handleAssignRoutes = async () => {
    setLoading(true);
    setError("");
    if (!sessionId) {
      setError("session_id não encontrado. Importe um romaneio primeiro.");
      setLoading(false);
      return;
    }
    // Supondo que você tem acesso às rotas e entregadores na tela
    // Aqui, routes = [{id, ...}], entregadores = [{id, nome}]
    // Ajuste conforme seu state real
    const routes = stopsProp || [];
    // Pegue assignments dos selects
    const assignments = getAssignmentsFromUI(routes, []);
    if (Object.keys(assignments).length === 0) {
      setError("Selecione ao menos um entregador para cada rota.");
      setLoading(false);
      return;
    }
    const result = await assignMultipleRoutes({ sessionId, assignments });
    setLoading(false);
    if (!result) {
      setError("Erro ao enviar rotas aos entregadores");
      return;
    }
    alert("Rotas enviadas com sucesso!");
  };
// ─── Configuração do endpoint backend ──────────────────────────────────────
const API_BASE = "/api";

// Função para dividir/otimizar rotas
async function divideAndAssignRoutes({ sessionId, numDeliverers, baseLat, baseLng }) {
  try {
    const res = await fetch(`${API_BASE}/routes/divide-and-assign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        num_deliverers: numDeliverers,
        base_lat: baseLat,
        base_lng: baseLng,
      }),
    });
    if (!res.ok) throw new Error("Erro ao dividir rotas: " + res.status);
    return await res.json();
  } catch (err) {
    console.error("[MapCircuitPremium] Erro na divisão de rotas:", err);
    return null;
  }
}

// Função para atribuir rotas aos entregadores (batch)
async function assignMultipleRoutes({ sessionId, assignments }) {
  try {
    const res = await fetch(`${API_BASE}/routes/assign-multiple`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        assignments: assignments,
      }),
    });
    if (!res.ok) throw new Error("Erro ao atribuir rotas: " + res.status);
    return await res.json();
  } catch (err) {
    console.error("[MapCircuitPremium] Erro ao atribuir rotas:", err);
    return null;
  }
}
import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { MapContainer, TileLayer, Polyline, Marker, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

/* ─── Google Fonts ────────────────────────────────────────────────────────── */
const fontLink = document.createElement("link");
fontLink.rel = "stylesheet";
fontLink.href = "https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Roboto:wght@400;500;700&display=swap";
document.head.appendChild(fontLink);

/* ─── Demo Data ───────────────────────────────────────────────────────────── */
const DEMO_STOPS = [
  { id: "ID 1",  address: "Rua Cupertino Durão, 81",    district: "Leblon, Rio de Janeiro, RJ",  lat: -22.9839, lng: -43.2235, time: "14:18", status: "pending" },
  { id: "ID 2",  address: "Rua General Urquiza, 102",   district: "Leblon, Rio de Janeiro, RJ",  lat: -22.9825, lng: -43.2201, time: "14:28", status: "pending" },
  { id: "ID 3",  address: "Av. Ataulfo de Paiva, 270",  district: "Leblon, Rio de Janeiro, RJ",  lat: -22.9844, lng: -43.2218, time: "14:38", status: "pending" },
  { id: "ID 4",  address: "Rua Dias Ferreira, 417",     district: "Leblon, Rio de Janeiro, RJ",  lat: -22.9858, lng: -43.2244, time: "14:52", status: "pending" },
  { id: "ID 5",  address: "Rua Aristides Espínola, 55", district: "Leblon, Rio de Janeiro, RJ",  lat: -22.9819, lng: -43.2259, time: "15:04", status: "pending" },
  { id: "ID 6",  address: "Rua Sambaíba, 304",          district: "Leblon, Rio de Janeiro, RJ",  lat: -22.9864, lng: -43.2275, time: "15:18", status: "pending" },
  { id: "ID 7",  address: "Rua Epitácio Pessoa, 700",   district: "Lagoa, Rio de Janeiro, RJ",   lat: -22.9801, lng: -43.2280, time: "15:32", status: "pending" },
  { id: "ID 8",  address: "Av. Borges de Medeiros, 300",district: "Lagoa, Rio de Janeiro, RJ",   lat: -22.9773, lng: -43.2190, time: "15:48", status: "pending" },
];

const ROUTE_NAME = "Leblon_22";
const ROUTE_TIME = "2h34min";
const ROUTE_KM   = "23,5 km";

/* ─── Map FlyTo ───────────────────────────────────────────────────────────── */
function FlyToStop({ position }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(position, 16, { animate: true, duration: 0.7 });
  }, [position, map]);
  return null;
}

/* ─── Circuit marker icon ─────────────────────────────────────────────────── */
function buildCircuitIcon(idx, status, isActive) {
  const isDone = status === "done";
  const isFail = status === "fail";
  const border = isDone ? "#1a73e8" : isFail ? "#d93025" : isActive ? "#1a56ff" : "#5f6368";
  const numColor = border;
  const size = 34;

  const badge = isDone
    ? `<span style="position:absolute;top:-6px;right:-5px;background:#fff;border-radius:50%;width:14px;height:14px;display:flex;align-items:center;justify-content:center;border:1.5px solid #1a73e8;font-size:8px;color:#1a73e8;font-weight:900;line-height:1;">✓</span>`
    : isFail
    ? `<span style="position:absolute;top:-6px;right:-5px;background:#fff;border-radius:50%;width:14px;height:14px;display:flex;align-items:center;justify-content:center;border:1.5px solid #d93025;font-size:8px;color:#d93025;font-weight:900;line-height:1;">✕</span>`
    : "";

  return L.divIcon({
    className: "",
    html: `
      <div style="position:relative;display:inline-flex;flex-direction:column;align-items:center;">
        <div style="
          width:${size}px;height:${size}px;
          background:#fff;
          border:2.5px solid ${border};
          border-radius:8px;
          display:flex;align-items:center;justify-content:center;
          font-family:'Roboto',sans-serif;font-weight:700;font-size:13px;
          color:${numColor};
          box-shadow:0 2px 6px rgba(0,0,0,0.22);
          position:relative;
        ">
          ${idx + 1}
          ${badge}
        </div>
        <div style="width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;border-top:7px solid ${border};margin-top:-1px;"></div>
      </div>`,
    iconSize: [size, size + 8],
    iconAnchor: [size / 2, size + 8],
  });
}

/* ─── Top Bar ─────────────────────────────────────────────────────────────── */
function TopBar({ routeName, onMenuClick }) {
  return (
    <div className="absolute top-0 left-0 right-0 z-10 flex items-center px-3 pt-4 gap-3 pointer-events-none">
      <button
        className="pointer-events-auto w-10 h-10 bg-white rounded-full shadow-md flex items-center justify-center"
        onClick={onMenuClick}
      >
        <svg width="20" height="20" fill="none" viewBox="0 0 24 24">
          <path d="M4 6h16M4 12h16M4 18h16" stroke="#3c4043" strokeWidth="2" strokeLinecap="round"/>
        </svg>
      </button>
      <div
        className="pointer-events-auto flex-1 bg-white rounded-full shadow-md px-4 h-10 flex items-center"
      >
        <span className="text-sm font-medium text-gray-700">{routeName}</span>
      </div>
    </div>
  );
}

/* ─── Map Controls ────────────────────────────────────────────────────────── */
function MapControls({ bottomOffset }) {
  return (
    <div
      className="absolute right-3 z-10 flex flex-col gap-2"
      style={{ bottom: `${bottomOffset + 16}px` }}
    >
      <button className="w-10 h-10 bg-white rounded-full shadow-md flex items-center justify-center">
        <svg width="20" height="20" fill="none" viewBox="0 0 24 24">
          <rect x="3" y="3" width="8" height="8" rx="1.5" stroke="#5f6368" strokeWidth="1.8"/>
          <rect x="13" y="3" width="8" height="8" rx="1.5" stroke="#5f6368" strokeWidth="1.8"/>
          <rect x="3" y="13" width="8" height="8" rx="1.5" stroke="#5f6368" strokeWidth="1.8"/>
          <rect x="13" y="13" width="8" height="8" rx="1.5" stroke="#5f6368" strokeWidth="1.8"/>
        </svg>
      </button>
      <button className="w-10 h-10 bg-white rounded-full shadow-md flex items-center justify-center">
        <svg width="20" height="20" fill="none" viewBox="0 0 24 24">
          <path d="M3 5h18M3 10h18M3 15h12" stroke="#5f6368" strokeWidth="2" strokeLinecap="round"/>
        </svg>
      </button>
    </div>
  );
}

/* ─── Stop Row ────────────────────────────────────────────────────────────── */
function StopRow({ stop, idx, isActive, onSelect, isLast }) {
  const isDone = stop.status === "done";
  const isFail = stop.status === "fail";
  const lineColor = isDone ? "#1a73e8" : "#dadce0";

  return (
    <div
      className={`flex items-stretch cursor-pointer ${isActive ? "bg-blue-50" : "hover:bg-gray-50"}`}
      onClick={() => onSelect(idx)}
      style={{ minHeight: 56 }}
    >
      {/* Timeline */}
      <div className="flex flex-col items-center w-14 shrink-0 pt-2">
        <div className={`w-8 h-8 rounded-lg border-2 flex items-center justify-center text-[13px] font-bold shrink-0 relative bg-white
          ${isDone ? "border-blue-600 text-blue-600"
            : isFail ? "border-red-500 text-red-500"
            : isActive ? "border-blue-600 text-blue-600"
            : "border-gray-400 text-gray-600"}`}>
          {idx + 1}
          {isDone && (
            <span className="absolute -top-1.5 -right-1.5 text-[8px] text-blue-600 font-black leading-none bg-white rounded-full px-0.5">✓</span>
          )}
        </div>
        {!isLast && (
          <div className="w-0.5 flex-1 mt-1 mb-0" style={{ background: lineColor, minHeight: 16 }} />
        )}
      </div>

      {/* Content */}
      <div className={`flex-1 pr-4 pt-2 pb-2 min-w-0 ${!isLast ? "border-b border-gray-100" : ""}`}>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <p className="text-[11px] text-gray-500 leading-none mb-0.5">{stop.time}</p>
            <p className={`text-[13px] font-medium leading-snug ${isDone ? "text-gray-400 line-through" : "text-gray-900"}`}>
              {stop.address}
            </p>
            <p className="text-[11px] text-gray-400 truncate">{stop.district}</p>
          </div>
          <div className={`shrink-0 mt-0.5 flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold border
            ${isDone ? "border-blue-200 text-blue-600 bg-blue-50"
              : isFail ? "border-red-200 text-red-500 bg-red-50"
              : "border-gray-200 text-gray-500"}`}>
            {stop.id}
            {isDone && (
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" fill="#1a73e8"/>
                <path d="M7 12l4 4 6-6" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Completed Banner ────────────────────────────────────────────────────── */
function CompletedBanner({ stops }) {
  return (
    <div className="px-4 pt-3 pb-4">
      <div className="flex items-center gap-2 mb-0.5">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" fill="#1e8e3e"/>
          <path d="M7 12l4 4 6-6" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span className="text-base font-bold text-gray-900">Rota concluída!</span>
      </div>
      <p className="text-sm text-gray-500 ml-7">{stops.length} paradas · Todas feitas</p>
      <button className="w-full mt-4 flex items-center justify-center gap-2 py-3 rounded-xl border border-gray-200 text-blue-600 text-sm font-medium">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M8 17l-5-5 5-5M16 7l5 5-5 5M14 7l-4 10" stroke="#1a73e8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Copiar paradas para uma nova rota
      </button>
      <button className="w-full mt-2 py-3 rounded-xl bg-blue-600 text-white text-sm font-bold">
        Criar nova rota
      </button>
    </div>
  );
}

/* ─── Action Buttons ──────────────────────────────────────────────────────── */
function ActionButtons({ stop, onAction }) {
  const handleNavigate = () => {
    if (!stop) return;
    const { lat, lng } = stop;
    const isMobile = /iPhone|Android/i.test(navigator.userAgent);
    const url = isMobile
      ? `waze://?ll=${lat},${lng}&navigate=yes`
      : `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=driving`;
    window.open(url, "_blank");
  };

  return (
    <div className="shrink-0 px-3 py-2 border-t border-gray-100">
      {stop && <p className="text-[11px] text-gray-500 mb-2 truncate font-medium">{stop.address}</p>}
      <div className="grid grid-cols-4 gap-1.5">
        <button
          onClick={handleNavigate}
          className="flex flex-col items-center justify-center gap-1 rounded-xl py-2.5 text-[10px] font-bold text-white"
          style={{ background: "#1a73e8" }}
        >
          <svg width="17" height="17" fill="white" viewBox="0 0 24 24"><path d="M12 2L3 12h5v10h8V12h5L12 2z"/></svg>
          Navegar
        </button>
        <button
          onClick={() => onAction("fail")}
          className="flex flex-col items-center justify-center gap-1 rounded-xl py-2.5 text-[10px] font-bold text-red-500 bg-red-50 border border-red-100"
        >
          <svg width="17" height="17" fill="none" viewBox="0 0 24 24"><path d="M6 6l12 12M6 18L18 6" stroke="#ef4444" strokeWidth="2.2" strokeLinecap="round"/></svg>
          Não entregue
        </button>
        <button
          onClick={() => onAction("done")}
          className="flex flex-col items-center justify-center gap-1 rounded-xl py-2.5 text-[10px] font-bold text-green-600 bg-green-50 border border-green-100"
        >
          <svg width="17" height="17" fill="none" viewBox="0 0 24 24"><path d="M5 13l4 4L19 7" stroke="#16a34a" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
          Entregue
        </button>
        <button
          onClick={() => onAction("transfer")}
          className="flex flex-col items-center justify-center gap-1 rounded-xl py-2.5 text-[10px] font-bold text-blue-600 bg-blue-50 border border-blue-100"
        >
          <svg width="17" height="17" fill="none" viewBox="0 0 24 24"><path d="M17 8l4 4-4 4M7 16l-4-4 4-4M21 12H3" stroke="#1a73e8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
          Transferir
        </button>
      </div>
    </div>
  );
}

/* ─── Bottom Sheet ────────────────────────────────────────────────────────── */
function BottomSheet({ stops, currentIdx, onStopSelect, onAction, expanded, setExpanded }) {
  const allDone  = stops.every(s => s.status !== "pending");
  const pending  = stops.filter(s => s.status === "pending").length;
  const stop     = stops[currentIdx];
  const listRef  = useRef(null);

  useEffect(() => {
    if (expanded && listRef.current) {
      const el = listRef.current.querySelector(`[data-idx="${currentIdx}"]`);
      if (el) el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [currentIdx, expanded]);

  const sheetStyle = {
    boxShadow: "0 -2px 20px rgba(0,0,0,0.13)",
    transition: "max-height .35s cubic-bezier(.4,0,.2,1)",
    maxHeight: expanded ? "82vh" : "auto",
    display: "flex",
    flexDirection: "column",
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-20 bg-white rounded-t-2xl" style={sheetStyle}>
      {/* Handle */}
      <div className="flex justify-center pt-2.5 pb-1 cursor-pointer shrink-0" onClick={() => setExpanded(v => !v)}>
        <div className="w-9 h-1 bg-gray-300 rounded-full" />
      </div>

      {/* ── COLLAPSED VIEW ── */}
      {!expanded && (
        <>
          {/* Search bar */}
          <div className="flex items-center gap-2 mx-4 mb-3 mt-1 bg-gray-100 rounded-full px-4 h-11">
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" stroke="#5f6368" strokeWidth="2"/><path d="M16.5 16.5l3.5 3.5" stroke="#5f6368" strokeWidth="2" strokeLinecap="round"/></svg>
            <span className="text-sm text-gray-400 flex-1">Adicione ou busque</span>
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><rect x="3" y="5" width="8" height="6" rx="1" stroke="#5f6368" strokeWidth="1.5"/><rect x="13" y="5" width="8" height="6" rx="1" stroke="#5f6368" strokeWidth="1.5"/><path d="M3 15h18" stroke="#5f6368" strokeWidth="1.5" strokeLinecap="round"/></svg>
            <svg width="16" height="16" fill="none" viewBox="0 0 24 24"><path d="M12 2a3 3 0 013 3v5a3 3 0 01-6 0V5a3 3 0 013-3z" stroke="#5f6368" strokeWidth="1.5"/><path d="M19 10a7 7 0 01-14 0M12 17v4M8 21h8" stroke="#5f6368" strokeWidth="1.5" strokeLinecap="round"/></svg>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="5" r="1.5" fill="#5f6368"/><circle cx="12" cy="12" r="1.5" fill="#5f6368"/><circle cx="12" cy="19" r="1.5" fill="#5f6368"/></svg>
          </div>

          {/* Route info */}
          <div className="px-4 mb-2">
            <p className="text-[13px] text-gray-500 mb-0.5">{ROUTE_TIME} · {stops.length} paradas · {ROUTE_KM}</p>
            <h1 className="text-[26px] font-bold text-gray-900 leading-tight" style={{ fontFamily: "'Google Sans','Roboto',sans-serif" }}>
              {ROUTE_NAME}
            </h1>
          </div>

          {/* Pause row */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-gray-400" />
              <div>
                <p className="text-[13px] font-medium text-gray-800">Sem pausa</p>
                <p className="text-xs text-gray-500">Toque para agendar uma pausa</p>
              </div>
            </div>
            <svg width="22" height="22" fill="none" viewBox="0 0 24 24"><path d="M18 8h1a4 4 0 010 8h-1M2 8h16v9a4 4 0 01-4 4H6a4 4 0 01-4-4V8zM6 2v4M10 2v4M14 2v4" stroke="#5f6368" strokeWidth="1.6" strokeLinecap="round"/></svg>
          </div>

          {/* Start point */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
            <div className="flex items-start gap-3">
              <div className="mt-1">
                <svg width="15" height="15" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4" fill="#1a73e8"/><circle cx="12" cy="12" r="8" stroke="#1a73e8" strokeWidth="1.5" fill="none" opacity="0.25"/></svg>
              </div>
              <div>
                <p className="text-[11px] text-gray-500">{stops[0]?.time}</p>
                <p className="text-[13px] font-medium text-gray-800">Ponto de partida</p>
                <p className="text-xs text-gray-500">Posição do GPS usada ao otimizar</p>
              </div>
            </div>
            <svg width="22" height="22" fill="none" viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" stroke="#1a73e8" strokeWidth="1.6"/><path d="M9 22V12h6v10" stroke="#1a73e8" strokeWidth="1.6"/></svg>
          </div>

          {/* CTA footer */}
          {allDone ? (
            <CompletedBanner stops={stops} />
          ) : (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 pb-6">
              <span className="text-lg font-bold text-green-600" style={{ fontFamily: "'Google Sans',sans-serif" }}>
                {ROUTE_TIME}
              </span>
              <div className="flex gap-2">
                <button className="px-6 py-2.5 rounded-full border border-gray-300 text-gray-800 text-sm font-medium">
                  Refinar
                </button>
                <button
                  className="px-6 py-2.5 rounded-full bg-blue-600 text-white text-sm font-bold"
                  onClick={() => setExpanded(true)}
                >
                  Confirmar
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* ── EXPANDED VIEW ── */}
      {expanded && (
        <>
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-100 shrink-0">
            <p className="text-xs text-gray-500">
              Término: {stops[stops.length - 1]?.time} · {pending} parada{pending !== 1 ? "s" : ""} · {ROUTE_KM}
            </p>
            <div className="flex items-center gap-4">
              <svg width="17" height="17" fill="none" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" stroke="#5f6368" strokeWidth="2"/><path d="M16.5 16.5l3.5 3.5" stroke="#5f6368" strokeWidth="2" strokeLinecap="round"/></svg>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="5" r="1.5" fill="#5f6368"/><circle cx="12" cy="12" r="1.5" fill="#5f6368"/><circle cx="12" cy="19" r="1.5" fill="#5f6368"/></svg>
            </div>
          </div>

          {/* Stop list */}
          <div ref={listRef} className="overflow-y-auto flex-1" style={{ overscrollBehavior: "contain" }}>
            {stops.map((s, i) => (
              <div key={s.id} data-idx={i}>
                <StopRow
                  stop={s}
                  idx={i}
                  isActive={i === currentIdx}
                  onSelect={onStopSelect}
                  isLast={i === stops.length - 1}
                />
              </div>
            ))}
            {allDone && <CompletedBanner stops={stops} />}
          </div>

          {/* Action buttons */}
          {!allDone && stop && (
            <ActionButtons stop={stop} onAction={onAction} />
          )}
        </>
      )}
    </div>
  );
}

/* ─── Root ────────────────────────────────────────────────────────────────── */
// O componente agora só renderiza com dados reais vindos por props
export default function MapCircuitPremium({ 
  stops: stopsProp, 
  routeName = ROUTE_NAME, 
  routeTime = ROUTE_TIME, 
  routeKm = ROUTE_KM,
  hideUI = false,
  userLocation,
  onPinClick,
  heading
}) {

  // Só renderiza se receber paradas reais (array válido e não vazio)
  const isValidStops = Array.isArray(stopsProp) && stopsProp.length > 0 && stopsProp.every(s => s.lat && s.lng);
  const [stops, setStops] = useState(isValidStops ? stopsProp : []);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const [sheetHeight, setSheetHeight] = useState(320);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Recebe session_id real por prop
  const sessionId = typeof window !== "undefined" && window.sessionId ? window.sessionId : (window.sessionStorage.getItem("session_id") || null);
  // Alternativamente, pode ser passado por prop: MapCircuitPremium({ ..., sessionId })
  const numDeliverers = 2; // Troque para real ou por prop
  const baseLat = stops[0]?.lat || -22.98172547;
  const baseLng = stops[0]?.lng || -43.20740461;

  // Log para debug
  useEffect(() => {
    console.log("[MapCircuitPremium] sessionId usado:", sessionId);
  }, [sessionId]);

  const currentStop = stops[currentIdx];
  const polyline = useMemo(() => stops.map(s => [s.lat, s.lng]), [stops]);

  // Atualiza stops se mudar a prop
  useEffect(() => {
    if (isValidStops) setStops(stopsProp);
  }, [stopsProp]);

  // Medir altura do sheet para offset dos controles
  useEffect(() => {
    const el = document.getElementById("circuit-sheet");
    if (el) setSheetHeight(el.offsetHeight);
  });

  const handleAction = useCallback((status) => {
    setStops(prev => prev.map((s, i) => i === currentIdx ? { ...s, status } : s));
    if (status === "done" || status === "fail") {
      const next = stops.findIndex((s, i) => i > currentIdx && s.status === "pending");
      if (next !== -1) setCurrentIdx(next);
    }
  }, [currentIdx, stops]);

  // Função para acionar divisão/otimização e atribuição batch
  const handleDivideRoutes = async () => {
    setLoading(true);
    setError("");
    if (!sessionId) {
      setError("session_id não encontrado. Importe um romaneio primeiro.");
      setLoading(false);
      return;
    }
    const payload = {
      session_id: sessionId,
      num_deliverers: numDeliverers,
      base_lat: baseLat,
      base_lng: baseLng
    };
    console.log("[MapCircuitPremium] Payload enviado:", payload);
    const result = await divideAndAssignRoutes(payload);
    if (!result || result.status !== "success") {
      setLoading(false);
      setError(result?.detail || "Erro ao dividir rotas");
      return;
    }
    // Atualiza stops com a primeira rota retornada (mock)
    if (result.routes && result.routes.length > 0) {
      // DEBUG: log quantidade de rotas e pontos recebidos
      console.log("[MapCircuitPremium] Rotas recebidas:", result.routes.length);
      result.routes.forEach((r, i) => {
        console.log(`Rota ${i+1}: ${r.points_sample?.length || 0} pontos`, r);
      });
      // Renderiza todos os pontos de todas as rotas juntos (para debug)
      const allStops = result.routes.flatMap((route, ridx) =>
        (route.points_sample || []).map((p, idx) => ({
          id: `${route.id}_${idx+1}`,
          address: p.address,
          district: p.district || "",
          lat: p.lat,
          lng: p.lng,
          time: p.time || "",
          status: "pending",
          routeIdx: ridx
        }))
      );
      setStops(allStops);
      setCurrentIdx(0);
    }
    // Após dividir, atribuir rotas automaticamente (mock: atribui todas ao primeiro entregador)
    if (result.routes && result.routes.length > 0) {
      // Exemplo: atribuir cada rota a um entregador diferente (mock)
      const assignments = {};
      result.routes.forEach((route, idx) => {
        // Aqui você pode usar lógica real para pegar o entregador selecionado pelo usuário
        // Exemplo: alternar entre dois entregadores
        const delivererId = idx % 2 === 0 ? 123456789 : 987654321; // Troque para IDs reais
        assignments[route.id] = delivererId;
      });
      const assignResult = await assignMultipleRoutes({ sessionId, assignments });
      if (!assignResult) {
        setError("Erro ao atribuir rotas aos entregadores");
      }
    }
    setLoading(false);
  };

  // Fallback premium se não houver rota
  if (!isValidStops) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-gray-50">
        <svg width="64" height="64" fill="none" viewBox="0 0 64 64">
          <circle cx="32" cy="32" r="32" fill="#e0e7ef"/>
          <path d="M20 32h24M32 20v24" stroke="#1a73e8" strokeWidth="3" strokeLinecap="round"/>
        </svg>
        <h2 className="mt-6 text-2xl font-bold text-gray-800">Nenhuma rota encontrada</h2>
        <p className="mt-2 text-gray-500 text-center max-w-xs">
          Não foi possível carregar as paradas da rota.<br/>
          Verifique se a rota está ativa ou tente novamente.
        </p>
        <button
          className="mt-6 px-6 py-2.5 rounded-full bg-blue-600 text-white text-sm font-bold"
          onClick={handleDivideRoutes}
          disabled={loading}
        >
          {loading ? "Processando..." : "Otimizar/Dividir Rotas"}
        </button>
        {error && <p className="mt-2 text-red-500 text-sm">{error}</p>}
      </div>
    );
  }

  // Renderização normal do mapa
  return (
    <div className="relative w-full h-full overflow-hidden" style={{ fontFamily: "'Roboto', sans-serif" }}>
      {/* ── Map ── */}
      {currentStop && (
        <MapContainer
          center={[currentStop.lat, currentStop.lng]}
          zoom={15}
          style={{ height: "100%", width: "100%", zIndex: 1 }}
          scrollWheelZoom={true}
          dragging={true}
          doubleClickZoom={false}
          attributionControl={false}
          zoomControl={false}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
            attribution="© CartoDB"
          />
          {!hideUI && <FlyToStop position={[currentStop.lat, currentStop.lng]} />}
          <Polyline positions={polyline} color="#1a56ff" weight={6} opacity={0.95} />
          {stops.map((stop, idx) => (
            <Marker
              key={stop.id}
              position={[stop.lat, stop.lng]}
              icon={buildCircuitIcon(idx, stop.status, idx === currentIdx)}
              eventHandlers={{ click: () => {
                setCurrentIdx(idx);
                if (onPinClick) onPinClick(idx);
              } }}
            />
          ))}
          {userLocation && (
            <Marker 
              position={userLocation} 
              icon={L.divIcon({
                className: 'bg-transparent',
                html: `<div style="width: 20px; height: 20px; background-color: #3b82f6; border: 3px solid white; border-radius: 50%; box-shadow: 0 0 6px rgba(0,0,0,0.4); transform: rotate(${heading || 0}deg);">
                        ${heading !== undefined ? '<div style="position: absolute; top: -6px; left: 5px; width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 6px solid #3b82f6;"></div>' : ''}
                       </div>`,
                iconSize: [20, 20],
                iconAnchor: [10, 10],
              })} 
            />
          )}
        </MapContainer>
      )}

      {/* ── UI Elements ── */}
      {!hideUI && (
        <>
          {/* ── Top Bar ── */}
          <TopBar routeName={routeName} onMenuClick={() => setExpanded(v => !v)} />

          {/* ── Map Controls ── */}
          <MapControls bottomOffset={sheetHeight} />

          {/* ── Bottom Sheet ── */}
          <div id="circuit-sheet">
            <BottomSheet
              stops={stops}
              currentIdx={currentIdx}
              onStopSelect={setCurrentIdx}
              onAction={handleAction}
              expanded={expanded}
              setExpanded={setExpanded}
            />
          </div>

          {/* ── Botão Confirmar e Enviar Rotas ── */}
          <div style={{ position: "absolute", bottom: 24, left: 0, right: 0, display: "flex", justifyContent: "center", zIndex: 30 }}>
            <button
              className="px-8 py-3 rounded-full bg-green-600 text-white text-lg font-bold shadow-lg"
              onClick={handleAssignRoutes}
              disabled={loading}
            >
              {loading ? "Enviando..." : "Confirmar e Enviar Rotas"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}