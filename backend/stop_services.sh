#!/bin/bash

# Stop all services script

echo "🛑 Stopping all services..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to kill process by PID file
kill_by_pid_file() {
    local pid_file=$1
    local service_name=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            echo -e "${YELLOW}Stopping $service_name (PID: $pid)...${NC}"
            kill $pid 2>/dev/null || kill -9 $pid 2>/dev/null
            sleep 1
            if kill -0 $pid 2>/dev/null; then
                echo -e "${RED}Failed to stop $service_name${NC}"
            else
                echo -e "${GREEN}✅ $service_name stopped${NC}"
            fi
        else
            echo -e "${YELLOW}$service_name was not running${NC}"
        fi
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}No PID file found for $service_name${NC}"
    fi
}

# Stop Backend
kill_by_pid_file "logs/backend.pid" "Backend"

# Stop Printer Simulator
kill_by_pid_file "logs/printer_simulator.pid" "Printer Simulator"

# Also kill by port (backup)
echo -e "${YELLOW}Checking for any remaining processes...${NC}"

# Kill anything on port 8000
if lsof -ti:8000 >/dev/null 2>&1; then
    echo -e "${YELLOW}Killing processes on port 8000...${NC}"
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
fi

# Kill anything on port 8001
if lsof -ti:8001 >/dev/null 2>&1; then
    echo -e "${YELLOW}Killing processes on port 8001...${NC}"
    lsof -ti:8001 | xargs kill -9 2>/dev/null || true
fi

echo -e "${GREEN}✅ All services stopped${NC}"