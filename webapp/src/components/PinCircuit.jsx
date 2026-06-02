import React from "react";

export default function PinCircuit({ number, onClick, isActive }) {
  return (
    <div
      className={`pin-circuit ${isActive ? "active" : ""}`}
      onClick={onClick}
      style={{
        cursor: "pointer",
        transition: "transform 0.2s",
        transform: isActive ? "scale(1.15)" : "scale(1)",
      }}
    >
      <svg width="44" height="60" viewBox="0 0 44 60" fill="none">
        <ellipse cx="22" cy="40" rx="20" ry="18" fill="#6C63FF" stroke="#fff" strokeWidth="4" />
        <circle cx="22" cy="22" r="16" fill="#fff" stroke="#6C63FF" strokeWidth="4" />
        <text
          x="22"
          y="28"
          textAnchor="middle"
          fontSize="18"
          fontWeight="bold"
          fill="#6C63FF"
          style={{ fontFamily: "Inter, Arial, sans-serif" }}
        >
          {number}
        </text>
      </svg>
      <style>{`
        .pin-circuit {
          box-shadow: 0 4px 16px rgba(108,99,255,0.25);
          border-radius: 22px;
          background: transparent;
          display: inline-block;
        }
        .pin-circuit.active {
          box-shadow: 0 8px 24px rgba(108,99,255,0.35);
        }
      `}</style>
    </div>
  );
}
