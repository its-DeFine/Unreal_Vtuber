#!/usr/bin/env python3
"""
Fixed Orchestrator CLI - Text-based control for VTuber Orchestrator
Works perfectly in WSL, Linux, and Windows environments
Created: 2025-07-14 (Fixed version)
"""
import os
import sys
import json
import time
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import httpx


class OrchestratorCLI:
    """Fixed text-based CLI for orchestrator control"""
    
    def __init__(self, orchestrator_url="http://localhost:8082"):
        self.orchestrator_url = orchestrator_url
        self.personas = {
            'trader': {
                'keywords': ['trade', 'trading', 'market', 'bitcoin', 'crypto', 'stock'],
                'color': '\033[93m',  # Yellow
                'emoji': '📈'
            },
            'educator': {
                'keywords': ['teach', 'explain', 'learn', 'what is', 'how does', 'education'],
                'color': '\033[92m',  # Green
                'emoji': '📚'
            },
            'streamer': {
                'keywords': ['stream', 'joke', 'fun', 'play', 'game', 'entertain'],
                'color': '\033[95m',  # Magenta
                'emoji': '🎮'
            }
        }
        self.reset_color = '\033[0m'
        self.history = []
    
    def print_banner(self):
        """Print welcome banner"""
        print("\n" + "="*60)
        print("🤖 VTuber Orchestrator CLI (Fixed Version)")
        print("="*60)
        print(f"📡 Connected to: {self.orchestrator_url}")
        print("\n📚 Available Personas:")
        for persona, info in self.personas.items():
            print(f"   {info['emoji']}  {info['color']}{persona.capitalize()}{self.reset_color}")
        print("\n💡 Commands:")
        print("   • Type naturally, personas are auto-detected")
        print("   • Use 'help' for more commands")
        print("   • Use 'stop' to stop System 2 conversations")
        print("   • Type 'exit' or 'quit' to leave")
        print("="*60 + "\n")
    
    def detect_persona(self, text: str) -> Optional[str]:
        """Detect persona from text"""
        text_lower = text.lower()
        
        # Check for explicit initialization commands
        init_patterns = [
            "initialize", "init", "switch to", "use", "activate", "start"
        ]
        
        if any(pattern in text_lower for pattern in init_patterns):
            # Check for specific persona mentions
            if "trader" in text_lower:
                return "trader"
            elif "educator" in text_lower or "teacher" in text_lower or "education" in text_lower:
                return "educator"
            elif "streamer" in text_lower or "entertainer" in text_lower:
                return "streamer"
        
        # Check for explicit persona mention
        for persona in self.personas:
            if persona in text_lower:
                return persona
        
        # Check keywords
        for persona, info in self.personas.items():
            if any(keyword in text_lower for keyword in info['keywords']):
                return persona
        
        return None
    
    def is_stop_command(self, text: str) -> bool:
        """Check if text is a natural language stop command"""
        text_lower = text.lower()
        stop_phrases = [
            "stop system 2",
            "stop s2",
            "stop the system 2",
            "stop system two",
            "stop conversation",
            "stop processing",
            "stop talking",
            "stop the conversation",
            "stop the processing",
            "halt system 2",
            "halt s2",
            "interrupt system 2",
            "interrupt s2",
            "cancel system 2",
            "cancel s2",
            "cancel the system 2 processes",
            "cancel all system 2",
            "no change is the just cancel all the system to speech"
        ]
        
        return any(phrase in text_lower for phrase in stop_phrases)
    
    async def send_to_orchestrator(self, text: str) -> Dict[str, Any]:
        """Send command to orchestrator"""
        # Check if this is a natural language stop command
        if self.is_stop_command(text):
            print("🛑 Natural language stop command detected...")
            stop_result = await self.stop_conversation()
            
            # Format as orchestrator response
            return {
                "success": stop_result.get("success"),
                "result": {"stop_result": stop_result},
                "routing": {"system": "stop"},
                "execution": {"stop": stop_result},
                "persona": "assistant"
            }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            stimulus = {
                "stimulus_id": f"cli_{int(time.time()*1000)}",
                "text": text,
                "context": {"source": "cli"}
            }
            
            # Detect and add persona
            persona = self.detect_persona(text)
            if persona:
                stimulus["context"]["persona"] = persona
            
            try:
                # Use the process endpoint for combined routing and execution
                response = await client.post(f"{self.orchestrator_url}/process", json=stimulus)
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "result": result,
                        "routing": result.get("routing_decision", {}),
                        "execution": result.get("execution_results", {}),
                        "persona": result.get("routing_decision", {}).get("config", {}).get("persona", "assistant")
                    }
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                
            except httpx.ConnectError:
                return {"success": False, "error": "Cannot connect to orchestrator. Is it running?"}
            except Exception as e:
                return {"success": False, "error": str(e)}
    
    async def stop_conversation(self) -> dict:
        """Stop current System 2 conversation"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try to stop via System 2 API directly
                s2_url = "http://localhost:8200/api/stimuli/stop"
                resp = await client.post(s2_url)
                
                if resp.status_code == 200:
                    return {
                        "success": True,
                        "response": resp.json(),
                        "method": "s2_direct"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"S2 API returned {resp.status_code}",
                        "method": "s2_direct"
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "s2_direct"
            }
    
    async def check_connection(self) -> bool:
        """Check orchestrator connection"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.orchestrator_url}/health")
                return resp.status_code == 200
        except:
            return False
    
    def show_help(self):
        """Show help information"""
        print("\n📖 Help")
        print("="*40)
        print("\n🎯 Example Commands:")
        print("   • 'teach me about blockchain'")
        print("   • 'trader analyze bitcoin'")
        print("   • 'tell me a joke'")
        print("   • 'what is machine learning?'")
        print("\n⚙️  Special Commands:")
        print("   • history - Show command history")
        print("   • clear - Clear screen")
        print("   • status - Check connection status")
        print("   • stop - Stop current System 2 conversation")
        print("   • help - Show this help")
        print("   • exit/quit - Exit the program")
        print("\n💡 Tips:")
        print("   • Natural language is supported")
        print("   • Personas are auto-detected")
        print("   • Add persona name for explicit routing")
        print("="*40 + "\n")
    
    def show_history(self):
        """Show command history"""
        if not self.history:
            print("📜 No command history yet")
            return
        
        print("\n📜 Command History")
        print("="*40)
        for i, (timestamp, cmd) in enumerate(self.history[-10:], 1):
            print(f"{i}. [{timestamp}] {cmd}")
        print("="*40 + "\n")
    
    def safe_input(self, prompt: str) -> str:
        """Safe input that handles EOF and interrupts"""
        try:
            if sys.stdin.isatty():
                return input(prompt)
            else:
                # Non-interactive mode
                line = sys.stdin.readline()
                if line:
                    return line.rstrip('\n')
                else:
                    raise EOFError()
        except EOFError:
            return "quit"
        except KeyboardInterrupt:
            return "quit"
    
    async def run(self):
        """Main CLI loop"""
        self.print_banner()
        
        # Check connection
        print("🔌 Checking orchestrator connection...")
        if await self.check_connection():
            print("✅ Connected successfully!\n")
        else:
            print("❌ Cannot connect to orchestrator!")
            print("Make sure it's running with:")
            print("  docker-compose -f docker-compose.all.yml up orchestrator\n")
            return
        
        # Main loop
        while True:
            try:
                # Get input safely
                user_input = self.safe_input("💬 > ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['exit', 'quit']:
                    print("\n👋 Goodbye!")
                    break
                elif user_input.lower() == 'help':
                    self.show_help()
                    continue
                elif user_input.lower() == 'clear':
                    os.system('clear' if os.name != 'nt' else 'cls')
                    self.print_banner()
                    continue
                elif user_input.lower() == 'history':
                    self.show_history()
                    continue
                elif user_input.lower() == 'status':
                    if await self.check_connection():
                        print("✅ Orchestrator is running")
                    else:
                        print("❌ Orchestrator is not responding")
                    continue
                elif user_input.lower() == 'stop':
                    print("🛑 Stopping current System 2 conversation...")
                    result = await self.stop_conversation()
                    if result.get("success"):
                        response_data = result.get("response", {})
                        if response_data.get("was_processing"):
                            stopped_id = response_data.get("stopped_stimuli_id", "unknown")
                            duration = response_data.get("processing_duration_seconds", 0)
                            print(f"✅ Stopped conversation: {stopped_id} (ran for {duration:.1f}s)")
                        else:
                            print("ℹ️ No conversation was currently running")
                    else:
                        print(f"❌ Failed to stop conversation: {result.get('error', 'Unknown error')}")
                    continue
                
                # Add to history
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.history.append((timestamp, user_input))
                
                # Process command
                print("🔄 Processing...")
                result = await self.send_to_orchestrator(user_input)
                
                if result.get("success"):
                    routing = result.get("routing", {})
                    execution = result.get("execution", {})
                    
                    system = routing.get("system", "unknown")
                    
                    # Handle stop command responses
                    if system == "stop":
                        stop_exec = execution.get("stop", {})
                        if stop_exec.get("success"):
                            response_data = stop_exec.get("response", {})
                            if response_data.get("was_processing"):
                                stopped_id = response_data.get("stopped_stimuli_id", "unknown")
                                duration = response_data.get("processing_duration_seconds", 0)
                                print(f"✅ Stopped System 2 conversation: {stopped_id} (ran for {duration:.1f}s)")
                            else:
                                print("ℹ️ System 2 is currently processing another stimuli")
                        else:
                            print(f"❌ Failed to stop: {stop_exec.get('error', 'Unknown error')}")
                    else:
                        # Normal routing
                        persona = routing.get("config", {}).get("persona", routing.get("config", {}).get("team", "assistant"))
                        
                        persona_info = self.personas.get(persona, {})
                        color = persona_info.get('color', '')
                        emoji = persona_info.get('emoji', '🤖')
                        
                        print(f"✅ {emoji} {color}{persona.capitalize()}{self.reset_color} ({system})")
                        
                        # Show execution results
                        if execution:
                            for sys_name, sys_result in execution.items():
                                if isinstance(sys_result, dict):
                                    if sys_result.get("success"):
                                        print(f"   {sys_name}: {sys_result.get('agent_decision', 'Success')}")
                                    else:
                                        print(f"   {sys_name}: {sys_result.get('error_message', 'Failed')}")
                else:
                    print(f"❌ Error: {result.get('error', 'Unknown error')}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


def main():
    """Entry point"""
    orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://localhost:8082")
    
    # Parse command line args
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("Usage: python orchestrator_cli_fixed.py [orchestrator_url]")
            print("Default URL: http://localhost:8082")
            return
        orchestrator_url = sys.argv[1]
    
    cli = OrchestratorCLI(orchestrator_url)
    
    try:
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ CLI Error: {e}")


if __name__ == "__main__":
    main()