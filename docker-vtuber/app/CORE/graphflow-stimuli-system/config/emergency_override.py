"""
Emergency override handler for critical situations.

This module contains the emergency override logic that can be dynamically
loaded and executed when EMERGENCY_OVERRIDE decisions are made.

The handle_emergency function can be modified without restarting the system
to adapt to different emergency scenarios.
"""

import asyncio
from typing import Dict, Any
import logging

logger = logging.getLogger("emergency_override")


async def handle_emergency(context: Dict[str, Any]) -> bool:
    """
    Handle emergency override situations.
    
    This function is called when an EMERGENCY_OVERRIDE decision is made.
    It has access to system interfaces and the execution plan.
    
    Args:
        context: Dictionary containing:
            - system1_interface: Interface to avatar/speech system
            - system2_interface: Interface to multi-agent system
            - execution_plan: The current execution plan
            
    Returns:
        bool: True if emergency handling was successful
    """
    try:
        logger.warning("EMERGENCY OVERRIDE ACTIVATED")
        
        system1_interface = context.get("system1_interface")
        system2_interface = context.get("system2_interface")
        execution_plan = context.get("execution_plan")
        
        if not execution_plan:
            logger.error("No execution plan provided to emergency handler")
            return False
        
        # Extract emergency details
        emergency_type = execution_plan.execution_params.get("emergency_type", "unknown")
        priority = execution_plan.priority.value
        stimuli_content = execution_plan.execution_params.get("stimuli_content", "")
        
        logger.info(
            f"Handling emergency: type={emergency_type}, priority={priority}"
        )
        
        # Emergency response strategies based on type
        if emergency_type == "system_critical":
            return await handle_system_critical(
                system1_interface, system2_interface, execution_plan
            )
        elif emergency_type == "security_threat":
            return await handle_security_threat(
                system1_interface, system2_interface, execution_plan
            )
        elif emergency_type == "performance_degradation":
            return await handle_performance_degradation(
                system1_interface, system2_interface, execution_plan
            )
        else:
            # Default emergency handling
            return await handle_default_emergency(
                system1_interface, system2_interface, execution_plan
            )
            
    except Exception as e:
        logger.error(f"Emergency handler failed: {e}")
        return False


async def handle_system_critical(
    system1_interface,
    system2_interface,
    execution_plan
) -> bool:
    """Handle system-critical emergencies."""
    try:
        tasks = []
        
        # 1. Notify through avatar if available
        if system1_interface:
            emergency_message = (
                "System critical alert detected. "
                "Initiating emergency protocols."
            )
            
            task1 = system1_interface.trigger_avatar_response(
                emergency_message,
                {
                    "stimuli_id": execution_plan.stimuli_id,
                    "priority": "critical",
                    "emotion": "serious",
                    "emergency": True
                }
            )
            tasks.append(task1)
        
        # 2. Alert all agents if available
        if system2_interface:
            from ..src.models.stimuli import AnalyzedStimuli, StimuliCategory
            
            emergency_stimuli = AnalyzedStimuli(
                id=execution_plan.stimuli_id,
                content=execution_plan.execution_params.get("stimuli_content", ""),
                source="emergency_override",
                category=StimuliCategory.EMERGENCY,
                confidence=1.0
            )
            
            task2 = system2_interface.submit_for_analysis(emergency_stimuli)
            tasks.append(task2)
        
        # Execute all emergency tasks
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check if at least one succeeded
            success_count = sum(
                1 for r in results 
                if not isinstance(r, Exception) and r
            )
            
            return success_count > 0
        
        return False
        
    except Exception as e:
        logger.error(f"System critical handler failed: {e}")
        return False


async def handle_security_threat(
    system1_interface,
    system2_interface,
    execution_plan
) -> bool:
    """Handle security threat emergencies."""
    try:
        # 1. Log security event
        logger.critical(
            "SECURITY THREAT DETECTED",
            stimuli_id=execution_plan.stimuli_id,
            threat_details=execution_plan.execution_params
        )
        
        # 2. Notify through avatar with warning
        if system1_interface:
            security_message = (
                "Security alert. Protective measures have been activated. "
                "Please stand by for further instructions."
            )
            
            await system1_interface.trigger_avatar_response(
                security_message,
                {
                    "stimuli_id": execution_plan.stimuli_id,
                    "priority": "critical",
                    "emotion": "alert",
                    "security_alert": True
                }
            )
        
        # 3. Trigger security analysis
        if system2_interface:
            # In a real implementation, this would trigger
            # security-specific agent workflows
            pass
        
        return True
        
    except Exception as e:
        logger.error(f"Security threat handler failed: {e}")
        return False


async def handle_performance_degradation(
    system1_interface,
    system2_interface,
    execution_plan
) -> bool:
    """Handle performance degradation emergencies."""
    try:
        # 1. Switch to degraded mode
        logger.warning(
            "Performance degradation detected, switching to degraded mode",
            stimuli_id=execution_plan.stimuli_id
        )
        
        # 2. Notify users of degraded performance
        if system1_interface:
            degradation_message = (
                "System performance is currently limited. "
                "Some features may be temporarily unavailable."
            )
            
            # Use lower priority to not overwhelm system
            await system1_interface.trigger_avatar_response(
                degradation_message,
                {
                    "stimuli_id": execution_plan.stimuli_id,
                    "priority": "low",
                    "emotion": "apologetic"
                }
            )
        
        # 3. Reduce load on System2
        # In a real implementation, this might pause non-critical agents
        
        return True
        
    except Exception as e:
        logger.error(f"Performance degradation handler failed: {e}")
        return False


async def handle_default_emergency(
    system1_interface,
    system2_interface,
    execution_plan
) -> bool:
    """Default emergency handling for unknown emergency types."""
    try:
        logger.warning(
            "Handling unknown emergency type",
            stimuli_id=execution_plan.stimuli_id,
            execution_params=execution_plan.execution_params
        )
        
        # Execute both systems with high priority
        tasks = []
        
        if system1_interface:
            content = execution_plan.execution_params.get(
                "stimuli_content", 
                "Emergency situation detected. Processing with high priority."
            )
            
            task1 = system1_interface.trigger_avatar_response(
                content,
                {
                    "stimuli_id": execution_plan.stimuli_id,
                    "priority": "high",
                    "emergency": True
                }
            )
            tasks.append(task1)
        
        if system2_interface:
            # Submit to agents for analysis
            from ..src.models.stimuli import AnalyzedStimuli, StimuliCategory
            
            emergency_stimuli = AnalyzedStimuli(
                id=execution_plan.stimuli_id,
                content=execution_plan.execution_params.get("stimuli_content", ""),
                source="emergency_override",
                category=StimuliCategory.EMERGENCY,
                confidence=0.9
            )
            
            task2 = system2_interface.submit_for_analysis(emergency_stimuli)
            tasks.append(task2)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results
            failures = [r for r in results if isinstance(r, Exception)]
            if failures:
                logger.error(
                    f"Some emergency tasks failed: {failures}"
                )
            
            return len(failures) < len(results)  # Partial success is still success
        
        return False
        
    except Exception as e:
        logger.error(f"Default emergency handler failed: {e}")
        return False


# Custom emergency handlers can be added below
# These will be called based on specific emergency types

async def handle_user_safety_emergency(
    system1_interface,
    system2_interface,
    execution_plan
) -> bool:
    """Handle user safety related emergencies."""
    # Implementation for user safety scenarios
    pass


async def handle_content_violation_emergency(
    system1_interface,
    system2_interface,
    execution_plan
) -> bool:
    """Handle content violation emergencies."""
    # Implementation for content violations
    pass