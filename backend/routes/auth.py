"""
routes/auth.py

Authentication endpoints:
    POST /api/auth/register
    POST /api/auth/login
    GET  /api/auth/me
    POST /api/auth/logout  (documented no-op — see function docstring)
"""

import logging
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from motor.core import AgnosticDatabase

from database import get_database
from models.user import UserRole, UserStatus
from schemas.user import TokenResponse, UserLoginRequest, UserPublic, UserRegisterRequest, SendLoginCodeRequest, VerifyLoginCodeRequest
from services.user_service import (
    authenticate_user,
    create_user,
    email_exists,
    to_public_dict,
)
from utils.deps import get_current_user
from utils.jwt_handler import create_access_token
from config import settings
from services.email_service import send_login_code_email

logger = logging.getLogger("budgetnest.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(payload: UserRegisterRequest, db: AgnosticDatabase = Depends(get_database)):
    """
    Register a new BudgetNest user.

    BudgetNest is a personal application with a single application
    role, so every self-registered account is created as UserRole.USER
    — role is never accepted from client input.
    """
    if await email_exists(db, payload.email):
        # Deliberately generic: don't hint at *why* in more detail than
        # necessary, but registration conventionally does confirm
        # duplicate emails (unlike login, which stays fully generic).
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user_doc = await create_user(
        db,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        role=UserRole.USER,
    )
    logger.info("New user registered: %s", payload.email)
    return UserPublic(**to_public_dict(user_doc))


@router.post("/login", response_model=TokenResponse, summary="Log in and receive a JWT access token")
async def login(payload: UserLoginRequest, db: AgnosticDatabase = Depends(get_database)):
    """
    Authenticate with email + password and receive a JWT access token.

    Invalid email and invalid password return the exact same generic
    error, so a caller cannot use this endpoint to enumerate which
    emails are registered.
    """
    user_doc = await authenticate_user(db, payload.email, payload.password)
    if user_doc is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user_doc["status"] != UserStatus.ACTIVE.value:
        # Checked only *after* credentials are confirmed valid, so this
        # never leaks account existence to an attacker guessing passwords.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user_doc['status'].lower()}",
        )

    access_token = create_access_token(user_id=str(user_doc["_id"]), role=user_doc["role"])

    return TokenResponse(
        access_token=access_token,
        user=UserPublic(**to_public_dict(user_doc)),
    )


@router.get("/me", response_model=UserPublic, summary="Get the currently authenticated user")
async def read_current_user(current_user: UserPublic = Depends(get_current_user)):
    """Requires a valid 'Authorization: Bearer <token>' header."""
    return current_user


@router.post("/logout", summary="Log out (client-side token discard)")
async def logout(current_user: UserPublic = Depends(get_current_user)):
    """
    JWT access tokens are stateless and are not stored server-side, so
    there is nothing for the server to invalidate yet. The client is
    responsible for discarding the token (e.g. clearing it from
    storage/memory) to complete logout.

    This endpoint exists so the frontend has a single, consistent place
    to call — it also confirms the token was valid at the time of
    logout. If server-side revocation is needed later (e.g. a
    "log out everywhere" feature), it can be added as a small
    'token_blacklist' or 'token_version' field on the existing user
    document in this same MongoDB database — no new database required.
    """
    return {"message": "Logged out. Please discard the access token on the client."}


def _otp_hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


@router.post("/send-login-code", summary="Send a six digit login verification code")
async def send_login_code(payload: SendLoginCodeRequest, db: AgnosticDatabase = Depends(get_database)):
    email = str(payload.email).strip().lower()
    user = await db.users.find_one({"email": email})
    if user is None:
        raise HTTPException(status_code=404, detail="No account found with this email. Please create an account first.")
    if user.get("status") != UserStatus.ACTIVE.value:
        raise HTTPException(status_code=403, detail="Account is not active")
    now = datetime.now(timezone.utc)
    previous = await db.login_verification_codes.find_one({"email": email, "used": False}, sort=[("created_at", -1)])
    if previous and previous.get("last_sent_at"):
        elapsed = (now - previous["last_sent_at"]).total_seconds()
        if elapsed < settings.OTP_RESEND_COOLDOWN_SECONDS:
            raise HTTPException(status_code=429, detail=f"Please wait {int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed)} seconds before requesting another code")
    await db.login_verification_codes.update_many({"email": email, "used": False}, {"$set": {"used": True}})
    code = f"{secrets.randbelow(1_000_000):06d}"
    doc = {"user_id": user["_id"], "email": email, "code_hash": _otp_hash(code), "created_at": now, "last_sent_at": now, "expires_at": now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES), "used": False, "attempts": 0}
    await db.login_verification_codes.insert_one(doc)
    try:
        await send_login_code_email(email, code)
    except Exception as exc:
        await db.login_verification_codes.delete_one({"email": email, "code_hash": doc["code_hash"]})
        logger.exception("Failed to send login verification email")
        # Always surface the real, specific reason the send failed (bad
        # app password, wrong host/port, missing env vars, etc.) instead
        # of a generic "try again later" — a generic message here was
        # previously impossible to debug from the frontend alone.
        if settings.SMTP_CONFIGURED:
            detail = f"Unable to send verification code: {exc}"
        else:
            missing = [
                name
                for name, value in (
                    ("SMTP_HOST", settings.SMTP_HOST),
                    ("SMTP_USERNAME", settings.SMTP_USERNAME),
                    ("SMTP_PASSWORD", settings.SMTP_PASSWORD),
                )
                if not value
            ]
            detail = (
                "Unable to send verification code: SMTP is not configured "
                f"(missing: {', '.join(missing)}) and EMAIL_DEV_CONSOLE_FALLBACK "
                "is disabled. Set these in backend/.env (see .env.example), or "
                "set EMAIL_DEV_CONSOLE_FALLBACK=true to print the code to the "
                "backend console instead."
            )
        raise HTTPException(status_code=503, detail=detail) from exc

    if settings.EMAIL_DEV_CONSOLE_FALLBACK:
        # SMTP isn't configured yet — the code was printed to the backend
        # console/log instead of emailed. Let the frontend say so instead
        # of silently claiming an email was sent.
        return {
            "message": "SMTP is not configured — check the backend console/log for your verification code.",
            "expires_in_minutes": settings.OTP_EXPIRE_MINUTES,
            "dev_mode": True,
        }
    return {"message": "Verification code sent", "expires_in_minutes": settings.OTP_EXPIRE_MINUTES}


@router.post("/verify-login-code", response_model=TokenResponse, summary="Verify email login code and receive JWT")
async def verify_login_code(payload: VerifyLoginCodeRequest, db: AgnosticDatabase = Depends(get_database)):
    email = str(payload.email).strip().lower()
    now = datetime.now(timezone.utc)
    record = await db.login_verification_codes.find_one({"email": email, "used": False}, sort=[("created_at", -1)])
    if not record or record.get("expires_at") <= now:
        raise HTTPException(status_code=400, detail="Verification code is invalid or expired")
    if record.get("attempts", 0) >= settings.OTP_MAX_ATTEMPTS:
        await db.login_verification_codes.update_one({"_id": record["_id"]}, {"$set": {"used": True}})
        raise HTTPException(status_code=429, detail="Too many verification attempts. Request a new code.")
    if not secrets.compare_digest(record["code_hash"], _otp_hash(payload.code)):
        await db.login_verification_codes.update_one({"_id": record["_id"]}, {"$inc": {"attempts": 1}})
        raise HTTPException(status_code=400, detail="Incorrect verification code")
    await db.login_verification_codes.update_one({"_id": record["_id"]}, {"$set": {"used": True}})
    user = await db.users.find_one({"_id": record["user_id"]})
    if not user or user.get("status") != UserStatus.ACTIVE.value:
        raise HTTPException(status_code=401, detail="Unable to complete login")
    access_token = create_access_token(user_id=str(user["_id"]), role=user["role"])
    return TokenResponse(access_token=access_token, user=UserPublic(**to_public_dict(user)))


@router.post("/resend-login-code", summary="Resend login verification code")
async def resend_login_code(payload: SendLoginCodeRequest, db: AgnosticDatabase = Depends(get_database)):
    return await send_login_code(payload, db)
