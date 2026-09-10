"""
utils/security.py

Password hashing helpers built directly on `bcrypt`.

bcrypt is used directly (rather than through passlib) to avoid
passlib/bcrypt version-compatibility issues, while still giving a
well-audited, industry-standard hashing algorithm with per-password
salting built in.
"""

import bcrypt

# bcrypt has a 72-byte input limit; longer passwords are truncated by
# the algorithm itself. We cap accepted password length in the schema
# (128 chars) and bcrypt handles the rest safely.


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password for storage. Never store the plain password."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # Malformed hash stored, or unexpected input — treat as verification failure
        # rather than raising, so callers can respond with a clean 401.
        return False
