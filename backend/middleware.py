"""
JWT Authentication Middleware

T032: Validate JWT signature using EdDSA from JWKS
T033: Verify JWT expiration time
T034: Extract user_id from JWT payload
"""

from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient
from config import settings
from typing import Optional


class JWTBearer(HTTPBearer):
    """
    HTTP Bearer authentication scheme that validates JWT tokens.

    This middleware:
    1. Extracts the Bearer token from Authorization header
    2. Validates JWT signature (T032)
    3. Checks expiration time (T033)
    4. Extracts user_id from payload (T034)
    5. Adds user_id to request state for route handlers
    """

    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)

        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication scheme. Use 'Bearer <token>'"
                )

            token = credentials.credentials
            user_id = verify_token(token)

            if not user_id:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired token"
                )

            # T034: Add user_id to request state for later use in route handlers
            request.state.user_id = user_id
            return credentials.credentials
        else:
            raise HTTPException(
                status_code=401,
                detail="Missing authorization credentials"
            )


# Initialize JWKS client to fetch public keys from Better Auth
# Better Auth exposes JWKS endpoint at /api/auth/jwks
JWKS_URL = f"{settings.BETTER_AUTH_URL}/api/auth/jwks"
jwks_client = PyJWKClient(JWKS_URL)


def verify_token(token: str) -> Optional[str]:
    """
    Verify the JWT token and return the user_id if valid.

    T032: Validates JWT signature using JWKS public key (EdDSA)
    T033: Verifies token expiration time
    T034: Extracts user_id from payload

    Args:
        token: JWT token string

    Returns:
        user_id if token is valid, None otherwise
    """
    try:
        print(f"=== DEBUG BACKEND: Received token (first 50 chars): {token[:50]}")

        # T032: Get the signing key from JWKS
        # The PyJWKClient fetches the public key from Better Auth's JWKS endpoint
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Decode and verify the JWT token using the public key
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["EdDSA", "ES256", "RS256"],  # Support Better Auth algorithms
            options={
                "verify_exp": True,  # T033: Verify expiration
                "verify_aud": False,  # Don't verify audience claim
            }
        )

        print(f"=== DEBUG BACKEND: Decoded payload: {payload}")

        # T034: Extract user_id from the payload
        # Better Auth uses 'id' or 'sub' field, so check both
        user_id = payload.get("user_id") or payload.get("id") or payload.get("sub")

        if not user_id:
            # Token must contain user_id, id, or sub
            print(f"=== DEBUG BACKEND: Token missing user_id/id/sub. Payload keys: {payload.keys()}")
            return None

        print(f"=== DEBUG BACKEND: Successfully validated token for user_id: {user_id}")
        return user_id

    except Exception as e:
        # Token signature invalid, expired, or malformed
        print(f"=== DEBUG BACKEND: JWT validation error: {e}")
        return None