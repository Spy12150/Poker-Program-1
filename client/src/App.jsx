import React from 'react';
// import GamePage from './pages/GamePage';
import GamePageWebSocket from './pages/GamePageWebSocket';  // Optimized version with WebP support
import { useImagePreloader } from './hooks/useImagePreloader';

function App() {
  // Preload card images for better performance
  useImagePreloader();
  
  return <GamePageWebSocket />;
  // For HTTP version (local dev): return <GamePage />;
}

export default App;
