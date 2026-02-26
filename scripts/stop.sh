#!/bin/bash
# Stop Antigravity Agent

echo "Stopping Antigravity Agent..."

# Stop Celery
pkill -f "celery.*antigravity"

# Stop Docker services
if command -v docker-compose &> /dev/null; then
    echo "Stopping Docker services..."
    docker-compose down
fi

echo "Antigravity Agent stopped"
