# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Kullanıcı modeli: bcrypt şifre hash ile güvenli kimlik doğrulama.
# SHA-256 geriye donuk uyumluluk: eski hashler giriş sırasında otomatik bcrypt'e yukseltilir.

import hashlib
from datetime import datetime

import bcrypt
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hash (60 karakter)
    display_name = Column(String(100), nullable=True)
    is_admin = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    @staticmethod
    def hash_password(password: str) -> str:
        """Şifreyi bcrypt ile hashle (tuzlu, yavas hash)."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def _is_sha256_hash(hash_value: str) -> bool:
        """Hash'in eski SHA-256 formati olup olmadigini kontrol et."""
        return len(hash_value) == 64 and all(c in "0123456789abcdef" for c in hash_value)

    def verify_password(self, password: str) -> bool:
        """Verilen şifreyi kontrol et. SHA-256 geriye donuk uyumluluk desteği."""
        if self._is_sha256_hash(self.password_hash):
            # Eski SHA-256 hash - karsilastir
            sha256_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
            if sha256_hash == self.password_hash:
                # Başarılı: eski hash'i bcrypt'e yukselt
                self.password_hash = self.hash_password(password)
                return True
            return False
        # Yeni bcrypt hash
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                self.password_hash.encode("utf-8"),
            )
        except (ValueError, TypeError):
            return False
