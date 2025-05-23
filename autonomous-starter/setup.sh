#!/bin/bash

# ==================================================================
# Autonomous Agent with Postgres - Complete Setup Script
# ==================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
DOCKER_COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

echo -e "${BLUE}🚀 Autonomous Agent with Postgres - Setup${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Function to log messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to prompt for input with default
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    read -p "$prompt [$default]: " input
    if [ -z "$input" ]; then
        eval "$var_name='$default'"
    else
        eval "$var_name='$input'"
    fi
}

# Step 1: Check prerequisites
log_step "1. Checking prerequisites..."

# Check Docker
if command_exists docker; then
    log_info "✅ Docker found: $(docker --version | head -n1)"
else
    log_error "❌ Docker not found. Please install Docker first."
    log_info "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check Docker Compose
if command_exists docker-compose; then
    log_info "✅ docker-compose found: $(docker-compose --version)"
    COMPOSE_CMD="docker-compose"
elif docker compose version >/dev/null 2>&1; then
    log_info "✅ docker compose found: $(docker compose version)"
    COMPOSE_CMD="docker compose"
else
    log_error "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

# Check Node.js (optional for development)
if command_exists node; then
    log_info "✅ Node.js found: $(node --version)"
else
    log_warn "⚠️  Node.js not found. Required for development mode only."
fi

# Check if running as root (not recommended)
if [ "$EUID" -eq 0 ]; then
    log_warn "⚠️  Running as root. Consider using a non-root user."
fi

echo ""

# Step 2: Handle existing PGLite data
log_step "2. Checking for existing PGLite data..."

PGLITE_DIR="$SCRIPT_DIR/elizadb"
if [ -d "$PGLITE_DIR" ] && [ "$(ls -A "$PGLITE_DIR" 2>/dev/null)" ]; then
    log_warn "📁 Found existing PGLite database directory"
    echo "   Directory: $PGLITE_DIR"
    echo ""
    read -p "Do you want to backup the existing PGLite data? (y/N): " backup_choice
    
    if [[ $backup_choice =~ ^[Yy]$ ]]; then
        BACKUP_DIR="$SCRIPT_DIR/backup"
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        BACKUP_PATH="$BACKUP_DIR/pglite_backup_$TIMESTAMP"
        
        mkdir -p "$BACKUP_DIR"
        cp -r "$PGLITE_DIR" "$BACKUP_PATH"
        log_info "✅ Backup created: $BACKUP_PATH"
    fi
else
    log_info "ℹ️  No existing PGLite data found"
fi

echo ""

# Step 3: Environment configuration
log_step "3. Setting up environment configuration..."

if [ -f "$ENV_FILE" ]; then
    log_warn "⚠️  .env file already exists"
    read -p "Do you want to overwrite it? (y/N): " overwrite_choice
    
    if [[ ! $overwrite_choice =~ ^[Yy]$ ]]; then
        log_info "Using existing .env file"
        echo ""
    else
        rm "$ENV_FILE"
    fi
fi

if [ ! -f "$ENV_FILE" ]; then
    log_info "📝 Creating .env file..."
    
    # Get user input for configuration
    echo ""
    echo "Please provide the following configuration:"
    echo ""
    
    # Database configuration
    prompt_with_default "PostgreSQL database name" "autonomous_agent" DB_NAME
    prompt_with_default "PostgreSQL port (host)" "5433" PG_PORT
    
    # VTuber integration
    prompt_with_default "VTuber endpoint URL" "http://localhost:5001/process_text" VTUBER_URL
    
    # Autonomous agent settings
    prompt_with_default "Autonomous loop interval (ms)" "30000" LOOP_INTERVAL
    
    # API Keys
    echo ""
    echo "API Keys (at least one is required):"
    read -p "OpenAI API Key (sk-...): " OPENAI_KEY
    read -p "Anthropic API Key (sk-ant-...): " ANTHROPIC_KEY
    read -p "Groq API Key (gsk_...): " GROQ_KEY
    
    # Create .env file
    cat > "$ENV_FILE" << EOF
# =================================
# AUTONOMOUS AGENT CONFIGURATION
# =================================

# Database Configuration - Postgres
DATABASE_URL=postgresql://postgres:postgres@localhost:$PG_PORT/$DB_NAME
POSTGRES_URL=postgresql://postgres:postgres@localhost:$PG_PORT/$DB_NAME
DB_TYPE=postgres

# VTuber Integration
VTUBER_ENDPOINT_URL=$VTUBER_URL

# Autonomous Agent Settings
AUTONOMOUS_LOOP_INTERVAL=$LOOP_INTERVAL
AGENT_NAME=Autoliza

# =================================
# AI PROVIDER API KEYS
# =================================

# OpenAI (Required for most functionality)
OPENAI_API_KEY=$OPENAI_KEY

# Anthropic (Alternative AI provider)
ANTHROPIC_API_KEY=$ANTHROPIC_KEY

# Groq (Fast inference alternative)
GROQ_API_KEY=$GROQ_KEY

# =================================
# DOCKER CONFIGURATION
# =================================

# Docker network settings
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=$DB_NAME

# =================================
# LOGGING AND MONITORING
# =================================

LOG_LEVEL=info
DB_LOGGING=false
NODE_ENV=production
PORT=3001

# =================================
# OPTIONAL INTEGRATIONS
# =================================

# Discord (optional)
# DISCORD_APPLICATION_ID=your-discord-app-id
# DISCORD_API_TOKEN=your-discord-bot-token

# Twitter/X (optional)
# TWITTER_USERNAME=your-twitter-username
# TWITTER_PASSWORD=your-twitter-password

# Telegram (optional)
# TELEGRAM_BOT_TOKEN=your-telegram-bot-token
EOF

    log_info "✅ .env file created successfully"
fi

echo ""

# Step 4: Validate configuration
log_step "4. Validating configuration..."

if [ ! -f "$ENV_FILE" ]; then
    log_error "❌ .env file not found"
    exit 1
fi

# Source the .env file
set -a
source "$ENV_FILE"
set +a

# Check required variables
REQUIRED_VARS=("DATABASE_URL" "POSTGRES_URL")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

# Check at least one API key
if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$GROQ_API_KEY" ]; then
    MISSING_VARS+=("At least one API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GROQ_API_KEY)")
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    log_error "❌ Missing required configuration:"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    log_info "Please edit $ENV_FILE and add the missing values"
    exit 1
fi

log_info "✅ Configuration validated"
echo ""

# Step 5: Check Docker setup
log_step "5. Checking Docker setup..."

# Check if Docker daemon is running
if ! docker info >/dev/null 2>&1; then
    log_error "❌ Docker daemon is not running"
    log_info "Please start Docker and try again"
    exit 1
fi

log_info "✅ Docker daemon is running"

# Check if docker-compose file exists
if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
    log_error "❌ docker-compose.yml not found"
    log_info "Expected location: $DOCKER_COMPOSE_FILE"
    exit 1
fi

log_info "✅ docker-compose.yml found"
echo ""

# Step 6: Check for port conflicts
log_step "6. Checking for port conflicts..."

check_port() {
    local port=$1
    local service=$2
    
    if lsof -i ":$port" >/dev/null 2>&1; then
        log_warn "⚠️  Port $port is already in use (needed for $service)"
        echo "   Current usage:"
        lsof -i ":$port" | head -n 2
        echo ""
        read -p "Do you want to continue anyway? (y/N): " continue_choice
        if [[ ! $continue_choice =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        log_info "✅ Port $port is available ($service)"
    fi
}

check_port "${PG_PORT:-5433}" "PostgreSQL"
check_port "3001" "Autonomous Agent"
echo ""

# Step 7: Build and start services
log_step "7. Building and starting services..."

echo "Starting PostgreSQL database..."
if $COMPOSE_CMD up postgres -d; then
    log_info "✅ PostgreSQL container started"
else
    log_error "❌ Failed to start PostgreSQL"
    exit 1
fi

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if $COMPOSE_CMD exec postgres pg_isready -U postgres >/dev/null 2>&1; then
        log_info "✅ PostgreSQL is ready"
        break
    fi
    
    echo -n "."
    sleep 2
    ATTEMPT=$((ATTEMPT + 1))
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    log_error "❌ PostgreSQL failed to start within timeout"
    log_info "Check logs: $COMPOSE_CMD logs postgres"
    exit 1
fi

echo ""

# Step 8: Start autonomous agent
echo "Building and starting autonomous agent..."
if $COMPOSE_CMD up autonomous-agent -d; then
    log_info "✅ Autonomous agent container started"
else
    log_error "❌ Failed to start autonomous agent"
    log_info "Check logs: $COMPOSE_CMD logs autonomous-agent"
    exit 1
fi

echo ""

# Step 9: Verify services
log_step "8. Verifying services..."

# Check container status
echo "Container status:"
$COMPOSE_CMD ps

echo ""

# Test database connection
echo "Testing database connection..."
if $COMPOSE_CMD exec postgres pg_isready -U postgres >/dev/null 2>&1; then
    log_info "✅ Database connection successful"
else
    log_warn "⚠️  Database connection test failed"
fi

# Check if autonomous agent is responding
echo "Testing autonomous agent health..."
sleep 5  # Give the agent time to start

if curl -s http://localhost:3001/health >/dev/null 2>&1; then
    log_info "✅ Autonomous agent is responding"
else
    log_warn "⚠️  Autonomous agent health check failed (this might be normal if health endpoint is not implemented)"
fi

echo ""

# Step 10: Success message and next steps
log_step "9. Setup complete! 🎉"

echo ""
echo -e "${GREEN}✅ Autonomous Agent with Postgres is now running!${NC}"
echo ""
echo "📊 Service Information:"
echo "   🐘 PostgreSQL: localhost:${PG_PORT:-5433}"
echo "   🤖 Autonomous Agent: localhost:3001"
echo "   🗂️  Database Name: ${DB_NAME:-autonomous_agent}"
echo ""
echo "🔧 Useful Commands:"
echo "   View logs:           $COMPOSE_CMD logs -f"
echo "   Stop services:       $COMPOSE_CMD down"
echo "   Restart services:    $COMPOSE_CMD restart"
echo "   Access database:     $COMPOSE_CMD exec postgres psql -U postgres -d ${DB_NAME:-autonomous_agent}"
echo ""
echo "📝 Configuration:"
echo "   Environment file:    $ENV_FILE"
echo "   Docker compose:      $DOCKER_COMPOSE_FILE"
echo ""
echo "🔗 VTuber Integration:"
echo "   Endpoint URL:        ${VTUBER_URL:-http://localhost:5001/process_text}"
echo "   Loop Interval:       ${LOOP_INTERVAL:-30000}ms"
echo ""
echo "💡 Tips:"
echo "   - Monitor logs with: $COMPOSE_CMD logs -f autonomous-agent"
echo "   - Access database with npm run docker:psql"
echo "   - Edit .env file to update configuration"
echo "   - All interactions will be stored in PostgreSQL"
echo ""

# Optional: Show recent logs
read -p "Do you want to see the recent logs? (y/N): " show_logs
if [[ $show_logs =~ ^[Yy]$ ]]; then
    echo ""
    echo "Recent logs (last 50 lines):"
    echo "==============================="
    $COMPOSE_CMD logs --tail=50
fi

echo ""
log_info "Setup completed successfully! 🚀"
echo ""
echo "The autonomous agent is now ready to:"
echo "  • Store all interactions in PostgreSQL"
echo "  • Learn from VTuber responses"
echo "  • Build contextual knowledge over time"
echo "  • Operate autonomously with configurable intervals"
echo ""
echo "Happy coding! 🎯" 