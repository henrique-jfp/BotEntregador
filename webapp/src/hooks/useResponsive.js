import { useState, useEffect } from 'react';

/**
 * Hook para detectar tamanho da tela e fornecer breakpoints responsivos
 * Breakpoints Tailwind:
 * - mobile: < 768px (sm)
 * - tablet: 768px - 1024px (md-lg)
 * - desktop: >= 1024px (lg)
 */
export function useResponsive() {
  // Inicializar com valores que respeitam SSR
  const [screenSize, setScreenSize] = useState(() => {
    if (typeof window === 'undefined') {
      return { width: 768, height: 1024 };
    }
    return {
      width: window.innerWidth,
      height: window.innerHeight,
    };
  });

  const [deviceType, setDeviceType] = useState(() => {
    if (typeof window === 'undefined') return 'mobile';
    // Developer override: force desktop layout when localStorage.forceDesktop === '1'
    try {
      if (localStorage.getItem('forceDesktop') === '1') return 'desktop';
    } catch (e) {}
    const w = window.innerWidth;
    if (w < 768) return 'mobile';
    if (w < 1024) return 'tablet';
    return 'desktop';
  });

  useEffect(() => {
    const handleResize = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      
      setScreenSize({ width: w, height: h });

      // Allow developer override to force desktop layout (useful when embedded)
      let forcedDesktop = false;
      try {
        forcedDesktop = localStorage.getItem('forceDesktop') === '1';
      } catch (e) {
        forcedDesktop = false;
      }

      if (forcedDesktop) {
        setDeviceType('desktop');
      } else if (w < 768) {
        setDeviceType('mobile');
      } else if (w < 1024) {
        setDeviceType('tablet');
      } else {
        setDeviceType('desktop');
      }
    };

    window.addEventListener('resize', handleResize);
    handleResize(); // Call once on mount to sync state

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return {
    width: screenSize.width,
    height: screenSize.height,
    isMobile: deviceType === 'mobile',
    isTablet: deviceType === 'tablet',
    isDesktop: deviceType === 'desktop',
    deviceType,
    // Helpers
    isSmallScreen: screenSize.width < 768,
    isMediumScreen: screenSize.width >= 768 && screenSize.width < 1024,
    isLargeScreen: screenSize.width >= 1024,
    isPortrait: screenSize.height > screenSize.width,
    isLandscape: screenSize.width > screenSize.height,
  };
}

export default useResponsive;
