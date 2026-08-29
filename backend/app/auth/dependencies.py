"""
FastAPI Authentication Dependencies (§1 Shared Auth Dependencies)
Enforces verified JWT authentication and server-side tenant derivation.
"""
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, Depends
import jwt
from backend.app.auth.jwt_auth import verify_jwt_token


def get_current_user(authorization: Optional[str] = Header(None, alias="Authorization")) -> Dict[str, Any]:
    """
    Validates the Supabase/JWT Bearer token from the Authorization header on every protected route.
    Raises HTTP 401 Unauthorized if missing, expired, or invalid.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail={"error": "Unauthorized", "message": "Missing Authorization header with Bearer token."}
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail={"error": "Unauthorized", "message": "Invalid Authorization header format. Expected 'Bearer <token>'."}
        )

    token = parts[1]
    try:
        payload = verify_jwt_token(token)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"error": "Token Expired", "message": "Authentication token has expired. Please log in again."}
        )
    except jwt.InvalidTokenError as err:
        raise HTTPException(
            status_code=401,
            detail={"error": "Invalid Token", "message": f"JWT verification failed: {str(err)}"}
        )


def get_current_tenant(current_user: Dict[str, Any] = Depends(get_current_user)) -> str:
    """
    Derives tenant_id exclusively from the verified JWT token claims.
    Never accepts tenant_id from client request body, query params, or unverified headers.
    """
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=403,
            detail={"error": "Forbidden", "message": "Authenticated user has no associated tenant_id claim."}
        )
    return str(tenant_id)
