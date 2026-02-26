#!/bin/bash
# Start Antigravity Agent

echo "Starting Antigravity Agent..."

# Activate virtual environment
source "${HOME}/.antigravity/venv/bin/activate"

# Start Docker services based on smart detection
if [ -f "smart_docker.py" ]; then
    echo "Smart-detecting Docker requirements..."
    python3 smart_docker.py
elif command -v docker-compose &> /dev/null; then
    echo "Falling back to standard Docker start..."
    docker-compose up -d
fi

# Start Celery worker
echo "Starting Celery worker..."
cd ..
export PYTHONPATH=$PYTHONPATH:$(pwd)
cd antigravity
celery -A antigravity.scheduler worker --loglevel=info &

echo "Antigravity Agent is running!"
echo "Press Ctrl+C to stop"

wait
