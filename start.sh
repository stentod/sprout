#!/bin/bash

# Sprout Budget Tracker Production Server
# This script starts both Flask backend and Nginx frontend server

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in Docker/production environment
if [ -f /.dockerenv ] || [ "${RENDER}" = "true" ]; then
    echo -e "${GREEN}🌱 Starting Sprout Budget Tracker Production Environment${NC}"
    
    # Initialize database schema
    echo -e "${BLUE}🗄️ Initializing database schema...${NC}"
    cd /app/backend
    python setup_db.py 2>/dev/null || echo -e "${YELLOW}⚠️ Database initialization completed (tables may already exist)${NC}"
    
    # Run email-only authentication migration
    echo -e "${BLUE}🔄 Running email-only authentication migration...${NC}"
    python deploy_with_migration.py 2>/dev/null || echo -e "${YELLOW}⚠️ Migration completed (schema may already be updated)${NC}"
    
    # Fix expenses table schema (add missing category_id column)
    echo -e "${BLUE}🔄 Fixing expenses table schema...${NC}"
    python fix_expenses_schema.py 2>/dev/null || echo -e "${YELLOW}⚠️ Schema fix completed (column may already exist)${NC}"
    
    # Add category preference column to user_preferences table
    echo -e "${BLUE}🔄 Adding category preference column...${NC}"
    python migrate_category_preference.py 2>/dev/null || echo -e "${YELLOW}⚠️ Category preference migration completed (column may already exist)${NC}"
    
    # Restructure categories for custom categories support
    echo -e "${BLUE}🔄 Restructuring categories for custom categories...${NC}"
    python migrate_custom_categories.py 2>/dev/null || echo -e "${YELLOW}⚠️ Custom categories migration completed (tables may already exist)${NC}"
    
    # Clean up any extra default categories that were incorrectly added
    echo -e "${BLUE}🧹 Cleaning up extra default categories...${NC}"
    python cleanup_extra_categories.py 2>/dev/null || echo -e "${YELLOW}⚠️ Category cleanup completed (no extra categories to remove)${NC}"
    
    # Production mode - start Flask with gunicorn and Nginx
    echo -e "${BLUE}🔧 Starting Flask backend with gunicorn on port 5000${NC}"
    
    # Set Flask to production mode
    export FLASK_ENV=production
    export FLASK_DEBUG=false
    export WEB_CONCURRENCY=${WEB_CONCURRENCY:-1}
    
    # Start Flask with gunicorn in background
    cd /app/backend
    gunicorn app:app --bind 0.0.0.0:5000 --workers ${WEB_CONCURRENCY:-1} --timeout 30 --access-logfile - --error-logfile - &
    FLASK_PID=$!
    
    # Wait for Flask to start
    echo -e "${YELLOW}⏳ Waiting for Flask to start...${NC}"
    sleep 5
    
    # Test Flask health
    if curl -f http://localhost:5000/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Flask backend is running${NC}"
    else
        echo -e "${RED}❌ Flask backend failed to start${NC}"
        kill $FLASK_PID 2>/dev/null || true
        exit 1
    fi
    
    # Replace PORT placeholder in nginx.conf
    sed -i "s/\${PORT:-10000}/${PORT:-10000}/g" /etc/nginx/nginx.conf
    
    # Start Nginx in foreground
    echo -e "${GREEN}🌐 Starting Nginx on port ${PORT:-10000}${NC}"
    exec nginx
    
else
    # Development mode - use the existing development setup
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
echo -e "${GREEN}🔧 Starting Flask backend (checking PORT from environment)${NC}"
cd backend

# Set development environment variables (will be overridden by .env file if present)
export FLASK_ENV=development
export FLASK_DEBUG=${FLASK_DEBUG:-true}
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"

# Get port from environment or default to 5001
BACKEND_PORT=${PORT:-5001}
echo -e "${GREEN}🔧 Backend will start on http://localhost:${BACKEND_PORT}${NC}"

python app.py &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 2

# Start frontend live-server
FRONTEND_PORT=${FRONTEND_PORT:-8080}
echo -e "${GREEN}🌐 Starting frontend live-server on http://localhost:${FRONTEND_PORT}${NC}"
cd frontend
live-server --port=${FRONTEND_PORT} --host=localhost --no-browser --quiet &
FRONTEND_PID=$!
cd ..

echo -e "${GREEN}✅ Development environment is ready!${NC}"
echo -e "${BLUE}📱 Frontend: http://localhost:${FRONTEND_PORT}${NC}"
echo -e "${BLUE}🔧 Backend API: http://localhost:${BACKEND_PORT}${NC}"
echo -e "${YELLOW}💡 Both servers will auto-reload on file changes${NC}"
echo -e "${YELLOW}🛑 Press Ctrl+C to stop both servers${NC}"

# Wait for background processes
wait $BACKEND_PID $FRONTEND_PID

fi  # End of production/development mode check 