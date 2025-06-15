"""
Agent-Tool Bridge: Integrates AutoGen agent decisions with tool execution
This module parses agent responses and executes the appropriate tools
"""

import re
import logging
from typing import Dict, Optional, Tuple, Any
from autogen_agent.tool_registry import ToolRegistry


class AgentToolBridge:
    """Bridges the gap between AutoGen agent conversations and tool execution"""
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.execution_patterns = [
            # Pattern 1: Explicit EXECUTE_TOOL command
            r'EXECUTE_TOOL:\s*(\w+)(?:\s+with\s+context:\s*(.+))?',
            # Pattern 2: "I will/should execute/run [tool_name]"
            r'(?:I will|I should|Let me|I\'ll)\s+(?:execute|run|use|apply)\s+(?:the\s+)?(\w+)(?:\s+tool)?',
            # Pattern 3: "Executing/Running [tool_name]"
            r'(?:Executing|Running|Using|Applying)\s+(?:the\s+)?(\w+)(?:\s+tool)?',
            # Pattern 4: Tool recommendation format
            r'(?:Recommend|Suggesting|Selected):\s*(\w+)(?:\s+tool)?',
            # Pattern 5: Action format
            r'ACTION:\s*(?:execute|run|use)\s+(\w+)',
        ]
        logging.info("🌉 [AGENT_TOOL_BRIDGE] Initialized with tool registry")
    
    def parse_agent_response(self, agent_name: str, response: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Parse agent response to extract tool execution commands
        Returns: (tool_name, context) or None if no execution command found
        """
        if not response:
            return None
            
        # Try each pattern to find tool execution commands
        for pattern in self.execution_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                tool_name = match.group(1).lower()
                
                # Check if this is a valid tool
                if tool_name in self.tool_registry.tools:
                    # Extract context if provided
                    context = {}
                    if len(match.groups()) > 1 and match.group(2):
                        # Simple context parsing (could be enhanced)
                        context_str = match.group(2)
                        context = self._parse_context_string(context_str)
                    
                    logging.info(f"🎯 [AGENT_TOOL_BRIDGE] Agent '{agent_name}' wants to execute tool: {tool_name}")
                    return tool_name, context
                else:
                    logging.debug(f"⚠️ [AGENT_TOOL_BRIDGE] Agent mentioned unknown tool: {tool_name}")
        
        # Check for implicit tool suggestions based on content
        implicit_tool = self._detect_implicit_tool_request(response)
        if implicit_tool:
            logging.info(f"🔍 [AGENT_TOOL_BRIDGE] Detected implicit tool request: {implicit_tool}")
            return implicit_tool, {}
            
        return None
    
    def _parse_context_string(self, context_str: str) -> Dict[str, Any]:
        """Parse a context string into a dictionary"""
        context = {}
        
        # Simple key-value parsing (format: key=value, key2=value2)
        pairs = re.findall(r'(\w+)\s*=\s*([^,]+)', context_str)
        for key, value in pairs:
            # Try to parse as number
            try:
                if '.' in value:
                    context[key] = float(value)
                else:
                    context[key] = int(value)
            except ValueError:
                # Keep as string, strip quotes if present
                context[key] = value.strip().strip('"\'')
        
        return context
    
    def _detect_implicit_tool_request(self, response: str) -> Optional[str]:
        """Detect implicit tool requests based on response content"""
        response_lower = response.lower()
        
        # Goal-related keywords
        if any(keyword in response_lower for keyword in ['goal', 'objective', 'target', 'milestone', 'achievement']):
            if 'create' in response_lower or 'set' in response_lower or 'establish' in response_lower:
                return 'goal_management_tools'
        
        # Performance/optimization keywords
        if any(keyword in response_lower for keyword in ['optimize', 'improve', 'performance', 'bottleneck', 'slow']):
            if 'code' in response_lower or 'system' in response_lower:
                return 'core_evolution_tool'
        
        # VTuber keywords
        if any(keyword in response_lower for keyword in ['vtuber', 'avatar', 'stream', 'audience']):
            if 'activate' in response_lower or 'start' in response_lower:
                return 'advanced_vtuber_control'
        
        return None
    
    async def execute_from_responses(self, agent_responses: Dict[str, str], context: Dict[str, Any], 
                                   vtuber_client=None, scb_client=None) -> Dict[str, Any]:
        """
        Parse all agent responses and execute any requested tools
        Returns summary of executions
        """
        executions = []
        
        for agent_name, response in agent_responses.items():
            # Parse response for tool execution
            parsed = self.parse_agent_response(agent_name, response)
            
            if parsed:
                tool_name, tool_context = parsed
                
                # Merge with provided context
                enhanced_context = {**context, **tool_context}
                enhanced_context['requested_by_agent'] = agent_name
                
                try:
                    # Execute the tool
                    result = await self.tool_registry.execute_tool_with_clients_async(
                        tool_name, enhanced_context, vtuber_client, scb_client
                    )
                    
                    if result:
                        executions.append({
                            'agent': agent_name,
                            'tool': tool_name,
                            'success': result.get('success', True),
                            'result': result
                        })
                        logging.info(f"✅ [AGENT_TOOL_BRIDGE] Executed {tool_name} requested by {agent_name}")
                    else:
                        logging.warning(f"⚠️ [AGENT_TOOL_BRIDGE] Tool {tool_name} returned no result")
                        
                except Exception as e:
                    logging.error(f"❌ [AGENT_TOOL_BRIDGE] Failed to execute {tool_name}: {e}")
                    executions.append({
                        'agent': agent_name,
                        'tool': tool_name,
                        'success': False,
                        'error': str(e)
                    })
        
        # If no explicit executions but we're in autonomous mode, use intelligent selection
        if not executions and context.get('autonomous', False):
            logging.info("🤖 [AGENT_TOOL_BRIDGE] No explicit tool requests, using intelligent selection")
            
            # Let the tool registry select based on context
            selected_tool = self.tool_registry.select_tool(context)
            if selected_tool:
                tool_name = [name for name, func in self.tool_registry.tools.items() if func == selected_tool][0]
                
                try:
                    result = await self.tool_registry.execute_tool_with_clients_async(
                        tool_name, context, vtuber_client, scb_client
                    )
                    
                    if result:
                        executions.append({
                            'agent': 'intelligent_selection',
                            'tool': tool_name,
                            'success': result.get('success', True),
                            'result': result
                        })
                        logging.info(f"✅ [AGENT_TOOL_BRIDGE] Intelligently selected and executed {tool_name}")
                        
                except Exception as e:
                    logging.error(f"❌ [AGENT_TOOL_BRIDGE] Failed to execute intelligently selected {tool_name}: {e}")
        
        return {
            'executions': executions,
            'total_executions': len(executions),
            'successful_executions': sum(1 for e in executions if e.get('success', False))
        }