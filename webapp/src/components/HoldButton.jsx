import React, { useRef, useState, useEffect } from 'react';
import { Check } from 'lucide-react';

export default function HoldButton({ 
  onConfirm, 
  label = 'Confirmar', 
  holdDuration = 1500,
  icon: Icon = Check 
}) {
  const [progress, setProgress] = useState(0);
  const [isCompleted, setIsCompleted] = useState(false);
  const holdRef = useRef(null);
  const intervalRef = useRef(null);

  const handleMouseDown = () => {
    if (isCompleted) return;

    intervalRef.current = setInterval(() => {
      setProgress(prev => {
        const newProgress = prev + (100 / (holdDuration / 50));
        if (newProgress >= 100) {
          clearInterval(intervalRef.current);
          setIsCompleted(true);
          onConfirm?.();
          setTimeout(() => {
            setProgress(0);
            setIsCompleted(false);
          }, 1000);
          return 100;
        }
        return newProgress;
      });
    }, 50);
  };

  const handleMouseUp = () => {
    clearInterval(intervalRef.current);
    if (progress < 100 && !isCompleted) {
      setProgress(0);
    }
  };

  useEffect(() => {
    return () => clearInterval(intervalRef.current);
  }, []);

  return (
    <button
      ref={holdRef}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onTouchStart={handleMouseDown}
      onTouchEnd={handleMouseUp}
      disabled={isCompleted}
      className={`relative w-full py-4 rounded-xl font-bold text-white overflow-hidden transition-all active:scale-95 ${
        isCompleted 
          ? 'bg-green-500 shadow-lg shadow-green-500/30' 
          : 'bg-gradient-to-r from-primary-600 to-purple-600 shadow-lg shadow-primary-500/30 hover:shadow-xl'
      }`}
    >
      {/* Progress Bar Background */}
      <div
        className={`absolute inset-0 ${isCompleted ? 'bg-green-600' : 'bg-primary-700'} transition-all duration-100`}
        style={{ width: `${progress}%` }}
      />

      {/* Content */}
      <div className="relative z-10 flex items-center justify-center gap-2">
        {isCompleted ? (
          <>
            <Check className="w-5 h-5 animate-bounce" />
            <span>Confirmado!</span>
          </>
        ) : (
          <>
            <Icon className="w-5 h-5" />
            <span>{label}</span>
            {progress > 0 && (
              <span className="text-xs opacity-70 ml-2">{Math.round(progress)}%</span>
            )}
          </>
        )}
      </div>
    </button>
  );
}
