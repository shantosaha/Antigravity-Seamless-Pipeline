#!/bin/bash
# Test Antigravity Installation

echo "Testing Antigravity Installation..."

# Activate virtual environment
source "${HOME}/.antigravity/venv/bin/activate"

# Test Python packages
echo ""
echo "Testing Python packages..."
python3 -c "import langgraph; print('✓ LangGraph')" || echo "✗ LangGraph"
python3 -c "import mem0; print('✓ Mem0')" || echo "✗ Mem0"
python3 -c "import langfuse; print('✓ LangFuse')" || echo "✗ LangFuse"
python3 -c "import llama_index; print('✓ LlamaIndex')" || echo "✗ LlamaIndex"
python3 -c "import redis; print('✓ Redis')" || echo "✗ Redis"

# Test Redis connection
echo ""
echo "Testing Redis connection..."
python3 -c "import redis; r = redis.Redis(host='localhost', port=6379); r.ping(); print('✓ Redis is running')" 2>/dev/null || echo "✗ Redis is not running"

# Test configuration files
echo ""
echo "Testing configuration files..."
for file in agent.yaml context/context_manager.yaml planner/planner.yaml; do
    if [ -f "$file" ]; then
        echo "✓ $file exists"
    else
        echo "✗ $file missing"
    fi
done

echo ""
echo "Test complete!"
