import { useEffect } from 'react';

/**
 * Custom hook for preloading card images (WebP format)
 * Uses batched loading for optimal performance
 */
export const useImagePreloader = () => {
  useEffect(() => {
    const preloadImages = async () => {
      // Generate all card image paths (WebP only)
      const suits = ['c', 'd', 'h', 's'];
      const ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'];
      
      const cardImages = [];
      suits.forEach(suit => {
        ranks.forEach(rank => {
          // Only WebP since we converted all PNG files
          cardImages.push(`/IvoryCards/${rank}${suit}.webp`);
        });
      });

      // Add card backs (WebP only)
      for (let i = 1; i <= 19; i++) {
        cardImages.push(`/IvoryCards/Cardback${i}.webp`);
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
                // Silently handle any missing files
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
 * Hook for optimized card image loading with WebP only
 */
export const useCardImage = (card) => {
  const getCardImageSrc = (cardCode) => {
    if (!cardCode || cardCode.length < 2) return '/IvoryCards/Cardback1.webp';
    
    const rank = cardCode[0];
    const suit = cardCode[1];
    
    // Use WebP only since we converted all PNG files
    return `/IvoryCards/${rank}${suit}.webp`;
  };
  
  return getCardImageSrc(card);
};
