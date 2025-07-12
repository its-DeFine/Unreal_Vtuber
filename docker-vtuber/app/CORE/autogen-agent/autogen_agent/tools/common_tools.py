"""
Common Tools - Shared across all teams.

Tools that are useful for all teams regardless of specialization.
Includes system utilities, communication tools, and general-purpose functionality.
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .base_tool import BaseTool, ToolResult, ToolStatus, ToolParameter, ToolExecutionContext


class SystemStatusTool(BaseTool):
    """Tool for checking system status and health."""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="check_type",
                type="string",
                description="Type of system check to perform",
                required=False,
                default="general",
                enum=["general", "detailed", "performance", "connectivity"]
            )
        ]
        
        super().__init__(
            name="system_status",
            description="Check system status and health metrics",
            parameters=parameters,
            timeout=10.0
        )
    
    async def execute(
        self,
        context: ToolExecutionContext,
        check_type: str = "general",
        **kwargs
    ) -> ToolResult:
        """Execute system status check"""
        
        try:
            await asyncio.sleep(0.5)  # Simulate system check time
            
            status = {
                "timestamp": datetime.now().isoformat(),
                "system_health": "healthy",
                "uptime": f"{random.randint(1, 30)} days",
                "version": "1.0.0",
                "status_details": {}
            }
            
            if check_type == "general":
                status["status_details"] = self._get_general_status()
            elif check_type == "detailed":
                status["status_details"] = self._get_detailed_status()
            elif check_type == "performance":
                status["status_details"] = self._get_performance_metrics()
            elif check_type == "connectivity":
                status["status_details"] = self._get_connectivity_status()
            
            return ToolResult(
                success=True,
                status=ToolStatus.SUCCESS,
                result=status,
                metadata={"tool": "system_status", "check_type": check_type}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                status=ToolStatus.FAILED,
                error_message=f"System status check failed: {str(e)}"
            )
    
    def _get_general_status(self) -> Dict[str, Any]:
        """Get general system status"""
        return {
            "services_running": random.randint(8, 12),
            "memory_usage": f"{random.randint(40, 80)}%",
            "disk_usage": f"{random.randint(20, 60)}%",
            "last_restart": (datetime.now() - timedelta(days=random.randint(1, 7))).isoformat()
        }
    
    def _get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed system information"""
        return {
            "cpu_cores": random.randint(4, 16),
            "total_memory_gb": random.randint(8, 64),
            "active_connections": random.randint(50, 200),
            "process_count": random.randint(100, 300),
            "network_interfaces": ["eth0", "lo"],
            "mounted_filesystems": ["/", "/home", "/tmp"]
        }
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            "cpu_usage_percent": round(random.uniform(10, 70), 1),
            "memory_usage_percent": round(random.uniform(30, 80), 1),
            "disk_io_rate": f"{random.randint(10, 100)} MB/s",
            "network_throughput": f"{random.randint(50, 500)} Mbps",
            "response_time_ms": round(random.uniform(5, 50), 1),
            "load_average": [round(random.uniform(0.5, 2.0), 2) for _ in range(3)]
        }
    
    def _get_connectivity_status(self) -> Dict[str, Any]:
        """Get connectivity status"""
        return {
            "internet_connection": "active",
            "dns_resolution": "working",
            "external_api_access": "available",
            "internal_services": "all_responding",
            "latency_ms": random.randint(10, 100),
            "bandwidth_available": f"{random.randint(100, 1000)} Mbps"
        }


class CommunicationTool(BaseTool):
    """Tool for inter-team communication and coordination."""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="action",
                type="string",
                description="Communication action to perform",
                required=True,
                enum=["send_message", "get_messages", "broadcast", "create_channel", "get_status"]
            ),
            ToolParameter(
                name="target",
                type="string",
                description="Target team or channel",
                required=False,
                default="general"
            ),
            ToolParameter(
                name="message",
                type="string",
                description="Message content",
                required=False
            ),
            ToolParameter(
                name="priority",
                type="string",
                description="Message priority level",
                required=False,
                default="normal",
                enum=["low", "normal", "high", "urgent"]
            )
        ]
        
        super().__init__(
            name="communication",
            description="Handle inter-team communication and coordination",
            parameters=parameters,
            timeout=5.0
        )
    
    async def execute(
        self,
        context: ToolExecutionContext,
        action: str,
        target: str = "general",
        message: str = None,
        priority: str = "normal",
        **kwargs
    ) -> ToolResult:
        """Execute communication action"""
        
        try:
            await asyncio.sleep(0.3)  # Simulate communication delay
            
            result = {}
            
            if action == "send_message":
                result = self._send_message(target, message, priority)
            elif action == "get_messages":
                result = self._get_messages(target)
            elif action == "broadcast":
                result = self._broadcast_message(message, priority)
            elif action == "create_channel":
                result = self._create_channel(target)
            elif action == "get_status":
                result = self._get_communication_status()
            
            return ToolResult(
                success=True,
                status=ToolStatus.SUCCESS,
                result=result,
                metadata={"tool": "communication", "action": action, "target": target}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                status=ToolStatus.FAILED,
                error_message=f"Communication action failed: {str(e)}"
            )
    
    def _send_message(self, target: str, message: str, priority: str) -> Dict[str, Any]:
        """Send message to target"""
        return {
            "message_id": f"msg_{random.randint(1000, 9999)}",
            "sent_to": target,
            "content": message,
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
            "delivery_status": "delivered"
        }
    
    def _get_messages(self, target: str) -> Dict[str, Any]:
        """Get messages from target"""
        sample_messages = [
            {"id": f"msg_{i}", "from": "trader_team", "content": f"Market update {i}", "timestamp": (datetime.now() - timedelta(minutes=i*10)).isoformat()}
            for i in range(1, 4)
        ]
        
        return {
            "channel": target,
            "message_count": len(sample_messages),
            "messages": sample_messages,
            "last_updated": datetime.now().isoformat()
        }
    
    def _broadcast_message(self, message: str, priority: str) -> Dict[str, Any]:
        """Broadcast message to all teams"""
        teams = ["trader", "teacher", "streamer"]
        return {
            "broadcast_id": f"bc_{random.randint(1000, 9999)}",
            "message": message,
            "priority": priority,
            "sent_to_teams": teams,
            "delivery_count": len(teams),
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_channel(self, channel_name: str) -> Dict[str, Any]:
        """Create new communication channel"""
        return {
            "channel_id": f"ch_{random.randint(1000, 9999)}",
            "channel_name": channel_name,
            "created_at": datetime.now().isoformat(),
            "members": [],
            "status": "active"
        }
    
    def _get_communication_status(self) -> Dict[str, Any]:
        """Get communication system status"""
        return {
            "active_channels": random.randint(5, 15),
            "total_messages_today": random.randint(50, 200),
            "online_teams": ["trader", "teacher", "streamer"],
            "message_queue_size": random.randint(0, 10),
            "last_broadcast": (datetime.now() - timedelta(hours=2)).isoformat()
        }


class UtilityTool(BaseTool):
    """Tool for general utility functions."""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="utility_type",
                type="string",
                description="Type of utility function to execute",
                required=True,
                enum=["format_data", "validate_input", "generate_id", "calculate_stats", "convert_units"]
            ),
            ToolParameter(
                name="data",
                type="string",
                description="Input data for utility function",
                required=False
            ),
            ToolParameter(
                name="format_type",
                type="string",
                description="Format type for data formatting",
                required=False,
                default="json",
                enum=["json", "csv", "xml", "yaml"]
            )
        ]
        
        super().__init__(
            name="utility",
            description="Perform general utility functions and data operations",
            parameters=parameters,
            timeout=10.0
        )
    
    async def execute(
        self,
        context: ToolExecutionContext,
        utility_type: str,
        data: str = None,
        format_type: str = "json",
        **kwargs
    ) -> ToolResult:
        """Execute utility function"""
        
        try:
            await asyncio.sleep(0.2)  # Simulate processing time
            
            result = {}
            
            if utility_type == "format_data":
                result = self._format_data(data, format_type)
            elif utility_type == "validate_input":
                result = self._validate_input(data)
            elif utility_type == "generate_id":
                result = self._generate_id()
            elif utility_type == "calculate_stats":
                result = self._calculate_stats(data)
            elif utility_type == "convert_units":
                result = self._convert_units(data)
            
            return ToolResult(
                success=True,
                status=ToolStatus.SUCCESS,
                result=result,
                metadata={"tool": "utility", "utility_type": utility_type}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                status=ToolStatus.FAILED,
                error_message=f"Utility function failed: {str(e)}"
            )
    
    def _format_data(self, data: str, format_type: str) -> Dict[str, Any]:
        """Format data according to specified type"""
        if not data:
            data = '{"sample": "data", "number": 42}'
        
        try:
            parsed_data = json.loads(data) if data.startswith('{') else {"raw_data": data}
        except:
            parsed_data = {"raw_data": data}
        
        formatted = {
            "json": json.dumps(parsed_data, indent=2),
            "csv": ",".join([f"{k}:{v}" for k, v in parsed_data.items()]),
            "xml": f"<data>{parsed_data}</data>",
            "yaml": "\n".join([f"{k}: {v}" for k, v in parsed_data.items()])
        }
        
        return {
            "original_format": "detected_json" if data and data.startswith('{') else "text",
            "target_format": format_type,
            "formatted_data": formatted.get(format_type, str(parsed_data)),
            "size_bytes": len(formatted.get(format_type, "")),
            "processing_time": "0.1s"
        }
    
    def _validate_input(self, data: str) -> Dict[str, Any]:
        """Validate input data"""
        if not data:
            return {"valid": False, "error": "No data provided"}
        
        validations = {
            "not_empty": len(data.strip()) > 0,
            "safe_length": len(data) < 10000,
            "valid_json": self._is_valid_json(data),
            "no_dangerous_content": not any(word in data.lower() for word in ['<script>', 'eval(', 'exec(']),
            "printable_chars": all(ord(c) < 127 for c in data)
        }
        
        return {
            "valid": all(validations.values()),
            "validation_results": validations,
            "data_length": len(data),
            "data_type": "json" if validations["valid_json"] else "text",
            "safety_score": sum(validations.values()) / len(validations)
        }
    
    def _generate_id(self) -> Dict[str, Any]:
        """Generate various types of IDs"""
        import uuid
        
        return {
            "uuid4": str(uuid.uuid4()),
            "short_id": f"id_{random.randint(100000, 999999)}",
            "timestamp_id": f"ts_{int(datetime.now().timestamp())}",
            "random_hex": ''.join(random.choices('0123456789abcdef', k=8)),
            "session_id": f"sess_{random.randint(10000, 99999)}_{int(datetime.now().timestamp())}"
        }
    
    def _calculate_stats(self, data: str) -> Dict[str, Any]:
        """Calculate statistics from data"""
        if not data:
            numbers = [random.randint(1, 100) for _ in range(10)]
        else:
            try:
                # Try to extract numbers from data
                import re
                numbers = [float(x) for x in re.findall(r'-?\d+\.?\d*', data)]
                if not numbers:
                    numbers = [len(data), len(data.split()), data.count(' ')]
            except:
                numbers = [len(data)]
        
        if numbers:
            return {
                "count": len(numbers),
                "sum": sum(numbers),
                "mean": sum(numbers) / len(numbers),
                "min": min(numbers),
                "max": max(numbers),
                "range": max(numbers) - min(numbers),
                "median": sorted(numbers)[len(numbers)//2]
            }
        else:
            return {"error": "No numeric data found"}
    
    def _convert_units(self, data: str) -> Dict[str, Any]:
        """Convert between different units"""
        conversions = {
            "time": {
                "1_hour": {"minutes": 60, "seconds": 3600, "milliseconds": 3600000},
                "1_day": {"hours": 24, "minutes": 1440, "seconds": 86400}
            },
            "data": {
                "1_gb": {"mb": 1024, "kb": 1048576, "bytes": 1073741824},
                "1_mb": {"kb": 1024, "bytes": 1048576}
            },
            "distance": {
                "1_km": {"meters": 1000, "cm": 100000, "miles": 0.621371},
                "1_mile": {"km": 1.60934, "meters": 1609.34, "feet": 5280}
            }
        }
        
        return {
            "available_conversions": list(conversions.keys()),
            "example_conversions": conversions,
            "input_data": data or "No input provided",
            "note": "Specify numeric value and units for specific conversion"
        }
    
    def _is_valid_json(self, data: str) -> bool:
        """Check if string is valid JSON"""
        try:
            json.loads(data)
            return True
        except:
            return False


# Tool registration
def register_common_tools():
    """Register all common tools with the catalog"""
    from .tool_catalog import register_tool
    
    register_tool(SystemStatusTool, category="system", team_types=["trader", "teacher", "streamer"], priority=5)
    register_tool(CommunicationTool, category="system", team_types=["trader", "teacher", "streamer"], priority=6)
    register_tool(UtilityTool, category="utility", team_types=["trader", "teacher", "streamer"], priority=4)


# Export all tools
__all__ = ["SystemStatusTool", "CommunicationTool", "UtilityTool", "register_common_tools"]