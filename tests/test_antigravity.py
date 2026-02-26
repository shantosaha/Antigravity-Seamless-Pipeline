#!/usr/bin/env python3
"""
Simple test script to verify Antigravity setup
"""

import sys
import yaml

def test_configuration():
    """Test that all configuration files are valid YAML"""
    print("Testing configuration files...")
    
    config_files = [
        'agent.yaml',
        'context/context_manager.yaml',
        'planner/planner.yaml',
        'policy/policy_engine.yaml',
        'policy/rules.yaml',
        'scheduler/scheduler.yaml',
        'knowledge/memory/config.yaml',
        'evaluator/evaluator.yaml',
        'telemetry/metrics.yaml',
        'mcp/servers.yaml',
        'input/input_schema.yaml',
    ]
    
    all_valid = True
    for config_file in config_files:
        try:
            with open(config_file, 'r') as f:
                yaml.safe_load(f)
            print(f"✓ {config_file}")
        except Exception as e:
            print(f"✗ {config_file}: {e}")
            all_valid = False
    
    return all_valid

def test_state_store():
    """Test that state store is valid JSON"""
    print("\nTesting state store...")
    
    try:
        import json
        with open('state/state_store.json', 'r') as f:
            json.load(f)
        print("✓ state/state_store.json")
        return True
    except Exception as e:
        print(f"✗ state/state_store.json: {e}")
        return False

def test_imports():
    """Test that required packages are installed"""
    print("\nTesting Python imports...")
    
    packages = [
        'langgraph',
        'mem0',
        'langfuse',
        'llama_index',
        'ragas',
        'celery',
        'redis',
        'yaml',
        'pydantic',
    ]
    
    all_imported = True
    for package in packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} not installed")
            all_imported = False
    
    return all_imported

def main():
    print("Antigravity Setup Verification\n")
    print("=" * 50)
    
    config_ok = test_configuration()
    state_ok = test_state_store()
    imports_ok = test_imports()
    
    print("\n" + "=" * 50)
    if config_ok and state_ok and imports_ok:
        print("✓ All tests passed!")
        print("\nAntigravity is ready to use!")
        print("\nNext steps:")
        print("1. Copy .env.template to .env and add your API keys")
        print("2. Start Docker services: docker-compose up -d")
        print("3. Start the agent: ./scripts/start.sh")
        return 0
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
