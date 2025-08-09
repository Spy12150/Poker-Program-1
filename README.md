# Riposte Poker AI

A simple web application for playing Texas Hold'em poker against an AI opponent. Built with React frontend and Flask backend.

I built this project because I got addicted to online poker and wanted to challenge myself to build an AI that could defeat myself in poker, which I was not able to do in my chess AI project I made when I just graduated high school.

## Project Info

This is a heads-up (1v1) Texas Hold'em poker website where you play against AIs that I've developed. 

So far there are 2 AIs, and 1 in development:
- Froggie - The first AI I made to test the game logic, does random action on each action
- Bladework - My hard-coded AI that I used my own poker knowledge to program. Includes a bucket system where hands are divided into 11 tiers for preflop decisionmaking. The AI can adjust play based on your vpip/pfr. It has a lot of features, including range calculations, board analysis, multi-street analysis, draw-analysis, and uses Monte Carlo simulations to solve spots. 

  - This bot was able to beat all the poker players I asked to test the program.

- Grand Challenger (In development) - This bot uses CFR (Counterfactual Regret Optimaztion) to split the vast poker game tree into information-sets. At each decision, it calculates how much a player or the AI "regrets" not doing a decision in past simulated hands. Through each run of self play it aims to reduce the average regret, eventually reaching the Nash Equilibrium (hopefully). 

  - This is all based on a 2007 paper by Martin Zinkevich, I recommend a read if you want to learn more. After implementing this I plan on taking it to the next step by implementing Deep CFR, which combines neutral networks with CFR optimization by introducing: 
    - an advantage network that learns to predict counterfactual regrets for pairs
    - a policy network that learns the running average strategy

The game runs entirely through WebSockets for real-time gameplay, with smooth card dealing animations and a clean interface. I wanted it to feel as close to playing online poker as possible, just without the risk of losing actual money (which was becoming a problem for me).

## Key Features

- **Real-time WebSocket gameplay** - No page refreshes, everything happens instantly
- **Advanced AI opponent** - Uses Monte Carlo simulations, opponent modeling, and betting line analysis
- **Smooth animations** - Cards deal naturally with CSS animations
- **Session statistics** - Tracks VPIP and basic stats for the current game
- **Responsive design** - Works on both desktop and mobile

## Tech Stack

- **Frontend**: React, Vite, Socket.IO, CSS animations
- **Backend**: Flask, Python
- **Deployment**: Vercel (Frontend) + Railway (production)

## Project Structure

```
Poker-Program-1/
├── client/                          # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── PokerTable.jsx      # Main game table with cards/chips
│   │   │   ├── ActionPanel.jsx     # Bet/check/fold buttons
│   │   │   ├── GameHeader.jsx      # Chip counts and game info
│   │   │   └── HandHistory.jsx     # Previous hands display
│   │   ├── pages/
│   │   │   └── GamePageWebSocket.jsx # Main game logic & state
│   │   ├── hooks/
│   │   │   ├── useSocket.js        # WebSocket connection management
│   │   │   └── useImagePreloader.js # Card image optimization
│   │   └── utils/
│   │       ├── gameUtils.js        # Helper functions
│   │       └── handEvaluation.js   # Hand ranking logic
│   └── public/IvoryCards/          # Custom card images (webp format)
│
├── server/                          # Flask backend
│   ├── app/
│   │   ├── game/
│   │   │   ├── poker.py            # Core poker game engine
│   │   │   ├── analytics.py       # Session stats tracking
│   │   │   └── hardcode_ai/        # AI decision making
│   │   │       ├── ai_bladework_v2.py    # Main AI (most advanced)
│   │   │       ├── ai_gto_enhanced.py    # GTO-based AI
│   │   │       ├── postflop_strategy.py  # Advanced postflop logic
│   │   │       ├── preflop_charts.py     # Starting hand ranges
│   │   │       └── poker_charts/         # Preflop strategy charts
│   │   ├── services/
│   │   │   ├── game_service.py     # Game state management
│   │   │   └── websocket_service.py # WebSocket event handling
│   │   └── routes.py               # API endpoints
│   └── requirements.txt            # Python dependencies
│
└── start-dev.sh                    # Development startup script
```

## AI Logic

The main AI (`ai_bladework_v2.py`) is where most of the magic happens. It's built around several key concepts:

- **Hand strength evaluation** using Monte Carlo simulations
- **Opponent modeling** that tracks your VPIP, aggression, and betting patterns
- **Betting line analysis** that remembers how you've been playing each street
- **Dynamic bet sizing** with variety from 25% pot up to 150% pot overbets
- **Bluff/value balance** so it's not exploitable by always betting strong hands

The AI gets more challenging the longer you play against it because it builds a profile of your playing style. It's definitely beaten me more times than I'd like to admit.

## Why I Built This

For fun 
lol

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
- Showdown determines winner if both players remain

## AI Strategy

The AI considers:
- Current hand strength using poker hand rankings
- Pot odds for calling decisions
- Different strategies for preflop vs postflop play
- Position and betting action when making decisions

## Development

To run both servers with one command from root directory:
```bash
./start-dev.sh
```

Start CFR AI virtual environment: source server/app/game/cfr_ai/cfr_venv/bin/activate

## Future Plans

- Support for 6-player games
- Finish CFR AI
- Tournament mode for human and AI with increasing blinds
- Saving game stats into a database
