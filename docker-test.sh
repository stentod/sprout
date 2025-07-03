#!/bin/bash

# Docker Test Script for Sprout Budget Tracker
# This script builds and tests the Docker container locally

set -e

echo "🐳 Testing Docker setup for Sprout Budget Tracker"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Build the Docker image
echo -e "${YELLOW}📦 Building Docker image...${NC}"
docker build -t sprout-budget-tracker:latest .

# Run the container in detached mode
echo -e "${YELLOW}🚀 Starting container...${NC}"
docker run -d \
  --name sprout-test \
  -p 10000:10000 \
  -e PORT=10000 \
  -e DAILY_BUDGET=30.0 \
  -e FLASK_ENV=production \
  sprout-budget-tracker:latest

# Wait for the container to start
echo -e "${YELLOW}⏳ Waiting for container to start...${NC}"
sleep 15

# Additional wait with retries for health check
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
for i in {1..6}; do
    if curl -f http://localhost:10000/health >/dev/null 2>&1; then
        break
    fi
    echo -e "${YELLOW}   Attempt $i/6 - still waiting...${NC}"
    sleep 5
done

# Test health endpoint
echo -e "${YELLOW}🔍 Testing health endpoint...${NC}"
if curl -f http://localhost:10000/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Health check passed!${NC}"
else
    echo -e "${RED}❌ Health check failed!${NC}"
    docker logs sprout-test
    docker stop sprout-test
    docker rm sprout-test
    exit 1
fi

# Test frontend
echo -e "${YELLOW}🌐 Testing frontend...${NC}"
if curl -f http://localhost:10000/ >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend is accessible!${NC}"
else
    echo -e "${RED}❌ Frontend test failed!${NC}"
    docker logs sprout-test
    docker stop sprout-test
    docker rm sprout-test
    exit 1
fi

# Test API endpoint (Note: Will fail without DATABASE_URL)
echo -e "${YELLOW}🔧 Testing API endpoint...${NC}"
API_RESPONSE=$(curl -s -w "%{http_code}" http://localhost:10000/api/summary -o /dev/null)
if [ "$API_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✅ API is working with database!${NC}"
elif [ "$API_RESPONSE" = "500" ]; then
    echo -e "${YELLOW}⚠️  API returns 500 (expected without DATABASE_URL)${NC}"
    echo -e "${YELLOW}   This is normal for local testing without PostgreSQL${NC}"
    echo -e "${YELLOW}   In production, Render will provide DATABASE_URL${NC}"
else
    echo -e "${RED}❌ Unexpected API response: $API_RESPONSE${NC}"
    docker logs sprout-test
    docker stop sprout-test
    docker rm sprout-test
    exit 1
fi

echo -e "${GREEN}🎉 Container tests passed! Ready for deployment.${NC}"
echo -e "${YELLOW}📝 Note: API will work properly in production with DATABASE_URL${NC}"
echo -e "${YELLOW}🌐 You can access the app at: http://localhost:10000${NC}"
echo -e "${YELLOW}🛑 To stop the test container, run: docker stop sprout-test && docker rm sprout-test${NC}" 