#!/bin/bash

# =============================================================================
# Real-Time AI Voice Streaming Platform - Deployment Script
# =============================================================================
# Version: 1.0
# Description: Main deployment script for setting up the complete voice 
#              streaming platform on a single Linux server
# =============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# =============================================================================
# CONFIGURATION AND CONSTANTS
# =============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$SCRIPT_DIR"
readonly LOG_DIR="$PROJECT_ROOT/logs"
readonly CONFIG_DIR="$PROJECT_ROOT/config"
readonly MODULES_DIR="$PROJECT_ROOT/modules"
readonly SERVICES_DIR="$PROJECT_ROOT/services"

# Platform requirements
readonly MIN_CUDA_VERSION="12.1"
readonly MIN_DOCKER_VERSION="20.10"
readonly REQUIRED_PORTS=(1935 8080 5000 8081)
readonly REQUIRED_PACKAGES=(curl wget git build-essential)

# Logging configuration
readonly LOG_FILE="$LOG_DIR/deployment_$(date +%Y%m%d_%H%M%S).log"
readonly ERROR_LOG="$LOG_DIR/deployment_errors_$(date +%Y%m%d_%H%M%S).log"

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================

setup_logging() {
    mkdir -p "$LOG_DIR"
    exec 1> >(tee -a "$LOG_FILE")
    exec 2> >(tee -a "$ERROR_LOG" >&2)
    log_info "🚀 Voice Platform Deployment Started - $(date)"
    log_info "📁 Project Root: $PROJECT_ROOT"
    log_info "📝 Log File: $LOG_FILE"
}

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*" | tee -a "$LOG_FILE"
}

log_warn() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $*" | tee -a "$LOG_FILE" >&2
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" | tee -a "$ERROR_LOG" >&2
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS] ✅ $*" | tee -a "$LOG_FILE"
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root for security reasons"
        log_info "Please run as a regular user with sudo privileges"
        exit 1
    fi
}

check_sudo() {
    if ! sudo -n true 2>/dev/null; then
        log_error "This script requires sudo privileges"
        log_info "Please ensure your user has sudo access"
        exit 1
    fi
}

check_system_requirements() {
    log_info "🔍 Checking system requirements..."
    
    # Check OS
    if [[ ! -f /etc/os-release ]]; then
        log_error "Cannot determine OS version"
        exit 1
    fi
    
    source /etc/os-release
    if [[ "$ID" != "ubuntu" ]] || [[ "${VERSION_ID}" < "20.04" ]]; then
        log_error "This script requires Ubuntu 20.04 or later"
        exit 1
    fi
    
    log_success "OS Check: Ubuntu ${VERSION_ID}"
    
    # Check available disk space (minimum 50GB)
    local available_space
    available_space=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    if [[ $available_space -lt 52428800 ]]; then  # 50GB in KB
        log_error "Insufficient disk space. Minimum 50GB required"
        exit 1
    fi
    
    log_success "Disk Space Check: $(( available_space / 1024 / 1024 ))GB available"
    
    # Check memory (minimum 16GB recommended)
    local total_mem
    total_mem=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    if [[ $total_mem -lt 16777216 ]]; then  # 16GB in KB
        log_warn "Less than 16GB RAM detected. Performance may be affected"
    fi
    
    log_success "Memory Check: $(( total_mem / 1024 / 1024 ))GB RAM"
}

load_module() {
    local module_name="$1"
    local module_path="$MODULES_DIR/${module_name}.sh"
    
    if [[ ! -f "$module_path" ]]; then
        log_error "Module not found: $module_path"
        return 1
    fi
    
    log_info "📦 Loading module: $module_name"
    # shellcheck source=/dev/null
    source "$module_path"
    log_success "Module loaded: $module_name"
}

validate_ports() {
    log_info "🔌 Checking port availability..."
    local blocked_ports=()
    
    for port in "${REQUIRED_PORTS[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            blocked_ports+=("$port")
        fi
    done
    
    if [[ ${#blocked_ports[@]} -gt 0 ]]; then
        log_error "The following required ports are already in use: ${blocked_ports[*]}"
        log_info "Please stop services using these ports or modify configuration"
        return 1
    fi
    
    log_success "All required ports are available"
}

# =============================================================================
# MAIN DEPLOYMENT FUNCTIONS
# =============================================================================

install_platform() {
    log_info "🚀 Starting platform installation..."
    
    # Load and execute system preparation
    load_module "system_prep" || exit 1
    prepare_system || exit 1
    
    # Load and execute AI model setup
    load_module "model_setup" || exit 1
    setup_ai_models || exit 1
    
    # Load and execute application deployment
    load_module "app_deployment" || exit 1
    deploy_applications || exit 1
    
    log_success "Platform installation completed successfully!"
}

configure_platform() {
    log_info "⚙️ Configuring platform..."
    
    # Load configuration module
    load_module "configuration" || exit 1
    configure_services || exit 1
    
    log_success "Platform configuration completed!"
}

start_platform() {
    log_info "▶️ Starting platform services..."
    
    # Load service management module
    load_module "service_management" || exit 1
    start_all_services || exit 1
    
    log_success "All platform services started!"
}

stop_platform() {
    log_info "⏹️ Stopping platform services..."
    
    # Load service management module
    load_module "service_management" || exit 1
    stop_all_services || exit 1
    
    log_success "All platform services stopped!"
}

status_platform() {
    log_info "📊 Checking platform status..."
    
    # Load monitoring module
    load_module "monitoring" || exit 1
    check_system_status || exit 1
}

update_platform() {
    log_info "🔄 Updating platform..."
    
    # Load update module
    load_module "update_manager" || exit 1
    update_system || exit 1
    
    log_success "Platform updated successfully!"
}

uninstall_platform() {
    log_warn "⚠️ This will completely remove the voice platform"
    read -p "Are you sure you want to continue? (yes/no): " -r
    
    if [[ $REPLY != "yes" ]]; then
        log_info "Uninstall cancelled"
        exit 0
    fi
    
    log_info "🗑️ Uninstalling platform..."
    
    # Load cleanup module
    load_module "cleanup" || exit 1
    cleanup_system || exit 1
    
    log_success "Platform uninstalled successfully!"
}

# =============================================================================
# HELP AND USAGE
# =============================================================================

show_help() {
    cat << EOF
Real-Time AI Voice Streaming Platform - Deployment Script

USAGE:
    $0 [OPTION]

OPTIONS:
    --install       Install the complete voice streaming platform
    --configure     Configure platform services and settings
    --start         Start all platform services
    --stop          Stop all platform services  
    --status        Show current platform status
    --update        Update platform components
    --uninstall     Remove the platform completely
    --help          Show this help message

EXAMPLES:
    $0 --install                    # Full installation
    $0 --configure                  # Configure after installation
    $0 --start                      # Start all services
    $0 --status                     # Check system status

REQUIREMENTS:
    - Ubuntu 20.04+ with sudo privileges
    - NVIDIA GPU with CUDA 12.1+ support
    - Minimum 16GB RAM (32GB recommended)
    - Minimum 50GB free disk space
    - Internet connection for downloads

PORTS USED:
    - 1935: RTMP streaming
    - 8080: Web interface
    - 5000: API server
    - 8081: WebSocket server

For more information, see: $PROJECT_ROOT/docs/README.md
EOF
}

# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

main() {
    # Initialize logging
    setup_logging
    
    # Security checks (only for operations that need them)
    case "${1:-}" in
        --help|"")
            show_help
            exit 0
            ;;
        --status)
            # Status check doesn't need root/sudo
            status_platform
            ;;
        *)
            # All other operations need security checks
            check_root
            check_sudo
            
            case "${1:-}" in
                --install)
                    check_system_requirements
                    validate_ports
                    install_platform
                    ;;
                --configure)
                    configure_platform
                    ;;
                --start)
                    start_platform
                    ;;
                --stop)
                    stop_platform
                    ;;
                --update)
                    update_platform
                    ;;
                --uninstall)
                    uninstall_platform
                    ;;
                *)
                    log_error "Unknown option: $1"
                    echo "Use --help for usage information"
                    exit 1
                    ;;
            esac
            ;;
    esac
}

# =============================================================================
# SCRIPT EXECUTION
# =============================================================================

# Trap to ensure cleanup on script exit
trap 'log_info "🏁 Script execution completed - $(date)"' EXIT

# Execute main function with all arguments
main "$@" 