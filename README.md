# Sprout Budget Tracker

Sprout is a minimalist personal budget tracker designed to help you stay financially aware on a daily basis. Built with Flask and SQLite on the backend and styled with Shoelace Web Components on the frontend, Sprout offers a clean interface and visual feedback to help users build better spending habits.

## Getting Started

Once the app is running:

1. Open `index.html` in your browser
2. Set your daily budget (shown at the top)
3. Add expenses as they occur throughout the day
4. Watch your plant grow (or wilt) based on spending habits!
5. Use the history page to review your last 7 days

The app resets your available budget every midnight.

## Tech Stack

- **Backend:** Python (Flask), PostgreSQL (production) / SQLite (development)
- **Frontend:** HTML, CSS, Vanilla JavaScript
- **Styling:** Custom CSS with Dark Mode
- **Deployment:** Ready for Render, Heroku, or similar platforms

## Project Structure

```
Sprout/
├── backend/
│   ├── app.py                   # Main Flask application
│   ├── setup_db.py             # Database setup script
│   ├── schema_postgres.sql     # PostgreSQL schema
│   ├── requirements.txt        # Python dependencies
│   └── POSTGRESQL_SETUP.md     # Database setup guide
├── frontend/
│   ├── index.html              # Main page
│   ├── history.html            # History page
│   ├── main.js                 # Main app logic
│   ├── history.js              # History page logic
│   ├── style.css              # Styling
│   └── logo.svg               # App logo
├── start.sh                    # Development server script
├── .env.example               # Environment variables template
└── README.md                  # This file
```

## Quick Start (Recommended)

### Prerequisites
- Python 3.x
- Node.js and npm (for live-server)

### One-Command Development Setup
```sh
./start.sh
```

This script will:
- ✅ Check and install all dependencies automatically
- 🔧 Start Flask backend on http://localhost:5000 (with auto-reload)
- 🌐 Start frontend live-server on http://localhost:8080 (with auto-reload)
- 🔄 Auto-restart both servers when files change
- 🛑 Clean shutdown with Ctrl+C

**Access your app at: http://localhost:8080**

---

## Manual Setup (Alternative)

### Backend
1. Navigate to the `backend` folder:
   ```sh
   cd backend
   ```
2. (Optional) Create a virtual environment:
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Run the Flask app:
   ```sh
   python app.py
   ```

### Frontend
1. Install live-server globally:
   ```sh
   npm install -g live-server
   ```
2. Navigate to frontend folder and start:
   ```sh
   cd frontend
   live-server --port=8080
   ```

---

## Features
- 💰 Daily balance display ($30 budget)
- ➕ Add expense (amount + optional description)
- 🔄 Real-time subtraction from balance
- 🌱 Plant graphic based on 7-day average (🌳🌱🥀☠️)
- 📈 30-day projection
- 📜 7-day history view
- 🌙 Daily reset at midnight
- 🧪 Dev tool: `?dayOffset=N` to simulate other days

---

## Development
- Backend auto-reloads on Python file changes
- Frontend auto-reloads on HTML/JS/CSS changes
- Both servers run concurrently with `./start.sh`

---

## License
MIT
## Environment Variables

The application supports the following environment variables:

- `DATABASE_URL` - PostgreSQL connection string (required for production)
- `DAILY_BUDGET` - Daily budget amount (default: 30.0)
- `PORT` - Server port (default: 5001)
- `FLASK_DEBUG` - Enable debug mode (default: false)
- `DB_HOST` - Database host (default: localhost)
- `DB_USER` - Database username (default: dstent)
- `DB_PASSWORD` - Database password (default: empty)

## Local Development

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your local configuration

3. Run the development server:
   ```bash
   ./start.sh
   ```

## Production Deployment

### Deploy to Render

1. Fork this repository
2. Create a new Web Service on Render
3. Connect your forked repository
4. Set environment variables:
   - `DAILY_BUDGET` (e.g., "30.0")
   - Any other custom configuration
5. Render will automatically provide `DATABASE_URL` for PostgreSQL

### Deploy to Heroku

1. Install Heroku CLI and create an app
2. Add PostgreSQL addon:
   ```bash
   heroku addons:create heroku-postgresql:hobby-dev
   ```
3. Set environment variables:
   ```bash
   heroku config:set DAILY_BUDGET=30.0
   ```
4. Deploy:
   ```bash
   git push heroku main
   ```

### Deploy to Railway

1. Connect your GitHub repository
2. Railway will auto-detect the Flask app
3. Add PostgreSQL database
4. Set environment variables in Railway dashboard

## Database Setup

The application will automatically create the necessary database tables on first run. For manual setup:

```bash
python backend/setup_db.py
```

## Features

- 📊 **Daily Budget Tracking** - Set and track your daily spending limit
- 🌱 **Visual Plant Status** - Watch your financial plant grow or wilt based on spending habits
- 📱 **Responsive Design** - Works on desktop and mobile devices
- 📈 **7-Day History** - Review your spending patterns over the last week
- 🔒 **Production Ready** - Environment-based configuration for easy deployment
- 🎨 **Dark Mode** - Easy on the eyes for daily use

## License

MIT License - feel free to use this project for your own budgeting needs!
