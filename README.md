# Avatar Control System

## What This Application Does

This is an innovative avatar application that enables real-time control of virtual avatars through an intelligent orchestrator agent and teams of specialized sub-agents. The system seamlessly integrates advanced AI capabilities with interactive 3D avatars for natural, dynamic interactions.

### Key Features:
- **Dual-System Architecture**: 
  - **System 1**: Avatar rendering, speech generation (LM), text-to-speech (TTS), and facial blend shape animation
  - **System 2**: Autogen teams that handle tool usage and complex decision-making
  
- **Shared Cognitive Blackboard**: A sophisticated communication layer where both systems exchange information
  - System 2 teams can write to shared blackboards
  - System 1 agents can only read from blackboards
  - Supports both team-specific and global cognitive spaces

- **Flexible Configuration**: Each System 1 agent maps to a System 2 team, enabling customizable agent-avatar pairings

## Prerequisites

- **Operating System**: Windows (required for Unreal Engine game)
- **Docker Desktop**: Must be installed on your Windows machine
- **NVDIA GPU**: at least 16GB VRAM + series 40 or 50 NVIDIA cards
- **Unreal Engine Game**: Download the avatar game from:
  
  [INSERT GAME DOWNLOAD URL HERE]

## Installation & Setup

1. **Download the Unreal Engine Game**
   - Navigate to the provided URL above
   - Download and extract the game files
   - Ensure the game executable is accessible

2. **Install Docker Desktop**
   - Download Docker Desktop for Windows from [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
   - Complete the installation and ensure Docker is running

3. **Configure Environment**
   ```bash
   # Copy the example environment file
   cp .example.env .env
   
   # Edit .env file with your specific configurations if needed
   ```

4. **Launch All Services**
   ```bash
   # From the repository root, run:
   docker compose -f docker-compose.all.yml up -d
   ```
   
   > **Note**: Wait for the `ollama_loader` container to complete and deactivate. This indicates all required Ollama models have been downloaded successfully.

5. **Start the Orchestrator CLI**
   ```bash
   # Navigate to scripts folder and run:
   ./scripts/orchestrator_cli.sh
   ```

## Usage

Once the system is running, you can interact with your avatars through the orchestrator CLI:

- **Direct Commands**: Type commands directly to communicate with avatars
- **Avatar Switching**: Change between different avatar personalities
- **Team Management**: Issue commands to different agent teams
- **Stimulus Routing**: Direct stimuli to either System 1 (avatar/visual) or System 2 (decision/tool) components

### Example Commands:
- Basic interaction: Simply type your message
- System-specific routing: Use prefixes or commands to target specific systems
- Team coordination: Manage multiple agent teams simultaneously

## Architecture Overview

```
┌─────────────────────┐     ┌─────────────────────┐
│     System 1        │     │     System 2        │
├─────────────────────┤     ├─────────────────────┤
│ • Avatar Renderer   │     │ • Autogen Teams     │
│ • Speech LM         │ ←───│ • Tool Usage        │
│ • TTS Engine        │     │ • Decision Making   │
│ • Blend Shapes      │     │                     │
└─────────────────────┘     └─────────────────────┘
         ↑                           ↓
         └───── Shared Cognitive ────┘
                  Blackboard
```

## Troubleshooting

- **Docker Issues**: Ensure Docker Desktop is running and has sufficient resources allocated
- **Ollama Models**: If models fail to download, check your internet connection and Docker logs
- **Game Connection**: Verify the Unreal Engine game is running before starting the orchestrator

## Enjoy!

Start exploring the possibilities of AI-driven avatar interactions. Experiment with different commands, create unique avatar personalities, and discover the full potential of this innovative system.