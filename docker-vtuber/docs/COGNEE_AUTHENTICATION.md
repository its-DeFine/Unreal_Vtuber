# Cognee Authentication Configuration

This guide explains how to configure authentication for the Cognee memory service in the docker-vtuber system.

## Overview

Cognee provides two authentication methods:
1. **Username/Password Authentication** - Full authentication with user management
2. **Bearer Token Authentication** - Pre-generated tokens for service integration (recommended)

## Configuration Options

### Option 1: Username/Password Authentication (Default)

Add these variables to your `.env` file:

```env
COGNEE_URL=http://cognee:8000
COGNEE_USERNAME=your_email@example.com
COGNEE_PASSWORD=your_password
```

**Note:** You need to register these credentials with your Cognee instance first.

### Option 2: Bearer Token Authentication (Recommended)

This method is recommended for service integration as it's simpler and more secure.

#### Generate a Bearer Token

1. Use the provided script to generate a token:

```bash
cd app/CORE/autogen-agent/scripts
python generate_cognee_token.py \
  --user-id "6763554c-91bd-432c-aba8-d42cd72ed659" \
  --tenant-id "autogen_tenant" \
  --roles admin \
  --secret "your-cognee-jwt-secret" \
  --hours 720  # 30 days
```

2. Add the generated token to your `.env` file:

```env
COGNEE_URL=http://cognee:8000
COGNEE_BEARER_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Important:** The `--secret` must match the `FASTAPI_USERS_JWT_SECRET` configured in your Cognee instance.

## Troubleshooting

### 401 Authentication Errors

If you see 401 errors in the logs:

1. **Check Token/Credentials**: Ensure your bearer token or username/password are correct
2. **Verify Secret Key**: The JWT secret used to generate tokens must match Cognee's configuration
3. **Check Expiration**: Bearer tokens expire - generate a new one if needed
4. **Verify Cognee URL**: Ensure the URL points to your Cognee instance

### Fallback to PostgreSQL

If Cognee authentication fails, the system will automatically fall back to PostgreSQL-only storage:

```
⚠️ [COGNITIVE_MEMORY] Cognee service unavailable - using PostgreSQL fallback
```

This ensures the system continues to function even if Cognee is unavailable.

### Disabling Cognee

To disable Cognee entirely, remove or empty the Cognee environment variables:

```env
COGNEE_URL=
COGNEE_BEARER_TOKEN=
```

## Security Best Practices

1. **Never commit tokens or passwords** to version control
2. **Use long-lived tokens** for production (e.g., 30-90 days)
3. **Rotate tokens regularly** 
4. **Use environment-specific tokens** for dev/staging/production
5. **Monitor authentication logs** for failed attempts

## Example Docker Compose Configuration

The docker-compose file automatically reads from your `.env`:

```yaml
environment:
  - COGNEE_URL=${COGNEE_URL:-http://cognee:8000}
  - COGNEE_USERNAME=${COGNEE_USERNAME:-}
  - COGNEE_PASSWORD=${COGNEE_PASSWORD:-}
  - COGNEE_BEARER_TOKEN=${COGNEE_BEARER_TOKEN:-}
```

This configuration supports both authentication methods with fallback defaults.