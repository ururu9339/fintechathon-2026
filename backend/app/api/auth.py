from datetime import datetime, timezone
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..auth import (
    _hash_token,
    _now,
    create_access_token,
    enforce_rate_limit,
    get_current_user,
    hash_password,
    issue_action_token,
    issue_refresh_session,
    request_client_key,
    send_email,
    verify_password,
)
from ..db import get_session
from ..models import EmailActionToken, RefreshSession, User

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)


class LoginRequest(RegisterRequest):
    pass


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class ActionTokenRequest(BaseModel):
    token: str = Field(min_length=20)


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3)


class PasswordResetConfirmRequest(ActionTokenRequest):
    password: str = Field(min_length=8)


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=8)


class UserResponse(BaseModel):
    id: str
    email: str
    is_active: bool
    email_verified: bool = False

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
    verification_email_sent: bool = False


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        email_verified=user.email_verified_at is not None,
    )


def _tokens(user: User, session: Session, verification_email_sent: bool = False) -> TokenResponse:
    refresh_token, refresh_session = issue_refresh_session(user.id, session)
    return TokenResponse(
        access_token=create_access_token(user.id, refresh_session.id),
        refresh_token=refresh_token,
        user=_user_response(user),
        verification_email_sent=verification_email_sent,
    )


def _send_verification(user: User, token: str) -> bool:
    base_url = os.getenv("APP_PUBLIC_URL", "http://localhost:3000").rstrip("/")
    return send_email(
        user.email,
        "Verify your Qyze Ai account",
        f"Open {base_url}/verify-email?token={token} to verify your email address.",
    )


@router.post("/register", response_model=TokenResponse)
def register(
    request: RegisterRequest,
    http_request: Request,
    session: Session = Depends(get_session),
):
    enforce_rate_limit(request_client_key(http_request, "register"), session, 5)
    email = request.email.strip().lower()
    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(status_code=409, detail="Email is already registered.")
    user = User(email=email, hashed_password=hash_password(request.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    token = issue_action_token(user.id, "verify_email", session)
    email_sent = _send_verification(user, token)
    return _tokens(user, session, email_sent)


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    http_request: Request,
    session: Session = Depends(get_session),
):
    enforce_rate_limit(request_client_key(http_request, "login"), session, 10)
    user = session.exec(
        select(User).where(User.email == request.email.strip().lower())
    ).first()
    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user.is_active or user.deleted_at:
        raise HTTPException(status_code=401, detail="User account is inactive.")
    return _tokens(user, session)


@router.post("/verify-email", response_model=UserResponse)
def verify_email(request: ActionTokenRequest, session: Session = Depends(get_session)):
    action = session.exec(
        select(EmailActionToken).where(
            EmailActionToken.token_hash == _hash_token(request.token),
            EmailActionToken.purpose == "verify_email",
            EmailActionToken.used_at.is_(None),
        )
    ).first()
    if action is None or action.expires_at <= _now():
        raise HTTPException(status_code=400, detail="Verification token is invalid or expired.")
    user = session.get(User, action.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Verification token is invalid.")
    now = datetime.now(timezone.utc)
    user.email_verified_at = now
    action.used_at = now
    session.add(user)
    session.add(action)
    session.commit()
    return _user_response(user)


@router.post("/password-reset/request")
def request_password_reset(
    request: PasswordResetRequest,
    http_request: Request,
    session: Session = Depends(get_session),
):
    enforce_rate_limit(request_client_key(http_request, "password-reset"), session, 5)
    user = session.exec(
        select(User).where(User.email == request.email.strip().lower())
    ).first()
    if user and user.is_active and not user.deleted_at:
        token = issue_action_token(user.id, "password_reset", session)
        send_email(
            user.email,
            "Reset your Qyze Ai password",
            f"Open {os.getenv('APP_PUBLIC_URL', 'http://localhost:3000').rstrip('/')}/reset-password?token={token} to set a new password.",
        )
    return {"message": "If the account exists, password reset instructions have been sent."}


@router.post("/password-reset/confirm", response_model=TokenResponse)
def confirm_password_reset(
    request: PasswordResetConfirmRequest,
    session: Session = Depends(get_session),
):
    action = session.exec(
        select(EmailActionToken).where(
            EmailActionToken.token_hash == _hash_token(request.token),
            EmailActionToken.purpose == "password_reset",
            EmailActionToken.used_at.is_(None),
        )
    ).first()
    if action is None or action.expires_at <= _now():
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired.")
    user = session.get(User, action.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Reset token is invalid.")
    now = datetime.now(timezone.utc)
    user.hashed_password = hash_password(request.password)
    user.password_changed_at = now
    action.used_at = now
    for active_session in session.exec(
        select(RefreshSession).where(
            RefreshSession.user_id == user.id,
            RefreshSession.revoked_at.is_(None),
        )
    ).all():
        active_session.revoked_at = now
        session.add(active_session)
    session.add(user)
    session.add(action)
    session.commit()
    return _tokens(user, session)


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: RefreshRequest, session: Session = Depends(get_session)):
    refresh_session = session.exec(
        select(RefreshSession).where(
            RefreshSession.token_hash == _hash_token(request.refresh_token)
        )
    ).first()
    if (
        refresh_session is None
        or refresh_session.revoked_at is not None
        or refresh_session.expires_at <= _now()
    ):
        raise HTTPException(status_code=401, detail="Refresh token is invalid or expired.")
    user = session.get(User, refresh_session.user_id)
    if user is None or not user.is_active or user.deleted_at:
        raise HTTPException(status_code=401, detail="User account is inactive.")
    refresh_session.revoked_at = _now()
    session.add(refresh_session)
    session.commit()
    tokens = _tokens(user, session)
    replacement = session.exec(
        select(RefreshSession).where(
            RefreshSession.token_hash == _hash_token(tokens.refresh_token)
        )
    ).one()
    refresh_session.replaced_by_id = replacement.id
    session.add(refresh_session)
    session.commit()
    return tokens


@router.post("/logout")
def logout(request: RefreshRequest, session: Session = Depends(get_session)):
    refresh_session = session.exec(
        select(RefreshSession).where(
            RefreshSession.token_hash == _hash_token(request.refresh_token)
        )
    ).first()
    if refresh_session and refresh_session.revoked_at is None:
        refresh_session.revoked_at = _now()
        session.add(refresh_session)
        session.commit()
    return {"message": "Logged out."}


@router.delete("/me")
def delete_account(
    request: DeleteAccountRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password.")
    now = datetime.now(timezone.utc)
    user.email = f"deleted-{user.id}@invalid.local"
    user.hashed_password = hash_password(__import__("secrets").token_urlsafe(32))
    user.is_active = False
    user.deleted_at = now
    for refresh_session in session.exec(
        select(RefreshSession).where(
            RefreshSession.user_id == user.id,
            RefreshSession.revoked_at.is_(None),
        )
    ).all():
        refresh_session.revoked_at = now
        session.add(refresh_session)
    session.add(user)
    session.commit()
    return {"message": "Account deleted."}


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return _user_response(user)
