#!/usr/bin/env python3
"""
Generate a JWT bearer token for Cognee authentication.
Based on the documentation at: https://docs.cognee.ai/

Usage:
    python generate_cognee_token.py --user-id <user_id> --tenant-id <tenant_id> --secret <secret_key>
"""

import jwt
import datetime
import argparse
import sys
import os

def create_jwt(user_id: str, tenant_id: str, roles: list[str], secret_key: str, hours_valid: int = 24):
    """
    Create a JWT token for Cognee authentication.
    
    Args:
        user_id: Unique user identifier
        tenant_id: Tenant identifier
        roles: List of roles (e.g., ["admin", "user"])
        secret_key: Secret key for signing (must match FASTAPI_USERS_JWT_SECRET in Cognee)
        hours_valid: Number of hours the token is valid (default: 24)
    
    Returns:
        JWT token string
    """
    payload = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "roles": roles,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=hours_valid),
        "iat": datetime.datetime.utcnow(),
    }
    
    return jwt.encode(payload, secret_key, algorithm="HS256")

def main():
    parser = argparse.ArgumentParser(description="Generate JWT token for Cognee authentication")
    parser.add_argument("--user-id", required=True, help="User ID (e.g., UUID)")
    parser.add_argument("--tenant-id", required=True, help="Tenant ID")
    parser.add_argument("--roles", nargs="+", default=["admin"], help="User roles (default: admin)")
    parser.add_argument("--secret", help="JWT secret key (or set COGNEE_JWT_SECRET env var)")
    parser.add_argument("--hours", type=int, default=24, help="Token validity in hours (default: 24)")
    
    args = parser.parse_args()
    
    # Get secret from args or environment
    secret_key = args.secret or os.getenv("COGNEE_JWT_SECRET")
    if not secret_key:
        print("Error: JWT secret key must be provided via --secret or COGNEE_JWT_SECRET env var")
        sys.exit(1)
    
    # Generate token
    token = create_jwt(
        user_id=args.user_id,
        tenant_id=args.tenant_id,
        roles=args.roles,
        secret_key=secret_key,
        hours_valid=args.hours
    )
    
    print(f"\n🔐 Generated JWT Token (valid for {args.hours} hours):\n")
    print(token)
    print(f"\n✅ Add this to your .env file as:")
    print(f"COGNEE_BEARER_TOKEN={token}")
    
    # Decode to show contents
    decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
    print(f"\n📋 Token contents:")
    print(f"  User ID: {decoded['user_id']}")
    print(f"  Tenant ID: {decoded['tenant_id']}")
    print(f"  Roles: {', '.join(decoded['roles'])}")
    print(f"  Expires: {datetime.datetime.fromtimestamp(decoded['exp']).strftime('%Y-%m-%d %H:%M:%S UTC')}")

if __name__ == "__main__":
    main()