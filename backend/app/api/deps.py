# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Paylasilan dependency injection fonksiyonlari.
# Coklu token kaynagi: Authorization header + httpOnly cookie
# IP doğrulama: Token'daki IP ile istemci IP'si karsilastirilir
# Token blacklist: Logout sonrası token geçersiz kilma

import hashlib
import ipaddress
import jwt
import logging
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.hal.base_driver import BaseNetworkDriver
from app.config import get_settings
from app.db.session import get_db
from app.models.user import User
import redis.asyncio as aioredis

settings = get_settings()
security = HTTPBearer(auto_error=False)
logger = logging.getLogger("tonbilai.auth")


def escape_like(value: str) -> str:
    """LIKE/CONTAINS sorgularinda wildcard enjeksiyonunu onle.
    % ve _ karakterlerini escape'ler."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

COOKIE_NAME = "tonbilai_session"

# Guvenilir proxy aglarini parse et (config'ten)
_TRUSTED_PROXY_NETS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
for _cidr in settings.TRUSTED_PROXIES.split(","):
    _cidr = _cidr.strip()
    if _cidr:
        try:
            _TRUSTED_PROXY_NETS.append(ipaddress.ip_network(_cidr, strict=False))
        except ValueError:
            pass


def _is_trusted_proxy(ip: str) -> bool:
    """IP adresinin guvenilir proxy listesinde olup olmadigini kontrol et."""
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in net for net in _TRUSTED_PROXY_NETS)
    except ValueError:
        return False


def _get_client_ip(request: Request) -> str:
    """İstemci IP adresini al. Sadece guvenilir proxy'den gelen X-Forwarded-For'a guven."""
    direct_ip = request.client.host if request.client else "unknown"
    # Sadece guvenilir proxy'den gelen isteklerde header'lara guven
    if _is_trusted_proxy(direct_ip):
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
    return direct_ip


def _extract_token(request: Request, credentials: HTTPAuthorizationCredentials | None) -> str | None:
    """Token'i al: Öncelik Bearer header > Cookie."""
    # 1. Authorization: Bearer <token>
    if credentials and credentials.credentials:
        return credentials.credentials
    # 2. httpOnly cookie
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        return cookie_token
    return None


async def get_redis_dep(request: Request) -> aioredis.Redis:
    """App state'ten Redis istemcisini al."""
    return request.app.state.redis


async def get_driver_dep(request: Request) -> BaseNetworkDriver:
    """App state'ten ag surucusunu al."""
    return request.app.state.driver


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """JWT token'dan mevcut kullanıcıyi al.
    Token kaynagi: Authorization header VEYA httpOnly cookie.
    IP doğrulama: Token'daki IP ile istemci IP'si eslestirilir.
    """
    token = _extract_token(request, credentials)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kimlik doğrulama gerekli",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        user_id = int(payload.get("sub", 0))
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum süresi doldu. Lütfen tekrar giriş yapin.",
        )
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz token",
        )

    # Token blacklist kontrolü (logout sonrası geçersiz kilma)
    try:
        redis_client: aioredis.Redis = request.app.state.redis
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:32]
        is_blacklisted = await redis_client.exists(f"auth:blacklist:{token_hash}")
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Oturum sonlandirilmis. Lütfen tekrar giriş yapin.",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # Redis hatasi durumunda auth'u engellemiyoruz

    # IP doğrulama: Token'daki IP ile istemci IP'si karsilastirilir
    token_ip = payload.get("ip")
    client_ip = _get_client_ip(request)
    if token_ip and token_ip != client_ip:
        logger.warning(
            f"IP uyumsuzlugu: token_ip={token_ip}, client_ip={client_ip}, "
            f"user_id={user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum güvenlik ihlali: IP adresi degisti. Tekrar giriş yapin.",
        )

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı",
        )
    return user


async def optional_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Opsiyonel kimlik doğrulama - token varsa dogrula, yoksa None."""
    token = _extract_token(request, credentials)
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        user_id = int(payload.get("sub", 0))

        # IP doğrulama
        token_ip = payload.get("ip")
        client_ip = _get_client_ip(request)
        if token_ip and token_ip != client_ip:
            return None

        return await db.get(User, user_id)
    except Exception:
        return None
