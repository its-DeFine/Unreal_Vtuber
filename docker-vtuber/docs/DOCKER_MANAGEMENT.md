# Docker Container Management

This document describes how to use the Docker management script for building, running, and testing containers in this project.

## Quick Start

The project includes a comprehensive Docker management script that simplifies container operations:

```bash
# Make the script executable (one-time setup)
chmod +x docker-manager

# Show all available options
./docker-manager --help

# Common operations
./docker-manager --build-run    # Build and run containers
./docker-manager --test         # Test the endpoint
./docker-manager --status       # Check container status
./docker-manager --logs         # View logs
```

## Script Features

### Core Operations

| Command | Description | Example |
|---------|-------------|---------|
| `--build` | Build containers only | `./docker-manager --build` |
| `--run` | Run containers without building | `./docker-manager --run` |
| `--build-run` | Build and run containers in one step | `./docker-manager --build-run` |
| `--stop` | Stop all running containers | `./docker-manager --stop` |
| `--down` | Stop and remove containers | `./docker-manager --down` |

### Testing & Monitoring

| Command | Description | Example |
|---------|-------------|---------|
| `--test` | Test the endpoint with automatic retries | `./docker-manager --test` |
| `--logs` | Show container logs (follow mode) | `./docker-manager --logs` |
| `--status` | Show container status and system resources | `./docker-manager --status` |

### Maintenance

| Command | Description | Example |
|---------|-------------|---------|
| `--clean` | Clean up containers, images, and volumes | `./docker-manager --clean` |

### Configuration Options

| Option | Description | Example |
|--------|-------------|---------|
| `--bridge-only` | Use only bridge compose file (neurosync, nginx-rtmp, redis) | `./docker-manager --run --bridge-only` |
| `--full-stack` | Use both bridge and byoc compose files | `./docker-manager --build-run --full-stack` |

## Architecture

The script manages two Docker Compose configurations:

### Bridge Configuration (Default)
- **Services**: neurosync, nginx-rtmp, redis
- **Compose file**: `docker-compose.bridge.yml`
- **Use case**: Core functionality testing

### Full Stack Configuration
- **Services**: All services from both compose files
- **Compose files**: `docker-compose.bridge.yml` + `docker-compose.byoc.yml`
- **Use case**: Complete system testing

## Common Workflows

### Development Workflow

1. **Initial Setup**
   ```bash
   ./docker-manager --build-run --bridge-only
   ```

2. **Test the System**
   ```bash
   ./docker-manager --test
   ```

3. **Monitor Logs**
   ```bash
   ./docker-manager --logs
   ```

4. **Check Status**
   ```bash
   ./docker-manager --status
   ```

### Production Deployment

1. **Full Stack Build**
   ```bash
   ./docker-manager --build --full-stack
   ```

2. **Run Production Stack**
   ```bash
   ./docker-manager --run --full-stack
   ```

3. **Verify Deployment**
   ```bash
   ./docker-manager --test
   ./docker-manager --status
   ```

### Troubleshooting

1. **Clean Start**
   ```bash
   ./docker-manager --down
   ./docker-manager --build-run
   ```

2. **Full System Reset**
   ```bash
   ./docker-manager --clean  # WARNING: Removes all containers and images
   ./docker-manager --build-run
   ```

3. **Debug Issues**
   ```bash
   ./docker-manager --logs    # Check logs
   ./docker-manager --status  # Check container status
   ```

## Features

### Intelligent Logging
- Automatic log file generation with timestamps
- Colored output for better readability
- Structured logging with timestamps

### Error Handling
- Automatic retry mechanism for endpoint testing
- Exit on error for build failures
- Comprehensive error messages

### Resource Management
- Automatic log directory creation
- System resource monitoring
- Clean shutdown procedures

## Endpoint Testing

The script includes automatic endpoint testing:

- **URL**: `http://localhost:5001/process_text`
- **Method**: POST
- **Payload**: `{"text":"Hello from docker-manager script"}`
- **Retries**: 5 attempts with 3-second intervals
- **Response**: JSON formatted if available

### Test Output Example

```bash
$ ./docker-manager --test
[2024-01-15 10:30:45] Testing endpoint: http://localhost:5001/process_text
[2024-01-15 10:30:46] Endpoint test successful!
[INFO] Response:
{
  "status": "success",
  "processed_text": "Hello from docker-manager script",
  "timestamp": "2024-01-15T10:30:46Z"
}
```

## Log Management

### Build Logs
- Location: `logs/build_YYYYMMDD_HHMMSS.log`
- Content: Full Docker build output with progress
- Format: Plain text with timestamps

### Container Logs
- Access: `./docker-manager --logs`
- Format: Docker compose logs with service names
- Mode: Follow mode (real-time updates)

## Environment Configuration

The script automatically detects and uses:

- `docker-compose.bridge.yml` - Core services
- `docker-compose.byoc.yml` - Extended services
- `logs/` - Log directory (auto-created)

## Error Codes

| Exit Code | Description |
|-----------|-------------|
| 0 | Success |
| 1 | Build failure or command error |
| 2 | Endpoint test failure |

## Advanced Usage

### Custom Compose Files

If you need to use different compose files, edit the configuration section in `scripts/docker-manager.sh`:

```bash
# Configuration
BRIDGE_COMPOSE="your-bridge-compose.yml"
BYOC_COMPOSE="your-byoc-compose.yml"
ENDPOINT_URL="http://localhost:your-port/your-endpoint"
```

### Integration with CI/CD

The script can be used in automated pipelines:

```bash
# Build and test
./docker-manager --build --bridge-only
./docker-manager --run --bridge-only
./docker-manager --test || exit 1
./docker-manager --down
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   chmod +x docker-manager
   chmod +x scripts/docker-manager.sh
   ```

2. **Docker Not Running**
   ```bash
   sudo systemctl start docker
   ```

3. **Compose Files Not Found**
   - Ensure you're running from the project root
   - Check that compose files exist

4. **Endpoint Test Fails**
   - Verify containers are running: `./docker-manager --status`
   - Check logs: `./docker-manager --logs`
   - Ensure services are ready (may take time to start)

5. **Build Failures**
   - Check build logs in `logs/` directory
   - Clean up and retry: `./docker-manager --clean && ./docker-manager --build-run`

### Getting Help

- Use `./docker-manager --help` for command reference
- Check logs for detailed error information
- Use `--status` to verify container states

## Migration from Manual Commands

If you were previously using manual Docker commands, here's the mapping:

| Old Command | New Command |
|-------------|-------------|
| `docker compose -f docker-compose.bridge.yml build` | `./docker-manager --build --bridge-only` |
| `docker compose -f docker-compose.bridge.yml up` | `./docker-manager --run --bridge-only` |
| `docker compose -f docker-compose.bridge.yml up --build` | `./docker-manager --build-run --bridge-only` |
| `curl -X POST ... http://localhost:5001/process_text` | `./docker-manager --test` |
| `docker compose logs` | `./docker-manager --logs` |
| `docker compose ps` | `./docker-manager --status` | 