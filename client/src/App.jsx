import React from 'react';
import GamePage from './pages/GamePage';
// import GamePageWebSocket from './pages/GamePageWebSocket';  // Available for production/hosting

function App() {
  return <GamePage />;
  // For WebSocket version (production): return <GamePageWebSocket />;
}

export default App;
