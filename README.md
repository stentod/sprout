# Sprout Budget Tracker

A personal budget tracker designed to help you stay financially aware on a daily basis. Built with Flask and PostgreSQL on the backend and vanilla JavaScript on the frontend, Sprout offers a clean interface and visual feedback to help users build better spending habits.

![Sprout Budget Tracker](frontend/image.png)

## Features

### Core Budget Management
- 💰 **Daily Budget Tracking** - Set and track your daily spending limit
- 🔄 **Budget Rollover** - Unspent money rolls over to the next day (optional)
- 📊 **Category-Based Budgeting** - Set individual budgets for different spending categories
- 🎯 **Visual Progress Tracking** - Real-time budget status with intuitive gauges

### User Experience
- 🌱 **Visual Plant Status** - Watch your financial plant grow or wilt based on spending habits
- 📱 **Responsive Design** - Works seamlessly on desktop and mobile devices
- 🌙 **Dark Mode Support** - Easy on the eyes for daily use
- ⚡ **Real-time Updates** - Instant feedback on spending and budget changes

### Authentication & Security
- 🔐 **User Authentication** - Secure email/password login system
- 📧 **Password Reset** - Email-based password recovery
- 🛡️ **Session Management** - Secure session handling with configurable timeouts
- 🔒 **Production Security** - Security headers and best practices

### Analytics & Insights
- 📈 **Spending Analytics** - Comprehensive charts and visualizations
- 📅 **7-Day History** - Review your spending patterns over the last week
- 🔥 **Spending Heatmap** - Visual calendar showing daily spending intensity
- 📊 **Category Breakdown** - See where your money goes by category
- 📉 **Trend Analysis** - Track spending trends over time (7, 14, 30, 90 days)

### Advanced Features
- 🏷️ **Expense Categories** - Organize expenses with customizable categories
- 📝 **Expense Descriptions** - Add detailed notes to your transactions
- ⏰ **Automatic Daily Reset** - Budget resets daily at midnight
- 🎮 **Day Simulation** - Test different scenarios with date simulation
- ⚙️ **User Preferences** - Customize daily limits, category requirements, and rollover settings

### Technical Features
- 🐳 **Production Ready** - Containerized with Docker for deployment
- 🧪 **Comprehensive Testing** - Full test suite with coverage reporting
- 📊 **Performance Optimized** - Database indexing and query optimization
- 🔄 **API-First Design** - RESTful API for all functionality
- 📱 **Progressive Web App** - Works offline and can be installed on devices

## Tech Stack

### Backend
- **Python 3.x** - Core backend language
- **Flask** - Lightweight web framework
- **PostgreSQL** - Production/Development database
- **Gunicorn** - WSGI HTTP Server

### Frontend
- **HTML5/CSS3** - Modern web standards
- **Vanilla JavaScript** - No framework dependencies
- **Responsive Design** - Mobile-first approach

### DevOps
- **Docker** - Containerization
- **Nginx** - Production web server
- **Render** - Cloud deployment platform

## Prerequisites

- **Docker** (for production builds)
- **Python 3.x** (for development)
- **Node.js** and **npm** (for frontend development server)

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/sprout-budget-tracker.git
cd sprout-budget-tracker
```

### 2. Development Setup

#### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Frontend Setup
```bash
npm install -g live-server
```

### 3. Environment Variables (Optional)

The application works with default values, but you can customize behavior with environment variables.

#### For Development (Local)

Create a `.env` file in the `backend/` directory to customize settings:

```bash
cd backend
cat > .env << EOF
DAILY_BUDGET=25.0
PORT=5001
FLASK_ENV=development
FLASK_DEBUG=true
DATABASE_URL=postgresql://localhost/sprout_budget
EOF
```

**Available Development Variables:**
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DAILY_BUDGET` | Daily budget amount | `30.0` | No |
| `PORT` | Flask server port | `5001` | No |
| `FLASK_ENV` | Flask environment | `development` | No |
| `FLASK_DEBUG` | Enable debug mode | `true` | No |
| `DATABASE_URL` | Database connection | Uses SQLite by default | No |

> **Note:** If no `.env` file exists, the app uses sensible defaults and SQLite for the database.

#### For Production (Render Platform)

Set these in your Render service's Environment Variables section:

**Required Production Variables:**
| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@host:5432/db` | ✅ Yes |
| `FLASK_ENV` | Flask environment | `production` | ✅ Yes |
| `DAILY_BUDGET` | Daily budget amount | `30.0` | No |
| `PORT` | External port | `10000` | No (Render sets this) |

**How to set in Render:**
1. Go to your Render service dashboard
2. Click "Environment" tab
3. Add the variables above
4. Deploy your service

## How to Build

### Development Build

No build step required for development. The application runs directly from source files.

### Production Build

Build the Docker image for production deployment:

```bash
docker build -t sprout-budget-tracker .
```

This creates a production container with Nginx + Flask using Gunicorn WSGI server.

## How to Run

### Development Mode (Recommended for Local Development)

#### Quick Start
```bash
./start.sh
```

**🌐 Access your app at: http://localhost:8080**

#### Manual Start
```bash
# Terminal 1: Start backend
cd backend
source venv/bin/activate
python app.py  # Starts on http://localhost:5001

# Terminal 2: Start frontend  
cd frontend
live-server --port=8080  # Starts on http://localhost:8080
```

### Production Mode (Docker)

```bash
docker run -p 10000:10000 \
  -e FLASK_ENV=production \
  -e DAILY_BUDGET=30.0 \
  sprout-budget-tracker
```

**🌐 Access your app at: http://localhost:10000**

### Development vs Production

| Aspect | Development (`./start.sh`) | Production (Docker) |
|--------|---------------------------|-------------------|
| **Frontend** | live-server on port 8080 | Nginx on port 10000 |
| **Backend** | Flask dev server on port 5001 | Gunicorn + Flask on port 5000 |
| **Database** | SQLite (local file) | PostgreSQL (Render managed) |
| **Environment** | `.env` file or local vars | Render environment variables |
| **Auto-reload** | ✅ Yes (both frontend/backend) | ❌ No (production stability) |
| **Debug Mode** | ✅ Yes (detailed errors) | ❌ No (security) |

## How to Test

### Test Development Environment

#### 1. Start the Development Servers
```bash
./start.sh
```

#### 2. Test Backend API
```bash
curl http://localhost:5001/health
```
Expected response:
```json
{"status":"ok"}
```

#### 3. Test Frontend
Open your browser to: http://localhost:8080

#### 4. Test API Endpoints
```bash
# Get current budget status
curl http://localhost:5001/api/budget

# Add an expense
curl -X POST http://localhost:5001/api/expenses \
  -H "Content-Type: application/json" \
  -d '{"amount": 15.50, "description": "Lunch"}'

# Get expense history
curl http://localhost:5001/api/expenses/history
```

### Test Production Environment

#### 1. Build and Run Production Container
```bash
docker build -t sprout-test .
docker run -d -p 10000:10000 -e FLASK_ENV=production --name sprout-container sprout-test
```

#### 2. Test Production Health
```bash
curl http://localhost:10000/health
```
Expected response:
```json
{"status":"ok"}
```

#### 3. Test Frontend
Open your browser to: http://localhost:10000

#### 4. Test Production API
```bash
# Test budget endpoint through Nginx
curl http://localhost:10000/api/budget

# Test adding expenses
curl -X POST http://localhost:10000/api/expenses \
  -H "Content-Type: application/json" \
  -d '{"amount": 25.00, "description": "Dinner"}'
```

#### 5. Cleanup Test Container
```bash
docker stop sprout-container && docker rm sprout-container
```

### How It Works (Architecture)
- **Port 10000** (External): Nginx serves frontend files and handles incoming requests
- **Port 5000** (Internal): Flask backend API running with Gunicorn WSGI server
- **Request Flow**: Browser → Nginx (10000) → Flask API (5000) → PostgreSQL

## Project Structure

```
Sprout/
├── backend/
│   ├── main.py                 # Main Flask application with blueprints
│   ├── app.py                  # Development entry point
│   ├── auth.py                 # Authentication routes and logic
│   ├── expenses.py             # Expense management and analytics
│   ├── categories.py           # Category management
│   ├── preferences.py          # User preferences and settings
│   ├── rollover_api.py         # Budget rollover functionality
│   ├── rollover_service.py     # Rollover business logic
│   ├── utils.py                # Shared utilities and helpers
│   ├── setup_db.py             # Database setup script
│   ├── schema_postgres.sql     # PostgreSQL schema
│   ├── requirements.txt        # Python dependencies
│   ├── run_tests.py            # Test runner script
│   ├── pytest.ini             # Pytest configuration
│   ├── conftest.py             # Test configuration
│   ├── tests/                  # Comprehensive test suite
│   │   ├── test_auth.py        # Authentication tests
│   │   ├── test_expenses.py    # Expense management tests
│   │   ├── test_categories.py  # Category management tests
│   │   ├── test_preferences.py # User preferences tests
│   │   └── test_summary.py     # Summary and analytics tests
│   ├── POSTGRESQL_SETUP.md     # Database setup guide
│   ├── EMAIL_SETUP.md          # Email configuration guide
│   └── TESTING.md              # Testing documentation
├── frontend/
│   ├── index.html              # Main dashboard
│   ├── auth.html               # Authentication page
│   ├── history.html            # Spending history
│   ├── analytics.html          # Analytics dashboard
│   ├── budgets.html            # Budget management
│   ├── settings.html           # User settings
│   ├── reset-password.html     # Password reset page
│   ├── main.js                 # Main app logic
│   ├── auth.js                 # Authentication logic
│   ├── history.js              # History page logic
│   ├── analytics.js            # Analytics and charts
│   ├── budgets.js              # Budget management
│   ├── settings.js             # Settings management
│   ├── reset-password.js       # Password reset logic
│   ├── style.css               # Styling and themes
│   ├── logo.svg                # App logo
│   └── image.png               # Screenshot for README
├── Dockerfile                  # Docker configuration
├── nginx.conf                  # Nginx configuration
├── start.sh                    # Development server script
├── render.yaml                 # Render deployment config
├── gunicorn.conf.py            # Gunicorn WSGI config
├── DEPLOYMENT.md               # Production deployment guide
└── README.md                   # This file
```

## Usage

### Getting Started
1. **Create Account**: Sign up with your email address and secure password
2. **Set Your Budget**: Configure your daily spending limit in settings
3. **Enable Rollover** (Optional): Allow unspent money to carry over to the next day
4. **Customize Categories**: Set up spending categories with individual budgets

### Daily Usage
1. **Track Expenses**: Add expenses throughout the day with descriptions and categories
2. **Monitor Progress**: Watch your plant visual and budget gauge update in real-time
3. **Check Analytics**: View detailed spending patterns and trends
4. **Review History**: Analyze your spending over the last 7 days or longer periods

### Advanced Features
1. **Category Management**: Create custom categories and set individual budgets
2. **Analytics Dashboard**: View comprehensive charts, heatmaps, and spending breakdowns
3. **Settings Customization**: Adjust preferences, rollover settings, and category requirements
4. **Day Simulation**: Test different scenarios using the day simulation feature

### Development Features
- **Day Simulation**: Use `?dayOffset=N` in URL to test different days
- **Auto-reload**: Both frontend and backend restart on file changes
- **Debug Mode**: Detailed error messages and stack traces
- **Local Database**: SQLite file for easy development testing

## Deployment

**Want to Deploy Online?** This app is designed for **Render** deployment using Docker containers.

👉 **See [DEPLOYMENT.md](DEPLOYMENT.md) for complete step-by-step instructions including:**
- Local Docker testing
- Render account setup
- PostgreSQL database creation
- Environment variable configuration
- Health monitoring and troubleshooting

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
