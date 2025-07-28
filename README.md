# Heads-Up Poker Web App

A simple web application for playing Texas Hold'em poker against an AI opponent. Built with React frontend and Flask backend.

I built this project because I got addicted to online poker and wanted to challenge myself to build an AI that could defeat myself in poker, which I was not able to do in my chess AI project I made when I just graduated high school.

## Features

- Complete poker game engine with proper betting rounds
- AI opponent that makes strategic decisions based on hand strength
- Real-time gameplay with instant responses
- Clean poker table interface
- Session management for multiple games

## Tech Stack

- Frontend: React 19 + Vite
- Backend: Flask + Python
- Hand Evaluation: Treys library
- Styling: CSS-in-JS

## Setup

You need Node.js and Python installed on your machine.

### Backend Setup
```bash
cd server
pip install -r requirements.txt
python run.py
```

The server will run on http://localhost:5000

### Frontend Setup
```bash
cd client
npm install
npm run dev
```

The frontend will run on http://localhost:3000

## How to Play

1. Open your browser to http://localhost:3000
2. Click "Start New Game" 
3. Use the action buttons (Fold, Call, Check, Raise) to play
4. Watch the pot, community cards, and stacks update automatically
5. After each hand ends, click "Deal Next Hand" to continue

## API Endpoints

- POST /start-game - Creates a new game session
- POST /player-action - Makes a poker action (fold/call/check/raise)
- GET /game-state/<id> - Returns current game state
- POST /new-hand - Starts the next hand

## Game Rules

Standard Texas Hold'em rules apply:
- Each player starts with $1000
- Blinds are $10 (small) and $20 (big)
- Best 5-card hand wins using hole cards + community cards
- Betting rounds: preflop, flop, turn, river
- Showdown determines winner if multiple players remain

## AI Strategy

The AI considers:
- Current hand strength using poker hand rankings
- Pot odds for calling decisions
- Different strategies for preflop vs postflop play
- Position and betting action when making decisions

## Development

To run both servers with one command:
```bash
./start-dev.sh
```

This script will start both the Flask backend and React frontend automatically.

## Project Structure

```
client/               # React frontend
  src/pages/          # Main game interface
  public/cards/       # Card image assets
server/               # Flask backend  
  app/game/           # Poker engine and AI
  app/routes.py       # API endpoints
```

## Future Plans

- Side pot handling for all-in scenarios
- Support for 6-player games
- More advanced AI strategies
- Tournament mode with increasing blinds
- Game statistics and hand history 

Sturucture for now:
Poker-Program-1/
├── README.md                                 # Basic project description
├── client/                                   # React/Vite frontend
│   ├── package.json                          # Dependencies (React 19, Vite 6)
│   ├── index.html                            # HTML entry point
│   ├── vite.config.js                        # Vite configuration
│   ├── eslint.config.js                      # ESLint config
│   ├── public/
│   │   ├── vite.svg
│   │   └── cards/                            # Complete deck of card images
│   │       ├── {rank}_of_{suit}.png          # Standard naming: 2-ace, clubs/diamonds/hearts/spades
│   │       ├── {face}_of_{suit}2.png         # DUPLICATES for face cards
│   │       ├── cardback.png                  # Hidden card back
│   │       ├── background.png                # Table background
│   │       └── {red/black}_joker.png         # Extra jokers
│   └── src/
│       ├── main.jsx                          # React entry point
│       ├── App.jsx                           # Minimal app wrapper
│       ├── index.css, App.css                # Styling
│       ├── pages/
│       │   └── GamePage.jsx                  # Main game UI (basic hand display)
│       └── assets/react.svg
├── server/                                    # Flask backend
│   ├── run.py                                # Flask app entry point
│   └── app/
│       ├── __init__.py                       # Flask factory with CORS
│       ├── routes.py                         # INCOMPLETE API routes
│       └── game/
│           ├── config.py                     # Game constants (2 players, $1000 stacks, $10/$20 blinds)
│           ├── hand_eval_lib.py              # Working treys integration
│           ├── hand_eval_pure.py             # Working on
│           ├── ai.py                         # STUB random AI
│           └── poker.py                      # CORE ENGINE with DUPLICATED functions