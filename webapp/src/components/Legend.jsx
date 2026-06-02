import React from "react";
export default function Legend() {
  return (
    <div className="legend-premium">
      <span><svg width="24" height="24"><ellipse cx="12" cy="12" rx="10" ry="10" fill="#6C63FF" /></svg> Parada</span>
      <span><svg width="24" height="24"><circle cx="12" cy="12" r="10" fill="#4285F4" /></svg> Sua localização</span>
      <style>{`
        .legend-premium {
          position: fixed;
          bottom: 24px;
          left: 24px;
          background: rgba(255,255,255,0.95);
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
          padding: 12px 20px;
          font-family: Inter, Arial, sans-serif;
          font-size: 16px;
          display: flex;
          gap: 24px;
          z-index: 999;
        }
        .legend-premium span {
          display: flex;
          align-items: center;
          gap: 8px;
        }
      `}</style>
    </div>
  );
}
