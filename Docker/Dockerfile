# Use Microsoft Windows Server Core as the base image
FROM mcr.microsoft.com/windows/server:ltsc2022

# Set the working directory
WORKDIR /app

# Copy the setup.ps1 script into the container
COPY ../scripts/setup.ps1 /app/setup.ps1

# Run the setup script using PowerShell
CMD ["powershell", "-ExecutionPolicy", "Bypass", "-File", "/app/setup.ps1"] 