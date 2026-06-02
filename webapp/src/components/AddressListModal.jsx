import React from "react";

export default function AddressListModal({ addresses, onClose }) {
  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <button className="close-btn" onClick={onClose} aria-label="Fechar lista">×</button>
        <h2>Lista de Endereços</h2>
        <ul>
          {addresses.map((addr, idx) => (
            <li key={addr.id}>
              <span className="pin-number">{idx+1}</span>
              <span className="address">{addr.street}, {addr.neighborhood}</span>
            </li>
          ))}
        </ul>
      </div>
      <style>{`
        .modal-overlay {
          position: fixed;
          top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0,0,0,0.18);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }
        .modal-content {
          background: #fff;
          border-radius: 18px;
          box-shadow: 0 8px 32px rgba(108,99,255,0.18);
          padding: 32px 24px 24px 24px;
          min-width: 320px;
          max-width: 90vw;
          max-height: 80vh;
          overflow-y: auto;
          position: relative;
        }
        .close-btn {
          position: absolute;
          top: 16px; right: 16px;
          background: none;
          border: none;
          font-size: 28px;
          color: #6C63FF;
          cursor: pointer;
        }
        h2 {
          margin-bottom: 18px;
          font-family: Inter, Arial, sans-serif;
          font-size: 22px;
          color: #333;
        }
        ul {
          list-style: none;
          padding: 0;
          margin: 0;
        }
        li {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 0;
          border-bottom: 1px solid #f0f0f0;
          font-size: 17px;
        }
        .pin-number {
          width: 32px; height: 32px;
          background: #6C63FF;
          color: #fff;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          font-size: 16px;
          box-shadow: 0 2px 8px rgba(108,99,255,0.12);
        }
        .address {
          color: #444;
        }
      `}</style>
    </div>
  );
}
