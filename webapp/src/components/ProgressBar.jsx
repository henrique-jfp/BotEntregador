import React, { useEffect, useState } from 'react';

export default function ProgressBar({ visible = true, percentage = 30 }) {
  const [showBar, setShowBar] = useState(visible);

  useEffect(() => {
    setShowBar(visible);
  }, [visible]);

  if (!showBar) return null;

  return (
    <div 
      className="fixed top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary-500 via-purple-500 to-accent-500 shadow-lg shadow-primary-500/50 z-50 transition-all duration-300"
      style={{ 
        width: `${percentage}%`,
        opacity: percentage === 100 ? 0 : 1
      }}
    />
  );
}
