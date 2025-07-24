# Sprout Budget Tracker

A minimalist personal budget tracker designed to help you stay financially aware on a daily basis. Built with Flask and PostgreSQL on the backend and vanilla JavaScript on the frontend, Sprout offers a clean interface and visual feedback to help users build better spending habits.

![Sprout Budget Tracker](frontend/image.png)

## Features

- 💰 **Daily Budget Tracking** - Set and track your daily spending limit
- 🌱 **Visual Plant Status** - Watch your financial plant grow or wilt based on spending habits
- 📱 **Responsive Design** - Works seamlessly on desktop and mobile devices
- 📈 **7-Day History** - Review your spending patterns over the last week
- 🌙 **Automatic Reset** - Budget resets daily at midnight
- 🎨 **Dark Mode Support** - Easy on the eyes for daily use
- 🔒 **Production Ready** - Containerized with Docker for deployment

## Tech Stack

### Backend
- **Python 3.x** - Core backend language
- **Flask** - Lightweight web framework
- **PostgreSQL** - Production database
- **SQLite** - Development database
- **Gunicorn** - WSGI HTTP Server

### Frontend
- **HTML5/CSS3** - Modern web standards
- **Vanilla JavaScript** - No framework dependencies
- **Responsive Design** - Mobile-first approach

### DevOps
- **Docker** - Containerization
- **Nginx** - Production web server
- **Render** - Cloud deployment platform

## Docker Quickstart

### Production Build & Run

Build and run the production version using Docker:

```bash
# Clone the repository
git clone https://github.com/yourusername/sprout-budget-tracker.git
cd sprout-budget-tracker

# Build the Docker image (creates production container with Nginx + Flask)
docker build -t sprout-budget-tracker .

# Run the production container
docker run -p 10000:10000 \
  -e FLASK_ENV=production \
  -e DAILY_BUDGET=30.0 \
  sprout-budget-tracker
```

**🌐 Access your app at: http://localhost:10000**

### How It Works
- **Port 10000** (External): Nginx serves frontend files and handles incoming requests
- **Port 5000** (Internal): Flask backend API running with Gunicorn WSGI server
- **Request Flow**: Browser → Nginx (10000) → Flask API (5000) → PostgreSQL

> **Note:** This Docker setup mirrors the exact production environment used on Render.

## Want to Deploy Online?

**Ready to deploy to production?** This app is designed for **Render** deployment using Docker containers.

👉 **See [DEPLOYMENT.md](DEPLOYMENT.md) for complete step-by-step instructions including:**
- Local Docker testing
- Render account setup
- PostgreSQL database creation
- Environment variable configuration
- Health monitoring and troubleshooting

## Local Development Setup

### Quick Start (Recommended)

For development with auto-reload and debugging:

```bash
# Clone and navigate to project
git clone https://github.com/yourusername/sprout-budget-tracker.git
cd sprout-budget-tracker

# Start development servers (uses ./start.sh)
./start.sh
```

**🌐 Access your app at: http://localhost:8080**

### Development vs Production

| Aspect | Development (`./start.sh`) | Production (Docker) |
|--------|---------------------------|-------------------|
| **Frontend** | live-server on port 8080 | Nginx on port 10000 |
| **Backend** | Flask dev server on port 5001 | Gunicorn + Flask on port 5000 |
| **Database** | SQLite (local file) | PostgreSQL (Render managed) |
| **Environment** | `.env` file or local vars | Render environment variables |
| **Auto-reload** | ✅ Yes (both frontend/backend) | ❌ No (production stability) |
| **Debug Mode** | ✅ Yes (detailed errors) | ❌ No (security) |

### Manual Development Setup

If you prefer not to use `./start.sh`:

#### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py  # Starts on http://localhost:5001
```

#### Frontend Setup
```bash
npm install -g live-server
cd frontend
live-server --port=8080  # Starts on http://localhost:8080
```

## Project Structure

```
Sprout/
├── backend/
│   ├── app.py                   # Main Flask application
│   ├── setup_db.py             # Database setup script
│   ├── schema_postgres.sql     # PostgreSQL schema
│   ├── requirements.txt        # Python dependencies
│   ├── POSTGRESQL_SETUP.md     # Database setup guide
│   └── db_init.sql             # SQLite schema (development)
├── frontend/
│   ├── index.html              # Main page
│   ├── history.html            # History page
│   ├── main.js                 # Main app logic
│   ├── history.js              # History page logic
│   ├── style.css              # Styling
│   ├── logo.svg               # App logo
│   └── image.png              # Screenshot for README
├── Dockerfile                  # Docker configuration
├── nginx.conf                 # Nginx configuration
├── start.sh                   # Development server script
├── render.yaml                # Render deployment config
├── gunicorn.conf.py           # Gunicorn WSGI config
├── DEPLOYMENT.md              # Production deployment guide
└── README.md                  # This file
```

## Environment Variables

### Development (Local)
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DAILY_BUDGET` | Daily budget amount | `30.0` | No |
| `PORT` | Flask server port | `5001` | No |
| `FLASK_ENV` | Flask environment | `development` | No |
| `FLASK_DEBUG` | Enable debug mode | `true` | No |

### Production (Render)
| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@host:5432/db` | ✅ Yes |
| `FLASK_ENV` | Flask environment | `production` | ✅ Yes |
| `DAILY_BUDGET` | Daily budget amount | `30.0` | No |
| `PORT` | External port | `10000` | No (Render sets this) |

## Testing Your Setup

### Test Development Environment
```bash
# Start development servers
./start.sh

# Test backend API (in a new terminal)
curl http://localhost:5001/health
# Expected: {"status":"ok"}

# Open frontend
open http://localhost:8080
```

### Test Production Docker Build
```bash
# Build and test production container
docker build -t sprout-test .
docker run -d -p 10000:10000 -e FLASK_ENV=production --name sprout-container sprout-test

# Test production health
curl http://localhost:10000/health
# Expected: {"status":"ok"}

# Test frontend
open http://localhost:10000

# Cleanup
docker stop sprout-container && docker rm sprout-container
```

## Usage

1. **Set Your Budget**: Enter your daily spending limit at the top of the page
2. **Track Expenses**: Add expenses throughout the day with optional descriptions
3. **Monitor Progress**: Watch your plant visual change based on spending habits
4. **Review History**: Use the history page to analyze your last 7 days
5. **Daily Reset**: Your budget automatically resets at midnight

### Development Features
- **Day Simulation**: Use `?dayOffset=N` in URL to test different days
- **Auto-reload**: Both frontend and backend restart on file changes
- **Debug Mode**: Detailed error messages and stack traces
- **Local Database**: SQLite file for easy development testing

## About This Project

This is a **personal portfolio project** demonstrating modern web development practices including containerization, cloud deployment, and responsive design.

### For Learning & Reference
- 📚 **Educational Use**: Feel free to study the code and architecture
- 🔧 **Personal Use**: Clone and modify for your own budget tracking needs
- 💡 **Learning Resource**: Demonstrates Flask, Docker, PostgreSQL, and Render deployment

### Reporting Issues
If you encounter bugs or have suggestions:
- 🐛 Open an issue on GitHub with details
- 💬 Describe the problem and steps to reproduce
- 🔍 Include browser/environment information

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for better financial awareness**
