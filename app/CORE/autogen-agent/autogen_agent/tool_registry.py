import importlib
import pkgutil
from typing import Callable, Dict, Optional


class ToolRegistry:
    def __init__(self, package: str = "autogen_agent.tools"):
        self.package = package
        self.tools: Dict[str, Callable[[dict], dict]] = {}

    def load_tools(self) -> None:
        package = importlib.import_module(self.package)
        for _, mod_name, _ in pkgutil.iter_modules(package.__path__):
            mod = importlib.import_module(f"{self.package}.{mod_name}")
            if hasattr(mod, "run"):
                self.tools[mod_name] = getattr(mod, "run")

    def select_tool(self, context: dict) -> Optional[Callable[[dict], dict]]:
        # naive selection: return first tool
        return next(iter(self.tools.values()), None)
