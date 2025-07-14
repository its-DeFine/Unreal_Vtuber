#!/usr/bin/env python3
"""
Orchestrator CLI - Text-based control for VTuber Orchestrator
Works perfectly in WSL, Linux, and Windows environments
Created: 2025-07-14
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
    """Text-based CLI for orchestrator control"""
    
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
        print("🤖 VTuber Orchestrator CLI")
        print("="*60)
        print(f"📡 Connected to: {self.orchestrator_url}")
        print("\n📚 Available Personas:")
        for persona, info in self.personas.items():
            print(f"   {info['emoji']}  {info['color']}{persona.capitalize()}{self.reset_color}")
        print("\n💡 Commands:")
        print("   • Type naturally, personas are auto-detected")
        print("   • Use 'help' for more commands")
        print("   • Type 'exit' or 'quit' to leave")
        print("="*60 + "\n")
    
    def detect_persona(self, text: str) -> Optional[str]:
        """Detect persona from text"""
        text_lower = text.lower()
        
        # Check for explicit persona mention
        for persona in self.personas:
            if persona in text_lower:
                return persona
        
        # Check keywords
        for persona, info in self.personas.items():
            if any(keyword in text_lower for keyword in info['keywords']):
                return persona
        
        return None
    
    async def send_to_orchestrator(self, text: str) -> Dict[str, Any]:
        """Send command to orchestrator"""
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
                # Route through orchestrator
                route_resp = await client.post(f"{self.orchestrator_url}/route", json=stimulus)
                if route_resp.status_code != 200:
                    return {"error": f"Routing failed: {route_resp.status_code}"}
                
                routing = route_resp.json()
                
                # Execute
                exec_resp = await client.post(f"{self.orchestrator_url}/execute", json=routing)
                
                return {
                    "success": exec_resp.status_code == 200,
                    "routing": routing,
                    "persona": routing.get("config", {}).get("persona", "assistant")
                }
                
            except httpx.ConnectError:
                return {"error": "Cannot connect to orchestrator. Is it running?"}
            except Exception as e:
                return {"error": str(e)}
    
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
                # Get input
                user_input = input("💬 > ").strip()
                
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
                
                # Add to history
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.history.append((timestamp, user_input))
                
                # Process command
                print("🔄 Processing...")
                result = await self.send_to_orchestrator(user_input)
                
                if result.get("success"):
                    persona = result.get("persona", "assistant")
                    persona_info = self.personas.get(persona, {})
                    color = persona_info.get('color', '')
                    emoji = persona_info.get('emoji', '🤖')
                    
                    system = result.get("routing", {}).get("system", "unknown")
                    print(f"✅ {emoji} {color}{persona.capitalize()}{self.reset_color} ({system})")
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
            print("Usage: python orchestrator_cli.py [orchestrator_url]")
            print("Default URL: http://localhost:8082")
            return
        orchestrator_url = sys.argv[1]
    
    cli = OrchestratorCLI(orchestrator_url)
    asyncio.run(cli.run())


if __name__ == "__main__":
    main()