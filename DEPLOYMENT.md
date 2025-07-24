# Deployment Guide

This guide explains how to deploy Sprout Budget Tracker to **Render** using Docker. The app runs as a single container with Nginx serving the frontend and proxying API requests to Flask.

## Architecture

```
Internet → Render → Nginx (Port 10000) → Flask Backend (Port 5000)
                         ↓
                    Static Files
                         ↓
                  PostgreSQL Database
```

## Prerequisites

- GitHub repository with your code
- [Render account](https://render.com) (free tier available)
- Docker installed locally (for testing)

## Environment Variables

Your app needs these environment variables in production:

| Variable | Description | Example Value | Required |
|----------|-------------|---------------|----------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@host:5432/db` | ✅ Yes |
| `FLASK_ENV` | Flask environment | `production` | ✅ Yes |
| `DAILY_BUDGET` | Default budget amount | `30.0` | ❌ No |
| `PORT` | External port | `10000` | ❌ No (Render sets this) |

## Local Testing

Before deploying, test the Docker setup locally:

### 1. Build the Docker Image

```bash
# Build the production container
docker build -t sprout-budget-tracker .
```

### 2. Run the Container

```bash
# Run with environment variables
docker run -p 10000:10000 \
  -e FLASK_ENV=production \
  -e DAILY_BUDGET=30.0 \
  sprout-budget-tracker
```

### 3. Test the Application

```bash
# Check health endpoint
curl http://localhost:10000/health

# Should return: {"status":"ok"}
```

**🌐 Open http://localhost:10000 in your browser to test the app**

### 4. Cleanup

```bash
# Stop and remove the container
docker stop $(docker ps -q --filter ancestor=sprout-budget-tracker)
docker rmi sprout-budget-tracker
```

## Deploy to Render

### Step 1: Push Code to GitHub

```bash
git add .
git commit -m "Deploy to Render"
git push origin main
```

### Step 2: Create PostgreSQL Database

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New"** → **"PostgreSQL"**
3. Choose a name (e.g., `sprout-database`)
4. Select **Free** plan
5. Click **"Create Database"**
6. **Copy the DATABASE_URL** (you'll need this in Step 4)

### Step 3: Create Web Service

1. Click **"New"** → **"Web Service"**
2. Connect your **GitHub repository**
3. Configure the service:
   - **Name**: `sprout-budget-tracker`
   - **Runtime**: **Docker**
   - **Plan**: **Free** (or higher)

### Step 4: Set Environment Variables

In the **Environment** section, add:

```
DATABASE_URL=<paste the URL from Step 2>
FLASK_ENV=production
DAILY_BUDGET=30.0
```

### Step 5: Deploy

1. Click **"Create Web Service"**
2. Render will automatically build and deploy your app
3. Your app will be available at: `https://your-service-name.onrender.com`

## Health Monitoring

Your app includes automatic health checks:

- **Health Endpoint**: `GET /health` returns `{"status": "ok"}`
- **Docker Health Check**: Runs every 30 seconds
- **Render Monitoring**: Automatic restart if health checks fail

## Troubleshooting

### Container Won't Start

```bash
# Test locally first
docker build -t debug-app .
docker run -it debug-app /bin/sh

# Check logs
docker logs <container-name>
```

### Database Connection Issues

1. **Verify DATABASE_URL** is set correctly in Render
2. **Check database status** in Render dashboard
3. **Restart the service** if needed

### App Shows 503 Error

This usually means the database isn't connected:

1. Check that PostgreSQL service is running
2. Verify the DATABASE_URL environment variable
3. Check logs in Render dashboard

### Common Issues

| Problem | Solution |
|---------|----------|
| Build fails | Check Dockerfile syntax and requirements.txt |
| Health check fails | Verify Flask starts on port 5000 internally |
| Static files not loading | Ensure files are in `frontend/` directory |
| Database errors | Check PostgreSQL service status and DATABASE_URL |

## Updating Your Deployment

To deploy changes:

```bash
git add .
git commit -m "Update application"
git push origin main
```

Render will automatically rebuild and redeploy your app.

## Scaling and Performance

### Free Tier Limitations
- **Sleep after 15 minutes** of inactivity
- **Limited CPU and memory**
- **Shared resources**

### Upgrading
- **Starter Plan**: Always-on service with more resources
- **Pro Plan**: Auto-scaling and custom domains

## Monitoring Your App

1. **Render Dashboard**: View logs, metrics, and deployments
2. **Health Endpoint**: Monitor `/health` for uptime
3. **Database Metrics**: Track PostgreSQL performance

---

## Summary

Your Sprout Budget Tracker is now deployed! The key points:

- ✅ **Docker container** runs Nginx + Flask
- ✅ **PostgreSQL database** for data persistence  
- ✅ **Automatic health checks** for reliability
- ✅ **Environment-based configuration** for flexibility
- ✅ **Simple updates** via git push

**Need help?** Check the [Render Documentation](https://render.com/docs) or review the troubleshooting section above. 