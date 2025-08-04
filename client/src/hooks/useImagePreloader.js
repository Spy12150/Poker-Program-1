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
 * Hook for optimized card image loading with WebP and fallback
 */
export const useCardImage = (card) => {
  const getCardImageSrc = (cardCode) => {
    console.log('useCardImage called with:', cardCode);
    
    if (!cardCode || typeof cardCode !== 'string') {
      console.warn('useCardImage: Invalid card code, using fallback:', cardCode);
      return '/IvoryCards/Cardback1.webp';
    }
    
    // Handle cardbacks (they start with "Cardback")
    if (cardCode.startsWith('Cardback')) {
      console.log('useCardImage: Detected cardback:', cardCode);
      return `/IvoryCards/${cardCode}.webp`;
    }
    
    // Handle regular cards (should be 2 characters: rank + suit)
    if (cardCode.length !== 2) {
      console.warn('useCardImage: Invalid card format, expected 2 chars, got:', cardCode.length, 'for card:', cardCode);
      return '/IvoryCards/Cardback1.webp';
    }
    
    const rank = cardCode[0];
    const suit = cardCode[1];
    
    // Validate rank and suit
    const validRanks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'];
    const validSuits = ['c', 'd', 'h', 's'];
    
    if (!validRanks.includes(rank) || !validSuits.includes(suit)) {
      console.warn('useCardImage: Invalid rank/suit combination:', rank, suit, 'for card:', cardCode);
      return '/IvoryCards/Cardback1.webp';
    }
    
    const result = `/IvoryCards/${rank}${suit}.webp`;
    console.log('useCardImage: Generated path:', result);
    return result;
  };
  
  return getCardImageSrc(card);
};
