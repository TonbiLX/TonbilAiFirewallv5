# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# TLS/Şifreleme API: DoT, sertifika yapıştırma/yükleme, doğrulama,
# Let's Encrypt otomatik sertifika alma.
# Güvenlik: Domain/email doğrulama, dosya upload boyut limiti.

import os
import re
import ssl
import asyncio
import logging
import tempfile
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.api.deps import get_current_user
from app.models.user import User

# Maksimum sertifika dosya boyutu: 1MB
MAX_CERT_FILE_SIZE = 1 * 1024 * 1024

# Domain doğrulama regex (basit, güvenli)
_DOMAIN_RE = re.compile(r"^([a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$")
# Email doğrulama regex (basit)
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.tls_config import TlsConfig
from app.schemas.tls_config import (
    TlsConfigUpdate, TlsConfigResponse,
    TlsValidateRequest, TlsValidateResponse,
)

router = APIRouter()
logger = logging.getLogger("tonbilai.tls")

CERT_DIR = "/opt/tonbilaios/backend/certs"


def _parse_cert_info(cert_pem: str, key_pem: str, domain: str = None) -> dict:
    """PEM sertifika ve anahtari dogrulayip bilgilerini cikar."""
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend

    result = {
        "valid": False,
        "subject": None,
        "issuer": None,
        "not_before": None,
        "not_after": None,
        "domain_match": None,
        "error": None,
    }

    try:
        # Sertifikayi parse et
        cert = x509.load_pem_x509_certificate(
            cert_pem.encode(), default_backend()
        )
        result["subject"] = cert.subject.rfc4514_string()
        result["issuer"] = cert.issuer.rfc4514_string()
        result["not_before"] = cert.not_valid_before_utc
        result["not_after"] = cert.not_valid_after_utc

        # Özel anahtari dogrula
        private_key = serialization.load_pem_private_key(
            key_pem.encode(), password=None, backend=default_backend()
        )

        # Sertifika süresi kontrolü
        now = datetime.utcnow()
        if cert.not_valid_after_utc.replace(tzinfo=None) < now:
            result["error"] = "Sertifika süresi dolmus"
            return result

        # Domain eslesmesi kontrolü
        if domain:
            try:
                san = cert.extensions.get_extension_for_class(
                    x509.SubjectAlternativeName
                )
                dns_names = san.value.get_values_for_type(x509.DNSName)
                result["domain_match"] = domain in dns_names
            except x509.ExtensionNotFound:
                # SAN yoksa CN'ye bak
                cn = cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
                if cn:
                    result["domain_match"] = cn[0].value == domain

        # Sertifika-anahtar eslesme kontrolü (SSL context ile)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".pem", delete=False
        ) as cf:
            cf.write(cert_pem)
            cert_tmp = cf.name
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".pem", delete=False
        ) as kf:
            kf.write(key_pem)
            key_tmp = kf.name

        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(cert_tmp, key_tmp)
            result["valid"] = True
        except ssl.SSLError as e:
            result["error"] = f"Sertifika-anahtar eslesmesi başarısız: {e}"
        finally:
            os.unlink(cert_tmp)
            os.unlink(key_tmp)

    except Exception as e:
        result["error"] = str(e)

    return result


def _save_cert_files(cert_pem: str, key_pem: str):
    """Sertifika ve anahtari dosya olarak kaydet."""
    os.makedirs(CERT_DIR, exist_ok=True)
    with open(os.path.join(CERT_DIR, "fullchain.pem"), "w") as f:
        f.write(cert_pem)
    with open(os.path.join(CERT_DIR, "privkey.pem"), "w") as f:
        f.write(key_pem)
    logger.info(f"TLS sertifikalari {CERT_DIR} dizinine kaydedildi.")


async def _reload_dot_if_running():
    """Sertifika degistikten sonra DoT sunucusunu yeniden başlat."""
    try:
        from app.workers.dns_proxy import reload_dot_server
        result = await reload_dot_server()
        if result:
            logger.info("DoT sunucusu yeni sertifikayla yeniden başlatildi.")
        else:
            logger.warning("DoT sunucusu yeniden başlatilamadi.")
    except Exception as e:
        logger.error(f"DoT reload hatasi: {e}")


@router.get("/config", response_model=TlsConfigResponse)
async def get_tls_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """TLS yapılandirmasini getir."""
    result = await db.execute(select(TlsConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        config = TlsConfig()
        db.add(config)
        await db.flush()
        await db.refresh(config)
    return config


@router.patch("/config", response_model=TlsConfigResponse)
async def update_tls_config(
    data: TlsConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """TLS yapılandirmasini güncelle. Sertifika yapıştırildiysa dogrula ve kaydet."""
    result = await db.execute(select(TlsConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        config = TlsConfig()
        db.add(config)
        await db.flush()

    updates = data.model_dump(exclude_unset=True)

    # Sertifika ve anahtar birlikte geliyorsa dogrula
    cert_chain = updates.get("certificate_chain", config.certificate_chain)
    priv_key = updates.get("private_key", config.private_key)
    domain = updates.get("domain", config.domain)

    cert_updated = False
    if cert_chain and priv_key and (
        "certificate_chain" in updates or "private_key" in updates
    ):
        info = _parse_cert_info(cert_chain, priv_key, domain)
        if info["valid"]:
            config.cert_valid = True
            config.cert_subject = info["subject"]
            config.cert_issuer = info["issuer"]
            config.cert_not_before = info["not_before"]
            config.cert_not_after = info["not_after"]
            # Dosyalara kaydet (DoT sunucusu için)
            _save_cert_files(cert_chain, priv_key)
            config.cert_path = os.path.join(CERT_DIR, "fullchain.pem")
            config.key_path = os.path.join(CERT_DIR, "privkey.pem")
            cert_updated = True
        else:
            config.cert_valid = False
            config.cert_subject = info.get("subject")
            config.cert_issuer = info.get("issuer")

    for key, value in updates.items():
        setattr(config, key, value)

    await db.flush()
    await db.refresh(config)

    # Sertifika degistiyse DoT sunucusunu yeniden başlat
    if cert_updated:
        await _reload_dot_if_running()

    return config


@router.post("/validate", response_model=TlsValidateResponse)
async def validate_certificate(
    data: TlsValidateRequest,
    current_user: User = Depends(get_current_user),
):
    """Sertifika ve anahtari dogrula. Gecerlilik, sure, domain eslesmesi kontrol eder."""
    info = _parse_cert_info(data.certificate_chain, data.private_key, data.domain)
    return TlsValidateResponse(**info)


@router.post("/upload-cert")
async def upload_certificate(
    cert_file: UploadFile = File(..., description="PEM sertifika zinciri"),
    key_file: UploadFile = File(..., description="PEM özel anahtar"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sertifika ve anahtar dosyalarini yukle."""
    # Dosya boyut kontrolü
    cert_bytes = await cert_file.read()
    if len(cert_bytes) > MAX_CERT_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Sertifika dosyasi cok buyuk (maks 1MB)")
    key_bytes = await key_file.read()
    if len(key_bytes) > MAX_CERT_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Anahtar dosyasi cok buyuk (maks 1MB)")
    try:
        cert_content = cert_bytes.decode("utf-8")
        key_content = key_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Geçersiz dosya kodlamasi (UTF-8 bekleniyor)")

    result = await db.execute(select(TlsConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        config = TlsConfig()
        db.add(config)
        await db.flush()

    info = _parse_cert_info(cert_content, key_content, config.domain)
    if not info["valid"]:
        logger.warning(f"Geçersiz sertifika yükleme denemesi: {info.get('error', 'bilinmeyen hata')}")
        raise HTTPException(
            status_code=400,
            detail="Geçersiz sertifika veya anahtar. Lütfen PEM formatinda gecerli dosyalar yükleyin.",
        )

    config.certificate_chain = cert_content
    config.private_key = key_content
    config.cert_valid = True
    config.cert_subject = info["subject"]
    config.cert_issuer = info["issuer"]
    config.cert_not_before = info["not_before"]
    config.cert_not_after = info["not_after"]

    _save_cert_files(cert_content, key_content)
    config.cert_path = os.path.join(CERT_DIR, "fullchain.pem")
    config.key_path = os.path.join(CERT_DIR, "privkey.pem")

    await db.flush()
    await db.refresh(config)

    # DoT sunucusunu yeni sertifikayla yeniden başlat
    await _reload_dot_if_running()

    return {
        "status": "success",
        "subject": info["subject"],
        "issuer": info["issuer"],
        "not_after": str(info["not_after"]),
        "message": "Sertifika ve anahtar başarıyla yuklendi.",
    }


@router.post("/letsencrypt")
async def request_letsencrypt(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Let's Encrypt sertifikasi talep et (certbot/acme ile)."""
    result = await db.execute(select(TlsConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config or not config.domain:
        raise HTTPException(status_code=400, detail="Once bir domain adi tanimlayin")
    if not config.lets_encrypt_email:
        raise HTTPException(status_code=400, detail="Let's Encrypt için email adresi gerekli")

    domain = config.domain
    email = config.lets_encrypt_email

    # Domain ve email format doğrulamasi (komut enjeksiyonu onleme)
    if not _DOMAIN_RE.match(domain):
        raise HTTPException(status_code=400, detail="Geçersiz domain formati")
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Geçersiz email formati")

    # certbot ile sertifika al (standalone mode - port 80 kullanir)
    try:
        loop = asyncio.get_event_loop()
        proc = await asyncio.create_subprocess_exec(
            "certbot", "certonly",
            "--standalone",
            "--non-interactive",
            "--agree-tos",
            "--email", email,
            "-d", domain,
            "--cert-path", os.path.join(CERT_DIR, "fullchain.pem"),
            "--key-path", os.path.join(CERT_DIR, "privkey.pem"),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            # certbot yoksa veya başarısızsa, acme.sh dene
            logger.warning(f"certbot başarısız: {stderr.decode()}")

            # Alternatif: openssl ile self-signed (fallback)
            proc2 = await asyncio.create_subprocess_exec(
                "openssl", "req", "-x509", "-newkey", "ec",
                "-pkeyopt", "ec_paramgen_curve:P-384",
                "-keyout", os.path.join(CERT_DIR, "privkey.pem"),
                "-out", os.path.join(CERT_DIR, "fullchain.pem"),
                "-days", "90", "-nodes",
                "-subj", f"/CN={domain}",
                "-addext", f"subjectAltName=DNS:{domain}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout2, stderr2 = await proc2.communicate()

            if proc2.returncode != 0:
                logger.error(f"Self-signed sertifika oluşturulamadi: {stderr2.decode()}")
                raise HTTPException(
                    status_code=500,
                    detail="Sertifika oluşturulamadi. Sistem loglarını kontrol edin.",
                )

            # Self-signed oluşturuldu
            with open(os.path.join(CERT_DIR, "fullchain.pem")) as f:
                cert_content = f.read()
            with open(os.path.join(CERT_DIR, "privkey.pem")) as f:
                key_content = f.read()

            config.certificate_chain = cert_content
            config.private_key = key_content
            config.cert_path = os.path.join(CERT_DIR, "fullchain.pem")
            config.key_path = os.path.join(CERT_DIR, "privkey.pem")
            config.lets_encrypt_enabled = False  # Self-signed
            config.enabled = True
            config.cert_valid = True

            info = _parse_cert_info(cert_content, key_content, domain)
            config.cert_subject = info.get("subject")
            config.cert_issuer = info.get("issuer")
            config.cert_not_before = info.get("not_before")
            config.cert_not_after = info.get("not_after")

            await db.flush()
            return {
                "status": "self_signed",
                "domain": domain,
                "message": f"certbot bulunamadı. {domain} için self-signed sertifika oluşturuldu (90 gun gecerli).",
            }

        # certbot başarılı - dosyalari oku
        le_cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
        le_key_path = f"/etc/letsencrypt/live/{domain}/privkey.pem"

        with open(le_cert_path) as f:
            cert_content = f.read()
        with open(le_key_path) as f:
            key_content = f.read()

        # Certs dizinine kopyala
        _save_cert_files(cert_content, key_content)

        config.certificate_chain = cert_content
        config.private_key = key_content
        config.cert_path = os.path.join(CERT_DIR, "fullchain.pem")
        config.key_path = os.path.join(CERT_DIR, "privkey.pem")
        config.lets_encrypt_enabled = True
        config.enabled = True
        config.cert_valid = True

        info = _parse_cert_info(cert_content, key_content, domain)
        config.cert_subject = info.get("subject")
        config.cert_issuer = info.get("issuer")
        config.cert_not_before = info.get("not_before")
        config.cert_not_after = info.get("not_after")

        await db.flush()
        return {
            "status": "success",
            "domain": domain,
            "cert_path": config.cert_path,
            "message": f"Let's Encrypt sertifikasi {domain} için başarıyla alindi.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Let's Encrypt hatasi: {e}")
        raise HTTPException(status_code=500, detail="Sertifika işlemi sırasında bir hata oluştu")


@router.post("/toggle")
async def toggle_encryption(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Şifrelemeyi etkinlestir/devre disi birak."""
    result = await db.execute(select(TlsConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        config = TlsConfig()
        db.add(config)
        await db.flush()

    # DoT etkinlestirmek için gecerli sertifika gerekli
    if not config.enabled and not config.cert_valid:
        raise HTTPException(
            status_code=400,
            detail="DoT etkinlestirmek için gecerli bir sertifika yükleyin.",
        )

    config.enabled = not config.enabled
    if config.enabled:
        config.dot_enabled = True
    else:
        config.dot_enabled = False

    await db.flush()

    # DoT etkinleştirildiğinde sunucuyu başlat/yeniden başlat
    if config.enabled:
        await _reload_dot_if_running()

    return {
        "enabled": config.enabled,
        "dot_enabled": config.dot_enabled,
        "message": (
            "DNS-over-TLS etkinlestirildi. Port 853 aktif."
            if config.enabled
            else "DNS-over-TLS devre disi birakildi."
        ),
    }
