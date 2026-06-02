import React from "react";

export default function FloatingButton({ onClick }) {
  return (
    <button className="floating-btn" onClick={onClick} aria-label="Ver lista de endereços">
      <svg width="32" height="32" fill="none">
        <rect x="6" y="10" width="20" height="3" rx="1.5" fill="#6C63FF"/>
        <rect x="6" y="16" width="20" height="3" rx="1.5" fill="#6C63FF"/>
        <rect x="6" y="22" width="20" height="3" rx="1.5" fill="#6C63FF"/>
      </svg>
      <style>{`
        .floating-btn {
          position: fixed;
          bottom: 32px;
          right: 32px;
          background: #fff;
          border-radius: 50%;
          box-shadow: 0 4px 16px rgba(108,99,255,0.18);
          border: none;
          width: 64px;
          height: 64px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: box-shadow 0.2s, transform 0.2s;
          cursor: pointer;
          z-index: 999;
        }
        .floating-btn:hover {
          box-shadow: 0 8px 32px rgba(108,99,255,0.28);
          transform: scale(1.08);
        }
      `}</style>
    </button>
  );
}
