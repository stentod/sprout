#!/bin/bash

# Sprout Budget Tracker Development Server
# This script starts both backend (Flask) and frontend (live-server) with auto-reload

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🌱 Starting Sprout Budget Tracker Development Environment${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install live-server if not present
install_live_server() {
    if ! command_exists live-server; then
        echo -e "${YELLOW}📦 Installing live-server...${NC}"
        if command_exists npm; then
            npm install -g live-server
        elif command_exists yarn; then
            yarn global add live-server
        else
            echo -e "${RED}❌ Error: npm or yarn is required to install live-server${NC}"
            echo -e "${YELLOW}Please install Node.js and npm first:${NC}"
            echo -e "  macOS: brew install node"
            echo -e "  Ubuntu: sudo apt install nodejs npm"
            exit 1
        fi
    fi
}

# Function to check Python dependencies
check_python_deps() {
    echo -e "${BLUE}🔍 Checking Python dependencies...${NC}"
    cd backend
    if [ ! -f "requirements.txt" ]; then
        echo -e "${RED}❌ requirements.txt not found in backend/${NC}"
        exit 1
    fi
    
    # Check if Flask is installed in virtual environment
    if ! python -c "import flask" 2>/dev/null; then
        echo -e "${YELLOW}📦 Installing Python dependencies in virtual environment...${NC}"
        pip install -r requirements.txt
    fi
    
    # Also check for psycopg2 specifically
    if ! python -c "import psycopg2" 2>/dev/null; then
        echo -e "${YELLOW}📦 Installing/reinstalling psycopg2...${NC}"
        pip install -r requirements.txt
    fi
    cd ..
}

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down servers...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up signal handlers for cleanup
trap cleanup SIGINT SIGTERM

# Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

source .venv/bin/activate

# Check and install dependencies
install_live_server
check_python_deps

echo -e "${BLUE}🚀 Starting development servers...${NC}"

# Start Flask backend with auto-reload
echo -e "${GREEN}🔧 Starting Flask backend on http://localhost:5001${NC}"
cd backend
export FLASK_ENV=development
export FLASK_DEBUG=1
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"
export DATABASE_URL='postgresql://dstent@localhost/sprout_budget'
python app.py &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 2

# Start frontend live-server
echo -e "${GREEN}🌐 Starting frontend live-server on http://localhost:8080${NC}"
cd frontend
live-server --port=8080 --host=localhost --no-browser --quiet &
FRONTEND_PID=$!
cd ..

echo -e "${GREEN}✅ Development environment is ready!${NC}"
echo -e "${BLUE}📱 Frontend: http://localhost:8080${NC}"
echo -e "${BLUE}🔧 Backend API: http://localhost:5001${NC}"
echo -e "${YELLOW}💡 Both servers will auto-reload on file changes${NC}"
echo -e "${YELLOW}🛑 Press Ctrl+C to stop both servers${NC}"

# Wait for background processes
wait $BACKEND_PID $FRONTEND_PID 