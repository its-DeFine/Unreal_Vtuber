# NeuroSync Docker Container

This repository contains a Dockerfile to build and run a full NeuroSync project in a Windows container.

## Installation Options

You have two options to run NeuroSync:

1. **Docker Container** - Run in an isolated environment (recommended for testing)
2. **Direct Installation** - Install directly on your Windows machine

## Prerequisites

### For Docker Installation
- Windows 10/11 with Docker Desktop installed
- Docker Desktop configured to use Windows containers
- For GPU acceleration: NVIDIA GPU with compatible drivers

### For Direct Installation
- Windows 10/11
- PowerShell 5.1 or later
- Administrator privileges
- NVIDIA GPU recommended for best performance

## Project Structure

```
neurosync-docker/
├── Dockerfile              # Container configuration
├── docker-compose.yml      # For easier container management
├── .dockerignore           # Excludes unnecessary files from build
├── README.md               # This file
└── scripts/
    └── run.ps1             # NeuroSync setup script
```

## Option 1: Using Docker

### Building the Docker Image

#### Using Docker Build

1. Place the `run.ps1` script in a folder named `scripts` at the root of this repository.
2. Open a PowerShell terminal and navigate to the repository directory.
3. Switch to Windows containers in Docker Desktop.
4. Build the Docker image:

```powershell
docker build -t neurosync:latest .
```

#### Using Docker Compose

Alternatively, you can use Docker Compose to build the image:

```powershell
docker-compose build
```

### Running the Container

#### Using Docker Run

##### Basic Run

```powershell
docker run --isolation=hyperv -it neurosync:latest
```

##### With GPU Passthrough (for NVIDIA GPU users)

```powershell
docker run --isolation=hyperv --gpus all -it neurosync:latest
```

#### Using Docker Compose

For basic usage:

```powershell
docker-compose up
```

For GPU support, uncomment the GPU configuration in `docker-compose.yml` first, then run:

```powershell
docker-compose up
```

## Option 2: Direct Installation

If you prefer to install NeuroSync directly on your computer:

1. Download the `run.ps1` script from the `scripts` folder.

2. Open PowerShell as Administrator:
   - Right-click on the Windows Start button
   - Select "Windows PowerShell (Admin)"

3. Navigate to the folder containing the script:
   ```powershell
   cd path\to\script\folder
   ```

4. Enable script execution (if not already enabled):
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
   ```

5. Run the installation script:
   ```powershell
   .\run.ps1
   ```

6. Follow any on-screen prompts during installation.

The script will:
- Install required dependencies (Python, Git, CUDA if needed)
- Download necessary model files
- Set up the NeuroSync environment
- Launch the application when complete

Installation may take 20-30 minutes depending on your internet connection.

## Accessing the GUI Application

Since NeuroSync is a GUI application, there are several options for accessing the interface:

1. **Remote Desktop**: Configure the container to allow RDP connections.

2. **X Server**: Use an X server like VcXsrv or Xming.

3. **Direct GPU Passthrough**: On Windows, you may be able to access the application directly with proper GPU passthrough configuration.

## Notes

- The container is several GB in size due to the dependencies required by NeuroSync.
- The script automatically downloads game files and model data during execution.
- Windows containers with GPU support have specific requirements and limitations.
- Create a `data` directory in the project root for persistent storage when using docker-compose.

## Troubleshooting

### Docker Installation Issues
- If the application fails to start, you can enter the container interactively and execute components manually:

```powershell
docker run --isolation=hyperv -it neurosync:latest powershell
```

- With docker-compose:

```powershell
docker-compose run --entrypoint powershell neurosync
```

### Direct Installation Issues
- If you encounter permission errors, make sure you're running PowerShell as Administrator.
- If the script fails, check the log file created in the same directory.
- For Python or CUDA issues, try installing those components manually before running the script again.

## License

This Docker configuration is provided for NeuroSync users and is subject to the licensing terms of the included software components.

**Please open an issue if you need to report any bug.**
