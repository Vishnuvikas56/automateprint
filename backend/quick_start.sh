#!/bin/bash

# Simplified Quick Start Script (NO venv creation, NO pip installs)
# Uses your existing environment (cyrusenv)

set -e

echo "🚀 Starting Production-Grade Print Management System..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# -----------------------------
# Function: check if service is running
# -----------------------------
check_service() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${GREEN}✅ $service is running on port $port${NC}"
        return 0
    else
        echo -e "${RED}❌ $service is NOT running on port $port${NC}"
        return 1
    fi
}

# -----------------------------
# Function: wait for a service
# -----------------------------
wait_for_service() {
    local port=$1
    local service=$2
    local max_wait=30
    local count=0
    
    echo -e "${YELLOW}⏳ Waiting for $service to start...${NC}"
    
    while [ $count -lt $max_wait ]; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "${GREEN}✅ $service started successfully${NC}"
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    
    echo -e "${RED}❌ $service failed to start within ${max_wait}s${NC}"
    return 1
}

# -----------------------------------------
# Check Python
# -----------------------------------------
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python 3 found${NC}"

# -----------------------------------------
# Check required backend files exist
# -----------------------------------------
required_files=("printers_v2.py" "backend.py" "smart_scheduler.py" "models.py")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Required file not found: $file${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ All required files found${NC}"

# -----------------------------------------
# Check .env
# -----------------------------------------
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating template...${NC}"
    cat > .env << EOF
# Database
DATABASE_URL=postgresql+psycopg2://vishnuvikasreddyr:mypassword@localhost:5432/print_db

# Razorpay
RAZORPAY_KEY_ID=rzp_test_RJmLixGhPAugzc
RAZORPAY_KEY_SECRET=SeoWn9j5bFMFiX1LQaNif1Yi

# APIs
PRINTER_API_URL=http://localhost:8001
BACKEND_WEBHOOK_URL=http://localhost:8000/webhook/printer-update

# JWT
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# GCS
GOOGLE_CLOUD_PROJECT=project-new-day-474408-720673ec4f66.json
GCS_BUCKET_NAME=automateprint
EOF
    echo -e "${YELLOW}⚠️  Please configure .env file with your settings${NC}"
fi

# -----------------------------------------
# Check PostgreSQL running
# -----------------------------------------
if ! pg_isready &> /dev/null; then
    echo -e "${RED}❌ PostgreSQL is not running. Please start PostgreSQL first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ PostgreSQL is running${NC}"

# -----------------------------------------
# Run migrations (if available)
# -----------------------------------------
echo -e "${YELLOW}🗄️  Running migrations (if any)...${NC}"
if [ -f "alembic.ini" ]; then
    alembic upgrade head
    echo -e "${GREEN}✅ Database migrations complete${NC}"
else
    echo -e "${YELLOW}⚠️  alembic.ini not found. Skipping migrations.${NC}"
fi

mkdir -p logs

echo ""
echo "======================================"
echo "  Starting Services"
echo "======================================"
echo ""

# Kill existing ports
echo -e "${YELLOW}🧹 Cleaning existing services...${NC}"
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 2

# -----------------------------------------
# Start Printer Simulator
# -----------------------------------------
echo -e "${YELLOW}🖨️  Starting Printer Simulator on port 8001...${NC}"
nohup uvicorn printers_v2:app --port 8001 --reload > logs/printer_simulator.log 2>&1 &
PRINTER_PID=$!
echo $PRINTER_PID > logs/printer_simulator.pid

if ! wait_for_service 8001 "Printer Simulator"; then
    echo -e "${RED}Check logs/printer_simulator.log${NC}"
    exit 1
fi

# -----------------------------------------
# Start Backend
# -----------------------------------------
echo -e "${YELLOW}🔧 Starting Backend on port 8000...${NC}"
nohup uvicorn backend:app --port 8000 --reload > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > logs/backend.pid

if ! wait_for_service 8000 "Backend"; then
    kill $PRINTER_PID || true
    echo -e "${RED}Check logs/backend.log${NC}"
    exit 1
fi

# -----------------------------------------
# Health Checks
# -----------------------------------------
echo ""
echo -e "${YELLOW}🏥 Running health checks...${NC}"
sleep 3

if curl -s http://localhost:8001/ > /dev/null; then
    echo -e "${GREEN}✅ Printer Simulator: Healthy${NC}"
else
    echo -e "${RED}❌ Printer Simulator: Unhealthy${NC}"
fi

if curl -s http://localhost:8000/ > /dev/null; then
    echo -e "${GREEN}✅ Backend: Healthy${NC}"
else
    echo -e "${RED}❌ Backend: Unhealthy${NC}"
fi

echo ""
echo "======================================"
echo "  🎉 System Started Successfully!"
======================================"
echo ""
echo -e "${GREEN}Printer Simulator: http://localhost:8001${NC}"
echo -e "${GREEN}Backend API:        http://localhost:8000${NC}"
echo -e "${GREEN}API Docs:           http://localhost:8000/docs${NC}"
echo ""
echo "Logs:"
echo "  tail -f logs/printer_simulator.log"
echo "  tail -f logs/backend.log"
echo ""
echo "Stop services:"
echo "  ./stop_services.sh"
echo ""
