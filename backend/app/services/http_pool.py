# --- HTTP Connection Pool ---
# Paylasilan httpx.AsyncClient singleton modulu.
# Her servis icin ayri isimli client olusturulur, connection pool paylasimi saglanir.
# Uygulama kapatilirken close_all() cagirilmalidir.

import logging

import httpx

logger = logging.getLogger("tonbilai.http_pool")

_clients: dict[str, httpx.AsyncClient] = {}


async def get_client(name: str = "default", **kwargs) -> httpx.AsyncClient:
    """
    Isimli httpx.AsyncClient singleton dondur.
    Ayni isimle cagirildiginda mevcut client'i dondurur (connection reuse).

    kwargs:
        timeout: int (varsayilan 10)
        headers: dict (varsayilan {})
    """
    if name not in _clients or _clients[name].is_closed:
        timeout = kwargs.get("timeout", 10)
        headers = kwargs.get("headers", {})
        _clients[name] = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
            headers=headers,
        )
        logger.info(f"HTTP pool: yeni client olusturuluyor — {name} (timeout={timeout})")
    return _clients[name]


async def close_all():
    """Tum client'lari kapat ve pool'u temizle."""
    for name, client in _clients.items():
        if not client.is_closed:
            await client.aclose()
            logger.debug(f"HTTP pool: client kapatildi — {name}")
    _clients.clear()
    logger.info("HTTP pool: tum client'lar kapatildi")
