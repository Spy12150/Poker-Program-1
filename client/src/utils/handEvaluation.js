// Hand evaluation utility functions
export const evaluateHand = (playerHand, communityCards) => {
  if (!playerHand || playerHand.length < 2) {
    return "No hand";
  }

  // Combine player hand and community cards
  const allCards = [...playerHand, ...(communityCards || [])];
  
  // If we have less than 5 cards, just evaluate what we have
  if (allCards.length < 5) {
    return evaluatePartialHand(allCards);
  }

  // Convert cards to a format we can work with
  const cards = allCards.map(card => {
    const rank = card[0];
    const suit = card[1];
    return { rank, suit };
  });

  // Count ranks and suits
  const rankCounts = {};
  const suitCounts = {};
  const ranks = [];

  cards.forEach(card => {
    rankCounts[card.rank] = (rankCounts[card.rank] || 0) + 1;
    suitCounts[card.suit] = (suitCounts[card.suit] || 0) + 1;
    ranks.push(card.rank);
  });

  // Convert ranks to numbers for comparison
  const rankValues = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
  };

  const rankNames = {
    '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9', 'T': '10', 'J': 'Jack', 'Q': 'Queen', 'K': 'King', 'A': 'Ace'
  };

  // Sort ranks by frequency and value
  const sortedRanks = Object.keys(rankCounts).sort((a, b) => {
    if (rankCounts[b] !== rankCounts[a]) {
      return rankCounts[b] - rankCounts[a];
    }
    return rankValues[b] - rankValues[a];
  });

  // Check for flush
  const isFlush = Object.values(suitCounts).some(count => count >= 5);
  
  // Check for straight
  const uniqueRanks = [...new Set(ranks)].map(r => rankValues[r]).sort((a, b) => b - a);
  let isStraight = false;
  let straightHigh = 0;
  
  // Check for regular straight
  for (let i = 0; i <= uniqueRanks.length - 5; i++) {
    if (uniqueRanks[i] - uniqueRanks[i + 4] === 4) {
      isStraight = true;
      straightHigh = uniqueRanks[i];
      break;
    }
  }
  
  // Check for A-2-3-4-5 straight (wheel)
  if (!isStraight && uniqueRanks.includes(14) && uniqueRanks.includes(2) && uniqueRanks.includes(3) && uniqueRanks.includes(4) && uniqueRanks.includes(5)) {
    isStraight = true;
    straightHigh = 5;
  }

  // Determine hand type
  const pairs = sortedRanks.filter(rank => rankCounts[rank] === 2);
  const trips = sortedRanks.filter(rank => rankCounts[rank] === 3);
  const quads = sortedRanks.filter(rank => rankCounts[rank] === 4);

  if (isStraight && isFlush) {
    if (straightHigh === 14) {
      return "Royal Flush";
    } else {
      const highCard = Object.keys(rankValues).find(k => rankValues[k] === straightHigh);
      return `Straight Flush, ${rankNames[highCard]}-high`;
    }
  } else if (quads.length > 0) {
    return `Four of a Kind, ${rankNames[quads[0]]}s`;
  } else if (trips.length > 0 && pairs.length > 0) {
    return `Full House, ${rankNames[trips[0]]}s full of ${rankNames[pairs[0]]}s`;
  } else if (isFlush) {
    const highCard = sortedRanks[0];
    return `Flush, ${rankNames[highCard]}-high`;
  } else if (isStraight) {
    const highCard = Object.keys(rankValues).find(k => rankValues[k] === straightHigh);
    return `Straight, ${rankNames[highCard]}-high`;
  } else if (trips.length > 0) {
    return `Three of a Kind, ${rankNames[trips[0]]}s`;
  } else if (pairs.length >= 2) {
    return `Two Pair, ${rankNames[pairs[0]]}s and ${rankNames[pairs[1]]}s`;
  } else if (pairs.length === 1) {
    return `Pair, ${rankNames[pairs[0]]}s`;
  } else {
    const highCard = sortedRanks[0];
    return `High Card, ${rankNames[highCard]}`;
  }
};

// Helper function for hands with fewer than 5 cards
export const evaluatePartialHand = (cards) => {
  if (cards.length === 0) return "No hand";
  
  const rankCounts = {};
  const ranks = [];
  
  cards.forEach(card => {
    const rank = card[0];
    rankCounts[rank] = (rankCounts[rank] || 0) + 1;
    ranks.push(rank);
  });

  const rankValues = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
  };

  const rankNames = {
    '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9', 'T': '10', 'J': 'Jack', 'Q': 'Queen', 'K': 'King', 'A': 'Ace'
  };

  // Sort ranks by frequency and value
  const sortedRanks = Object.keys(rankCounts).sort((a, b) => {
    if (rankCounts[b] !== rankCounts[a]) {
      return rankCounts[b] - rankCounts[a];
    }
    return rankValues[b] - rankValues[a];
  });

  const pairs = sortedRanks.filter(rank => rankCounts[rank] === 2);
  
  if (pairs.length >= 1) {
    return `Pair, ${rankNames[pairs[0]]}s`;
  } else {
    const highCard = sortedRanks[0];
    return `High Card, ${rankNames[highCard]}`;
  }
};

// Card translation utility
export const translateCard = (shortCode) => {
  // Debug logging to catch invalid card formats
  console.log('translateCard called with:', shortCode, 'type:', typeof shortCode);
  
  if (!shortCode || typeof shortCode !== 'string' || shortCode.length < 2) {
    console.error('translateCard received invalid card:', shortCode);
    return 'Cardback1'; // Return safe fallback
  }

  const rankMap = {
    '2': '2', '3': '3', '4': '4', '5': '5', '6': '6',
    '7': '7', '8': '8', '9': '9', 'T': 'T', 'J': 'J',
    'Q': 'Q', 'K': 'K', 'A': 'A'
  };
  const suitMap = {
    's': 's',
    'h': 'h',
    'd': 'd',
    'c': 'c'
  };

  const rank = rankMap[shortCode[0]];
  const suit = suitMap[shortCode[1]];
  
  // Additional validation
  if (!rank || !suit) {
    console.error('translateCard: invalid rank or suit in card:', shortCode, 'rank:', rank, 'suit:', suit);
    console.error('translateCard: shortCode[0]:', shortCode[0], 'shortCode[1]:', shortCode[1]);
    return 'Cardback1'; // Return safe fallback
  }
  
  const result = `${rank}${suit}`;
  console.log('translateCard result:', result);
  return result;
};
