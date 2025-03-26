# Use Windows Server Core as the base image
FROM mcr.microsoft.com/windows/servercore:ltsc2022

# Set labels for the image
LABEL maintainer="NeuroSync Team"
LABEL description="Windows container for running NeuroSync with PowerShell automation"
LABEL version="1.0"

# Set PowerShell as the default shell with optimized settings
SHELL ["powershell", "-Command", "$ErrorActionPreference = 'Stop'; $ProgressPreference = 'SilentlyContinue';"]

# Create working directory
WORKDIR C:/app

# Copy the PowerShell script to the container
COPY scripts/run.ps1 C:/app/scripts/

# Set execution policy to allow script execution
RUN Set-ExecutionPolicy Bypass -Scope Process -Force

# Install Chocolatey package manager
RUN Set-ExecutionPolicy Bypass -Scope Process -Force; \
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; \
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install Git using Chocolatey with optimized settings
RUN choco install git -y --no-progress --limit-output

# Install Python 3.13.1 with optimized download
RUN $pythonUrl = "https://www.python.org/ftp/python/3.13.1/python-3.13.1-amd64.exe"; \
    $tempFile = "C:\python-installer.exe"; \
    # Use WebClient for faster downloads
    $webClient = New-Object System.Net.WebClient; \
    $webClient.DownloadFile($pythonUrl, $tempFile); \
    # Install with optimized settings
    Start-Process -FilePath $tempFile -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0" -Wait; \
    Remove-Item -Path $tempFile -Force; \
    # Verify installation
    python --version

# Install Visual C++ Redistributables needed by the application (minimize layers)
RUN choco install vcredist140 vcredist2015 vcredist2013 vcredist2012 vcredist2010 directx -y --no-progress --limit-output

# Create required directories
RUN New-Item -ItemType Directory -Force -Path C:/app/scripts/NeuroSync_Setup_Temp | Out-Null; \
    New-Item -ItemType Directory -Force -Path C:/app/scripts/NeuroSync | Out-Null; \
    New-Item -ItemType Directory -Force -Path C:/app/data | Out-Null

# Install Python packages in a single layer
RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir gdown flask numpy librosa pygame pandas timecode pydub audioop-lts && \
    # Install PyTorch without CUDA (will be installed by script if needed)
    python -m pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Clone repositories (this will be overridden by the script but setting up structure)
RUN git config --global core.autocrlf false && \
    git clone --depth 1 https://github.com/UD1sto/NeuroSync_Player_Vt C:/app/scripts/NeuroSync/NeuroSync_Player_Vt && \
    git clone --depth 1 https://github.com/AnimaVR/NeuroSync_Local_API C:/app/scripts/NeuroSync/NeuroSync_Local_API

# Set environment variables
ENV PYTHONIOENCODING=UTF-8
ENV PATH="C:\Program Files\Git\bin;C:\Program Files\Git\cmd;C:\Python313\Scripts;C:\Python313;${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Configure container to support running with GPU if available
LABEL com.nvidia.volumes.needed="nvidia_driver"

# Add volume for persistent data
VOLUME C:/app/data

# Health check to verify container is running correctly
HEALTHCHECK --interval=60s --timeout=15s --start-period=60s --retries=3 \
    CMD powershell -Command "if (Get-Process -Name 'NEUROSYNC' -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"

# Set the entry point to execute the PowerShell script
ENTRYPOINT ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", "C:/app/scripts/run.ps1"]

# Note: This container runs a Windows GUI application requiring:
# - For graphics output: Use with Windows containers on a Windows host with GPU passthrough
# - For NVIDIA GPU acceleration: Use with appropriate Windows container NVIDIA support 