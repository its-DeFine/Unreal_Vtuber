# Multi-platform Dockerfile for NeuroSync VTuber Project
# This will detect the OS environment and use the appropriate base image

# Windows-specific build
FROM mcr.microsoft.com/windows/server:ltsc2022 AS windows-build

# Set working directory
WORKDIR /app

# Copy the setup.ps1 script into the container
COPY scripts/setup.ps1 /app/setup.ps1

# Enable verbose progress display for Docker build
ENV POWERSHELL_PROGRESS_PREFERENCE="Continue"
ENV DOCKER_BUILDKIT=1

# Run the setup script
# Assuming setup.ps1 contains Write-Host or other output commands for progress
RUN powershell -ExecutionPolicy Bypass -File /app/setup.ps1

# ===== Linux distributions below =====

# Distribution not tested yet
FROM debian:bullseye-slim AS debian-build

WORKDIR /app

# Install PowerShell on Debian
RUN apt-get update && \
    apt-get install -y curl wget apt-transport-https software-properties-common && \
    wget -q https://packages.microsoft.com/config/debian/11/packages-microsoft-prod.deb && \
    dpkg -i packages-microsoft-prod.deb && \
    apt-get update && \
    apt-get install -y powershell && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* packages-microsoft-prod.deb

# Copy the setup script
COPY scripts/setup.ps1 /app/setup.ps1

# Run the setup script
RUN pwsh -ExecutionPolicy Bypass -File /app/setup.ps1

# Distribution not tested yet
FROM ubuntu:22.04 AS ubuntu-build

WORKDIR /app

# Install PowerShell on Ubuntu
RUN apt-get update && \
    apt-get install -y curl wget apt-transport-https software-properties-common && \
    wget -q https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb && \
    dpkg -i packages-microsoft-prod.deb && \
    apt-get update && \
    apt-get install -y powershell && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* packages-microsoft-prod.deb

# Copy the setup script
COPY scripts/setup.ps1 /app/setup.ps1

# Run the setup script
RUN pwsh -ExecutionPolicy Bypass -File /app/setup.ps1

# Distribution not tested yet
FROM fedora:latest AS fedora-build

WORKDIR /app

# Install PowerShell on Fedora
RUN dnf update -y && \
    dnf install -y curl wget && \
    curl https://packages.microsoft.com/config/rhel/8/prod.repo | tee /etc/yum.repos.d/microsoft.repo && \
    dnf install -y powershell && \
    dnf clean all

# Copy the setup script
COPY scripts/setup.ps1 /app/setup.ps1

# Run the setup script
RUN pwsh -ExecutionPolicy Bypass -File /app/setup.ps1

# OS detection and selection script
FROM alpine:latest AS detector
WORKDIR /detector
RUN apk add --no-cache bash
COPY <<EOF detector.sh
#!/bin/bash
if [ -f /etc/os-release ]; then
    . /etc/os-release
    case "$ID" in
        debian)
            echo "debian-build"
            ;;
        ubuntu)
            echo "ubuntu-build"
            ;;
        fedora)
            echo "fedora-build"
            ;;
        *)
            echo "Unsupported Linux distribution: $ID"
            exit 1
            ;;
    esac
elif [ "$(uname)" == "Windows_NT" ]; then
    echo "windows-build"
else
    echo "Unsupported operating system"
    exit 1
fi
EOF
RUN chmod +x detector.sh
ENTRYPOINT ["./detector.sh"]

# Final stage - this will be selected at build time based on the OS
FROM ${PLATFORM:-windows-build}

# This allows us to pass the platform explicitly:
# docker build --build-arg PLATFORM=debian-build -t neurosync-setup .
ARG PLATFORM
# The default is windows-build if not specified

# Build progress should be controlled via `docker build --progress=plain`