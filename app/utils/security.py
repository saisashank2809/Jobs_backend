"""
Security utilities for password hashing and verification.
Uses the bcrypt library directly for maximum performance and reliability.
"""

import bcrypt

def get_password_hash(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    """
    # bcrypt.hashpw expects bytes
    password_bytes = password.encode('utf-8')
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string for database storage
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        # Fallback for unexpected hash formats or errors
        return False
