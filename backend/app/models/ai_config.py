# --- Ajan: ANALIST (THE ANALYST) ---
# Yapay Zeka yapılandirma modeli: tek satirlik config tablosu.
# Birden fazla LLM saglayicisi destekler (OpenAI, Anthropic, Google, DeepSeek, Groq, vb.)

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text
from app.db.base import Base


class AiConfig(Base):
    """Yapay Zeka LLM yapılandirmasi."""
    __tablename__ = "ai_config"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Saglayici secimi: none, openai, anthropic, google, deepseek, groq, openrouter, ollama, custom
    provider = Column(String(50), nullable=False, default="none")

    # API kimlik bilgileri
    api_key = Column(String(500), nullable=True)
    base_url = Column(String(500), nullable=True)  # Ollama/Custom için

    # Model secimi
    model = Column(String(100), nullable=True)

    # Sohbet yonlendirme modu: tfidf, llm, hybrid
    chat_mode = Column(String(20), nullable=False, default="tfidf")

    # LLM parametreleri
    temperature = Column(Float, default=0.3)
    max_tokens = Column(Integer, default=1024)

    # Log analizi
    log_analysis_enabled = Column(Boolean, default=False)
    log_analysis_interval_minutes = Column(Integer, default=60)
    log_analysis_max_logs = Column(Integer, default=100)

    # Maliyet kontrolü
    daily_request_limit = Column(Integer, default=200)
    daily_request_count = Column(Integer, default=0)
    daily_reset_date = Column(String(10), nullable=True)  # "2026-02-16"

    # Özel sistem promptu
    custom_system_prompt = Column(Text, nullable=True)

    # Durum
    enabled = Column(Boolean, default=False)
    last_test_result = Column(String(500), nullable=True)
    last_test_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
