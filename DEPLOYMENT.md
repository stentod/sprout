# Deployment Guide - Sprout Budget Tracker

This guide covers deploying your Sprout Budget Tracker as a single Docker container on Render, Heroku, or other cloud platforms.

## 📋 Overview

The deployment setup includes:
- **Docker**: Single container running both Flask backend and Nginx frontend
- **Nginx**: Serves static files and proxies API requests to Flask
- **Flask**: Runs on port 5000 internally
- **PostgreSQL**: Database (provided by cloud platform)

## 🏗️ Architecture

```
Internet → Render (Port 10000) → Nginx → Flask (Port 5000)
                                    ↓
                               Static Files (Frontend)
```

## 📁 Files Created

- `Dockerfile` - Multi-stage build with Python and Nginx
- `nginx.conf` - Nginx configuration for serving frontend + API proxy
- `start.sh` - Modified to detect production vs development
- `render.yaml` - Render deployment configuration
- `docker-test.sh` - Local testing script
- `.dockerignore` - Optimize Docker build

## 🚀 Deploy to Render

### Option 1: Using render.yaml (Recommended)

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Add Docker deployment setup"
   git push origin main
   ```

2. **Connect to Render**:
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect `render.yaml`

3. **Environment Variables** (automatically set by render.yaml):
   - `DAILY_BUDGET=30.0`
   - `FLASK_ENV=production`
   - `DATABASE_URL` (provided by PostgreSQL service)

### Option 2: Manual Setup

1. **Create Web Service**:
   - Go to Render Dashboard
   - Click "New" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**:
   - **Runtime**: Docker
   - **Dockerfile Path**: `./Dockerfile`
   - **Port**: Leave default (Render sets PORT env var)

3. **Add PostgreSQL Database**:
   - Click "New" → "PostgreSQL"
   - Choose free plan
   - Note the database URL

4. **Environment Variables**:
   - `DAILY_BUDGET=30.0`
   - `FLASK_ENV=production`
   - `DATABASE_URL` (copy from PostgreSQL service)

## 🐳 Local Testing

Test the Docker setup locally before deploying:

```bash
# Run the test script
./docker-test.sh

# Or manually:
docker build -t sprout-budget-tracker .
docker run -d --name sprout-test -p 10000:10000 -e PORT=10000 -e DAILY_BUDGET=30.0 sprout-budget-tracker
```

Access the app at: http://localhost:10000

Clean up:
```bash
docker stop sprout-test
docker rm sprout-test
```

## 🔧 How It Works

### 1. Container Startup
- `start.sh` detects production environment
- Starts Flask on port 5000 (internal)
- Starts Nginx on PORT (external, usually 10000)

### 2. Request Routing
- **Frontend files**: `nginx.conf` serves from `/app/frontend/`
- **API requests**: `nginx.conf` proxies `/api/*` to Flask
- **Health checks**: `/health` proxied to Flask

### 3. Environment Detection
- **Production**: `/.dockerenv` exists OR `RENDER=true`
- **Development**: Falls back to live-server setup

## 📊 Monitoring

### Health Checks
- **Endpoint**: `/health`
- **Docker**: Built-in health check every 30s
- **Render**: Automatic health monitoring

### Logs
- **Render**: Available in dashboard
- **Docker**: `docker logs <container>`

## 🛠️ Troubleshooting

### Common Issues

1. **Port Conflicts**:
   - Make sure no other services use port 10000
   - Check `PORT` environment variable

2. **Database Connection**:
   - Verify `DATABASE_URL` is set correctly
   - Check PostgreSQL service status

3. **Static Files Not Loading**:
   - Verify frontend files are in `/app/frontend/`
   - Check nginx configuration

### Debug Commands

```bash
# Check container status
docker ps

# View logs
docker logs sprout-test

# Enter container
docker exec -it sprout-test /bin/bash

# Test Flask directly
curl http://localhost:5000/health

# Test Nginx
curl http://localhost:10000/health
```

## 🔄 Updates

To update your deployment:

1. **Make changes** to your code
2. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Update application"
   git push origin main
   ```
3. **Render** will automatically rebuild and deploy

## 📈 Scaling

### Render
- **Free Tier**: 1 instance, sleeps after 15 minutes
- **Starter Plan**: Always on, more resources
- **Pro Plan**: Auto-scaling, custom domains

### Performance Tips
- Enable gzip compression (already configured)
- Use CDN for static assets
- Optimize database queries
- Add caching headers (already configured)

## 🔐 Security

The setup includes:
- Security headers (X-Frame-Options, X-XSS-Protection, etc.)
- HTTPS (handled by Render)
- Database connection encryption
- No sensitive data in logs

## 📝 Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PORT` | External port for Nginx | `10000` | No |
| `DATABASE_URL` | PostgreSQL connection | - | Yes |
| `DAILY_BUDGET` | Daily budget amount | `30.0` | No |
| `FLASK_ENV` | Flask environment | `production` | No |
| `FLASK_DEBUG` | Debug mode | `false` | No |

## 🎯 Next Steps

1. **Test locally** with `./docker-test.sh`
2. **Deploy to Render** using render.yaml
3. **Configure custom domain** (optional)
4. **Set up monitoring** and alerts
5. **Add SSL certificate** (automatic with Render)

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section
2. Review logs in Render dashboard
3. Test locally with Docker
4. Verify environment variables 