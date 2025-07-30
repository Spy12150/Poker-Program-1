#!/bin/bash

# Poker App Development Startup Script

echo "Starting Poker App Development Environment..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python3 is required but not installed."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Node.js is required but not installed."
    exit 1
fi

# Function to kill background processes on exit
cleanup() {
    echo "Cleaning up processes..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}
trap cleanup EXIT

# Start backend server
echo "Starting Flask backend server..."
cd server
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1
python run.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend server
echo "Starting React frontend server..."
cd client
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo "Both servers are starting up!"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:5001"
echo "Ready to play poker!"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for user to stop
wait
