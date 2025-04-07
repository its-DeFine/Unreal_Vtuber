# NeuroSync VTuber Project

Welcome to the NeuroSync VTuber project! This repository contains tools and resources for building **Live Autonomous Virtual Agents** using the NeuroSync real-time facial animation system.

## What is this project?

This project combines Unreal Engine's MetaHuman technology with NeuroSync's audio-to-face animation capabilities to create responsive, autonomous virtual characters that can:

- Stream live on platforms like Twitch
- Interact with viewers in real-time
- Respond naturally with appropriate facial expressions
- Run completely locally for privacy and low latency

## Quick Navigation

- [Key Features](#key-features)
- [Installation Methods](#installation-methods)
  - [Docker Installation](#method-1-docker-installation)
  - [Direct Installation](#method-2-direct-installation)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)

# NeuroSync: Real-Time Audio-to-Face Animation

NeuroSync is a cutting-edge transformer-based neural network system that generates real-time facial animations from audio input, converting audio features into facial blendshapes at 60fps.

[![NeuroSync Demo](https://img.youtube.com/vi/eQPtJWLIElk/0.jpg)](https://www.youtube.com/watch?v=eQPtJWLIElk)

## Key Features

- **Real-Time Animation**: 60fps facial animations with low latency
- **MetaHuman Integration**: Stream blendshapes to UE5 via LiveLink
- **Full-Face Expression**: Complete facial animations including emotional expressions
- **LLM Integration**: Utilities for creating interactive AI characters
- **Local Processing**: Run everything locally for privacy and reduced latency

## Components

- **NeuroSync Local API** – Real-time facial data processing
- **NeuroSync Player** – Animation data transmission to UE/LiveLink-compatible software

## Installation Options

| Method | Description | Best For |
|--------|-------------|----------|
| **Docker Container** | Isolated environment | Testing, development, isolation |
| **Direct Installation** | Native installation on Windows | Performance, everyday use |

### Prerequisites

**Docker Installation**
- Windows 10/11
- Docker Desktop with Windows containers
- NVIDIA GPU with compatible drivers (for acceleration)

> **Important Docker Setup:** Before attempting to use this project, ensure that Docker Desktop is installed and configured properly for Windows containers. Follow the [official Microsoft documentation](https://learn.microsoft.com/en-us/virtualization/windowscontainers/quick-start/set-up-environment?tabs=dockerce) for detailed setup instructions.

**Direct Installation**
- Windows 10/11
- PowerShell 5.1+
- Admin privileges
- NVIDIA GPU (recommended)

## Installation Methods

### Method 1: Docker Installation

```powershell
# 1. Ensure Docker Desktop is using Windows containers
# To switch to Windows containers:
# - Right-click Docker Desktop in system tray
# - Select "Switch to Windows containers..."
# - Wait for Docker to restart

# 2. Build the Docker image
cd Unreal_Vtuber/Docker
docker build -t neurosync-setup .

# 3. Run the container
docker run --name neurosync-container --gpus all neurosync-setup
```

> **Note:** If you encounter errors about "no matching manifest for linux/amd64", this indicates Docker is still in Linux container mode. Follow step 1 to switch to Windows containers.

### Method 2: Direct Installation

```powershell
# 1. Clone the repository (if you haven't already)
git clone https://github.com/your-org/NeuroSync.git
cd NeuroSync

# 2. Run the setup script as Administrator
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1

# 3. Update your .env file with your Twitch key and other settings  
Copy the `.env.example` file to `.env` and update the settings

# 4. After installation completes, launch with
powershell -ExecutionPolicy Bypass -File scripts/stream_and_run.ps1
```

The setup script:
- Installs dependencies (Python, Git, CUDA)
- Downloads model files
- Configures the environment
- Initializes required components

## GUI Access in Docker

When running in Docker, access the GUI via:
- Remote Desktop (configure container for RDP)
- X Server (VcXsrv/Xming)
- Direct GPU passthrough (with proper configuration)

## Troubleshooting

**Docker Installation**
- Debug container interactively: `docker run --isolation=hyperv -it neurosync-setup powershell`
- Container is several GB due to dependencies
- GPU passthrough requires proper NVIDIA driver configuration

**Direct Installation**
- Run PowerShell as Administrator for permission issues
- Check log file in script directory for errors
- For Python/CUDA issues, try manual component installation

## Notes

- The setup script takes 20-30 minutes depending on internet speed
- **Custom Fork**: We use a custom NeuroSync_Player fork with Livepeer Pipelines in llm_to_face

**Coming Soon**: Eliza OS Integration

## Resources

- [NeuroSync Player Repository](https://github.com/AnimaVR/NeuroSync_Player)
- [YouTube Demo & Tutorials](https://www.youtube.com/@animaai_mai)

## License

Subject to licensing terms of included software components.

**Report bugs by opening an issue in this repository.**
