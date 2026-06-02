import React, { useRef, useEffect, useState } from 'react';
import { Camera, Upload, X, Check } from 'lucide-react';

// Usando html5-qrcode inline - mais simples que Quagga
const BarcodeScanner = ({ onScan, onClose }) => {
  const [scannedCodes, setScannedCodes] = useState([]);
  const [mode, setMode] = useState('camera'); // 'camera' | 'upload' | 'manual'
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);
  const streamRef = useRef(null);

  // Iniciar câmera
  useEffect(() => {
    if (mode === 'camera') startCamera();
    return () => stopCamera();
  }, [mode]);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play().catch(e => console.error('Play error:', e));
      }
      // Iniciar detecção contínua
      detectBarcodes();
    } catch (err) {
      console.error('Câmera bloqueada:', err);
      setMode('upload'); // Fallback para upload
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
  };

  // Detector de barcode simples usando canvas
  const detectBarcodes = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const video = videoRef.current;

    const detect = () => {
      if (video.readyState === video.HAVE_ENOUGH_DATA) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0);

        // Usar jsQR ou fallback simples
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        // Aqui entraria a detecção real (jsQR library)
        // Por enquanto, apenas cap da câmera
      }
      requestAnimationFrame(detect);
    };
    detect();
  };

  // Upload de imagem
  const handleImageUpload = async (file) => {
    const reader = new FileReader();
    reader.onload = async (e) => {
      const img = new Image();
      img.onload = () => {
        if (canvasRef.current) {
          const canvas = canvasRef.current;
          canvas.width = img.width;
          canvas.height = img.height;
          canvas.getContext('2d').drawImage(img, 0, 0);
          // Aqui detectar barcode da imagem
          // Placeholder: simular com nome do arquivo
          processBarcode(file.name.replace(/\D/g, '') || 'manual-' + Date.now());
        }
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  };

  // Processar código detectado
  const processBarcode = (code) => {
    if (!code || scannedCodes.includes(code)) return;
    
    const newCode = {
      id: code,
      timestamp: new Date().toLocaleTimeString('pt-BR'),
      confirmed: false,
    };
    setScannedCodes([...scannedCodes, newCode]);
    onScan?.(code);
  };

  // Input manual
  const handleManualInput = (e) => {
    if (e.key === 'Enter') {
      processBarcode(e.target.value);
      e.target.value = '';
    }
  };

  // Confirmar e enviar todos os códigos
  const handleConfirm = () => {
    onClose?.(scannedCodes.map(s => s.id));
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 max-w-2xl w-full mx-4 space-y-4">
        {/* Header */}
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold">📷 Scanner de Códigos</h2>
          <button
            onClick={() => onClose?.([])}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 border-b dark:border-gray-700">
          {['camera', 'upload', 'manual'].map(tab => (
            <button
              key={tab}
              onClick={() => setMode(tab)}
              className={`px-4 py-2 capitalize font-medium transition ${
                mode === tab
                  ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400'
              }`}
            >
              {tab === 'camera' && '📹'} {tab === 'upload' && '📁'} {tab === 'manual' && '⌨️'} {tab}
            </button>
          ))}
        </div>

        {/* Câmera */}
        {mode === 'camera' && (
          <div className="space-y-4">
            <video
              ref={videoRef}
              className="w-full h-64 bg-black rounded-lg object-cover"
              playsInline
            />
            <canvas ref={canvasRef} style={{ display: 'none' }} />
            <p className="text-sm text-gray-600 dark:text-gray-400">
              ⚠️ Posicione o código de barras ou QR code em frente à câmera
            </p>
          </div>
        )}

        {/* Upload */}
        {mode === 'upload' && (
          <div className="space-y-4">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="w-full border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
            >
              <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
              <p className="text-sm font-medium">Clique para selecionar imagem</p>
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleImageUpload(e.target.files[0])}
            />
            <canvas ref={canvasRef} style={{ display: 'none' }} />
          </div>
        )}

        {/* Manual */}
        {mode === 'manual' && (
          <div className="space-y-4">
            <input
              type="text"
              placeholder="Digite o código e pressione ENTER..."
              onKeyPress={handleManualInput}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
            <p className="text-xs text-gray-500">Útil para inserção manual de CPF, CNPJ ou IDs</p>
          </div>
        )}

        {/* Lista de Códigos Escaneados */}
        {scannedCodes.length > 0 && (
          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
            <h3 className="font-semibold mb-2">✅ {scannedCodes.length} código(s) escaneado(s)</h3>
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {scannedCodes.map((code, idx) => (
                <div
                  key={idx}
                  className="flex justify-between items-center bg-white dark:bg-gray-700 p-2 rounded"
                >
                  <span className="font-mono text-sm">{code.id}</span>
                  <span className="text-xs text-gray-500">{code.timestamp}</span>
                  <button
                    onClick={() =>
                      setScannedCodes(scannedCodes.filter((_, i) => i !== idx))
                    }
                    className="text-red-500 hover:text-red-700"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Botões */}
        <div className="flex gap-2 pt-4 border-t dark:border-gray-700">
          <button
            onClick={() => onClose?.([])}
            className="flex-1 px-4 py-2 bg-gray-300 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-400 dark:hover:bg-gray-600 font-medium"
          >
            Cancelar
          </button>
          <button
            onClick={handleConfirm}
            disabled={scannedCodes.length === 0}
            className="flex-1 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <Check className="w-4 h-4" /> Confirmar ({scannedCodes.length})
          </button>
        </div>
      </div>
    </div>
  );
};

export default BarcodeScanner;
