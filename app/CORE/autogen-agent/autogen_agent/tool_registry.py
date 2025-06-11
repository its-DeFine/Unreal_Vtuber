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
        # VTuber tools disabled until sophisticated control system is implemented
        self.disabled_tools = [
            "cognitive_vtuber_tool",      # Legacy VTuber tool - will be deprecated
            "advanced_vtuber_control",    # Future VTuber control - not implemented yet
        ]
        
        # Get additional disabled tools from environment
        env_disabled = os.getenv("DISABLED_TOOLS", "").split(",")
        self.disabled_tools.extend([tool.strip() for tool in env_disabled if tool.strip()])
        
        logging.info(f"🔧 [TOOL_REGISTRY] Initialized with {len(self.disabled_tools)} disabled tools: {self.disabled_tools}")

    def load_tools(self) -> None:
        """Load tools from the tools package, respecting disabled tools list"""
        logging.info(f"🔄 [TOOL_REGISTRY] Loading tools from {self.package}...")
        
        try:
            package = importlib.import_module(self.package)
            loaded_count = 0
            disabled_count = 0
            
            for _, mod_name, _ in pkgutil.iter_modules(package.__path__):
                if mod_name in self.disabled_tools:
                    logging.info(f"🚫 [TOOL_REGISTRY] Skipping disabled tool: {mod_name}")
                    disabled_count += 1
                    continue
                
                # Skip __init__ and other non-tool modules
                if mod_name.startswith("__"):
                    continue
                
                try:
                    mod = importlib.import_module(f"{self.package}.{mod_name}")
                    if hasattr(mod, "run"):
                        self.tools[mod_name] = getattr(mod, "run")
                        logging.info(f"✅ [TOOL_REGISTRY] Loaded tool: {mod_name}")
                        loaded_count += 1
                    else:
                        logging.warning(f"⚠️ [TOOL_REGISTRY] Module {mod_name} has no 'run' function")
                except Exception as e:
                    logging.error(f"❌ [TOOL_REGISTRY] Failed to load tool {mod_name}: {e}")
            
            logging.info(f"🔧 [TOOL_REGISTRY] Tool loading complete: {loaded_count} loaded, {disabled_count} disabled")
            
        except Exception as e:
            logging.error(f"❌ [TOOL_REGISTRY] Failed to load tools package: {e}")

    def select_tool(self, context: dict) -> Optional[Callable[[dict], dict]]:
        """Select a tool based on context - enhanced selection logic"""
        if not self.tools:
            logging.warning("⚠️ [TOOL_REGISTRY] No tools available for selection")
            return None
        
        # 🎯 Enhanced tool selection logic (placeholder for future sophistication)
        # For now, use first available tool but log the selection
        available_tools = list(self.tools.keys())
        
        # Simple round-robin or context-based selection can be added here
        selected_tool_name = available_tools[0]  # Naive selection for now
        selected_tool = self.tools[selected_tool_name]
        
        logging.info(f"🎯 [TOOL_REGISTRY] Selected tool: {selected_tool_name} from {len(available_tools)} available tools")
        
        return selected_tool
    
    def get_available_tools(self) -> List[str]:
        """Get list of currently available (loaded) tools"""
        return list(self.tools.keys())
    
    def get_disabled_tools(self) -> List[str]:
        """Get list of currently disabled tools"""
        return self.disabled_tools.copy()
    
    def enable_tool(self, tool_name: str) -> bool:
        """Enable a previously disabled tool"""
        if tool_name in self.disabled_tools:
            self.disabled_tools.remove(tool_name)
            # Reload the specific tool
            try:
                mod = importlib.import_module(f"{self.package}.{tool_name}")
                if hasattr(mod, "run"):
                    self.tools[tool_name] = getattr(mod, "run")
                    logging.info(f"✅ [TOOL_REGISTRY] Enabled tool: {tool_name}")
                    return True
            except Exception as e:
                logging.error(f"❌ [TOOL_REGISTRY] Failed to enable tool {tool_name}: {e}")
        return False
    
    def disable_tool(self, tool_name: str) -> bool:
        """Disable a currently active tool"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            if tool_name not in self.disabled_tools:
                self.disabled_tools.append(tool_name)
            logging.info(f"🚫 [TOOL_REGISTRY] Disabled tool: {tool_name}")
            return True
        return False
    
    def get_tool_status(self) -> Dict[str, str]:
        """Get status of all tools (enabled/disabled)"""
        status = {}
        
        # Get all possible tools from the package
        try:
            package = importlib.import_module(self.package)
            for _, mod_name, _ in pkgutil.iter_modules(package.__path__):
                if mod_name.startswith("__"):
                    continue
                    
                if mod_name in self.tools:
                    status[mod_name] = "enabled"
                elif mod_name in self.disabled_tools:
                    status[mod_name] = "disabled"
                else:
                    status[mod_name] = "unknown"
        except Exception as e:
            logging.error(f"❌ [TOOL_REGISTRY] Failed to get tool status: {e}")
        
        return status
