# PostgreSQL Setup for Sprout Budget Tracker

## Prerequisites

1. **Install PostgreSQL 15**:
   ```bash
   brew install postgresql@15
   ```

2. **Start PostgreSQL service**:
   ```bash
   brew services start postgresql@15
   ```

## Database Setup

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Create .env file** (copy and customize):
   ```bash
   # Create .env file in backend/ directory
   echo "DATABASE_URL=postgresql://localhost/sprout_budget" > .env
   ```

3. **Initialize database**:
   ```bash
   python setup_db.py
   ```

## Manual Database Setup (Alternative)

If the setup script doesn't work, you can create the database manually:

```bash
# Create database
createdb sprout_budget

# Create tables
psql sprout_budget -f schema_postgres.sql
```

## Environment Variables

The following environment variables are required:

- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql://localhost/sprout_budget`)
- `DB_USER`: PostgreSQL username (optional, defaults to system user)
- `DB_PASSWORD`: PostgreSQL password (optional, only if using password auth)

## Deployment Ready

Your app is now configured for PostgreSQL and ready for deployment platforms like:
- Heroku
- Railway
- DigitalOcean App Platform
- AWS Elastic Beanstalk

Most platforms will automatically provide a `DATABASE_URL` environment variable. 