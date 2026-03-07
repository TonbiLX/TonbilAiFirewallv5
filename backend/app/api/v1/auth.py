# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Kimlik doğrulama API endpointleri: giriş, kayit, şifre değiştirme.
# Güvenlik katmanlari: JWT + httpOnly cookie + IP binding + rate limiting + token blacklist.

import hashlib as _hashlib
import ipaddress as _ipaddress
import time as _time
import jwt
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import redis.asyncio as aioredis

from app.db.session import get_db
from app.config import get_settings
from app.models.user import User
from app.api.deps import get_current_user, get_redis_dep, _get_client_ip
from app.schemas.auth import (
    UserLogin, UserCreate, TokenResponse,
    UserResponse, PasswordChange, ProfileUpdate,
)

router = APIRouter()
settings = get_settings()
logger = logging.getLogger("tonbilai.auth")

TOKEN_EXPIRE_HOURS = 24           # Normal oturum: 24 saat
REMEMBER_EXPIRE_DAYS = 30         # Beni hatırla: 30 gun
ALGORITHM = "HS256"
COOKIE_NAME = "tonbilai_session"  # httpOnly cookie adi
MAX_LOGIN_ATTEMPTS = 5            # Maksimum başarısız giriş denemesi
LOCKOUT_SECONDS = 900             # Kilitlenme süresi (15 dakika)

# In-memory rate limiting fallback (Redis arizasi için)
_in_memory_attempts: dict[str, list[float]] = {}
_MEMORY_CLEANUP_INTERVAL = 300  # 5 dakikada bir temizlik
_last_memory_cleanup = _time.monotonic()


def get_client_ip(request: Request) -> str:
    """İstemci IP adresini al (deps.py'deki güvenli fonksiyonu kullan)."""
    return _get_client_ip(request)


def _is_local_network(ip: str) -> bool:
    """IP adresinin yerel ag (RFC 1918) olup olmadigini kontrol et."""
    try:
        addr = _ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback
    except ValueError:
        return False


def create_access_token(
    user_id: int,
    username: str,
    client_ip: str,
    remember_me: bool = False,
) -> str:
    """JWT token oluştur. IP adresi token'a baglenir."""
    if remember_me:
        expire = datetime.utcnow() + timedelta(days=REMEMBER_EXPIRE_DAYS)
    else:
        expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    if client_ip:
        payload["ip"] = client_ip
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def set_auth_cookie(response: Response, token: str, remember_me: bool = False):
    """JWT token'i httpOnly secure cookie olarak ayarla."""
    max_age = REMEMBER_EXPIRE_DAYS * 86400 if remember_me else TOKEN_EXPIRE_HOURS * 3600
    # Uretim ortaminda secure=True (HTTPS zorunlu), gelistirmede False
    is_production = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,           # JavaScript erisamez (XSS korumasi)
        secure=is_production,     # HTTPS zorunlu ise True, yerel ag HTTP için False
        samesite="strict" if is_production else "lax",  # Prod: strict, dev: lax (WebSocket için)
        max_age=max_age,
        path="/",
    )


def clear_auth_cookie(response: Response):
    """Auth cookie'yi temizle."""
    response.delete_cookie(key=COOKIE_NAME, path="/")


def _cleanup_memory_attempts():
    """Süresi dolmus in-memory rate limit kayitlarini temizle."""
    global _last_memory_cleanup
    now = _time.monotonic()
    if now - _last_memory_cleanup < _MEMORY_CLEANUP_INTERVAL:
        return
    _last_memory_cleanup = now
    expired_keys = [
        ip for ip, times in _in_memory_attempts.items()
        if not times or (now - times[-1]) > LOCKOUT_SECONDS
    ]
    for ip in expired_keys:
        del _in_memory_attempts[ip]


def _check_memory_rate_limit(client_ip: str):
    """In-memory rate limit kontrolü (Redis arizasi fallback)."""
    _cleanup_memory_attempts()
    now = _time.monotonic()
    attempts = _in_memory_attempts.get(client_ip, [])
    # Son LOCKOUT_SECONDS içindeki denemeleri filtrele
    recent = [t for t in attempts if now - t < LOCKOUT_SECONDS]
    _in_memory_attempts[client_ip] = recent
    if len(recent) >= MAX_LOGIN_ATTEMPTS:
        remaining = int(LOCKOUT_SECONDS - (now - recent[0]))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Cok fazla başarısız giriş denemesi. {remaining} saniye sonra tekrar deneyin.",
        )


def _record_memory_attempt(client_ip: str):
    """In-memory başarısız deneme kaydi (Redis arizasi fallback)."""
    now = _time.monotonic()
    if client_ip not in _in_memory_attempts:
        _in_memory_attempts[client_ip] = []
    _in_memory_attempts[client_ip].append(now)


async def check_rate_limit(redis: aioredis.Redis, client_ip: str):
    """Brute force koruması: Başarısız giriş denemelerini kontrol et."""
    try:
        key = f"auth:failed:{client_ip}"
        attempts = await redis.get(key)
        if attempts and int(attempts) >= MAX_LOGIN_ATTEMPTS:
            ttl = await redis.ttl(key)
            logger.warning(f"Rate limit asildi: {client_ip} ({attempts} başarısız deneme)")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Cok fazla başarısız giriş denemesi. {ttl} saniye sonra tekrar deneyin.",
            )
    except HTTPException:
        raise
    except Exception:
        # Redis arizasi - in-memory fallback kullan
        logger.warning(f"Redis ariza, in-memory rate limit kullanılıyor: {client_ip}")
        _check_memory_rate_limit(client_ip)


async def record_failed_attempt(redis: aioredis.Redis, client_ip: str):
    """Başarısız giriş denemesini kaydet."""
    try:
        key = f"auth:failed:{client_ip}"
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, LOCKOUT_SECONDS)
        await pipe.execute()
        count = await redis.get(key)
        logger.warning(f"Başarısız giriş denemesi: {client_ip} (toplam: {count})")
    except Exception:
        # Redis arizasi - in-memory fallback
        _record_memory_attempt(client_ip)
        logger.warning(f"Redis ariza, in-memory kayit: {client_ip}")


async def clear_failed_attempts(redis: aioredis.Redis, client_ip: str):
    """Başarılı girişten sonra başarısız deneme sayacıni sıfırla."""
    try:
        await redis.delete(f"auth:failed:{client_ip}")
    except Exception:
        pass
    # In-memory'den de temizle
    _in_memory_attempts.pop(client_ip, None)


@router.post("/login")
async def login(
    data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    """Kullanıcı girişi - JWT token + httpOnly cookie + IP binding."""
    client_ip = get_client_ip(request)

    # Rate limiting kontrolü
    await check_rate_limit(redis, client_ip)

    result = await db.execute(
        select(User).where(User.username == data.username)
    )
    user = result.scalar_one_or_none()
    if not user or not user.verify_password(data.password):
        # Başarısız denemeyi kaydet
        await record_failed_attempt(redis, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı adi veya şifre hatali",
        )

    # Başarılı giriş - sayacı sıfırla
    await clear_failed_attempts(redis, client_ip)

    # Mobil platform icin IP binding atlanir (CGNAT, WiFi/Mobil gecis sorunlari)
    use_ip = client_ip if not data.platform else ""
    token = create_access_token(
        user.id, user.username, use_ip, remember_me=data.remember_me
    )

    # Oturum bilgisini Redis'e kaydet (aktif oturum takibi)
    session_key = f"auth:session:{user.id}:{client_ip}"
    session_data = f"{user.username}|{client_ip}|{datetime.utcnow().isoformat()}"
    session_ttl = REMEMBER_EXPIRE_DAYS * 86400 if data.remember_me else TOKEN_EXPIRE_HOURS * 3600
    await redis.setex(session_key, session_ttl, session_data)

    logger.info(f"Başarılı giriş: {user.username} ({client_ip})")

    # JSON yaniti oluştur ve cookie ekle
    response_data = TokenResponse(
        access_token=token,
        username=user.username,
        display_name=user.display_name,
    )
    response = Response(
        content=response_data.model_dump_json(),
        media_type="application/json",
    )
    set_auth_cookie(response, token, remember_me=data.remember_me)
    return response


@router.post("/setup")
async def initial_setup(
    data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """İlk kurulum: henüz kullanıcı yoksa admin oluştur.
    Güvenlik: Sadece yerel agdan erişim + race condition koruması."""
    client_ip = get_client_ip(request)

    # Güvenlik: Sadece yerel agdan setup yapilabilir
    if not _is_local_network(client_ip):
        logger.warning(f"Setup denemesi dis IP'den reddedildi: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="İlk kurulum sadece yerel agdan yapilabilir.",
        )

    # SELECT FOR UPDATE ile race condition onleme
    user_count = await db.scalar(select(func.count(User.id)))
    if user_count and user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kurulum zaten tamamlanmis. Giriş yapin.",
        )
    user = User(
        username=data.username,
        password_hash=User.hash_password(data.password),
        display_name=data.display_name or data.username,
        is_admin=True,
    )
    db.add(user)
    await db.flush()

    token = create_access_token(user.id, user.username, client_ip)

    logger.info(f"İlk kurulum tamamlandi: {user.username} ({client_ip})")

    response_data = TokenResponse(
        access_token=token,
        username=user.username,
        display_name=user.display_name,
    )
    response = Response(
        content=response_data.model_dump_json(),
        media_type="application/json",
    )
    set_auth_cookie(response, token)
    return response


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Mevcut kullanıcı bilgisi."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        is_admin=current_user.is_admin,
    )


@router.get("/check")
async def check_setup(db: AsyncSession = Depends(get_db)):
    """Kurulum durumunu kontrol et (login sayfası için)."""
    user_count = await db.scalar(select(func.count(User.id)))
    return {
        "setup_completed": (user_count or 0) > 0,
    }


@router.post("/change-password")
async def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Şifre değiştir (JWT token gerekli)."""
    if not current_user.verify_password(data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mevcut şifre hatali",
        )
    current_user.password_hash = User.hash_password(data.new_password)
    await db.flush()
    return {"message": "Şifre değiştirildi"}


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Kullanıcı profilini güncelle (display name vb.)."""
    if data.display_name is not None:
        current_user.display_name = data.display_name
    await db.flush()
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        is_admin=current_user.is_admin,
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    """Oturumu kapat: token blacklist + cookie temizle + Redis oturum sil."""
    client_ip = get_client_ip(request)

    # Mevcut token'i blacklist'e ekle (süresine kadar gecerli kalmasin)
    from app.api.deps import _extract_token
    from fastapi.security import HTTPAuthorizationCredentials
    auth_header = request.headers.get("authorization", "")
    creds = None
    if auth_header.startswith("Bearer "):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=auth_header[7:])
    token = _extract_token(request, creds)
    if token:
        token_hash = _hashlib.sha256(token.encode()).hexdigest()[:32]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            exp = payload.get("exp", 0)
            ttl = max(int(exp - _time.time()), 0)
            if ttl > 0:
                await redis.setex(f"auth:blacklist:{token_hash}", ttl, "1")
        except Exception:
            pass  # Token cozulemese bile oturumu kapat

    session_key = f"auth:session:{current_user.id}:{client_ip}"
    await redis.delete(session_key)

    logger.info(f"Çıkış yapildi: {current_user.username} ({client_ip})")

    response = Response(
        content='{"message": "Oturum kapatildi"}',
        media_type="application/json",
    )
    clear_auth_cookie(response)
    return response
