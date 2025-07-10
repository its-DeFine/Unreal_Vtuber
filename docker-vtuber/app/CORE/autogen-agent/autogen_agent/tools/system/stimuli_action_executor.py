import os
import json
import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional, List

# Import clients for external actions
from ..clients.scb_client import SCBClient
from ..clients.vtuber_client import VTuberClient


async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unified Stimuli Action Executor Tool
    
    This tool handles all stimuli team decisions through a single interface.
    It can perform three types of actions based on parameters:
    1. objective_update: Update main team objectives
    2. knowledge_push: Push insights to Cognee memory system
    3. placeholder_action: Execute dynamic actions (calendar, APIs, etc.)
    
    Parameters:
    - action_type: ["objective_update", "knowledge_push", "placeholder_action"]
    - objective_updates: Updates for main team (when action_type="objective_update")
    - knowledge_data: Data to push to Cognee (when action_type="knowledge_push")
    - placeholder_action: Dynamic action config (when action_type="placeholder_action")
    - agent_reasoning: Full team decision rationale
    - priority: Execution priority level
    """
    
    start_time = datetime.now()
    
    try:
        # Extract parameters
        action_type = context.get("action_type", "knowledge_push")
        agent_reasoning = context.get("agent_reasoning", "No reasoning provided")
        priority = context.get("priority", "medium")
        
        logging.info(f"🎯 [STIMULI_EXECUTOR] Processing {action_type} action with priority: {priority}")
        
        # Execute based on action type
        if action_type == "objective_update":
            result = await _execute_objective_update(context)
        elif action_type == "knowledge_push":
            result = await _execute_knowledge_push(context)
        elif action_type == "placeholder_action":
            result = await _execute_placeholder_action(context)
        else:
            logging.warning(f"⚠️ [STIMULI_EXECUTOR] Unknown action type: {action_type}")
            result = await _execute_knowledge_push(context)  # Default fallback
        
        # Add execution metadata
        result.update({
            "action_type": action_type,
            "agent_reasoning": agent_reasoning,
            "priority": priority,
            "execution_time": (datetime.now() - start_time).total_seconds(),
            "timestamp": datetime.now().isoformat(),
            "tool_used": "stimuli_action_executor"
        })
        
        # DO NOT automatically trigger S1 Avatar - only admin commands should enable voice
        # await _trigger_s1_avatar_response(context, result, action_type)  # DISABLED
        logging.info(f"🚫 [STIMULI_EXECUTOR] S1 Avatar trigger disabled for {action_type} - stimuli-driven architecture")
        
        # Also send to VTuber for legacy compatibility
        vtuber_client = context.get("vtuber_client")
        if vtuber_client and result.get("success"):
            vtuber_message = f"🎯 Stimuli Action: {action_type} completed successfully"
            vtuber_client.post_message(vtuber_message)
        
        logging.info(f"✅ [STIMULI_EXECUTOR] {action_type} action completed successfully")
        return result
        
    except Exception as e:
        logging.error(f"❌ [STIMULI_EXECUTOR] Error executing stimuli action: {e}")
        return {
            "success": False,
            "error": str(e),
            "action_type": action_type,
            "timestamp": datetime.now().isoformat(),
            "tool_used": "stimuli_action_executor"
        }


async def _execute_objective_update(context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute objective update for main team"""
    try:
        objective_updates = context.get("objective_updates", {})
        
        if not objective_updates:
            return {
                "success": False,
                "error": "No objective updates provided",
                "message": "Objective update failed - no updates specified"
            }
        
        # Create/update objectives file for main team
        objectives_file = "/tmp/main_team_objectives.json"
        
        # Load existing objectives
        existing_objectives = []
        if os.path.exists(objectives_file):
            try:
                with open(objectives_file, 'r') as f:
                    existing_objectives = json.load(f)
            except Exception as e:
                logging.warning(f"⚠️ [STIMULI_EXECUTOR] Error loading existing objectives: {e}")
        
        # Add new objectives
        new_objective = {
            "id": f"stimuli_obj_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "objectives": objective_updates.get("new_objectives", []),
            "source": "stimuli_team_decision",
            "timestamp": datetime.now().isoformat(),
            "priority": context.get("priority", "medium"),
            "reasoning": context.get("agent_reasoning", "")
        }
        
        existing_objectives.append(new_objective)
        
        # Keep only last 50 objectives
        if len(existing_objectives) > 50:
            existing_objectives = existing_objectives[-50:]
        
        # Save updated objectives
        with open(objectives_file, 'w') as f:
            json.dump(existing_objectives, f, indent=2)
        
        # Also save to shared memory location if available
        shared_objectives_file = "/app/shared_state/main_team_objectives.json"
        os.makedirs(os.path.dirname(shared_objectives_file), exist_ok=True)
        
        try:
            with open(shared_objectives_file, 'w') as f:
                json.dump(existing_objectives, f, indent=2)
            logging.info("📝 [STIMULI_EXECUTOR] Objectives saved to shared state")
        except Exception as e:
            logging.warning(f"⚠️ [STIMULI_EXECUTOR] Could not save to shared state: {e}")
        
        return {
            "success": True,
            "message": f"Updated main team objectives with {len(objective_updates.get('new_objectives', []))} new objectives",
            "objectives_added": len(objective_updates.get('new_objectives', [])),
            "total_objectives": len(existing_objectives),
            "objectives_file": objectives_file
        }
        
    except Exception as e:
        logging.error(f"❌ [STIMULI_EXECUTOR] Error executing objective update: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Objective update failed"
        }


async def _execute_knowledge_push(context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute knowledge push to Cognee memory system"""
    try:
        knowledge_data = context.get("knowledge_data", {})
        
        if not knowledge_data:
            return {
                "success": False,
                "error": "No knowledge data provided",
                "message": "Knowledge push failed - no data specified"
            }
        
        # Try to push to Cognee if available
        cognee_pushed = False
        
        # Check if we have access to cognitive memory
        if hasattr(context, 'cognitive_memory') and context.cognitive_memory:
            try:
                # Store knowledge in Cognee
                await context.cognitive_memory.store_knowledge(
                    knowledge_data,
                    source="stimuli_team_analysis",
                    category="stimuli_insight"
                )
                cognee_pushed = True
                logging.info("🧠 [STIMULI_EXECUTOR] Knowledge pushed to Cognee successfully")
            except Exception as e:
                logging.warning(f"⚠️ [STIMULI_EXECUTOR] Error pushing to Cognee: {e}")
        
        # Fallback: Save to local knowledge store
        knowledge_file = "/tmp/stimuli_knowledge_store.json"
        
        # Load existing knowledge
        existing_knowledge = []
        if os.path.exists(knowledge_file):
            try:
                with open(knowledge_file, 'r') as f:
                    existing_knowledge = json.load(f)
            except Exception as e:
                logging.warning(f"⚠️ [STIMULI_EXECUTOR] Error loading existing knowledge: {e}")
        
        # Add new knowledge
        new_knowledge = {
            "id": f"stimuli_knowledge_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "data": knowledge_data,
            "source": "stimuli_team_analysis",
            "timestamp": datetime.now().isoformat(),
            "reasoning": context.get("agent_reasoning", ""),
            "cognee_pushed": cognee_pushed
        }
        
        existing_knowledge.append(new_knowledge)
        
        # Keep only last 1000 knowledge entries
        if len(existing_knowledge) > 1000:
            existing_knowledge = existing_knowledge[-1000:]
        
        # Save updated knowledge
        with open(knowledge_file, 'w') as f:
            json.dump(existing_knowledge, f, indent=2)
        
        return {
            "success": True,
            "message": f"Knowledge pushed successfully - Cognee: {cognee_pushed}, Local: True",
            "cognee_pushed": cognee_pushed,
            "local_stored": True,
            "total_knowledge_entries": len(existing_knowledge),
            "knowledge_file": knowledge_file
        }
        
    except Exception as e:
        logging.error(f"❌ [STIMULI_EXECUTOR] Error executing knowledge push: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Knowledge push failed"
        }


async def _execute_placeholder_action(context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute placeholder action (dynamic actions like calendar, APIs, etc.)"""
    try:
        placeholder_action = context.get("placeholder_action", {})
        
        if not placeholder_action:
            return {
                "success": False,
                "error": "No placeholder action provided",
                "message": "Placeholder action failed - no action specified"
            }
        
        action_description = placeholder_action.get("action_description", "")
        action_parameters = placeholder_action.get("parameters", {})
        
        # Analyze action description to determine action type
        action_type = _determine_action_type(action_description)
        
        if action_type == "calendar":
            result = await _execute_calendar_action(action_description, action_parameters, context)
        elif action_type == "notification":
            result = await _execute_notification_action(action_description, action_parameters, context)
        elif action_type == "api_call":
            result = await _execute_api_call_action(action_description, action_parameters, context)
        elif action_type == "file_operation":
            result = await _execute_file_operation_action(action_description, action_parameters, context)
        else:
            # Generic placeholder action
            result = await _execute_generic_action(action_description, action_parameters, context)
        
        return result
        
    except Exception as e:
        logging.error(f"❌ [STIMULI_EXECUTOR] Error executing placeholder action: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Placeholder action failed"
        }


def _determine_action_type(action_description: str) -> str:
    """Determine the type of placeholder action based on description"""
    description_lower = action_description.lower()
    
    if any(keyword in description_lower for keyword in ["calendar", "schedule", "event", "meeting", "appointment"]):
        return "calendar"
    elif any(keyword in description_lower for keyword in ["notify", "alert", "remind", "notification"]):
        return "notification"
    elif any(keyword in description_lower for keyword in ["api", "call", "request", "endpoint", "webhook"]):
        return "api_call"
    elif any(keyword in description_lower for keyword in ["file", "save", "write", "create", "document"]):
        return "file_operation"
    else:
        return "generic"


async def _execute_calendar_action(action_description: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute calendar-related placeholder action"""
    try:
        # Extract calendar details from description and parameters
        event_details = {
            "title": parameters.get("title", "Stimuli-Generated Event"),
            "description": action_description,
            "timestamp": datetime.now().isoformat(),
            "source": "stimuli_team_decision",
            "reasoning": context.get("agent_reasoning", "")
        }
        
        # Save to calendar store (placeholder - could integrate with actual calendar API)
        calendar_file = "/tmp/stimuli_calendar_events.json"
        
        existing_events = []
        if os.path.exists(calendar_file):
            try:
                with open(calendar_file, 'r') as f:
                    existing_events = json.load(f)
            except Exception as e:
                logging.warning(f"⚠️ [STIMULI_EXECUTOR] Error loading existing events: {e}")
        
        existing_events.append(event_details)
        
        with open(calendar_file, 'w') as f:
            json.dump(existing_events, f, indent=2)
        
        return {
            "success": True,
            "message": f"Calendar event created: {event_details['title']}",
            "action_type": "calendar",
            "event_details": event_details,
            "total_events": len(existing_events)
        }
        
    except Exception as e:
        logging.error(f"❌ [STIMULI_EXECUTOR] Error executing calendar action: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Calendar action failed"
        }


async def _execute_notification_action(action_description: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute notification-related placeholder action"""
    try:
        # Send notification via VTuber if available
        vtuber_client = context.get("vtuber_client")
        if vtuber_client:
            notification_message = f"🔔 Stimuli Notification: {action_description}"
            vtuber_client.post_message(notification_message)
        
        # Log notification
        notification_details = {
            "message": action_description,
            "timestamp": datetime.now().isoformat(),
            "source": "stimuli_team_decision",
            "parameters": parameters,
            "vtuber_sent": bool(vtuber_client)
        }
        
        return {
            "success": True,
            "message": f"Notification sent: {action_description[:50]}...",
            "action_type": "notification",
            "notification_details": notification_details
        }
        
    except Exception as e:
        logging.error(f"❌ [STIMULI_EXECUTOR] Error executing notification action: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Notification action failed"
        }


async def _execute_api_call_action(action_description: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute API call placeholder action"""
    try:
        # This is a placeholder for actual API calls
        # In a real implementation, this would make actual HTTP requests
        
        api_details = {
            "description": action_description,
            "parameters": parameters,
            "timestamp": datetime.now().isoformat(),
            "source": "stimuli_team_decision",
            "status": "simulated"  # Placeholder - would be "executed" for real calls
        }
        
        # Save API call log
        api_log_file = "/tmp/stimuli_api_calls.json"
        
        existing_calls = []
        if os.path.exists(api_log_file):
            try:
                with open(api_log_file, 'r') as f:
                    existing_calls = json.load(f)
            except Exception as e:
                logging.warning(f"⚠️ [STIMULI_EXECUTOR] Error loading existing API calls: {e}")
        
        existing_calls.append(api_details)
        
        with open(api_log_file, 'w') as f:
            json.dump(existing_calls, f, indent=2)
        
        return {
            "success": True,
            "message": f"API call simulated: {action_description[:50]}...",
            "action_type": "api_call",
            "api_details": api_details,
            "total_calls": len(existing_calls)
        }
        
    except Exception as e:
        logging.error(f"❌ [STIMULI_EXECUTOR] Error executing API call action: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "API call action failed"
        }


async def _execute_file_operation_action(action_description: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute file operation placeholder action"""
    try:
        # Create file based on description
        file_content = {
            "description": action_description,
            "parameters": parameters,
            "timestamp": datetime.now().isoformat(),
            "source": "stimuli_team_decision",
            "reasoning": context.get("agent_reasoning", "")
        }
        
        # Determine filename
        filename = parameters.get("filename", f"stimuli_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        filepath = f"/tmp/{filename}"
        
        # Save file
        with open(filepath, 'w') as f:
            json.dump(file_content, f, indent=2)
        
        return {
            "success": True,
            "message": f"File created: {filename}",
            "action_type": "file_operation",
            "filepath": filepath,
            "file_content": file_content
        }
        
    except Exception as e:
        logging.error(f"❌ [STIMULI_EXECUTOR] Error executing file operation action: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "File operation action failed"
        }


async def _execute_generic_action(action_description: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute generic placeholder action"""
    try:
        # Generic action logging
        action_details = {
            "description": action_description,
            "parameters": parameters,
            "timestamp": datetime.now().isoformat(),
            "source": "stimuli_team_decision",
            "reasoning": context.get("agent_reasoning", ""),
            "status": "logged"
        }
        
        # Save to generic action log
        action_log_file = "/tmp/stimuli_generic_actions.json"
        
        existing_actions = []
        if os.path.exists(action_log_file):
            try:
                with open(action_log_file, 'r') as f:
                    existing_actions = json.load(f)
            except Exception as e:
                logging.warning(f"⚠️ [STIMULI_EXECUTOR] Error loading existing actions: {e}")
        
        existing_actions.append(action_details)
        
        with open(action_log_file, 'w') as f:
            json.dump(existing_actions, f, indent=2)
        
        return {
            "success": True,
            "message": f"Generic action logged: {action_description[:50]}...",
            "action_type": "generic",
            "action_details": action_details,
            "total_actions": len(existing_actions)
        }
        
    except Exception as e:
        logging.error(f"❌ [STIMULI_EXECUTOR] Error executing generic action: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Generic action failed"
        }


async def _trigger_s1_avatar_response(context: Dict[str, Any], result: Dict[str, Any], action_type: str) -> bool:
    """
    Trigger S1 Avatar speech/animation via /process_text endpoint
    """
    try:
        # Only trigger avatar for successful actions
        if not result.get("success", False):
            logging.debug("🎭 [STIMULI_EXECUTOR] Skipping S1 avatar trigger - action was not successful")
            return False
        
        # Get S1 endpoint from environment or use default
        s1_endpoint = os.getenv("S1_AVATAR_ENDPOINT", "http://localhost:5001")
        process_text_url = f"{s1_endpoint}/process_text"
        
        # Generate appropriate response text based on action type and result
        response_text = _generate_avatar_response_text(action_type, result, context)
        
        if not response_text:
            logging.debug("🎭 [STIMULI_EXECUTOR] No response text generated for avatar")
            return False
        
        # Prepare payload for S1 avatar /process_text endpoint
        payload = {
            "text": response_text,
            "direct_speech": True,  # Use direct speech to avoid LLM processing 
            "autonomous_context": {
                "source": "stimuli_action_executor",
                "action_type": action_type,
                "stimuli_id": context.get("stimuli_id"),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Make async HTTP request to S1 avatar
        timeout = aiohttp.ClientTimeout(total=10.0)  # 10 second timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(process_text_url, json=payload) as response:
                if response.status == 200:
                    response_data = await response.json()
                    logging.info(f"✅ [STIMULI_EXECUTOR] S1 Avatar triggered successfully: {response_data.get('status', 'unknown')}")
                    return True
                else:
                    response_text = await response.text()
                    logging.warning(f"⚠️ [STIMULI_EXECUTOR] S1 Avatar request failed: HTTP {response.status} - {response_text}")
                    return False
                    
    except aiohttp.ClientError as e:
        logging.warning(f"⚠️ [STIMULI_EXECUTOR] S1 Avatar connection error: {e}")
        return False
    except asyncio.TimeoutError:
        logging.warning("⚠️ [STIMULI_EXECUTOR] S1 Avatar request timeout")
        return False
    except Exception as e:
        logging.error(f"❌ [STIMULI_EXECUTOR] Error triggering S1 Avatar: {e}")
        return False


def _generate_avatar_response_text(action_type: str, result: Dict[str, Any], context: Dict[str, Any]) -> Optional[str]:
    """
    Generate appropriate response text for the avatar based on action type and result
    """
    try:
        stimuli_content = context.get("stimuli_request", {}).get("content", "")
        agent_reasoning = context.get("agent_reasoning", "")
        
        # Generate response based on action type
        if action_type == "objective_update":
            objectives_added = result.get("objectives_added", 0)
            if objectives_added > 0:
                return f"I've updated the main team objectives with {objectives_added} new goals based on the recent stimuli."
            else:
                return "I've reviewed the objectives based on the recent input."
                
        elif action_type == "knowledge_push":
            cognee_pushed = result.get("cognee_pushed", False)
            if cognee_pushed:
                return "I've successfully stored new insights in the memory system for future reference."
            else:
                return "I've logged the new information for later analysis."
                
        elif action_type == "placeholder_action":
            action_details = result.get("action_details", {})
            description = action_details.get("description", "")
            if description:
                return f"I've executed the requested action: {description[:100]}"
            else:
                return "I've completed the requested action successfully."
                
        else:
            # Generic response
            if stimuli_content:
                return f"I've processed your input: {stimuli_content[:50]}{'...' if len(stimuli_content) > 50 else ''}"
            else:
                return "I've successfully processed the recent stimuli."
                
    except Exception as e:
        logging.error(f"❌ [STIMULI_EXECUTOR] Error generating avatar response text: {e}")
        return None