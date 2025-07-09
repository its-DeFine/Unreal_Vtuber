import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class ObjectiveBridge:
    """
    Bridge system for sharing objectives between main team and stimuli team
    
    This system enables:
    1. Stimuli team to update main team objectives
    2. Main team to read updated objectives on restart
    3. Persistent storage of objectives across system restarts
    4. Objective versioning and history tracking
    """
    
    def __init__(self, shared_state_dir: str = "/app/shared_state"):
        self.shared_state_dir = shared_state_dir
        self.objectives_file = os.path.join(shared_state_dir, "main_team_objectives.json")
        self.objectives_history_file = os.path.join(shared_state_dir, "objectives_history.json")
        self.current_objectives = []
        self.objectives_history = []
        
        # Ensure shared state directory exists
        os.makedirs(shared_state_dir, exist_ok=True)
        
        # Load existing objectives
        self._load_objectives()
        
        logging.info(f"🌉 [OBJECTIVE_BRIDGE] Initialized with {len(self.current_objectives)} objectives")
    
    def _load_objectives(self):
        """Load current objectives and history from files"""
        try:
            # Load current objectives
            if os.path.exists(self.objectives_file):
                with open(self.objectives_file, 'r') as f:
                    self.current_objectives = json.load(f)
                logging.info(f"📋 [OBJECTIVE_BRIDGE] Loaded {len(self.current_objectives)} current objectives")
            
            # Load objectives history
            if os.path.exists(self.objectives_history_file):
                with open(self.objectives_history_file, 'r') as f:
                    self.objectives_history = json.load(f)
                logging.info(f"📚 [OBJECTIVE_BRIDGE] Loaded {len(self.objectives_history)} historical objectives")
                
        except Exception as e:
            logging.error(f"❌ [OBJECTIVE_BRIDGE] Error loading objectives: {e}")
            self.current_objectives = []
            self.objectives_history = []
    
    def _save_objectives(self):
        """Save current objectives and history to files"""
        try:
            # Save current objectives
            with open(self.objectives_file, 'w') as f:
                json.dump(self.current_objectives, f, indent=2)
            
            # Save objectives history
            with open(self.objectives_history_file, 'w') as f:
                json.dump(self.objectives_history, f, indent=2)
            
            logging.info(f"💾 [OBJECTIVE_BRIDGE] Saved {len(self.current_objectives)} objectives to shared state")
            
        except Exception as e:
            logging.error(f"❌ [OBJECTIVE_BRIDGE] Error saving objectives: {e}")
    
    def add_objectives_from_stimuli(self, objective_data: Dict[str, Any], source: str = "stimuli_team") -> bool:
        """
        Add new objectives from stimuli team
        
        Args:
            objective_data: Dictionary containing objective information
            source: Source of the objectives (default: "stimuli_team")
            
        Returns:
            bool: True if objectives were added successfully
        """
        try:
            # Create objective entry
            objective_entry = {
                "id": f"obj_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "data": objective_data,
                "status": "active",
                "priority": objective_data.get("priority", "medium")
            }
            
            # Add to current objectives
            self.current_objectives.append(objective_entry)
            
            # Add to history
            self.objectives_history.append({
                **objective_entry,
                "action": "added"
            })
            
            # Keep only last 100 current objectives
            if len(self.current_objectives) > 100:
                removed_objectives = self.current_objectives[:-100]
                self.current_objectives = self.current_objectives[-100:]
                
                # Mark removed objectives as archived in history
                for removed_obj in removed_objectives:
                    self.objectives_history.append({
                        **removed_obj,
                        "action": "archived",
                        "archived_timestamp": datetime.now().isoformat()
                    })
            
            # Keep only last 1000 historical entries
            if len(self.objectives_history) > 1000:
                self.objectives_history = self.objectives_history[-1000:]
            
            # Save to files
            self._save_objectives()
            
            logging.info(f"✅ [OBJECTIVE_BRIDGE] Added objective from {source}: {objective_entry['id']}")
            return True
            
        except Exception as e:
            logging.error(f"❌ [OBJECTIVE_BRIDGE] Error adding objectives: {e}")
            return False
    
    def get_current_objectives(self, priority_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get current objectives for main team
        
        Args:
            priority_filter: Optional priority filter ("high", "medium", "low")
            
        Returns:
            List of current objectives
        """
        try:
            objectives = self.current_objectives.copy()
            
            # Filter by priority if specified
            if priority_filter:
                objectives = [obj for obj in objectives if obj.get("priority") == priority_filter]
            
            # Sort by timestamp (newest first)
            objectives.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            logging.info(f"📋 [OBJECTIVE_BRIDGE] Retrieved {len(objectives)} objectives (filter: {priority_filter})")
            return objectives
            
        except Exception as e:
            logging.error(f"❌ [OBJECTIVE_BRIDGE] Error getting objectives: {e}")
            return []
    
    def get_new_objectives_since_restart(self, restart_timestamp: str) -> List[Dict[str, Any]]:
        """
        Get objectives added since the last main team restart
        
        Args:
            restart_timestamp: ISO timestamp of when main team last restarted
            
        Returns:
            List of new objectives
        """
        try:
            new_objectives = [
                obj for obj in self.current_objectives
                if obj.get("timestamp", "") > restart_timestamp
            ]
            
            logging.info(f"🆕 [OBJECTIVE_BRIDGE] Found {len(new_objectives)} new objectives since restart")
            return new_objectives
            
        except Exception as e:
            logging.error(f"❌ [OBJECTIVE_BRIDGE] Error getting new objectives: {e}")
            return []
    
    def mark_objective_completed(self, objective_id: str, completion_details: Dict[str, Any] = None) -> bool:
        """
        Mark an objective as completed
        
        Args:
            objective_id: ID of the objective to mark as completed
            completion_details: Optional details about completion
            
        Returns:
            bool: True if objective was marked as completed
        """
        try:
            # Find objective in current objectives
            for i, obj in enumerate(self.current_objectives):
                if obj.get("id") == objective_id:
                    # Update status
                    obj["status"] = "completed"
                    obj["completion_timestamp"] = datetime.now().isoformat()
                    obj["completion_details"] = completion_details or {}
                    
                    # Add to history
                    self.objectives_history.append({
                        **obj,
                        "action": "completed"
                    })
                    
                    # Remove from current objectives
                    self.current_objectives.pop(i)
                    
                    # Save changes
                    self._save_objectives()
                    
                    logging.info(f"✅ [OBJECTIVE_BRIDGE] Marked objective {objective_id} as completed")
                    return True
            
            logging.warning(f"⚠️ [OBJECTIVE_BRIDGE] Objective {objective_id} not found")
            return False
            
        except Exception as e:
            logging.error(f"❌ [OBJECTIVE_BRIDGE] Error marking objective completed: {e}")
            return False
    
    def get_objectives_for_main_team_prompt(self) -> str:
        """
        Get formatted objectives for main team prompt
        
        Returns:
            Formatted string with current objectives
        """
        try:
            if not self.current_objectives:
                return "No current objectives from stimuli team."
            
            # Get high priority objectives first
            high_priority = [obj for obj in self.current_objectives if obj.get("priority") == "high"]
            medium_priority = [obj for obj in self.current_objectives if obj.get("priority") == "medium"]
            low_priority = [obj for obj in self.current_objectives if obj.get("priority") == "low"]
            
            prompt_parts = []
            
            if high_priority:
                prompt_parts.append("🔥 HIGH PRIORITY OBJECTIVES:")
                for obj in high_priority[:3]:  # Show top 3 high priority
                    objectives_list = obj.get("data", {}).get("new_objectives", [])
                    if objectives_list:
                        prompt_parts.append(f"- {objectives_list[0]} (Source: {obj.get('source', 'unknown')})")
            
            if medium_priority:
                prompt_parts.append("\n📋 MEDIUM PRIORITY OBJECTIVES:")
                for obj in medium_priority[:3]:  # Show top 3 medium priority
                    objectives_list = obj.get("data", {}).get("new_objectives", [])
                    if objectives_list:
                        prompt_parts.append(f"- {objectives_list[0]} (Source: {obj.get('source', 'unknown')})")
            
            if low_priority:
                prompt_parts.append("\n📝 LOW PRIORITY OBJECTIVES:")
                for obj in low_priority[:2]:  # Show top 2 low priority
                    objectives_list = obj.get("data", {}).get("new_objectives", [])
                    if objectives_list:
                        prompt_parts.append(f"- {objectives_list[0]} (Source: {obj.get('source', 'unknown')})")
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            logging.error(f"❌ [OBJECTIVE_BRIDGE] Error formatting objectives for prompt: {e}")
            return "Error retrieving objectives."
    
    def get_objectives_summary(self) -> Dict[str, Any]:
        """
        Get summary of current objectives state
        
        Returns:
            Dictionary with objectives summary
        """
        try:
            summary = {
                "total_current_objectives": len(self.current_objectives),
                "total_historical_objectives": len(self.objectives_history),
                "priority_breakdown": {
                    "high": len([obj for obj in self.current_objectives if obj.get("priority") == "high"]),
                    "medium": len([obj for obj in self.current_objectives if obj.get("priority") == "medium"]),
                    "low": len([obj for obj in self.current_objectives if obj.get("priority") == "low"])
                },
                "recent_additions": len([
                    obj for obj in self.current_objectives 
                    if obj.get("timestamp", "") > (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).isoformat()
                ]),
                "files": {
                    "objectives_file": self.objectives_file,
                    "history_file": self.objectives_history_file
                }
            }
            
            return summary
            
        except Exception as e:
            logging.error(f"❌ [OBJECTIVE_BRIDGE] Error getting objectives summary: {e}")
            return {"error": str(e)}
    
    def clear_old_objectives(self, days_old: int = 7) -> int:
        """
        Clear objectives older than specified days
        
        Args:
            days_old: Number of days after which to clear objectives
            
        Returns:
            Number of objectives cleared
        """
        try:
            from datetime import timedelta
            
            cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()
            
            # Find old objectives
            old_objectives = [
                obj for obj in self.current_objectives
                if obj.get("timestamp", "") < cutoff_date
            ]
            
            # Move to history
            for obj in old_objectives:
                self.objectives_history.append({
                    **obj,
                    "action": "auto_archived",
                    "archived_timestamp": datetime.now().isoformat()
                })
            
            # Remove from current
            self.current_objectives = [
                obj for obj in self.current_objectives
                if obj.get("timestamp", "") >= cutoff_date
            ]
            
            # Save changes
            self._save_objectives()
            
            logging.info(f"🗑️ [OBJECTIVE_BRIDGE] Cleared {len(old_objectives)} old objectives")
            return len(old_objectives)
            
        except Exception as e:
            logging.error(f"❌ [OBJECTIVE_BRIDGE] Error clearing old objectives: {e}")
            return 0
    
    async def monitor_objectives(self, callback_func: Optional[callable] = None):
        """
        Monitor objectives file for changes (useful for real-time updates)
        
        Args:
            callback_func: Optional callback function to call when objectives change
        """
        try:
            last_modified = 0
            
            while True:
                try:
                    if os.path.exists(self.objectives_file):
                        current_modified = os.path.getmtime(self.objectives_file)
                        
                        if current_modified > last_modified:
                            last_modified = current_modified
                            
                            # Reload objectives
                            self._load_objectives()
                            
                            # Call callback if provided
                            if callback_func:
                                await callback_func(self.current_objectives)
                            
                            logging.info("🔄 [OBJECTIVE_BRIDGE] Objectives updated from file")
                
                except Exception as e:
                    logging.error(f"❌ [OBJECTIVE_BRIDGE] Error monitoring objectives: {e}")
                
                # Wait before next check
                await asyncio.sleep(5)
                
        except Exception as e:
            logging.error(f"❌ [OBJECTIVE_BRIDGE] Error in objectives monitoring: {e}")


# Global instance for easy access
_global_objective_bridge = None


def get_objective_bridge(shared_state_dir: str = "/app/shared_state") -> ObjectiveBridge:
    """Get global objective bridge instance"""
    global _global_objective_bridge
    
    if _global_objective_bridge is None:
        _global_objective_bridge = ObjectiveBridge(shared_state_dir)
    
    return _global_objective_bridge


async def initialize_objective_bridge(shared_state_dir: str = "/app/shared_state") -> ObjectiveBridge:
    """Initialize and return objective bridge"""
    bridge = get_objective_bridge(shared_state_dir)
    
    # Clean up old objectives (older than 7 days)
    cleared_count = bridge.clear_old_objectives(days_old=7)
    if cleared_count > 0:
        logging.info(f"🗑️ [OBJECTIVE_BRIDGE] Cleared {cleared_count} old objectives on initialization")
    
    return bridge