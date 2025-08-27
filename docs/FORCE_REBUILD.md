# Force Rebuild System for Unreal VTuber

*Created: 2025-08-27*

## Overview

This system ensures that the Unreal VTuber containers are rebuilt from scratch whenever critical changes are made to the repository, preventing cache-related issues and ensuring consistency across deployments.

## Automatic Rebuilds

### GitHub Actions Workflow

The system automatically triggers rebuilds via GitHub Actions when:

1. **Push to main/BYOC branches** - Any commit triggers a change detection
2. **Pull requests** - Rebuilds run to validate changes
3. **Manual trigger** - Via GitHub Actions UI with force rebuild option

### Files That Trigger Rebuilds

The following file changes automatically trigger a full rebuild:

- `**/Dockerfile*` - Any Dockerfile changes
- `**/docker-compose*.yml` - Docker Compose configuration changes
- `**/requirements*.txt` - Python dependency changes
- `**/package*.json` - Node.js dependency changes
- `NeuroBridge/**` - Any changes in the NeuroBridge module

## Manual Rebuilds

### Using the Script

Run a force rebuild locally:

```bash
# Full rebuild with no cache
./scripts/force-rebuild.sh

# Rebuild with cache (faster)
./scripts/force-rebuild.sh --cache

# Keep old images (no cleanup)
./scripts/force-rebuild.sh --no-clean

# Use different compose file
./scripts/force-rebuild.sh -f docker-compose.bridge.yml
```

### Using Docker Compose Directly

```bash
# Stop and clean everything
docker-compose -f docker-compose.byoc.yml down --rmi local -v

# Rebuild with no cache
docker-compose -f docker-compose.byoc.yml build --no-cache --parallel

# Start services
docker-compose -f docker-compose.byoc.yml up -d
```

## Configuration

### rebuild.config.yml

The rebuild behavior is configured in `rebuild.config.yml`:

```yaml
rebuild_settings:
  force_no_cache: true        # Always use --no-cache
  clean_before_build: true    # Remove old images
  parallel_builds: true       # Build in parallel
  max_parallel: 3            # Max parallel builds
```

### Environment Variables

Set these in your environment or `.env` file:

```bash
# Force rebuild on every update
FORCE_REBUILD_ON_VTUBER_UPDATE=true

# Slack notifications (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

## Health Checks

After rebuild, the system checks:

1. **NeuroSync API** - `http://localhost:5000/health`
2. **BYOC Worker** - `http://localhost:9876/health`
3. **WebApp** - `http://localhost:3000`

## CI/CD Integration

### GitHub Actions

The workflow runs on:
- Every push to main/BYOC
- Every pull request
- Manual dispatch

### Deployment

After successful rebuild:

1. Images are tagged with commit SHA
2. Pushed to GitHub Container Registry
3. Notification sent to PR (if applicable)

## Troubleshooting

### Rebuild Not Triggering

1. Check workflow runs: Go to Actions tab in GitHub
2. Verify file changes match trigger patterns
3. Check branch protection rules

### Build Failures

1. **Out of space**: Clean Docker system
   ```bash
   docker system prune -af
   ```

2. **Network issues**: Check Docker daemon
   ```bash
   docker info
   ```

3. **GPU issues**: Verify NVIDIA drivers
   ```bash
   nvidia-smi
   ```

### Health Check Failures

1. Check logs:
   ```bash
   docker-compose -f docker-compose.byoc.yml logs neurosync
   ```

2. Verify ports:
   ```bash
   netstat -tuln | grep -E "5000|9876|3000"
   ```

3. Test endpoints:
   ```bash
   curl http://localhost:5000/health
   ```

## Performance Considerations

### Build Times

- **Full rebuild**: 5-10 minutes
- **With cache**: 1-3 minutes
- **Parallel builds**: 30-50% faster

### Resource Usage

- **CPU**: High during build (all cores)
- **Memory**: ~8GB during build
- **Disk**: ~20GB for images and cache
- **Network**: ~2GB download for base images

## Best Practices

1. **Always rebuild for production** deployments
2. **Use cache for development** to save time
3. **Clean images weekly** to free disk space
4. **Monitor health checks** after deployment
5. **Tag images properly** for rollback capability

## Rollback Procedure

If a rebuild causes issues:

```bash
# List available images
docker images | grep vtuber

# Tag and use previous version
docker tag ghcr.io/its-define/vtuber-neurosync:SHA_HERE neurosync:rollback
docker-compose -f docker-compose.byoc.yml up -d
```

## Security Notes

- Never cache sensitive layers (keys, tokens)
- Always rebuild after security updates
- Use specific base image versions in production
- Scan images for vulnerabilities regularly

## Related Documentation

- [Docker Compose BYOC Setup](../docker-compose.byoc.yml)
- [NeuroBridge Documentation](../NeuroBridge/README.md)
- [GitHub Actions Workflows](../.github/workflows/)