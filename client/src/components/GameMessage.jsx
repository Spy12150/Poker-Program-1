import React from 'react';

const GameMessage = ({ message }) => {
  if (!message) return null;

  return (
    <div className="message">
      {message}
    </div>
  );
};

export default GameMessage;
