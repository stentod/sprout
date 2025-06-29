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

- **Backend:** Python (Flask), SQLite
- **Frontend:** HTML, CSS, Vanilla JavaScript
- **Styling:** Shoelace Web Components (Dark Mode

## Project Structure

```
Sprout/
├── backend/
│   ├── app.py
│   ├── db.sqlite3
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── history.html
│   ├── main.js
│   ├── history.js
│   ├── style.css
│   └── image.png
├── start.sh
└── README.md
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