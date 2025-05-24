import React, { useState } from 'react';

const GamePage = () => {
  const [playerHand, setPlayerHand] = useState([]);
  const [aiHand, setAiHand] = useState([]);
  const [community, setCommunity] = useState([]);

  const startGame = async () => {
    const res = await fetch('http://localhost:5000/start-game', {
      method: 'POST'
    });
    const data = await res.json();

    setPlayerHand(data.player_hand);
    setAiHand(data.ai_hand.map(() => 'cardback')); // hide AI cards
    setCommunity(data.community);
  };

  return (
    <div
      style={{
        backgroundImage: 'url(/cards/background.png)',
        backgroundSize: 'cover',
        height: '100vh',
        padding: '2rem',
        color: 'white'
      }}
    >
      <h1>Heads-Up Poker</h1>

      <button onClick={startGame}>Start Game</button>

      <h2>Player Hand</h2>
      <div>
        {playerHand.map((card, idx) => (
          <img key={idx} src={`/cards/${translateCard(card)}.png`} height="100" />
        ))}
      </div>

      <h2>AI Hand</h2>
      <div>
        {aiHand.map((card, idx) => (
          <img key={idx} src={`/cards/${card}.png`} height="100" />
        ))}
      </div>
    </div>
  );
};

// e.g. "As" → "ace_of_spades"
const translateCard = (shortCode) => {
  const rankMap = {
    '2': '2', '3': '3', '4': '4', '5': '5', '6': '6',
    '7': '7', '8': '8', '9': '9', 'T': '10', 'J': 'jack',
    'Q': 'queen', 'K': 'king', 'A': 'ace'
  };
  const suitMap = {
    's': 'spades',
    'h': 'hearts',
    'd': 'diamonds',
    'c': 'clubs'
  };

  const rank = rankMap[shortCode[0]];
  const suit = suitMap[shortCode[1]];
  return `${rank}_of_${suit}`;
};

export default GamePage;
