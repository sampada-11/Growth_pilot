"""
Supabase / JWT Authentication & Tenant Token Service (§1 Multi-Tenant Auth Hardening)
Handles token creation, JWT cryptographic validation, and demo tenant credentials.
"""
import os
import time
import hashlib
import hmac
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

# JWT Configuration
JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "growthpilot_jwt_secret_key_2026_super_secure_production_token")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours
PASSWORD_SALT = "growthpilot_secure_salt_2026"


def hash_password(password: str) -> str:
    """Computes SHA-256 HMAC hash for user passwords."""
    return hmac.new(PASSWORD_SALT.encode(), password.encode(), hashlib.sha256).hexdigest()


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verifies a plain password against the stored hash in constant time."""
    computed = hash_password(plain_password)
    return hmac.compare_digest(computed, password_hash)


# Pre-registered Demo Tenants (§4 Second Demo Tenant)
DEMO_USERS = {
    "alpha@growthpilot.demo": {
        "user_id": "usr_alpha_001",
        "email": "alpha@growthpilot.demo",
        "password_hash": hash_password("password123"),
        "tenant_id": "tenant_store_alpha",
        "store_name": "SoundWave Audio (Tenant A)",
        "role": "growth_manager"
    },
    "beta@growthpilot.demo": {
        "user_id": "usr_beta_002",
        "email": "beta@growthpilot.demo",
        "password_hash": hash_password("password123"),
        "tenant_id": "tenant_store_beta",
        "store_name": "PulseWear Smart Gear (Tenant B)",
        "role": "growth_manager"
    }
}


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generates a cryptographically signed JWT with tenant_id claims."""
    to_encode = data.copy()
    now_utc = datetime.now(timezone.utc)
    expire = now_utc + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": now_utc})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates JWT token signature and expiry.
    Raises jwt.PyJWTError if invalid.
    """
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    if "tenant_id" not in payload:
        raise jwt.InvalidTokenError("Token missing mandatory 'tenant_id' claim")
    return payload


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates email & password against registered users."""
    user = DEMO_USERS.get(email.lower())
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def register_user(email: str, password: str, store_name: str) -> Dict[str, Any]:
    """Registers a new user and provisions a new tenant_id."""
    clean_email = email.lower()
    if clean_email in DEMO_USERS:
        raise ValueError("User with this email already exists")

    tenant_id = f"tenant_{clean_email.split('@')[0]}_{int(time.time())}"
    user = {
        "user_id": f"usr_{int(time.time())}",
        "email": clean_email,
        "password_hash": hash_password(password),
        "tenant_id": tenant_id,
        "store_name": store_name or "My E-Commerce Store",
        "role": "growth_manager"
    }
    DEMO_USERS[clean_email] = user
    return user
