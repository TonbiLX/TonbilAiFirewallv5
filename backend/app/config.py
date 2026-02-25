# --- Ajan: MUHAFIZ (THE GUARDIAN) + MIMAR (THE ARCHITECT) ---
# Sistem konfigurasyonu: Pydantic BaseSettings ile tip-güvenli ortam degiskeni yükleme.
# Güvenlik: Uretimde zayif SECRET_KEY kullanımini engeller.

import secrets
import logging
from pydantic_settings import BaseSettings
from functools import lru_cache

_config_logger = logging.getLogger("tonbilai.config")

# Bilinen zayif/varsayilan secret key'ler
_WEAK_SECRET_KEYS = {
    "change-me", "change-me-to-a-random-string", "secret", "password",
    "admin", "test", "dev", "development", "1234", "12345678",
}


class Settings(BaseSettings):
    # Veritabani
    DATABASE_URL: str

    # Redis (Docker: redis://redis:6379/0, Native: redis://localhost:6379/0)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Uygulama
    ENVIRONMENT: str = "development"  # "development" | "production"
    SECRET_KEY: str = "change-me"
    CORS_ORIGINS: str = "http://localhost:5173"

    # Guvenilir reverse proxy IP'leri (sadece bunlardan gelen X-Forwarded-For'a guven)
    TRUSTED_PROXIES: str = "172.16.0.0/12,10.0.0.0/8,192.168.0.0/16,127.0.0.1"

    # Senkronizasyon iscisi
    SYNC_INTERVAL_SECONDS: int = 60

    # Mock trafik ureteci
    MOCK_TRAFFIC_INTERVAL_SECONDS: float = 5.0
    MOCK_DEVICE_COUNT: int = 8

    # DNS Engelleme (Faz 2)
    DNS_BLOCKLIST_UPDATE_HOURS: int = 6

    # DHCP Simulatoru (Faz 2)
    DHCP_SIMULATOR_INTERVAL_SECONDS: float = 30.0

    # 5651 Kanun Uyumu: Log saklama ve imzalama
    LOG_RETENTION_DAYS: int = 730           # 2 yil (minimum yasal gereksinim)
    LOG_ARCHIVE_PATH: str = "/opt/tonbilaios/backend/logs/signed"
    LOG_SIGNING_ENABLED: bool = True

    # Flow Tracker (Per-flow baglanti takibi)
    FLOW_TRACK_INTERVAL_SECONDS: int = 20
    FLOW_DB_SYNC_INTERVAL_SECONDS: int = 60
    FLOW_RETENTION_DAYS: int = 7

    @property
    def is_dev(self) -> bool:
        return self.ENVIRONMENT == "development"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    s = Settings()
    # Uretim ortaminda zayif SECRET_KEY kullanımi engellenir
    if s.ENVIRONMENT == "production" and (
        s.SECRET_KEY.lower() in _WEAK_SECRET_KEYS or len(s.SECRET_KEY) < 32
    ):
        raise RuntimeError(
            "GÜVENLİK HATASI: Üretim ortamında zayıf SECRET_KEY kullanımı yasaktır. "
            f"En az 32 karakter uzunlugunda kriptografik rastgele bir anahtar kullanın. "
            f"Ornek: SECRET_KEY={secrets.token_urlsafe(48)}"
        )
    # Gelistirme ortaminda varsayilan key uyarısı
    if s.SECRET_KEY.lower() in _WEAK_SECRET_KEYS:
        _config_logger.warning(
            "GÜVENLİK UYARISI: Varsayılan SECRET_KEY kullanılıyor! "
            "Üretim ortamına geçmeden önce değiştirin."
        )
    return s
