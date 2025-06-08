#!/bin/bash

# =============================================================================
# System Preparation Module
# =============================================================================
# Description: Installs NVIDIA drivers, CUDA 12.1, Docker with GPU support,
#              and configures the base system
# Version: 1.0
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION AND CONSTANTS
# =============================================================================

readonly CUDA_VERSION="12.1"
readonly CUDA_MAJOR_VERSION="12"
readonly CUDA_MINOR_VERSION="1"
readonly DOCKER_COMPOSE_VERSION="v2.24.1"
readonly GSTREAMER_VERSION="1.20"

# Package lists
readonly SYSTEM_PACKAGES=(
    "curl"
    "wget"
    "git"
    "build-essential"
    "gcc"
    "g++"
    "make"
    "cmake"
    "pkg-config"
    "software-properties-common"
    "apt-transport-https"
    "ca-certificates"
    "gnupg"
    "lsb-release"
    "htop"
    "nano"
    "vim"
    "net-tools"
    "ufw"
)

readonly GSTREAMER_PACKAGES=(
    "gstreamer1.0-tools"
    "gstreamer1.0-plugins-base"
    "gstreamer1.0-plugins-good"
    "gstreamer1.0-plugins-bad"
    "gstreamer1.0-plugins-ugly"
    "gstreamer1.0-libav"
    "gstreamer1.0-rtsp"
    "libgstreamer1.0-dev"
    "libgstreamer-plugins-base1.0-dev"
    "libgstreamer-plugins-bad1.0-dev"
)

# Required ports for the voice platform
readonly REQUIRED_PORTS=(1935 8080 5000 8081)

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

check_package_manager() {
    log_info "🔍 [System Prep] Checking package manager availability..."
    
    if ! command -v apt &> /dev/null; then
        log_error "[System Prep] apt package manager not found. This script requires Ubuntu/Debian."
        return 1
    fi
    
    log_success "[System Prep] Package manager check passed"
    return 0
}

check_internet_connection() {
    log_info "🌐 [System Prep] Checking internet connectivity..."
    
    local test_urls=("google.com" "ubuntu.com" "nvidia.com")
    local connection_ok=false
    
    for url in "${test_urls[@]}"; do
        if ping -c 1 -W 5 "$url" &> /dev/null; then
            connection_ok=true
            break
        fi
    done
    
    if [[ "$connection_ok" != true ]]; then
        log_error "[System Prep] No internet connection detected. Installation requires internet access."
        return 1
    fi
    
    log_success "[System Prep] Internet connectivity verified"
    return 0
}

# =============================================================================
# SUBTASK 1: Ubuntu Package Updates and System Dependencies
# =============================================================================

update_system_packages() {
    log_info "📦 [System Prep] Starting Ubuntu package updates and system dependencies installation..."
    
    # Update package lists
    log_info "[System Prep] Updating package lists..."
    if ! sudo apt update; then
        log_error "[System Prep] Failed to update package lists"
        return 1
    fi
    
    # Upgrade existing packages
    log_info "[System Prep] Upgrading existing packages..."
    if ! sudo DEBIAN_FRONTEND=noninteractive apt upgrade -y; then
        log_error "[System Prep] Failed to upgrade packages"
        return 1
    fi
    
    # Install system dependencies
    log_info "[System Prep] Installing system dependencies..."
    for package in "${SYSTEM_PACKAGES[@]}"; do
        log_info "[System Prep] Installing package: $package"
        if ! sudo DEBIAN_FRONTEND=noninteractive apt install -y "$package"; then
            log_error "[System Prep] Failed to install package: $package"
            return 1
        fi
    done
    
    # Verify GCC installation (required for CUDA)
    log_info "[System Prep] Verifying GCC installation..."
    if ! gcc --version &> /dev/null; then
        log_error "[System Prep] GCC not properly installed"
        return 1
    fi
    
    local gcc_version
    gcc_version=$(gcc --version | head -n1)
    log_success "[System Prep] GCC verified: $gcc_version"
    
    # Install GStreamer packages
    log_info "[System Prep] Installing GStreamer packages..."
    for package in "${GSTREAMER_PACKAGES[@]}"; do
        log_info "[System Prep] Installing GStreamer package: $package"
        if ! sudo DEBIAN_FRONTEND=noninteractive apt install -y "$package"; then
            log_warn "[System Prep] Optional GStreamer package failed: $package (continuing...)"
        fi
    done
    
    # Verify GStreamer installation
    if gst-launch-1.0 --version &> /dev/null; then
        local gst_version
        gst_version=$(gst-launch-1.0 --version 2>&1 | grep "GStreamer" | head -n1)
        log_success "[System Prep] GStreamer verified: $gst_version"
    else
        log_error "[System Prep] GStreamer installation verification failed"
        return 1
    fi
    
    log_success "[System Prep] ✅ Subtask 1 completed: Ubuntu package updates and system dependencies"
    return 0
}

# =============================================================================
# SUBTASK 2: NVIDIA Driver Detection and Installation
# =============================================================================

install_nvidia_drivers() {
    log_info "🎮 [System Prep] Starting NVIDIA driver detection and installation..."
    
    # Check for NVIDIA GPU
    log_info "[System Prep] Detecting NVIDIA GPU..."
    if ! lspci | grep -i nvidia &> /dev/null; then
        log_error "[System Prep] No NVIDIA GPU detected. This platform requires an NVIDIA GPU."
        return 1
    fi
    
    local gpu_info
    gpu_info=$(lspci | grep -i nvidia | head -n1)
    log_success "[System Prep] NVIDIA GPU detected: $gpu_info"
    
    # Check if drivers are already installed
    if nvidia-smi &> /dev/null; then
        local driver_version
        driver_version=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits | head -n1)
        log_info "[System Prep] NVIDIA drivers already installed: $driver_version"
        
        # Verify driver is working
        if nvidia-smi &> /dev/null; then
            log_success "[System Prep] Existing NVIDIA drivers are functional"
            return 0
        fi
    fi
    
    # Add NVIDIA GPG key and repository
    log_info "[System Prep] Adding NVIDIA repository..."
    if ! wget -qO - https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub | sudo apt-key add -; then
        log_error "[System Prep] Failed to add NVIDIA GPG key"
        return 1
    fi
    
    # Install recommended NVIDIA drivers
    log_info "[System Prep] Installing recommended NVIDIA drivers..."
    if ! sudo ubuntu-drivers autoinstall; then
        log_error "[System Prep] Failed to install NVIDIA drivers"
        return 1
    fi
    
    # Check if reboot is required
    if [[ -f /var/run/reboot-required ]]; then
        log_warn "[System Prep] ⚠️  System reboot required for NVIDIA drivers to load properly"
        log_warn "[System Prep] Please reboot and re-run the installation after reboot"
        log_warn "[System Prep] Run: sudo reboot"
        return 2  # Special return code for reboot required
    fi
    
    # Verify driver installation
    log_info "[System Prep] Verifying NVIDIA driver installation..."
    if nvidia-smi &> /dev/null; then
        local driver_version
        driver_version=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits | head -n1)
        log_success "[System Prep] NVIDIA drivers installed successfully: $driver_version"
    else
        log_error "[System Prep] NVIDIA driver installation verification failed"
        return 1
    fi
    
    log_success "[System Prep] ✅ Subtask 2 completed: NVIDIA driver installation"
    return 0
}

# =============================================================================
# SUBTASK 3: CUDA 12.1 Toolkit Setup and Validation
# =============================================================================

install_cuda_toolkit() {
    log_info "🚀 [System Prep] Starting CUDA 12.1 toolkit installation..."
    
    # Check if CUDA is already installed
    if nvcc --version &> /dev/null; then
        local cuda_version
        cuda_version=$(nvcc --version | grep "release" | sed 's/.*release \([0-9]*\.[0-9]*\).*/\1/')
        log_info "[System Prep] CUDA already installed: $cuda_version"
        
        if [[ "$cuda_version" == "$CUDA_VERSION" ]]; then
            log_success "[System Prep] CUDA $CUDA_VERSION already installed and configured"
            return 0
        else
            log_warn "[System Prep] Different CUDA version detected ($cuda_version), installing CUDA $CUDA_VERSION"
        fi
    fi
    
    # Download CUDA toolkit
    local cuda_installer="cuda_${CUDA_VERSION}.0_530.30.02_linux.run"
    local cuda_url="https://developer.download.nvidia.com/compute/cuda/${CUDA_VERSION}.0/local_installers/$cuda_installer"
    
    log_info "[System Prep] Downloading CUDA $CUDA_VERSION toolkit..."
    if ! wget -O "/tmp/$cuda_installer" "$cuda_url"; then
        log_error "[System Prep] Failed to download CUDA toolkit"
        return 1
    fi
    
    # Make installer executable
    chmod +x "/tmp/$cuda_installer"
    
    # Install CUDA toolkit (silent installation)
    log_info "[System Prep] Installing CUDA $CUDA_VERSION toolkit..."
    if ! sudo "/tmp/$cuda_installer" --silent --toolkit --samples --override; then
        log_error "[System Prep] CUDA toolkit installation failed"
        return 1
    fi
    
    # Configure environment variables
    log_info "[System Prep] Configuring CUDA environment variables..."
    
    local cuda_env_config="
# CUDA Environment Variables
export PATH=/usr/local/cuda-${CUDA_VERSION}/bin\${PATH:+:\${PATH}}
export LD_LIBRARY_PATH=/usr/local/cuda-${CUDA_VERSION}/lib64\${LD_LIBRARY_PATH:+:\${LD_LIBRARY_PATH}}
export CUDA_HOME=/usr/local/cuda-${CUDA_VERSION}
"
    
    # Add to .bashrc if not already present
    if ! grep -q "CUDA Environment Variables" ~/.bashrc; then
        echo "$cuda_env_config" >> ~/.bashrc
        log_info "[System Prep] CUDA environment variables added to ~/.bashrc"
    fi
    
    # Create symbolic link to current CUDA installation
    if [[ ! -L /usr/local/cuda ]]; then
        sudo ln -sf "/usr/local/cuda-${CUDA_VERSION}" /usr/local/cuda
    fi
    
    # Source the environment variables for current session
    export PATH="/usr/local/cuda-${CUDA_VERSION}/bin:${PATH}"
    export LD_LIBRARY_PATH="/usr/local/cuda-${CUDA_VERSION}/lib64:${LD_LIBRARY_PATH:-}"
    export CUDA_HOME="/usr/local/cuda-${CUDA_VERSION}"
    
    # Verify CUDA installation
    log_info "[System Prep] Verifying CUDA installation..."
    if /usr/local/cuda/bin/nvcc --version &> /dev/null; then
        local installed_version
        installed_version=$(/usr/local/cuda/bin/nvcc --version | grep "release" | sed 's/.*release \([0-9]*\.[0-9]*\).*/\1/')
        log_success "[System Prep] CUDA $installed_version installed and verified successfully"
    else
        log_error "[System Prep] CUDA installation verification failed"
        return 1
    fi
    
    # Cleanup installer
    rm -f "/tmp/$cuda_installer"
    
    log_success "[System Prep] ✅ Subtask 3 completed: CUDA 12.1 toolkit installation"
    return 0
}

# =============================================================================
# SUBTASK 4: Docker and Docker Compose Installation
# =============================================================================

install_docker() {
    log_info "🐳 [System Prep] Starting Docker and Docker Compose installation..."
    
    # Check if Docker is already installed
    if command -v docker &> /dev/null; then
        local docker_version
        docker_version=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
        log_info "[System Prep] Docker already installed: $docker_version"
        
        # Check if user is in docker group
        if groups "$USER" | grep -q docker; then
            log_success "[System Prep] Docker already configured for user $USER"
            
            # Check Docker Compose
            if docker compose version &> /dev/null; then
                local compose_version
                compose_version=$(docker compose version --short)
                log_success "[System Prep] Docker Compose already installed: $compose_version"
                return 0
            fi
        fi
    fi
    
    # Remove old Docker installations
    log_info "[System Prep] Removing old Docker installations if present..."
    sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Add Docker GPG key
    log_info "[System Prep] Adding Docker GPG key..."
    if ! curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg; then
        log_error "[System Prep] Failed to add Docker GPG key"
        return 1
    fi
    
    # Add Docker repository
    log_info "[System Prep] Adding Docker repository..."
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Update package lists
    sudo apt update
    
    # Install Docker Engine
    log_info "[System Prep] Installing Docker Engine..."
    if ! sudo DEBIAN_FRONTEND=noninteractive apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin; then
        log_error "[System Prep] Docker installation failed"
        return 1
    fi
    
    # Add user to docker group
    log_info "[System Prep] Adding user $USER to docker group..."
    sudo usermod -aG docker "$USER"
    
    # Start and enable Docker service
    log_info "[System Prep] Starting Docker service..."
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # Test Docker installation (requires new group membership)
    log_info "[System Prep] Testing Docker installation..."
    if sudo docker run --rm hello-world &> /dev/null; then
        log_success "[System Prep] Docker installation verified successfully"
    else
        log_error "[System Prep] Docker installation test failed"
        return 1
    fi
    
    # Verify Docker Compose
    if docker compose version &> /dev/null; then
        local compose_version
        compose_version=$(docker compose version --short)
        log_success "[System Prep] Docker Compose verified: $compose_version"
    else
        log_error "[System Prep] Docker Compose verification failed"
        return 1
    fi
    
    log_success "[System Prep] ✅ Subtask 4 completed: Docker and Docker Compose installation"
    log_warn "[System Prep] ⚠️  Please log out and log back in for Docker group membership to take effect"
    return 0
}

# =============================================================================
# SUBTASK 5: NVIDIA Container Toolkit Configuration
# =============================================================================

configure_nvidia_docker() {
    log_info "🔧 [System Prep] Starting NVIDIA Container Toolkit configuration..."
    
    # Check if NVIDIA Container Toolkit is already configured
    if docker info 2>/dev/null | grep -q nvidia; then
        log_info "[System Prep] NVIDIA Container Toolkit already configured"
        
        # Test GPU access in container
        if sudo docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi &> /dev/null; then
            log_success "[System Prep] NVIDIA Container Toolkit is working correctly"
            return 0
        fi
    fi
    
    # Add NVIDIA Container Toolkit repository
    log_info "[System Prep] Adding NVIDIA Container Toolkit repository..."
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    
    # Update package lists
    sudo apt update
    
    # Install NVIDIA Container Toolkit
    log_info "[System Prep] Installing NVIDIA Container Toolkit..."
    if ! sudo DEBIAN_FRONTEND=noninteractive apt install -y nvidia-container-toolkit; then
        log_error "[System Prep] NVIDIA Container Toolkit installation failed"
        return 1
    fi
    
    # Configure Docker to use NVIDIA runtime
    log_info "[System Prep] Configuring Docker for NVIDIA runtime..."
    sudo nvidia-ctk runtime configure --runtime=docker
    
    # Restart Docker service
    log_info "[System Prep] Restarting Docker service..."
    sudo systemctl restart docker
    
    # Wait for Docker to restart
    sleep 5
    
    # Test GPU access in container
    log_info "[System Prep] Testing GPU access in Docker container..."
    if sudo docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        log_success "[System Prep] NVIDIA Container Toolkit configured successfully"
    else
        log_error "[System Prep] NVIDIA Container Toolkit test failed"
        return 1
    fi
    
    log_success "[System Prep] ✅ Subtask 5 completed: NVIDIA Container Toolkit configuration"
    return 0
}

# =============================================================================
# SUBTASK 6: Firewall and Network Configuration
# =============================================================================

configure_firewall_and_network() {
    log_info "🔥 [System Prep] Starting firewall and network configuration..."
    
    # Configure UFW firewall
    log_info "[System Prep] Configuring UFW firewall..."
    
    # Enable UFW if not already enabled
    if ! sudo ufw status | grep -q "Status: active"; then
        sudo ufw --force enable
        log_info "[System Prep] UFW firewall enabled"
    fi
    
    # Configure firewall rules for required ports
    for port in "${REQUIRED_PORTS[@]}"; do
        log_info "[System Prep] Opening port $port..."
        if ! sudo ufw allow "$port"; then
            log_error "[System Prep] Failed to open port $port"
            return 1
        fi
    done
    
    # Allow SSH (port 22) to maintain access
    sudo ufw allow ssh
    
    # Allow Docker subnet (if not already configured)
    sudo ufw allow from 172.17.0.0/16
    sudo ufw allow from 172.18.0.0/16
    
    # Show firewall status
    local firewall_status
    firewall_status=$(sudo ufw status numbered)
    log_info "[System Prep] Firewall configuration:\n$firewall_status"
    
    # Configure network optimizations
    log_info "[System Prep] Applying network optimizations..."
    
    # Create network optimization configuration
    local net_config="/etc/sysctl.d/99-voice-platform.conf"
    sudo tee "$net_config" > /dev/null << 'EOF'
# Voice Platform Network Optimizations
# Increase network buffer sizes for streaming
net.core.rmem_max = 268435456
net.core.wmem_max = 268435456
net.core.rmem_default = 65536
net.core.wmem_default = 65536
net.ipv4.tcp_rmem = 4096 65536 268435456
net.ipv4.tcp_wmem = 4096 65536 268435456

# Reduce network latency
net.ipv4.tcp_congestion_control = bbr
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_sack = 1
net.ipv4.tcp_no_metrics_save = 1

# Optimize for real-time streaming
net.core.netdev_budget = 600
net.core.netdev_budget_usecs = 5000
EOF
    
    # Apply network optimizations
    sudo sysctl -p "$net_config"
    
    # Verify port accessibility
    log_info "[System Prep] Validating port configuration..."
    for port in "${REQUIRED_PORTS[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            log_warn "[System Prep] Port $port appears to be in use"
        else
            log_success "[System Prep] Port $port is available"
        fi
    done
    
    # Test internet connectivity after firewall configuration
    if check_internet_connection; then
        log_success "[System Prep] Internet connectivity verified after firewall configuration"
    else
        log_error "[System Prep] Internet connectivity lost after firewall configuration"
        return 1
    fi
    
    log_success "[System Prep] ✅ Subtask 6 completed: Firewall and network configuration"
    return 0
}

# =============================================================================
# MAIN SYSTEM PREPARATION FUNCTION
# =============================================================================

prepare_system() {
    log_info "🔧 [System Prep] Starting comprehensive system preparation..."
    
    # Pre-flight checks
    check_package_manager || return 1
    check_internet_connection || return 1
    
    # Execute all subtasks in order
    local subtask_functions=(
        "update_system_packages"           # Subtask 1
        "install_nvidia_drivers"           # Subtask 2  
        "install_cuda_toolkit"             # Subtask 3
        "install_docker"                   # Subtask 4
        "configure_nvidia_docker"          # Subtask 5
        "configure_firewall_and_network"   # Subtask 6
    )
    
    local failed_subtasks=()
    local reboot_required=false
    
    for i in "${!subtask_functions[@]}"; do
        local subtask_num=$((i + 1))
        local func="${subtask_functions[$i]}"
        
        log_info "[System Prep] 🚀 Executing Subtask $subtask_num: $func"
        
        if $func; then
            log_success "[System Prep] ✅ Subtask $subtask_num completed successfully"
        else
            local exit_code=$?
            if [[ $exit_code -eq 2 ]]; then
                # Special case: reboot required
                reboot_required=true
                log_warn "[System Prep] ⚠️  Subtask $subtask_num requires system reboot"
                break
            else
                log_error "[System Prep] ❌ Subtask $subtask_num failed"
                failed_subtasks+=("$subtask_num:$func")
            fi
        fi
    done
    
    # Handle reboot requirement
    if [[ "$reboot_required" == true ]]; then
        log_warn "[System Prep] ⚠️  SYSTEM REBOOT REQUIRED"
        log_warn "[System Prep] Please reboot the system and re-run the installation:"
        log_warn "[System Prep] sudo reboot"
        return 2
    fi
    
    # Report results
    if [[ ${#failed_subtasks[@]} -eq 0 ]]; then
        log_success "[System Prep] 🎉 All system preparation tasks completed successfully!"
        
        # Display system information
        log_info "[System Prep] 📊 System Information Summary:"
        log_info "[System Prep] OS: $(lsb_release -d | cut -f2)"
        
        if nvidia-smi &> /dev/null; then
            local gpu_info
            gpu_info=$(nvidia-smi --query-gpu=name,driver_version --format=csv,noheader,nounits | head -n1)
            log_info "[System Prep] GPU: $gpu_info"
        fi
        
        if nvcc --version &> /dev/null; then
            local cuda_version
            cuda_version=$(nvcc --version | grep "release" | sed 's/.*release \([0-9]*\.[0-9]*\).*/\1/')
            log_info "[System Prep] CUDA: $cuda_version"
        fi
        
        if docker --version &> /dev/null; then
            local docker_version
            docker_version=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
            log_info "[System Prep] Docker: $docker_version"
        fi
        
        return 0
    else
        log_error "[System Prep] ❌ Failed subtasks: ${failed_subtasks[*]}"
        return 1
    fi
} 