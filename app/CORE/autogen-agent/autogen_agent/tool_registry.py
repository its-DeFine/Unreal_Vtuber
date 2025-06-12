import importlib
import pkgutil
import logging
import os
from typing import Callable, Dict, Optional, List


class ToolRegistry:
    def __init__(self, package: str = "autogen_agent.tools"):
        self.package = package
        self.tools: Dict[str, Callable[[dict], dict]] = {}
        self.disabled_tools: List[str] = []
        
        # 🚫 DISABLED TOOLS - Focus on core evolution system
        # VTuber tools management updated
        self.disabled_tools = [
            "cognitive_vtuber_tool",      # Legacy VTuber tool - will be deprecated
            # "advanced_vtuber_control",  # ENABLED NOW - VTuber control implemented
        ]
        
        # Get additional disabled tools from environment
        env_disabled = os.getenv("DISABLED_TOOLS", "").split(",")
        self.disabled_tools.extend([tool.strip() for tool in env_disabled if tool.strip()])
        
        logging.info(f"🔧 [TOOL_REGISTRY] Initialized with {len(self.disabled_tools)} disabled tools: {self.disabled_tools}")

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
                        logging.info(f"✅ [TOOL_REGISTRY] Loaded tool: {tool_name}")
                    else:
                        logging.warning(f"⚠️ [TOOL_REGISTRY] Module {tool_name} has no 'run' function")
                        
                except ImportError as e:
                    logging.error(f"❌ [TOOL_REGISTRY] Failed to import {tool_name}: {e}")
                    
        except ImportError as e:
            logging.error(f"❌ [TOOL_REGISTRY] Failed to import package {self.package}: {e}")

    def select_tool(self, context: dict) -> Optional[Callable]:
        """Select the most appropriate tool based on context"""
        if not self.tools:
            logging.warning("⚠️ [TOOL_REGISTRY] No tools available")
            return None
            
        # Simple round-robin selection for now
        iteration = context.get("iteration", 0)
        tool_names = list(self.tools.keys())
        selected_name = tool_names[iteration % len(tool_names)]
        
        logging.info(f"🛠️ [TOOL_REGISTRY] Selected tool: {selected_name}")
        return self.tools[selected_name]

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
        """Execute a specific tool with client access"""
        tool = self.get_tool_by_name(tool_name)
        if not tool:
            logging.warning(f"⚠️ [TOOL_REGISTRY] Tool '{tool_name}' not found")
            return None
            
        # Add clients to context
        enhanced_context = self.add_clients_to_context(context, vtuber_client, scb_client)
        
        try:
            result = tool(enhanced_context)
            logging.info(f"✅ [TOOL_REGISTRY] Tool '{tool_name}' executed successfully")
            return result
        except Exception as e:
            logging.error(f"❌ [TOOL_REGISTRY] Tool '{tool_name}' execution failed: {e}")
            return None

    def get_vtuber_control_tool(self) -> Optional[Callable]:
        """Get the VTuber control tool specifically"""
        return self.get_tool_by_name("advanced_vtuber_control")

    def get_tool_status(self) -> Dict[str, Any]:
        """Get registry status and tool information"""
        return {
            "total_tools": len(self.tools),
            "available_tools": list(self.tools.keys()),
            "disabled_tools": self.disabled_tools,
            "vtuber_control_available": "advanced_vtuber_control" in self.tools,
            "core_evolution_available": "core_evolution_tool" in self.tools
        }
