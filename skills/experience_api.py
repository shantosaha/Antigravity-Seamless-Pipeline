#!/usr/bin/env python3
"""
Antigravity Experience API

Provides unified API for Antigravity pipeline and 32-agent system
to share experience data and enable continuous learning.
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ExperienceAPI:
    """Unified API for experience tracking and learning"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.state_dir = Path.home() / '.antigravity' / 'state'
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Storage backends (initialized lazily)
        self._postgres = None
        self._redis = None
        self._qdrant = None
        
        # In-memory cache
        self._cache = {}
        self._cache_ttl = {}
        
    def _load_config(self, config_path: str = None) -> dict:
        """Load configuration from file or use defaults"""
        if config_path is None:
            config_path = Path.home() / '.antigravity' / 'config.json'
        elif isinstance(config_path, str):
            config_path = Path(os.path.expanduser(config_path))
        
        default_config = {
            "experience": {
                "enabled": True,
                "storage": {
                    "type": "file",
                    "file": {
                        "enabled": True,
                        "path": str(Path.home() / '.antigravity' / 'state' / 'experiences.json')
                    }
                },
                "learning": {
                    "enabled": True,
                    "minExperiencesForPattern": 5,
                    "minConfidenceForRecommendation": 0.7,
                    "patternRecognitionInterval": 100
                }
            }
        }
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                # Merge configs
                return self._merge_configs(default_config, user_config)
        
        return default_config
    
    def _merge_configs(self, default: dict, user: dict) -> dict:
        """Recursively merge user config into default config"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    def record(self, experience: Dict[str, Any]) -> str:
        """
        Record a new experience
        
        Args:
            experience: Experience record with agent, task, decision, outcome
            
        Returns:
            Experience ID
        """
        # Generate experience ID
        exp_id = self._generate_id(experience)
        
        # Add metadata
        experience['id'] = exp_id
        experience['timestamp'] = datetime.utcnow().isoformat()
        
        # Store based on configured backend
        storage_type = self.config['experience']['storage']['type']
        
        if storage_type == 'file' or self.config['experience']['storage']['file']['enabled']:
            self._store_file(experience)
        
        # Clear cache for queries that might be affected
        self._invalidate_cache('get_best_skill')
        self._invalidate_cache('get_similar_experiences')
        
        # Check if we should recognize patterns
        if self.config['experience']['learning']['enabled']:
            self._maybe_recognize_patterns()
        
        logger.debug(f"Recorded experience: {exp_id}")
        return exp_id
    
    def get_best_skill(self, task_context: Dict[str, str]) -> Optional[str]:
        """
        Get the best skill for a given task based on learned experiences
        
        Args:
            task_context: Task type and complexity
            
        Returns:
            Best skill name or None
        """
        cache_key = f"best_skill:{hashlib.md5(json.dumps(task_context, sort_keys=True).encode()).hexdigest()}"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        # Get experiences for this task type
        experiences = self._get_experiences_for_task(task_context)
        
        if not experiences:
            return None
        
        # Group by skill and calculate success rates
        skill_stats = {}
        for exp in experiences:
            skill = exp.get('decision', {}).get('skillUsed', 'builtin')
            if skill not in skill_stats:
                skill_stats[skill] = {'successes': 0, 'total': 0, 'quality_sum': 0}
            
            skill_stats[skill]['total'] += 1
            if exp.get('outcome', {}).get('success', False):
                skill_stats[skill]['successes'] += 1
            skill_stats[skill]['quality_sum'] += exp.get('outcome', {}).get('quality', 0)
        
        # Find best skill (minimum 3 experiences)
        best_skill = None
        best_score = 0
        
        for skill, stats in skill_stats.items():
            if stats['total'] < 3:
                continue
            
            success_rate = stats['successes'] / stats['total']
            avg_quality = stats['quality_sum'] / stats['total']
            score = (success_rate * 0.6) + (avg_quality / 100 * 0.4)
            
            if score > best_score:
                best_score = score
                best_skill = skill
        
        # Cache result
        if best_skill:
            self._cache[cache_key] = best_skill
            self._cache_ttl[cache_key] = datetime.utcnow() + timedelta(hours=1)
        
        return best_skill
    
    def get_recommendation(self, task_context: Dict[str, str]) -> Dict[str, Any]:
        """
        Get skill recommendation based on patterns
        
        Args:
            task_context: Task type and complexity (must include 'task_type')
            
        Returns:
            Recommendation with skill, confidence, reason
        """
        # Require at least a task_type to make a recommendation
        if not task_context or not task_context.get('task_type'):
            return {
                "skill": None,
                "confidence": 0.0,
                "reason": "No task_type provided — cannot recommend",
                "alternative": "builtin"
            }
        
        best_skill = self.get_best_skill(task_context)
        
        if not best_skill:
            return {
                "skill": None,
                "confidence": 0.0,
                "reason": "No experiences found for this task type",
                "alternative": "builtin"
            }
        
        # Get statistics for this skill
        experiences = self._get_experiences_for_task(task_context)
        skill_experiences = [e for e in experiences if e.get('decision', {}).get('skillUsed') == best_skill]
        
        if not skill_experiences:
            return {
                "skill": None,
                "confidence": 0.0,
                "reason": "No data for recommended skill",
                "alternative": "builtin"
            }
        
        success_count = sum(1 for e in skill_experiences if e.get('outcome', {}).get('success', False))
        avg_quality = sum(e.get('outcome', {}).get('quality', 0) for e in skill_experiences) / len(skill_experiences)
        
        # Confidence = success_rate * 0.6 + quality * 0.4
        confidence = (success_count / len(skill_experiences)) * 0.6 + (avg_quality / 100) * 0.4
        
        # Read threshold from config
        min_confidence = self.config['experience']['learning'].get('minConfidenceForRecommendation', 0.7)
        
        if confidence < min_confidence:
            return {
                "skill": best_skill,
                "confidence": round(confidence, 2),
                "reason": f"Confidence {confidence:.0%} below threshold {min_confidence:.0%} ({len(skill_experiences)} experiences)",
                "alternative": "builtin",
                "belowThreshold": True
            }
        
        return {
            "skill": best_skill,
            "confidence": round(confidence, 2),
            "reason": f"{avg_quality:.0f}% avg quality from {len(skill_experiences)} experiences",
            "alternative": "builtin",
            "belowThreshold": False
        }
    
    def get_similar_experiences(self, query: Dict[str, Any], limit: int = 5) -> List[Dict]:
        """
        Get similar experiences (simple keyword matching for now)
        
        Args:
            query: Search query
            limit: Max results
            
        Returns:
            List of similar experiences
        """
        all_experiences = self._load_experiences()
        
        # Simple keyword matching (Qdrant would do vector similarity)
        scored = []
        for exp in all_experiences:
            score = 0
            
            # Match task type
            if query.get('task_type') == exp.get('task', {}).get('type'):
                score += 3
            
            # Match complexity
            if query.get('complexity') == exp.get('task', {}).get('complexity'):
                score += 2
            
            # Match agent
            if query.get('agent') == exp.get('agent'):
                score += 1
            
            if score > 0:
                scored.append((score, exp))
        
        # Sort by score and return top results
        scored.sort(key=lambda x: x[0], reverse=True)
        return [exp for score, exp in scored[:limit]]
    
    def get_statistics(self, agent: str = None) -> Dict[str, Any]:
        """
        Get experience statistics
        
        Args:
            agent: Filter by agent (optional)
            
        Returns:
            Statistics dictionary
        """
        experiences = self._load_experiences()
        
        if agent:
            experiences = [e for e in experiences if e.get('agent') == agent]
        
        if not experiences:
            return {
                "total": 0,
                "success_rate": 0.0,
                "avg_duration": 0,
                "avg_quality": 0,
                "by_skill": {}
            }
        
        # Calculate stats
        total = len(experiences)
        successes = sum(1 for e in experiences if e.get('outcome', {}).get('success', False))
        durations = [e.get('outcome', {}).get('duration', 0) for e in experiences if e.get('outcome', {}).get('duration')]
        qualities = [e.get('outcome', {}).get('quality', 0) for e in experiences if e.get('outcome', {}).get('quality')]
        
        # Group by skill
        by_skill = {}
        for exp in experiences:
            skill = exp.get('decision', {}).get('skillUsed', 'builtin')
            if skill not in by_skill:
                by_skill[skill] = {'count': 0, 'successes': 0}
            by_skill[skill]['count'] += 1
            if exp.get('outcome', {}).get('success', False):
                by_skill[skill]['successes'] += 1
        
        # Calculate success rates by skill
        for skill in by_skill:
            by_skill[skill]['success_rate'] = by_skill[skill]['successes'] / by_skill[skill]['count']
        
        return {
            "total": total,
            "success_rate": round(successes / total, 2) if total > 0 else 0.0,
            "avg_duration": round(sum(durations) / len(durations), 0) if durations else 0,
            "avg_quality": round(sum(qualities) / len(qualities), 0) if qualities else 0,
            "by_skill": by_skill
        }
    
    def recognize_patterns(self) -> List[Dict[str, Any]]:
        """
        Analyze experiences to recognize patterns
        
        Returns:
            List of recognized patterns
        """
        experiences = self._load_experiences()
        patterns = []
        
        # Group by task type
        by_task_type = {}
        for exp in experiences:
            task_type = exp.get('task', {}).get('type')
            if task_type:
                if task_type not in by_task_type:
                    by_task_type[task_type] = []
                by_task_type[task_type].append(exp)
        
        # Analyze each group
        for task_type, task_experiences in by_task_type.items():
            if len(task_experiences) < self.config['experience']['learning']['minExperiencesForPattern']:
                continue
            
            # Group by skill
            by_skill = {}
            for exp in task_experiences:
                skill = exp.get('decision', {}).get('skillUsed', 'builtin')
                if skill not in by_skill:
                    by_skill[skill] = []
                by_skill[skill].append(exp)
            
            # Find best performing skill
            for skill, skill_experiences in by_skill.items():
                if len(skill_experiences) < 3:
                    continue
                
                successes = sum(1 for e in skill_experiences if e.get('outcome', {}).get('success', False))
                success_rate = successes / len(skill_experiences)
                avg_q = sum(e.get('outcome', {}).get('quality', 0) for e in skill_experiences) / len(skill_experiences)
                
                if success_rate >= 0.9:
                    patterns.append({
                        "id": f"pattern-{task_type}-{skill}",
                        "type": "SUCCESS",
                        "conditions": {
                            "task_type": task_type,
                            "skill": skill
                        },
                        "metrics": {
                            "success_rate": success_rate,
                            "avg_quality": round(avg_q, 1),
                            "occurrence_count": len(skill_experiences),
                            "confidence": min(1.0, len(skill_experiences) / 10)
                        },
                        "insight": f"{skill} has {success_rate*100:.0f}% success rate for {task_type} (avg quality {avg_q:.0f})",
                        "recommended_action": f"USE_SKILL: {skill}"
                    })
        
        # Save patterns
        self._save_patterns(patterns)
        
        return patterns
    
    def _generate_id(self, experience: Dict[str, Any]) -> str:
        """Generate unique experience ID"""
        content = json.dumps(experience, sort_keys=True)
        return f"exp-{hashlib.md5(content.encode()).hexdigest()[:12]}"
    
    def _store_file(self, experience: Dict[str, Any]):
        """Store experience to JSON file"""
        experiences = self._load_experiences()
        experiences.append(experience)
        
        # Keep only last 10000 experiences
        if len(experiences) > 10000:
            experiences = experiences[-10000:]
        
        file_path = os.path.expanduser(self.config['experience']['storage']['file']['path'])
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump({
                "experiences": experiences,
                "lastUpdated": datetime.utcnow().isoformat()
            }, f, indent=2)
    
    def _load_experiences(self) -> List[Dict]:
        """Load experiences from file"""
        file_path = os.path.expanduser(self.config['experience']['storage']['file']['path'])
        
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return data.get('experiences', [])
        except (json.JSONDecodeError, IOError):
            logger.warning(f'Corrupt or unreadable experiences file: {file_path}')
            return []
    
    def _get_experiences_for_task(self, task_context: Dict[str, str]) -> List[Dict]:
        """Get experiences matching task context. Requires at least task_type to filter."""
        # Guard: if no filters are provided, return empty to prevent matching everything
        if not task_context or (not task_context.get('task_type') and not task_context.get('complexity')):
            return []
        
        all_experiences = self._load_experiences()
        
        filtered = []
        for exp in all_experiences:
            task = exp.get('task', {})
            
            # Match task type
            if task_context.get('task_type') and task.get('type') != task_context['task_type']:
                continue
            
            # Match complexity
            if task_context.get('complexity') and task.get('complexity') != task_context['complexity']:
                continue
            
            filtered.append(exp)
        
        return filtered
    
    def _maybe_recognize_patterns(self):
        """Recognize patterns if enough new experiences"""
        # Load pattern recognition state
        state_file = self.state_dir / 'pattern_state.json'
        
        last_recognition = 0
        last_count = 0
        
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
                last_recognition = state.get('last_count', 0)
        
        current_count = len(self._load_experiences())
        
        # Recognize if we have enough new experiences
        interval = self.config['experience']['learning']['patternRecognitionInterval']
        if current_count - last_recognition >= interval:
            self.recognize_patterns()
            
            # Update state
            with open(state_file, 'w') as f:
                json.dump({
                    'last_count': current_count,
                    'last_recognition': datetime.utcnow().isoformat()
                }, f, indent=2)
    
    def _save_patterns(self, patterns: List[Dict]):
        """Save recognized patterns"""
        patterns_file = self.state_dir / 'patterns.json'
        
        with open(patterns_file, 'w') as f:
            json.dump({
                "patterns": patterns,
                "lastUpdated": datetime.utcnow().isoformat()
            }, f, indent=2)
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid"""
        if key not in self._cache:
            return False
        
        ttl = self._cache_ttl.get(key, datetime.utcnow())
        return datetime.utcnow() < ttl
    
    def _invalidate_cache(self, prefix: str):
        """Invalidate cache entries matching prefix"""
        for key in list(self._cache.keys()):
            if key.startswith(prefix):
                del self._cache[key]
                if key in self._cache_ttl:
                    del self._cache_ttl[key]


# Singleton instance
_experience_api = None

def get_experience_api() -> ExperienceAPI:
    """Get or create ExperienceAPI singleton"""
    global _experience_api
    if _experience_api is None:
        _experience_api = ExperienceAPI()
    return _experience_api


# Convenience functions
def record_experience(experience: Dict[str, Any]) -> str:
    """Record a new experience"""
    return get_experience_api().record(experience)

def get_best_skill(task_context: Dict[str, str]) -> Optional[str]:
    """Get best skill for task"""
    return get_experience_api().get_best_skill(task_context)

def get_recommendation(task_context: Dict[str, str]) -> Dict[str, Any]:
    """Get skill recommendation"""
    return get_experience_api().get_recommendation(task_context)
