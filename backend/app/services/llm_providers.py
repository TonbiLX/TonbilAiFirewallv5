# --- Ajan: ANALIST (THE ANALYST) ---
# Coklu LLM saglayici adaptorleri. Tum API cagilari httpx ile yapilir.
# Yeni Python bagimliligi EKLENMEZ.
# SSRF korumasi: Özel/yerel ag adreslerine istek yapilmasi engellenir.

import ipaddress
import logging
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("tonbilai.llm_providers")

# ============================================================
# Saglayici Tanimlari (Frontend dropdown için de kullanilir)
# ============================================================

PROVIDER_REGISTRY: list[dict] = [
    {
        "id": "openai",
        "name": "OpenAI (ChatGPT)",
        "models": [
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "context": 128000},
            {"id": "gpt-4o", "name": "GPT-4o", "context": 128000},
            {"id": "gpt-4.1-nano", "name": "GPT-4.1 Nano", "context": 1047576},
            {"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini", "context": 1047576},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "context": 16385},
        ],
        "requires_api_key": True,
        "requires_base_url": False,
        "default_base_url": "https://api.openai.com",
        "description": "OpenAI modelleri. GPT-4o-mini ucuz ve hizli.",
    },
    {
        "id": "anthropic",
        "name": "Anthropic (Claude)",
        "models": [
            {"id": "claude-sonnet-4-5-20250929", "name": "Claude Sonnet 4.5", "context": 200000},
            {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "context": 200000},
        ],
        "requires_api_key": True,
        "requires_base_url": False,
        "default_base_url": "https://api.anthropic.com",
        "description": "Anthropic Claude modelleri. Turkce'de cok başarılı.",
    },
    {
        "id": "google",
        "name": "Google (Gemini)",
        "models": [
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "context": 1048576},
            {"id": "gemini-2.0-flash-lite", "name": "Gemini 2.0 Flash Lite", "context": 1048576},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "context": 2097152},
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "context": 1048576},
        ],
        "requires_api_key": True,
        "requires_base_url": False,
        "default_base_url": "https://generativelanguage.googleapis.com",
        "description": "Google Gemini. Flash modelleri ucretsiz kotali.",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "models": [
            {"id": "deepseek-chat", "name": "DeepSeek Chat (V3)", "context": 64000},
            {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner (R1)", "context": 64000},
        ],
        "requires_api_key": True,
        "requires_base_url": False,
        "default_base_url": "https://api.deepseek.com",
        "description": "DeepSeek. Cok ucuz ve guclu (aylik ~$0.50).",
    },
    {
        "id": "groq",
        "name": "Groq",
        "models": [
            {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B", "context": 128000},
            {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B", "context": 128000},
            {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B", "context": 32768},
            {"id": "gemma2-9b-it", "name": "Gemma 2 9B", "context": 8192},
        ],
        "requires_api_key": True,
        "requires_base_url": False,
        "default_base_url": "https://api.groq.com/openai",
        "description": "Groq. Ucretsiz kota mevcut, cok hizli inference.",
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "models": [
            {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "context": 128000},
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "context": 200000},
            {"id": "google/gemini-2.0-flash-exp:free", "name": "Gemini 2.0 Flash (Free)", "context": 1048576},
            {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Llama 3.3 70B (Free)", "context": 128000},
            {"id": "deepseek/deepseek-chat-v3-0324:free", "name": "DeepSeek V3 (Free)", "context": 64000},
        ],
        "requires_api_key": True,
        "requires_base_url": False,
        "default_base_url": "https://openrouter.ai/api",
        "description": "OpenRouter. Tum modellere tek API ile erişim. Ucretsiz modeller mevcut.",
    },
    {
        "id": "ollama",
        "name": "Ollama (Yerel)",
        "models": [
            {"id": "llama3.2:3b", "name": "Llama 3.2 3B", "context": 128000},
            {"id": "llama3.1:8b", "name": "Llama 3.1 8B", "context": 128000},
            {"id": "qwen2.5:7b", "name": "Qwen 2.5 7B", "context": 32768},
            {"id": "gemma2:9b", "name": "Gemma 2 9B", "context": 8192},
            {"id": "phi3:mini", "name": "Phi-3 Mini", "context": 128000},
        ],
        "requires_api_key": False,
        "requires_base_url": True,
        "default_base_url": "http://localhost:11434",
        "description": "Ollama yerel model. API key gerektirmez, internet gerektirmez.",
    },
    {
        "id": "custom",
        "name": "Özel Endpoint",
        "models": [
            {"id": "custom", "name": "Özel Model", "context": 32000},
        ],
        "requires_api_key": False,
        "requires_base_url": True,
        "default_base_url": None,
        "description": "OpenAI uyumlu herhangi bir API endpoint.",
    },
]


def get_provider_info() -> list[dict]:
    """Frontend için saglayici listesini dondur."""
    return PROVIDER_REGISTRY


def _get_default_base_url(provider: str) -> str | None:
    """Saglayiçinin varsayilan base_url'ini dondur."""
    for p in PROVIDER_REGISTRY:
        if p["id"] == provider:
            return p.get("default_base_url")
    return None


# ============================================================
# OpenAI Uyumlu Cagri (OpenAI, DeepSeek, Groq, OpenRouter, Ollama, Custom)
# ============================================================

async def _call_openai_compatible(
    messages: list[dict],
    model: str,
    api_key: str | None,
    base_url: str,
    temperature: float,
    max_tokens: int,
    extra_headers: dict | None = None,
) -> str | None:
    """OpenAI /v1/chat/completions uyumlu API çağrısı."""
    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(
                    f"OpenAI-compat API hatasi ({resp.status_code}): "
                    f"{resp.text[:300]}"
                )
                return None
    except Exception as e:
        logger.error(f"OpenAI-compat API bağlantı hatasi: {e}")
        return None


# ============================================================
# Anthropic API (farkli format)
# ============================================================

async def _call_anthropic(
    messages: list[dict],
    model: str,
    api_key: str,
    base_url: str,
    temperature: float,
    max_tokens: int,
) -> str | None:
    """Anthropic /v1/messages API çağrısı."""
    url = f"{base_url.rstrip('/')}/v1/messages"

    system_msg = ""
    user_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_msg = msg["content"]
        else:
            user_messages.append(msg)

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": user_messages,
    }
    if system_msg:
        payload["system"] = system_msg

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return data["content"][0]["text"]
            else:
                logger.error(
                    f"Anthropic API hatasi ({resp.status_code}): "
                    f"{resp.text[:300]}"
                )
                return None
    except Exception as e:
        logger.error(f"Anthropic API bağlantı hatasi: {e}")
        return None


# ============================================================
# Google Gemini API (farkli format)
# ============================================================

async def _call_google(
    messages: list[dict],
    model: str,
    api_key: str,
    base_url: str,
    temperature: float,
    max_tokens: int,
) -> str | None:
    """Google Gemini generateContent API çağrısı."""
    url = (
        f"{base_url.rstrip('/')}/v1beta/models/{model}:generateContent"
        f"?key={api_key}"
    )

    contents = []
    system_instruction = None
    for msg in messages:
        if msg["role"] == "system":
            system_instruction = msg["content"]
        elif msg["role"] == "user":
            contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
        elif msg["role"] == "assistant":
            contents.append({"role": "model", "parts": [{"text": msg["content"]}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                logger.error(
                    f"Google API hatasi ({resp.status_code}): "
                    f"{resp.text[:300]}"
                )
                return None
    except Exception as e:
        logger.error(f"Google API bağlantı hatasi: {e}")
        return None


# ============================================================
# Ana Dispatcher
# ============================================================

# Ollama için izin verilen yerel host'lar (sadece bunlar)
_OLLAMA_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "0.0.0.0", "::1", "host.docker.internal"}


def _validate_llm_url(url: str, provider: str) -> bool:
    """SSRF korumasi: LLM base URL'nin yerel/özel ag adresine isaret etmedigini dogrula.
    Ollama: Sadece localhost/loopback'e izin verilir (dis sunucular engellenir).
    Diger saglayicilar: Yerel/özel ag adresleri engellenir."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False

        if provider == "ollama":
            # Ollama sadece localhost'ta çalışır - dis sunuculara izin verme
            return hostname.lower() in _OLLAMA_ALLOWED_HOSTS

        # Diger saglayicilar: yerel/özel adresleri engelle
        blocked_hosts = {
            "127.0.0.1", "localhost", "0.0.0.0", "::1",
            "169.254.169.254", "metadata.google.internal",
        }
        if hostname.lower() in blocked_hosts:
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False
        except ValueError:
            pass
        return True
    except Exception:
        return False


async def call_llm(
    provider: str,
    messages: list[dict],
    model: str,
    api_key: str | None,
    base_url: str | None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> str | None:
    """Secilen saglayiciya göre LLM API çağrısı yap."""

    resolved_url = base_url or _get_default_base_url(provider) or ""

    # SSRF korumasi: yerel/özel ag adreslerine istek engellenir
    if resolved_url and not _validate_llm_url(resolved_url, provider):
        logger.warning(f"SSRF engellendi: LLM base URL geçersiz: {resolved_url}")
        return None

    if provider == "anthropic":
        if not api_key:
            logger.error("Anthropic için API anahtarı gerekli.")
            return None
        return await _call_anthropic(
            messages, model, api_key, resolved_url, temperature, max_tokens
        )

    if provider == "google":
        if not api_key:
            logger.error("Google için API anahtarı gerekli.")
            return None
        return await _call_google(
            messages, model, api_key, resolved_url, temperature, max_tokens
        )

    # OpenAI uyumlu saglayicilar
    if provider in ("openai", "deepseek", "groq", "openrouter", "ollama", "custom"):
        extra_headers = None
        if provider == "openrouter":
            extra_headers = {
                "HTTP-Referer": "https://tonbilaios.local",
                "X-Title": "TonbilAiOS Router",
            }
        return await _call_openai_compatible(
            messages, model, api_key, resolved_url,
            temperature, max_tokens, extra_headers
        )

    logger.error(f"Bilinmeyen saglayici: {provider}")
    return None
