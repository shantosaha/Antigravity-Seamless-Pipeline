import os
import subprocess
import yaml
import json
import time
import sys
from pathlib import Path

class AntigravityResourceManager:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root or os.getcwd())
        self.config_paths = {
            'agent': self.project_root / 'agent.yaml',
            'docker_compose': self.project_root / 'docker-compose.yml',
            'rules': self.project_root / 'policy/rules.yaml',
            'scheduler': self.project_root / 'scheduler/scheduler.yaml',
            'memory': self.project_root / 'knowledge/memory/config.yaml',
            'requirements': self.project_root / 'requirements.txt'
        }
        self.state_file = self.project_root / 'state/state_store.json'

    def get_needed_services(self):
        needed = set()
        
        # Check memory config
        if self.config_paths['memory'].exists():
            with open(self.config_paths['memory'], 'r') as f:
                memory_config = yaml.safe_load(f)
                storage_type = memory_config.get('storage', {}).get('provider')
                if storage_type == 'qdrant':
                    needed.add('qdrant')

        # Check scheduler config
        if self.config_paths['scheduler'].exists():
            with open(self.config_paths['scheduler'], 'r') as f:
                sched_config = yaml.safe_load(f)
                broker = sched_config.get('broker', '')
                if 'redis' in broker:
                    needed.add('redis')

        # Check requirements.txt as a fallback
        if not needed and self.config_paths['requirements'].exists():
            with open(self.config_paths['requirements'], 'r') as f:
                reqs = f.read().lower()
                if 'qdrant' in reqs: needed.add('qdrant')
                if 'redis' in reqs: needed.add('redis')
                if 'psycopg2' in reqs or 'postgres' in reqs: needed.add('postgres')

        return needed

    def is_docker_running(self):
        try:
            subprocess.run(['docker', 'info'], check=True, capture_output=True)
            return True
        except:
            return False

    def get_active_containers(self):
        try:
            result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], check=True, capture_output=True, text=True)
            return result.stdout.splitlines()
        except:
            return []

    def start_services(self, services):
        if not services:
            print("No services needed based on current requirements.")
            return

        print(f"Detected requirements for: {', '.join(services)}")
        
        if not self.is_docker_running():
            print("Error: Docker is not running. Please start Docker Desktop.")
            return

        active = self.get_active_containers()
        to_start = []
        for svc in services:
            container_name = f"antigravity-{svc}"
            if container_name not in active:
                to_start.append(svc)

        if to_start:
            print(f"Starting required services: {', '.join(to_start)}...")
            # We use docker-compose up -d [service] if we want to be selective, 
            # but usually starting all defined ones is safer for dependencies.
            subprocess.run(['docker-compose', 'up', '-d'] + to_start, cwd=self.project_root)
            print("Services started successfully.")
        else:
            print("All required services are already running.")

    def get_policy(self):
        if self.config_paths['rules'].exists():
            with open(self.config_paths['rules'], 'r') as f:
                rules = yaml.safe_load(f)
                return rules.get('resource_management', {})
        return {}

    def stop_unused_services(self, force=False):
        policy = self.get_policy()
        auto_stop = policy.get('auto_shutdown_on_idle', False)
        
        if force:
            print("Stopping all Antigravity Docker services...")
            subprocess.run(['docker-compose', 'down'], cwd=self.project_root)
            return

        if not auto_stop:
            print("Auto-shutdown is disabled by policy.")
            return

        # Check idle time from state store
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                # In a real app, 'last_activity' would be updated by the agent
                last_activity = state.get('last_activity', 0)
                timeout = policy.get('idle_timeout_minutes', 30) * 60
                
                if time.time() - last_activity > timeout:
                    print(f"Project has been idle for >{timeout/60} minutes. Stopping services...")
                    subprocess.run(['docker-compose', 'down'], cwd=self.project_root)
                else:
                    print("Project is still active. Keeping services running.")

if __name__ == "__main__":
    manager = AntigravityResourceManager()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--stop":
        manager.stop_unused_services(force=True)
    else:
        needed = manager.get_needed_services()
        manager.start_services(needed)
