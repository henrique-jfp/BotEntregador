import React from "react";

export default function FullscreenToggle({ isFullscreen, onToggle }) {
  return (
    <button className="fullscreen-btn" onClick={onToggle} aria-label={isFullscreen ? "Minimizar" : "Maximizar"}>
      {isFullscreen ? (
        <svg width="28" height="28" fill="none"><rect x="6" y="6" width="16" height="16" rx="4" stroke="#fff" strokeWidth="2"/><path d="M10 10L18 18M18 10L10 18" stroke="#fff" strokeWidth="2"/></svg>
      ) : (
        <svg width="28" height="28" fill="none"><rect x="6" y="6" width="16" height="16" rx="4" stroke="#fff" strokeWidth="2"/><path d="M10 10L18 18M18 10L10 18" stroke="#fff" strokeWidth="2"/></svg>
      )}
      <style>{`
        .fullscreen-btn {
          position: absolute;
          top: 18px;
          right: 18px;
          background: #6C63FF;
          border: none;
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(108,99,255,0.18);
          width: 36px;
          height: 36px;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: box-shadow 0.2s, transform 0.2s;
          z-index: 100;
        }
        .fullscreen-btn:hover {
          box-shadow: 0 4px 16px rgba(108,99,255,0.28);
          transform: scale(1.08);
        }
      `}</style>
    </button>
  );
}
