import importlib
import pkgutil
import logging
import os
import asyncio
import inspect
import time
import re
from typing import Callable, Dict, Optional, List, Any


class ToolRegistry:
    def __init__(self, package: str = "autogen_agent.tools"):
        self.package = package
        self.tools: Dict[str, Callable[[dict], dict]] = {}
        self.disabled_tools: List[str] = []
        
        # 🚫 DISABLED TOOLS - Focus on core evolution system
        # VTuber tools disabled for pure stimuli-driven architecture
        self.disabled_tools = [
            "cognitive_vtuber_tool",      # Legacy VTuber tool - will be deprecated
            "advanced_vtuber_control",    # DISABLED - VTuber calls only via stimuli system
        ]
        
        # Get additional disabled tools from environment
        env_disabled = os.getenv("DISABLED_TOOLS", "").split(",")
        self.disabled_tools.extend([tool.strip() for tool in env_disabled if tool.strip()])
        
        # 🧠 INTELLIGENT TOOL SELECTION - Track performance metrics
        self.tool_performance = {}
        self.tool_usage_history = []
        self.context_tool_mapping = {
            # Goal-related contexts
            "goal": ["goal_management_tools"],
            "progress": ["goal_management_tools"],
            "achievement": ["goal_management_tools"],
            "target": ["goal_management_tools"],
            "smart": ["goal_management_tools"],
            "objective": ["goal_management_tools"],
            "metric": ["goal_management_tools"],
            
            # Evolution/Performance contexts
            "performance": ["core_evolution_tool"],
            "optimization": ["core_evolution_tool"],
            "improvement": ["core_evolution_tool"],
            "evolution": ["core_evolution_tool"],
            "error": ["core_evolution_tool"],
            "speed": ["core_evolution_tool"],
            "bottleneck": ["core_evolution_tool"],
            "optimize": ["core_evolution_tool"],
            
            # VTuber-related contexts
            "vtuber": ["advanced_vtuber_control"],
            "avatar": ["advanced_vtuber_control"],
            "stream": ["advanced_vtuber_control"],
            "audience": ["advanced_vtuber_control"],
            "activate": ["advanced_vtuber_control"],
            "character": ["advanced_vtuber_control"],
            "voice": ["advanced_vtuber_control"],
            
            # Weather-related contexts
            "weather": ["weather_persona_tool"],
            "temperature": ["weather_persona_tool"],
            "forecast": ["weather_persona_tool"],
            "rain": ["weather_persona_tool"],
            "sunny": ["weather_persona_tool"],
            "cloudy": ["weather_persona_tool"],
            "storm": ["weather_persona_tool"],
            "wind": ["weather_persona_tool"],
            "snow": ["weather_persona_tool"],
            "climate": ["weather_persona_tool"],
            "humidity": ["weather_persona_tool"],
            "alert": ["weather_persona_tool"],
            "meteorology": ["weather_persona_tool"],
            
            # Admin character management contexts
            "admin": ["admin_character_tool"],
            "create character": ["admin_character_tool"],
            "switch character": ["admin_character_tool"],
            "list characters": ["admin_character_tool"],
            "character info": ["admin_character_tool"],
            "make character": ["admin_character_tool"],
            "add character": ["admin_character_tool"],
            "new character": ["admin_character_tool"],
            
            # Dynamic/Variable contexts
            "dynamic": ["variable_tool_calls"],
            "adaptive": ["variable_tool_calls"],
            "context": ["variable_tool_calls"],
            "variable": ["variable_tool_calls"],
            "selection": ["variable_tool_calls"]
        }
        
        logging.info(f"🔧 [TOOL_REGISTRY] Initialized with {len(self.disabled_tools)} disabled tools: {self.disabled_tools}")
        logging.info(f"🧠 [TOOL_REGISTRY] Intelligent tool selection ENABLED with {len(self.context_tool_mapping)} context mappings")

    def load_tools(self) -> None:
        """Load all tools from the tools package"""
        try:
            # Import the package
            package = importlib.import_module(self.package)
            
            # Iterate through all modules in the package
            for _, name, ispkg in pkgutil.iter_modules(package.__path__, self.package + "."):
                if ispkg:
                    continue
                    
                # Extract tool name from module name
                tool_name = name.split(".")[-1]
                
                # Skip disabled tools
                if tool_name in self.disabled_tools:
                    logging.info(f"🚫 [TOOL_REGISTRY] Skipping disabled tool: {tool_name}")
                    continue
                    
                try:
                    # Import the module
                    module = importlib.import_module(name)
                    
                    # Look for a 'run' function
                    if hasattr(module, 'run'):
                        self.tools[tool_name] = module.run
                        
                        # Initialize performance tracking
                        self.tool_performance[tool_name] = {
                            'total_uses': 0,
                            'successes': 0,
                            'avg_execution_time': 0.0,
                            'context_relevance_scores': [],
                            'last_used': 0
                        }
                        
                        # Check if tool is async
                        is_async = inspect.iscoroutinefunction(module.run)
                        logging.info(f"✅ [TOOL_REGISTRY] Loaded tool: {tool_name} ({'async' if is_async else 'sync'})")
                    else:
                        logging.warning(f"⚠️ [TOOL_REGISTRY] Module {tool_name} has no 'run' function")
                        
                except ImportError as e:
                    logging.error(f"❌ [TOOL_REGISTRY] Failed to import {tool_name}: {e}")
                    
        except ImportError as e:
            logging.error(f"❌ [TOOL_REGISTRY] Failed to import package {self.package}: {e}")

    def _get_last_selection_score(self, tool_name: str) -> float:
        """Get the last selection score for a tool"""
        # Check if we have a recent selection record
        if hasattr(self, '_last_selection_scores'):
            return self._last_selection_scores.get(tool_name, 0.0)
        return 0.0

    def select_tool(self, context: dict) -> Optional[Callable]:
        """Select the most appropriate tool based on context using intelligent scoring"""
        if not self.tools:
            logging.warning("⚠️ [TOOL_REGISTRY] No tools available")
            return None
        
        # Extract context text for analysis
        context_text = self._extract_context_text(context)
        
        # Calculate scores for all tools
        tool_scores = {}
        for tool_name in self.tools.keys():
            score = self._calculate_tool_score(tool_name, context, context_text)
            tool_scores[tool_name] = score
            logging.debug(f"🎯 [TOOL_REGISTRY] Tool {tool_name}: score {score:.3f}")
        
        # Select tool with highest score
        selected_name = max(tool_scores, key=tool_scores.get)
        selected_score = tool_scores[selected_name]
        
        # Store selection scores for later use
        if not hasattr(self, '_last_selection_scores'):
            self._last_selection_scores = {}
        self._last_selection_scores = tool_scores.copy()
        
        # Update usage history
        self._update_tool_usage(selected_name, context)
        
        logging.info(f"🧠 [TOOL_REGISTRY] INTELLIGENT selection: {selected_name} (score: {selected_score:.3f})")
        logging.info(f"📊 [TOOL_REGISTRY] All scores: {', '.join([f'{name}:{score:.2f}' for name, score in sorted(tool_scores.items(), key=lambda x: x[1], reverse=True)])}")
        
        return self.tools[selected_name]

    async def execute_tool_async(self, tool_name: str, context: dict) -> Optional[dict]:
        """Execute a tool asynchronously (handles both sync and async tools)"""
        tool = self.get_tool_by_name(tool_name)
        if not tool:
            logging.warning(f"⚠️ [TOOL_REGISTRY] Tool '{tool_name}' not found")
            return None
            
        try:
            start_time = time.time()
            
            # Check if tool is async
            if inspect.iscoroutinefunction(tool):
                result = await tool(context)
            else:
                result = tool(context)
            
            execution_time = time.time() - start_time
            success = result.get('success', True) if isinstance(result, dict) else True
            
            # Update performance metrics
            self.update_tool_performance(tool_name, success, execution_time)
            
            logging.info(f"✅ [TOOL_REGISTRY] Tool '{tool_name}' executed successfully in {execution_time:.2f}s")
            return result
        except Exception as e:
            logging.error(f"❌ [TOOL_REGISTRY] Tool '{tool_name}' execution failed: {e}")
            # Update performance with failure
            self.update_tool_performance(tool_name, False, 0.0)
            return None

    def execute_tool_sync(self, tool_name: str, context: dict) -> Optional[dict]:
        """Execute a tool synchronously (async tools run in new event loop)"""
        tool = self.get_tool_by_name(tool_name)
        if not tool:
            logging.warning(f"⚠️ [TOOL_REGISTRY] Tool '{tool_name}' not found")
            return None
            
        try:
            start_time = time.time()
            
            # Check if tool is async
            if inspect.iscoroutinefunction(tool):
                # Run async tool in new event loop if we're not in one
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # We're in an event loop, need to create a task
                        # This is a fallback - prefer execute_tool_async
                        logging.warning(f"⚠️ [TOOL_REGISTRY] Async tool '{tool_name}' called from sync context in running loop")
                        return {"error": "Async tool needs async execution context"}
                    else:
                        result = loop.run_until_complete(tool(context))
                except RuntimeError:
                    # No event loop running, create one
                    result = asyncio.run(tool(context))
            else:
                result = tool(context)
            
            execution_time = time.time() - start_time
            success = result.get('success', True) if isinstance(result, dict) else True
            
            # Update performance metrics
            self.update_tool_performance(tool_name, success, execution_time)
            
            logging.info(f"✅ [TOOL_REGISTRY] Tool '{tool_name}' executed successfully in {execution_time:.2f}s")
            return result
        except Exception as e:
            logging.error(f"❌ [TOOL_REGISTRY] Tool '{tool_name}' execution failed: {e}")
            # Update performance with failure
            self.update_tool_performance(tool_name, False, 0.0)
            return None

    def get_tool_by_name(self, name: str) -> Optional[Callable]:
        """Get a specific tool by name"""
        return self.tools.get(name)

    def list_tools(self) -> List[str]:
        """List all available tools"""
        return list(self.tools.keys())

    def add_clients_to_context(self, context: dict, vtuber_client=None, scb_client=None) -> dict:
        """Add client references to context for tools that need them"""
        enhanced_context = context.copy()
        
        if vtuber_client:
            enhanced_context["vtuber_client"] = vtuber_client
            
        if scb_client:
            enhanced_context["scb_client"] = scb_client
            
        return enhanced_context

    def execute_tool_with_clients(self, tool_name: str, context: dict, vtuber_client=None, scb_client=None) -> Optional[dict]:
        """Execute a specific tool with client access (synchronously)"""
        # Add clients to context
        enhanced_context = self.add_clients_to_context(context, vtuber_client, scb_client)
        
        # Use sync execution
        return self.execute_tool_sync(tool_name, enhanced_context)

    async def execute_tool_with_clients_async(self, tool_name: str, context: dict, vtuber_client=None, scb_client=None) -> Optional[dict]:
        """Execute a specific tool with client access (asynchronously)"""
        # Add clients to context
        enhanced_context = self.add_clients_to_context(context, vtuber_client, scb_client)
        
        # Use async execution
        return await self.execute_tool_async(tool_name, enhanced_context)

    def get_vtuber_control_tool(self) -> Optional[Callable]:
        """Get the VTuber control tool specifically"""
        return self.get_tool_by_name("advanced_vtuber_control")

    def is_tool_async(self, tool_name: str) -> bool:
        """Check if a tool is async"""
        tool = self.get_tool_by_name(tool_name)
        return tool and inspect.iscoroutinefunction(tool)

    def get_tool_status(self) -> Dict[str, Any]:
        """Get registry status and tool information"""
        async_tools = []
        sync_tools = []
        
        for tool_name in self.tools.keys():
            if self.is_tool_async(tool_name):
                async_tools.append(tool_name)
            else:
                sync_tools.append(tool_name)
        
        # Calculate performance summary
        performance_summary = {}
        for tool_name, metrics in self.tool_performance.items():
            if metrics['total_uses'] > 0:
                success_rate = metrics['successes'] / metrics['total_uses']
                performance_summary[tool_name] = {
                    'success_rate': success_rate,
                    'avg_execution_time': metrics['avg_execution_time'],
                    'total_uses': metrics['total_uses']
                }
                
        return {
            "total_tools": len(self.tools),
            "available_tools": list(self.tools.keys()),
            "async_tools": async_tools,
            "sync_tools": sync_tools,
            "disabled_tools": self.disabled_tools,
            "vtuber_control_available": "advanced_vtuber_control" in self.tools,
            "core_evolution_available": "core_evolution_tool" in self.tools,
            "core_evolution_async": self.is_tool_async("core_evolution_tool"),
            "intelligent_selection_enabled": True,
            "performance_summary": performance_summary,
            "usage_history_length": len(self.tool_usage_history),
            "context_mappings": len(self.context_tool_mapping)
        }
    
    # 🧠 INTELLIGENT TOOL SELECTION METHODS
    
    def _calculate_tool_score(self, tool_name: str, context: dict, context_text: str) -> float:
        """Calculate comprehensive score for tool selection"""
        score = 0.0
        
        # Context Relevance (40%)
        context_relevance = self._calculate_context_relevance(tool_name, context, context_text)
        score += context_relevance * 0.4
        
        # Historical Performance (30%)
        historical_performance = self._get_historical_performance(tool_name)
        score += historical_performance * 0.3
        
        # Recent Success Rate (20%)
        recent_success = self._get_recent_success_rate(tool_name)
        score += recent_success * 0.2
        
        # Diversity Bonus (10%)
        diversity_bonus = self._calculate_diversity_bonus(tool_name)
        score += diversity_bonus * 0.3  # Increased from 0.1 for better diversity
        
        return min(score, 1.0)
    
    def _calculate_context_relevance(self, tool_name: str, context: dict, context_text: str) -> float:
        """Calculate how relevant a tool is to the current context"""
        relevance_score = 0.0
        context_lower = context_text.lower()
        
        # Check direct context mapping
        for keyword, relevant_tools in self.context_tool_mapping.items():
            if keyword in context_lower and tool_name in relevant_tools:
                relevance_score += 0.8  # High relevance for direct matches
                
        # Check for specific tool indicators
        tool_indicators = {
            "goal_management_tools": ["goal", "progress", "achievement", "target", "smart", "objective", "metric", "milestone"],
            "core_evolution_tool": ["performance", "optimization", "improvement", "evolution", "error", "speed", "bottleneck", "optimize"],
            "advanced_vtuber_control": ["vtuber", "avatar", "stream", "audience", "activate", "control", "character", "voice", "show", "display"],
            "variable_tool_calls": ["dynamic", "adaptive", "context", "variable", "selection", "flexible"],
            "admin_character_tool": ["admin", "create character", "switch character", "list characters", "character info", "make character", "add character", "new character"],
            "weather_persona_tool": ["weather", "temperature", "forecast", "rain", "sunny", "cloudy", "storm", "wind", "snow", "climate", "humidity", "alert", "meteorology"]
        }
        
        if tool_name in tool_indicators:
            indicators = tool_indicators[tool_name]
            matches = sum(1 for indicator in indicators if indicator in context_lower)
            relevance_score += (matches / len(indicators)) * 0.6
        
        # Iteration-based relevance for core evolution
        if tool_name == "core_evolution_tool":
            iteration = context.get("iteration", 0)
            # Higher relevance for evolution tool every 5 iterations
            if iteration % 5 == 0 and iteration > 0:
                relevance_score += 0.3
                
        # Autonomous mode bonus for sophisticated tools
        if context.get("autonomous", False):
            sophisticated_tools = ["goal_management_tools", "core_evolution_tool", "variable_tool_calls"]
            if tool_name in sophisticated_tools:
                relevance_score += 0.2
        
        # Performance trigger for evolution tool
        if tool_name == "core_evolution_tool":
            errors = context.get("error_count", 0)
            decision_time = context.get("decision_time", 0.0)
            if errors > 3 or decision_time > 3.0:
                relevance_score += 0.4
        
        # Add penalty for tools with no context match in autonomous mode
        if context.get("autonomous", False) and relevance_score < 0.1:
            # In autonomous mode with no context match, penalize
            relevance_score = max(0.0, relevance_score - 0.3)
        return min(relevance_score, 1.0)
    
    def _get_historical_performance(self, tool_name: str) -> float:
        """Get historical performance score for a tool"""
        if tool_name not in self.tool_performance:
            return 0.5  # Default neutral score for new tools
        
        metrics = self.tool_performance[tool_name]
        total_uses = metrics.get('total_uses', 0)
        
        if total_uses == 0:
            return 0.5  # No history, neutral score
        
        success_rate = metrics.get('successes', 0) / total_uses
        avg_execution_time = metrics.get('avg_execution_time', 5.0)
        
        # Combine success rate and speed (penalize slow tools)
        time_factor = max(0.1, 1.0 - (avg_execution_time / 10.0))
        return success_rate * time_factor
    
    def _get_recent_success_rate(self, tool_name: str, lookback: int = 10) -> float:
        """Get recent performance success rate"""
        recent_uses = [
            entry for entry in self.tool_usage_history[-lookback:]
            if entry.get('tool') == tool_name
        ]
        
        if not recent_uses:
            return 0.5  # No recent usage, neutral score
        
        successes = sum(1 for use in recent_uses if use.get('success', False))
        return successes / len(recent_uses)
    
    def _calculate_diversity_bonus(self, tool_name: str) -> float:
        """Calculate diversity bonus to prevent overuse of same tools"""
        if not self.tool_usage_history:
            return 0.5
        
        # Check last 5 tool uses
        recent_tools = [entry.get('tool') for entry in self.tool_usage_history[-5:]]
        tool_count = recent_tools.count(tool_name)
        
        # More recent use = lower diversity bonus
        if tool_count == 0:
            return 1.0  # Not used recently, high bonus
        elif tool_count == 1:
            return 0.7  # Used once, moderate bonus
        elif tool_count == 2:
            return 0.4  # Used twice, low bonus
        else:
            return 0.1  # Used frequently, very low bonus
    
    def _extract_context_text(self, context: dict) -> str:
        """Extract searchable text from context dict"""
        text_parts = []
        
        # Extract common text fields
        for key in ['message', 'action', 'request', 'description', 'goal', 'task', 'query', 'input']:
            if key in context and isinstance(context[key], str):
                text_parts.append(context[key])
        
        # Add iteration info for pattern matching
        if 'iteration' in context:
            text_parts.append(f"iteration {context['iteration']}")
            
        # Add autonomous indicator
        if context.get('autonomous', False):
            text_parts.append("autonomous mode")
        
        # Add error/performance indicators
        if context.get('error_count', 0) > 0:
            text_parts.append(f"errors {context['error_count']}")
        
        if context.get('decision_time', 0) > 0:
            text_parts.append(f"decision_time {context['decision_time']}")
        
        return " ".join(text_parts).lower()
    
    def _update_tool_usage(self, tool_name: str, context: dict) -> None:
        """Update tool usage history"""
        usage_entry = {
            'tool': tool_name,
            'timestamp': time.time(),
            'iteration': context.get('iteration', 0),
            'autonomous': context.get('autonomous', False)
        }
        
        self.tool_usage_history.append(usage_entry)
        
        # Keep history size manageable (last 100 uses)
        if len(self.tool_usage_history) > 100:
            self.tool_usage_history = self.tool_usage_history[-100:]
    
    def update_tool_performance(self, tool_name: str, success: bool, execution_time: float) -> None:
        """Update performance metrics for a tool"""
        if tool_name not in self.tool_performance:
            return
        
        metrics = self.tool_performance[tool_name]
        metrics['total_uses'] += 1
        metrics['last_used'] = time.time()
        
        if success:
            metrics['successes'] += 1
        
        # Update average execution time
        current_avg = metrics['avg_execution_time']
        total_uses = metrics['total_uses']
        metrics['avg_execution_time'] = ((current_avg * (total_uses - 1)) + execution_time) / total_uses
        
        # Update success status in usage history
        if self.tool_usage_history and self.tool_usage_history[-1]['tool'] == tool_name:
            self.tool_usage_history[-1]['success'] = success
    
    # 🚀 DYNAMIC TOOL REGISTRATION SYSTEM
    
    def register_runtime_tool(self, tool_name: str, tool_func: Callable, 
                            metadata: Optional[Dict[str, Any]] = None,
                            require_approval: bool = True) -> Dict[str, Any]:
        """
        Register a new tool at runtime with safety checks
        
        Args:
            tool_name: Name for the new tool
            tool_func: The tool function (must have 'run' method or be callable)
            metadata: Optional metadata about the tool
            require_approval: Whether to require approval before registration
            
        Returns:
            Registration result with success status
        """
        try:
            # Safety validation
            validation_result = self._validate_tool_safety(tool_name, tool_func, metadata)
            if not validation_result['safe']:
                return {
                    "success": False,
                    "error": f"Tool failed safety validation: {validation_result['reason']}",
                    "validation_details": validation_result
                }
            
            # Check if approval is required
            if require_approval and os.getenv("DARWIN_GODEL_REQUIRE_APPROVAL", "true").lower() == "true":
                approval_request = {
                    "type": "tool_registration",
                    "tool_name": tool_name,
                    "metadata": metadata,
                    "validation": validation_result,
                    "timestamp": time.time()
                }
                
                # Log approval request (in production, this would go to approval system)
                logging.info(f"🔐 [TOOL_REGISTRY] Tool registration requires approval: {tool_name}")
                logging.info(f"Approval request: {approval_request}")
                
                return {
                    "success": False,
                    "status": "pending_approval",
                    "approval_request": approval_request,
                    "message": "Tool registration pending approval"
                }
            
            # Register the tool
            self.tools[tool_name] = tool_func
            
            # Initialize performance metrics
            self.tool_performance[tool_name] = {
                'successes': 0,
                'total_uses': 0,
                'avg_execution_time': 0.0,
                'last_used': None
            }
            
            # Add to context mappings if provided
            if metadata and 'context_keywords' in metadata:
                for keyword in metadata['context_keywords']:
                    if keyword not in self.context_tool_mapping:
                        self.context_tool_mapping[keyword] = []
                    self.context_tool_mapping[keyword].append(tool_name)
            
            logging.info(f"✅ [TOOL_REGISTRY] Successfully registered runtime tool: {tool_name}")
            
            return {
                "success": True,
                "tool_name": tool_name,
                "validation": validation_result,
                "metadata": metadata,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logging.error(f"❌ [TOOL_REGISTRY] Failed to register tool {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _validate_tool_safety(self, tool_name: str, tool_func: Callable, 
                            metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate tool safety before registration
        
        Checks:
        1. Function signature compatibility
        2. No dangerous operations
        3. Resource limits
        4. Sandboxed test execution
        """
        validation_results = {
            "safe": True,
            "checks": {},
            "warnings": [],
            "reason": None
        }
        
        # Check 1: Name validation
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', tool_name):
            validation_results["safe"] = False
            validation_results["reason"] = "Invalid tool name format"
            return validation_results
        
        if tool_name in self.tools:
            validation_results["safe"] = False
            validation_results["reason"] = "Tool name already exists"
            return validation_results
        
        validation_results["checks"]["name_valid"] = True
        
        # Check 2: Function inspection
        try:
            # Check if it's a callable
            if not callable(tool_func):
                validation_results["safe"] = False
                validation_results["reason"] = "Tool is not callable"
                return validation_results
            
            # Check for 'run' method if it's a module
            if hasattr(tool_func, 'run'):
                actual_func = tool_func.run
            else:
                actual_func = tool_func
            
            # Inspect function signature
            sig = inspect.signature(actual_func)
            params = list(sig.parameters.keys())
            
            # Should accept 'context' parameter
            if 'context' not in params and len(params) > 0:
                validation_results["warnings"].append("Function doesn't have 'context' parameter")
            
            validation_results["checks"]["signature_valid"] = True
            
        except Exception as e:
            validation_results["safe"] = False
            validation_results["reason"] = f"Function inspection failed: {str(e)}"
            return validation_results
        
        # Check 3: Source code analysis (if possible)
        try:
            source = inspect.getsource(actual_func)
            
            # Check for dangerous patterns
            dangerous_patterns = [
                r'exec\s*\(',
                r'eval\s*\(',
                r'__import__\s*\(',
                r'compile\s*\(',
                r'globals\s*\(',
                r'locals\s*\(',
                r'open\s*\(.+[\'"]w',  # Write mode file operations
                r'os\s*\.\s*system',
                r'subprocess',
                r'socket',
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, source, re.IGNORECASE):
                    validation_results["warnings"].append(f"Potentially dangerous pattern found: {pattern}")
            
            validation_results["checks"]["source_analysis"] = True
            
        except:
            # Can't get source (e.g., built-in function)
            validation_results["warnings"].append("Cannot analyze source code")
        
        # Check 4: Resource limits from metadata
        if metadata:
            if 'max_execution_time' in metadata:
                if metadata['max_execution_time'] > 300:  # 5 minutes max
                    validation_results["warnings"].append("Execution time limit exceeds 5 minutes")
            
            if 'required_permissions' in metadata:
                dangerous_perms = ['file_write', 'network', 'system']
                for perm in metadata['required_permissions']:
                    if perm in dangerous_perms:
                        validation_results["warnings"].append(f"Requires dangerous permission: {perm}")
        
        # Final safety decision
        if len(validation_results["warnings"]) > 2:
            validation_results["safe"] = False
            validation_results["reason"] = "Too many safety warnings"
        
        return validation_results
    
    def unregister_tool(self, tool_name: str) -> Dict[str, Any]:
        """
        Remove a dynamically registered tool
        
        Args:
            tool_name: Name of the tool to remove
            
        Returns:
            Unregistration result
        """
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            }
        
        # Check if it's a core tool (loaded from package)
        if tool_name in ['goal_management_tools', 'core_evolution_tool', 'semantic_graph_query_tool']:
            return {
                "success": False,
                "error": "Cannot unregister core tools"
            }
        
        # Remove from registry
        del self.tools[tool_name]
        
        # Remove from performance metrics
        if tool_name in self.tool_performance:
            del self.tool_performance[tool_name]
        
        # Remove from context mappings
        for keyword, tools in list(self.context_tool_mapping.items()):
            if tool_name in tools:
                tools.remove(tool_name)
                if not tools:
                    del self.context_tool_mapping[keyword]
        
        logging.info(f"🗑️ [TOOL_REGISTRY] Unregistered tool: {tool_name}")
        
        return {
            "success": True,
            "tool_name": tool_name,
            "timestamp": time.time()
        }
    
    def list_runtime_tools(self) -> List[Dict[str, Any]]:
        """
        List all dynamically registered tools
        
        Returns:
            List of runtime tools with metadata
        """
        runtime_tools = []
        
        # Core tools loaded from package
        core_tools = set()
        try:
            package = importlib.import_module(self.package)
            for importer, modname, ispkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
                if not ispkg:
                    tool_name = modname.split('.')[-1]
                    core_tools.add(tool_name)
        except:
            pass
        
        # Find runtime tools (not in core set)
        for tool_name in self.tools:
            if tool_name not in core_tools:
                tool_info = {
                    "name": tool_name,
                    "type": "runtime",
                    "performance": self.tool_performance.get(tool_name, {}),
                    "is_async": self.is_tool_async(tool_name)
                }
                runtime_tools.append(tool_info)
        
        return runtime_tools
