import React from 'react';
import GamePageWebSocket from './pages/GamePageWebSocket';
import { useImagePreloader } from './hooks/useImagePreloader';

function App() {
  // Preload card images for better performance
  useImagePreloader();
  
  return <GamePageWebSocket />;
}

export default App;
