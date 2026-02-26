#!/bin/bash
# Update Antigravity Dependencies

echo "Updating Antigravity dependencies..."

# Activate virtual environment
source "${HOME}/.antigravity/venv/bin/activate"

# Update Python packages
echo "Updating Python packages..."
pip install --upgrade pip
pip install --upgrade -r requirements.txt

# Update Docker images
if command -v docker-compose &> /dev/null; then
    echo "Updating Docker images..."
    docker-compose pull
fi

echo "Update complete!"
