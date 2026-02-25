# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Kimlik doğrulama semalari. Şifre karmasiklik doğrulamasi dahil.

import re
from pydantic import BaseModel, field_validator


def _validate_password_strength(password: str) -> str:
    """Şifre karmasiklik kontrolü: en az 8 karakter, buyuk/kucuk harf, rakam."""
    if len(password) < 8:
        raise ValueError("Şifre en az 8 karakter olmalıdır")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Şifre en az bir buyuk harf icermelidir")
    if not re.search(r"[a-z]", password):
        raise ValueError("Şifre en az bir kucuk harf icermelidir")
    if not re.search(r"\d", password):
        raise ValueError("Şifre en az bir rakam icermelidir")
    return password


class UserLogin(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str | None = None

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    display_name: str | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    is_admin: bool

    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_new_password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class ProfileUpdate(BaseModel):
    display_name: str | None = None
