import os

from dotenv import load_dotenv
from openai import OpenAI
from cryptography.fernet import Fernet, InvalidToken

load_dotenv()


def get_openai_client() -> OpenAI | None:
    api_key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=api_key) if api_key else None


def _cipher() -> Fernet:
    key = os.getenv("PII_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("PII_ENCRYPTION_KEY is required for PII encryption.")
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise RuntimeError("PII_ENCRYPTION_KEY is not a valid Fernet key.") from exc


def encrypt_pii(data: str) -> str:
    if not data or data == "NA":
        return data
    return _cipher().encrypt(data.encode()).decode()


def decrypt_pii(token: str) -> str:
    if not token or token == "NA":
        return token
    try:
        return _cipher().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("PII decryption failed; check the configured encryption key.") from exc
