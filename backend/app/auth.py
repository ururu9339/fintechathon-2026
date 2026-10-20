import hashlib
import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from .db import get_session
from .models import (
    BusinessMembership,
    EmailActionToken,
    RateLimitBucket,
    RefreshSession,
    User,
)

load_dotenv()
_bearer = HTTPBearer(auto_error=False)
ACCESS_TOKEN_MINUTES = 30
REFRESH_TOKEN_DAYS = 30


def _secret() -> str:
    secret = os.getenv("AMANAH_PAY_JWT_SECRET")
    if not secret or len(secret) < 32:
        raise RuntimeError("AMANAH_PAY_JWT_SECRET must contain at least 32 characters.")
    return secret


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: str, session_id: str | None = None) -> str:
    now = _now()
    claims = {"sub": user_id, "iat": now, "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES)}
    if session_id:
        claims["sid"] = session_id
    return jwt.encode(claims, _secret(), algorithm="HS256")


def issue_refresh_session(user_id: str, session: Session) -> tuple[str, RefreshSession]:
    raw_token = secrets.token_urlsafe(48)
    refresh_session = RefreshSession(
        user_id=user_id,
        token_hash=_hash_token(raw_token),
        expires_at=_now() + timedelta(days=REFRESH_TOKEN_DAYS),
    )
    session.add(refresh_session)
    session.commit()
    session.refresh(refresh_session)
    return raw_token, refresh_session


def issue_action_token(user_id: str, purpose: str, session: Session) -> str:
    raw_token = secrets.token_urlsafe(48)
    session.add(
        EmailActionToken(
            user_id=user_id,
            token_hash=_hash_token(raw_token),
            purpose=purpose,
            expires_at=_now() + timedelta(hours=24 if purpose == "verify_email" else 1),
        )
    )
    session.commit()
    return raw_token


def send_email(to_email: str, subject: str, body: str) -> bool:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM")
    if not all((host, username, password, sender)):
        return False
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(message)
    return True


def enforce_rate_limit(
    key: str,
    session: Session,
    limit: int,
    window_seconds: int = 900,
) -> None:
    now = _now()
    bucket = session.exec(
        select(RateLimitBucket).where(RateLimitBucket.bucket_key == key)
    ).first()
    if bucket is None or (now - bucket.window_start).total_seconds() >= window_seconds:
        if bucket is None:
            bucket = RateLimitBucket(bucket_key=key, window_start=now, request_count=0)
        else:
            bucket.window_start = now
            bucket.request_count = 0
    bucket.request_count += 1
    session.add(bucket)
    session.commit()
    if bucket.request_count > limit:
        raise HTTPException(status_code=429, detail="Too many requests. Try again later.")


def _decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except (jwt.InvalidTokenError, RuntimeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid authentication token.") from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    payload = _decode_access_token(credentials.credentials)
    user = session.get(User, payload.get("sub"))
    if user is None or not user.is_active or user.deleted_at:
        raise HTTPException(status_code=401, detail="User account is inactive or missing.")
    session_id = payload.get("sid")
    if session_id:
        refresh_session = session.get(RefreshSession, session_id)
        if refresh_session is None or refresh_session.revoked_at or refresh_session.expires_at <= _now():
            raise HTTPException(status_code=401, detail="Session is no longer active.")
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = _decode_access_token(credentials.credentials)
        user = session.get(User, payload.get("sub"))
        return user if user and user.is_active and not user.deleted_at else None
    except HTTPException:
        return None


def require_business_access(
    business_id: str,
    user: User,
    session: Session,
    minimum_role: str = "viewer",
) -> None:
    if not isinstance(user, User):
        return
    membership = session.exec(
        select(BusinessMembership).where(
            BusinessMembership.business_id == business_id,
            BusinessMembership.user_id == user.id,
        )
    ).first()
    if membership is None:
        raise HTTPException(status_code=403, detail="User has no access to this business.")
    if minimum_role == "owner" and membership.role != "owner":
        raise HTTPException(status_code=403, detail="Owner access is required.")


def get_current_business_id(user: User, session: Session) -> str:
    memberships = session.exec(
        select(BusinessMembership).where(BusinessMembership.user_id == user.id)
    ).all()
    if not memberships:
        raise HTTPException(status_code=403, detail="User is not linked to a business.")
    if len(memberships) > 1:
        raise HTTPException(
            status_code=409,
            detail="Multiple businesses are linked to this account; select a business context first.",
        )
    return memberships[0].business_id


def request_client_key(request: Request, prefix: str) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    client = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return f"{prefix}:{client}"
