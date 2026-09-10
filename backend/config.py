"""
config.py

Centralized application configuration.
Loads values from environment variables (via a .env file in development)
so that no secrets or environment-specific values are hard-coded.
"""

import os
from dotenv import load_dotenv

# Load variables from a .env file (if present) into the process environment.
# In production, real environment variables should be set directly and this
# call simply becomes a no-op if no .env file exists.
load_dotenv()


def _get_env(name: str, default: str | None = None, required: bool = False) -> str:
    """Small helper to fetch an environment variable with optional validation."""
    value = os.getenv(name, default)
    if required and (value is None or value == ""):
        raise RuntimeError(
            f"Missing required environment variable: '{name}'. "
            f"Check your .env file against .env.example."
        )
    return value


def _get_env_bool(name: str, default: bool) -> bool:
    """
    Boolean env var helper that accepts common truthy spellings
    (true/1/yes/on), not just the literal string "true". Without this,
    a .env value like EMAIL_DEV_CONSOLE_FALLBACK=1 was silently treated
    as false, which could unexpectedly disable the local dev fallback
    and turn a "SMTP not configured" case into a hard 503.
    """
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("true", "1", "yes", "on")


class Settings:
    """
    Application settings, populated once at import time.
    Import `settings` from this module wherever configuration is needed.
    """

    # --- App metadata ---
    APP_NAME: str = "BudgetNest Backend"
    APP_VERSION: str = "0.1.0"

    # --- MongoDB ---
    MONGO_URL: str = _get_env("MONGO_URL", required=True)
    DB_NAME: str = _get_env("DB_NAME", required=True)

    # --- JWT (values loaded now for future auth stage; not used yet) ---
    JWT_SECRET: str = _get_env("JWT_SECRET", required=True)
    JWT_ALGORITHM: str = _get_env("JWT_ALGORITHM", default="HS256")
    JWT_EXPIRE_MINUTES: int = int(_get_env("JWT_EXPIRE_MINUTES", default="60"))

    # --- CORS ---
    # Comma-separated list of allowed origins, e.g.:
    # CORS_ORIGINS=http://localhost:3000,http://localhost:5173
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in _get_env("CORS_ORIGINS", default="http://localhost:3000").split(",")
        if origin.strip()
    ]


# Single shared settings instance used across the application.
settings = Settings()

# SMTP / email OTP settings
Settings.SMTP_HOST = _get_env("SMTP_HOST", default="")
Settings.SMTP_PORT = int(_get_env("SMTP_PORT", default="587"))
Settings.SMTP_USERNAME = _get_env("SMTP_USERNAME", default="")
Settings.SMTP_PASSWORD = _get_env("SMTP_PASSWORD", default="")
Settings.SMTP_FROM_EMAIL = _get_env("SMTP_FROM_EMAIL", default=Settings.SMTP_USERNAME)
Settings.SMTP_FROM_NAME = _get_env("SMTP_FROM_NAME", default="BudgetNest")
Settings.SMTP_USE_TLS = _get_env_bool("SMTP_USE_TLS", default=True)
Settings.OTP_EXPIRE_MINUTES = int(_get_env("OTP_EXPIRE_MINUTES", default="10"))
Settings.OTP_RESEND_COOLDOWN_SECONDS = int(_get_env("OTP_RESEND_COOLDOWN_SECONDS", default="60"))
Settings.OTP_MAX_ATTEMPTS = int(_get_env("OTP_MAX_ATTEMPTS", default="5"))

# Whether SMTP is fully configured. Used at startup to surface a clear,
# early warning (see main.py) instead of letting /auth/send-login-code
# fail mysteriously on first use with a generic 503.
Settings.SMTP_CONFIGURED = bool(
    Settings.SMTP_HOST and Settings.SMTP_USERNAME and Settings.SMTP_PASSWORD
)

# When SMTP is not configured (e.g. local development in VS Code with no
# mail credentials on hand), fall back to printing the verification code
# to the backend console/log instead of returning a 503 to the client.
# This is what lets "Email Code" sign-in work end-to-end out of the box
# before real SMTP credentials are ever set up. It is automatically
# disabled the moment SMTP_HOST/USERNAME/PASSWORD are filled in, and can
# always be forced off explicitly (e.g. in production) via
# EMAIL_DEV_CONSOLE_FALLBACK=false in the environment.
Settings.EMAIL_DEV_CONSOLE_FALLBACK = (
    _get_env_bool("EMAIL_DEV_CONSOLE_FALLBACK", default=True)
    and not Settings.SMTP_CONFIGURED
)
