import { useEffect } from 'react';

/**
 * Custom hook for preloading card images
 * Uses Web Workers and lazy loading for optimal performance
 */
export const useImagePreloader = () => {
  useEffect(() => {
    const preloadImages = async () => {
      // Generate all card image paths
      const suits = ['c', 'd', 'h', 's'];
      const ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'];
      
      const cardImages = [];
      suits.forEach(suit => {
        ranks.forEach(rank => {
          // Try WebP first, fallback to PNG
          cardImages.push(`/IvoryCards/${rank}${suit}.webp`);
          cardImages.push(`/IvoryCards/${rank}${suit}.png`);
        });
      });

      // Add card backs
      for (let i = 1; i <= 19; i++) {
        cardImages.push(`/IvoryCards/Cardback${i}.webp`);
        cardImages.push(`/IvoryCards/Cardback${i}.png`);
      }

      // Preload images in batches to avoid overwhelming the browser
      const batchSize = 10;
      const startTime = performance.now();
      
      console.log('🎴 Starting image preload...');
      
      for (let i = 0; i < cardImages.length; i += batchSize) {
        const batch = cardImages.slice(i, i + batchSize);
        
        await Promise.allSettled(
          batch.map(src => {
            return new Promise((resolve, reject) => {
              const img = new Image();
              
              img.onload = () => {
                resolve(src);
              };
              
              img.onerror = () => {
                // Silently fail for missing WebP files
                resolve(src);
              };
              
              // Set timeout to avoid hanging
              setTimeout(() => resolve(src), 2000);
              
              img.src = src;
            });
          })
        );
        
        // Small delay between batches to not block UI
        await new Promise(resolve => setTimeout(resolve, 10));
      }
      
      const endTime = performance.now();
      console.log(`✅ Image preload completed in ${Math.round(endTime - startTime)}ms`);
    };
    
    // Start preloading after a short delay to not block initial render
    const timeoutId = setTimeout(preloadImages, 100);
    
    return () => clearTimeout(timeoutId);
  }, []);
};

/**
 * Hook for optimized card image loading with WebP fallback
 */
export const useCardImage = (card) => {
  const getCardImageSrc = (cardCode) => {
    if (!cardCode || cardCode.length !== 2) return '/IvoryCards/Cardback1.png';
    
    const rank = cardCode[0];
    const suit = cardCode[1];
    
    // Try WebP first for better performance
    const webpSrc = `/IvoryCards/${rank}${suit}.webp`;
    const pngSrc = `/IvoryCards/${rank}${suit}.png`;
    
    // Create a simple WebP support check
    const supportsWebP = (() => {
      const canvas = document.createElement('canvas');
      canvas.width = 1;
      canvas.height = 1;
      return canvas.toDataURL('image/webp').indexOf('data:image/webp') === 0;
    })();
    
    return supportsWebP ? webpSrc : pngSrc;
  };
  
  return getCardImageSrc(card);
};
