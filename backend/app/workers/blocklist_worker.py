# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Blocklist iscisi: periyodik olarak blocklist kaynaklarini indirir, ayristir ve
# engellenen domain setini Redis'e yukler.
# SSRF korumasi: Özel/yerel IP adreslerine HTTP istegi yapilmasi engellenir.
# AdGuardHome referans alinan özellikler:
#   - Checksum ile değişiklik tespiti
#   - Otomatik format algilama (hosts, adblock, domain, IP)
#   - Güncelleme istatistikleri (onceki/sonraki domain sayısı, eklenen/cikarilan)

import asyncio
import hashlib
import ipaddress
import logging
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.blocklist import Blocklist
from app.models.dns_rule import DnsRule, DnsRuleType
from app.hal.base_driver import BaseNetworkDriver
from app.config import get_settings

logger = logging.getLogger("tonbilai.blocklist_worker")
settings = get_settings()

# ===== YEREL DOMAIN CACHE =====
# Indirilen domainler yerel dosyada saklanır, boylece rebuild işleminde
# tekrar internetten indirme yapmaya gerek kalmaz.
CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "blocklist_cache"


def _ensure_cache_dir():
    """Cache dizinini oluştur."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def save_domains_to_cache(blocklist_id: int, domains: set) -> None:
    """Parse edilmis domainleri yerel dosyaya kaydet."""
    _ensure_cache_dir()
    cache_file = CACHE_DIR / f"{blocklist_id}.txt"
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(domains)))
        logger.debug(f"Cache kaydedildi: blocklist {blocklist_id} ({len(domains)} domain)")
    except Exception as e:
        logger.warning(f"Cache yazma hatasi (blocklist {blocklist_id}): {e}")


def load_domains_from_cache(blocklist_id: int) -> set | None:
    """Cache dosyasindan domainleri oku. Dosya yoksa None dondur."""
    cache_file = CACHE_DIR / f"{blocklist_id}.txt"
    if not cache_file.exists():
        return None
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            domains = {line.strip() for line in f if line.strip()}
        return domains
    except Exception as e:
        logger.warning(f"Cache okuma hatasi (blocklist {blocklist_id}): {e}")
        return None


def delete_domain_cache(blocklist_id: int) -> None:
    """Blocklist cache dosyasini sil."""
    cache_file = CACHE_DIR / f"{blocklist_id}.txt"
    try:
        cache_file.unlink(missing_ok=True)
    except Exception:
        pass

# Domain doğrulama regex'i
_DOMAIN_RE = re.compile(
    r'^(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(\.[a-zA-Z0-9-]{1,63})*\.[a-zA-Z]{2,}$'
)

# IP adresi doğrulama (basit kontrol)
_IPV4_RE = re.compile(
    r'^(\d{1,3}\.){3}\d{1,3}$'
)


def _is_valid_domain(domain: str) -> bool:
    """Domain adinin gecerli olup olmadigini kontrol et."""
    if not domain or len(domain) > 253:
        return False
    return bool(_DOMAIN_RE.match(domain))


def _is_valid_ip(ip_str: str) -> bool:
    """IP adresinin gecerli olup olmadigini kontrol et."""
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False


def _strip_inline_comment(line: str) -> str:
    """Satır ici yorumu kaldir (# isareti sonrası)."""
    idx = line.find('#')
    if idx >= 0:
        return line[:idx].strip()
    return line.strip()


# ===== FORMAT PARSER'LAR =====

def parse_hosts_format(content: str) -> set:
    """Hosts dosya formatini ayristir.
    Desteklenen formatlar:
      - 0.0.0.0 domain.com
      - 127.0.0.1 domain.com
      - ::1 domain.com
      - 0.0.0.0 domain.com # yorum
      - Tab veya bosluk ayirici
    """
    domains = set()
    host_prefixes = {"0.0.0.0", "127.0.0.1", "::1", "::"}

    for line in content.split("\n"):
        line = _strip_inline_comment(line)
        if not line:
            continue

        # Tab veya bosluk ile ayir
        parts = line.split()
        if len(parts) < 2:
            continue

        prefix = parts[0]
        if prefix not in host_prefixes:
            continue

        # Ilk domain'i al (bazi listeler birden fazla domain satirda yer alir)
        for i in range(1, len(parts)):
            domain = parts[i].lower().strip(".")
            if domain and domain != "localhost" and domain != "local" \
               and domain != "broadcasthost" and "." in domain:
                if _is_valid_domain(domain):
                    domains.add(domain)

    return domains


def parse_domain_list_format(content: str) -> set:
    """Bir satira bir domain formatini ayristir.
    Ayrica URL satirlarindan domain cikarir ve IP adreslerini de toplar.
    """
    domains = set()

    for line in content.split("\n"):
        line = _strip_inline_comment(line)
        if not line or line.startswith("!") or line.startswith("["):
            continue

        # URL ise domain cikar
        if line.startswith("http://") or line.startswith("https://"):
            try:
                parsed = urlparse(line)
                if parsed.hostname:
                    hostname = parsed.hostname.lower()
                    if _is_valid_domain(hostname):
                        domains.add(hostname)
            except Exception:
                pass
            continue

        # Ilk kelimeyi al (bazi satirlarda bosluktan sonra yorum olabilir)
        token = line.split()[0].lower().strip(".")

        # IP adresi ise ekle
        if _is_valid_ip(token):
            domains.add(token)
            continue

        # Domain ise ekle
        if token and "." in token and _is_valid_domain(token):
            domains.add(token)

    return domains


def parse_adblock_format(content: str) -> set:
    """AdBlock filtre formatini ayristir.
    Desteklenen formatlar:
      - ||domain.com^
      - ||domain.com^$third-party
      - ||domain.com^$important
      - ||*.domain.com^ (wildcard - ana domain alinir)
    Atlanan satirlar:
      - @@||domain.com^ (whitelist/istisna kuralı)
      - ! yorum satiri
      - [Adblock Plus ...] header
      - # ile baslayan satirlar
      - Regex patterler (/ ile baslayan)
    """
    domains = set()

    for line in content.split("\n"):
        line = line.strip()

        # Bos satir, yorum, header atla
        if not line or line.startswith("!") or line.startswith("#") \
           or line.startswith("[") or line.startswith("/"):
            continue

        # Whitelist (istisna) kurallarini atla
        if line.startswith("@@"):
            continue

        # ||domain^ formatini isle
        if line.startswith("||"):
            # || sonrasıni al
            rest = line[2:]

            # ^ isareti veya $ isareti veya satir sonuna kadar domain'i cikar
            domain = ""
            for ch in rest:
                if ch in ("^", "$", "/", "*", "|"):
                    break
                domain += ch

            domain = domain.lower().strip(".")
            if domain and "." in domain and _is_valid_domain(domain):
                domains.add(domain)

    return domains


def parse_ip_list_format(content: str) -> set:
    """Saf IP adresi listesi formatini ayristir (IP blocklist).
    Her satirda bir IP adresi (IPv4 veya IPv6).
    """
    ips = set()

    for line in content.split("\n"):
        line = _strip_inline_comment(line)
        if not line or line.startswith("!") or line.startswith("["):
            continue

        token = line.split()[0].strip()
        if _is_valid_ip(token):
            ips.add(token)

    return ips


# ===== FORMAT ALGILAMA =====

def detect_blocklist_format(content: str) -> str:
    """Blocklist iceriginden formati otomatik algila.
    Dondurulen degerler: 'hosts', 'adblock', 'domain_list', 'ip_list'
    """
    lines = []
    for l in content.split("\n"):
        l = l.strip()
        if l and not l.startswith("#") and not l.startswith("!") and not l.startswith("["):
            lines.append(l)
        if len(lines) >= 100:
            break

    if not lines:
        return "domain_list"

    hosts_count = 0
    adblock_count = 0
    domain_count = 0
    ip_count = 0

    host_prefixes = {"0.0.0.0", "127.0.0.1", "::1", "::"}

    for line in lines:
        stripped = _strip_inline_comment(line)
        if not stripped:
            continue

        parts = stripped.split()

        # AdBlock formati kontrolü
        if stripped.startswith("||") and ("^" in stripped or "$" in stripped):
            adblock_count += 1
        elif stripped.startswith("@@||"):
            adblock_count += 1
        # Hosts formati kontrolü
        elif len(parts) >= 2 and parts[0] in host_prefixes:
            hosts_count += 1
        # IP adresi kontrolü
        elif len(parts) == 1 and _is_valid_ip(parts[0]):
            ip_count += 1
        # Domain kontrolü
        elif len(parts) == 1 and "." in parts[0] and _is_valid_domain(parts[0].strip(".")):
            domain_count += 1

    # En yuksek skora göre format belirle
    scores = {
        "adblock": adblock_count,
        "hosts": hosts_count,
        "ip_list": ip_count,
        "domain_list": domain_count,
    }
    best = max(scores, key=scores.get)

    # En az 1 eslesme olmali, yoksa domain_list varsay
    if scores[best] == 0:
        return "domain_list"
    return best


def parse_any_format(content: str) -> set:
    """İçerik formatini otomatik algilayip parse et."""
    detected = detect_blocklist_format(content)
    logger.debug(f"Otomatik algilanan format: {detected}")

    if detected == "hosts":
        return parse_hosts_format(content)
    elif detected == "adblock":
        return parse_adblock_format(content)
    elif detected == "ip_list":
        return parse_ip_list_format(content)
    return parse_domain_list_format(content)


# ===== CHECKSUM =====

def compute_content_hash(content: str) -> str:
    """İçerik için SHA256 checksum hesapla."""
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()


# ===== SSRF KORUMASI =====

def _validate_blocklist_url(url: str) -> bool:
    """SSRF korumasi: URL'nin yerel/özel ag adresine isaret etmedigini dogrula."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        # Bilinen tehlikeli host'lar
        blocked_hosts = {
            "127.0.0.1", "localhost", "0.0.0.0", "::1",
            "169.254.169.254",  # Cloud metadata endpoint
            "metadata.google.internal",
        }
        if hostname.lower() in blocked_hosts:
            return False
        # Özel IP aralıklari kontrolü
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False
        except ValueError:
            pass  # Domain adi, IP degil - sorun yok
        return True
    except Exception:
        return False


# ===== FETCH & PARSE =====

async def fetch_and_parse_blocklist(blocklist: Blocklist) -> tuple[set, str]:
    """Blocklist kaynagini indir ve ayristir.
    Doner: (domains_set, content_hash)
    """
    import httpx

    url = blocklist.url
    if not url:
        raise RuntimeError("Blocklist URL'si tanimlanmamis")

    # SSRF korumasi
    if not _validate_blocklist_url(url):
        raise RuntimeError(f"Geçersiz URL: özel/yerel adresler desteklenmez ({url})")

    headers = {
        "User-Agent": "TonbilAiOS/1.0 DNS-Blocker",
        "Accept-Encoding": "gzip, deflate",
        "Accept": "text/plain, */*",
    }

    # Once SSL doğrulamali dene, başarısız olursa SSL'siz dene
    last_error = None
    for verify_ssl in (True, False):
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0),
                follow_redirects=True,
                max_redirects=5,
                verify=verify_ssl,
                headers=headers,
            ) as client:
                chunks = []
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_text(chunk_size=65536):
                        chunks.append(chunk)
                content = "".join(chunks)

            if not content.strip():
                raise RuntimeError(f"Bos içerik donduruldu ({url})")

            # Checksum hesapla
            content_hash = compute_content_hash(content)

            # Parse et
            domains = parse_any_format(content)
            if not verify_ssl:
                logger.warning(f"Blocklist '{blocklist.name}': SSL doğrulama devre disi birakildi ({url})")
            logger.info(f"Blocklist '{blocklist.name}': {url} -> {len(domains)} domain/IP indirildi")
            return domains, content_hash

        except httpx.ConnectError as e:
            if verify_ssl:
                last_error = e
                logger.debug(f"SSL hatasi, SSL'siz deneniyor: {url}")
                continue
            raise RuntimeError(f"Bağlantı hatasi ({url}): {e}")
        except httpx.TimeoutException as e:
            raise RuntimeError(f"Zaman asimi ({url}): {type(e).__name__}")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"HTTP {e.response.status_code} hatasi ({url})")
        except RuntimeError:
            raise
        except Exception as e:
            if verify_ssl:
                last_error = e
                continue
            raise RuntimeError(f"Indirme hatasi ({url}): {e}")

    raise RuntimeError(f"Indirilemedi ({url}): {last_error}")


# ===== TEK BLOCKLIST GUNCELLEME =====

async def refresh_single_blocklist(
    blocklist: Blocklist, session, driver: BaseNetworkDriver
) -> dict:
    """Tek bir blocklist'i güncelle ve istatistik dondur.
    Doner: {
        blocklist_id, name, previous_domain_count, new_domain_count,
        added_count, removed_count, status, error_message
    }
    """
    previous_count = blocklist.domain_count or 0
    result = {
        "blocklist_id": blocklist.id,
        "name": blocklist.name,
        "previous_domain_count": previous_count,
        "new_domain_count": 0,
        "added_count": 0,
        "removed_count": 0,
        "status": "error",
        "error_message": None,
    }

    try:
        domains, content_hash = await fetch_and_parse_blocklist(blocklist)
        new_count = len(domains)

        # Checksum karsilastirma: degismemisse "unchanged" dondur
        if blocklist.content_hash and blocklist.content_hash == content_hash:
            # Cache dosyasi yoksa yine de kaydet
            if load_domains_from_cache(blocklist.id) is None:
                save_domains_to_cache(blocklist.id, domains)
            result["new_domain_count"] = previous_count
            result["status"] = "unchanged"
            # last_updated'i yine de güncelle (kontrol yapildigini gostermek için)
            blocklist.last_updated = datetime.utcnow()
            blocklist.last_error = None
            logger.info(f"Blocklist '{blocklist.name}': içerik degismedi (checksum esit)")
            return result

        # Domainleri cache'e kaydet
        save_domains_to_cache(blocklist.id, domains)

        # Eklenen/cikarilan sayısı hesapla (yaklaik deger - onceki set yok)
        added = max(0, new_count - previous_count)
        removed = max(0, previous_count - new_count)

        # Veritabani güncelle
        blocklist.domain_count = new_count
        blocklist.content_hash = content_hash
        blocklist.last_updated = datetime.utcnow()
        blocklist.last_error = None

        result["new_domain_count"] = new_count
        result["added_count"] = added
        result["removed_count"] = removed
        result["status"] = "updated"

        logger.info(
            f"Blocklist '{blocklist.name}' güncellendi: "
            f"{previous_count} -> {new_count} domain "
            f"(+{added}, -{removed})"
        )

    except Exception as e:
        err_msg = str(e) or type(e).__name__
        blocklist.last_error = err_msg
        result["error_message"] = err_msg
        result["new_domain_count"] = previous_count
        logger.error(f"Blocklist '{blocklist.name}' güncellenemedi: {err_msg}")

    return result


# ===== TOPLU GUNCELLEME =====

async def refresh_all_blocklists(driver: BaseNetworkDriver) -> dict:
    """Tum aktif blocklist'leri güncelle ve toplu istatistik dondur.
    Doner: {
        total_blocklists, updated_count, unchanged_count, failed_count,
        total_domains_before, total_domains_after, new_domains_added,
        results: [...]
    }
    """
    results = []
    total_before = 0
    total_after = 0

    async with async_session_factory() as session:
        result_q = await session.execute(
            select(Blocklist).where(Blocklist.enabled == True)  # noqa: E712
        )
        blocklists = result_q.scalars().all()

        for bl in blocklists:
            total_before += (bl.domain_count or 0)
            r = await refresh_single_blocklist(bl, session, driver)
            total_after += r["new_domain_count"]
            results.append(r)

        await session.commit()

    # Redis engelleme setini yeniden oluştur
    try:
        await rebuild_blocked_domains_set(driver)
    except Exception as e:
        logger.warning(f"Redis engelleme seti güncellenirken hata (devam ediliyor): {e}")

    updated_count = sum(1 for r in results if r["status"] == "updated")
    unchanged_count = sum(1 for r in results if r["status"] == "unchanged")
    failed_count = sum(1 for r in results if r["status"] == "error")

    summary = {
        "total_blocklists": len(results),
        "updated_count": updated_count,
        "unchanged_count": unchanged_count,
        "failed_count": failed_count,
        "total_domains_before": total_before,
        "total_domains_after": total_after,
        "new_domains_added": max(0, total_after - total_before),
        "results": results,
    }

    logger.info(
        f"Toplu güncelleme tamamlandi: {len(results)} liste, "
        f"{updated_count} güncellendi, {unchanged_count} degismedi, {failed_count} hata. "
        f"Toplam: {total_before} -> {total_after} domain"
    )

    return summary


# ===== ENGELLEME SETI OLUSTURMA =====

async def rebuild_blocked_domains_set(driver: BaseNetworkDriver):
    """Tum aktif blocklistlerden ve özel kurallardan engelleme setini yeniden oluştur.
    Öncelikle yerel cache dosyalarindan okur (hizli).
    Cache yoksa internetten indirir ve cache'e kaydeder (yavas, sadece ilk seferde).
    """
    logger.info("Engellenen domain seti yeniden oluşturuluyor...")
    all_blocked = set()

    async with async_session_factory() as session:
        # 1. Aktif blocklistlerden domainleri topla (CACHE'DEN)
        result = await session.execute(
            select(Blocklist).where(Blocklist.enabled == True)  # noqa: E712
        )
        blocklists = result.scalars().all()

        for bl in blocklists:
            try:
                # Öncelikle cache'den oku (milisaniyeler içinde)
                domains = load_domains_from_cache(bl.id)
                if domains is not None:
                    all_blocked.update(domains)
                    logger.debug(f"Blocklist '{bl.name}': cache'den {len(domains)} domain yuklendi")
                else:
                    # Cache yoksa indir ve kaydet (ilk calistirma veya cache temizlenmis)
                    logger.info(f"Blocklist '{bl.name}': cache bulunamadı, indiriliyor...")
                    domains, content_hash = await fetch_and_parse_blocklist(bl)
                    save_domains_to_cache(bl.id, domains)
                    all_blocked.update(domains)
                    bl.domain_count = len(domains)
                    bl.content_hash = content_hash
                    bl.last_updated = datetime.utcnow()
                    bl.last_error = None
                    logger.info(f"Blocklist '{bl.name}': {len(domains)} domain indirildi ve cache'lendi")
            except Exception as e:
                bl.last_error = str(e)
                logger.error(f"Blocklist '{bl.name}' yüklenemedi: {e}")

        # 2. Özel BLOCK kurallarini ekle
        block_rules = await session.execute(
            select(DnsRule).where(DnsRule.rule_type == DnsRuleType.BLOCK)
        )
        for rule in block_rules.scalars().all():
            all_blocked.add(rule.domain.lower())

        # 3. Özel ALLOW kurallarini cikar (whitelist override)
        allow_rules = await session.execute(
            select(DnsRule).where(DnsRule.rule_type == DnsRuleType.ALLOW)
        )
        for rule in allow_rules.scalars().all():
            all_blocked.discard(rule.domain.lower())

        await session.commit()

    # 4. Driver'a yukle (Redis SET)
    try:
        await driver.load_blocked_domains(all_blocked)
    except Exception as e:
        logger.warning(f"Redis'e domain seti yuklenirken hata: {e}")
    logger.info(f"Toplam {len(all_blocked)} benzersiz domain engellendi.")
    return len(all_blocked)


# ===== KATEGORI / PROFIL DOMAIN YONETIMI =====


async def rebuild_category_domains(category_key: str, redis_client=None):
    """Bir kategorinin domain setini yeniden olustur.
    Linked blocklist'lerin cache dosyalarindan + custom_domains'den okur.
    -> dns:category_domains:{category_key} Redis SET'e yazar.
    """
    from app.models.content_category import ContentCategory
    from app.models.category_blocklist import CategoryBlocklist

    if redis_client is None:
        from app.db.redis_client import get_redis
        redis_client = await get_redis()

    all_domains = set()

    async with async_session_factory() as session:
        # Kategoriyi bul
        result = await session.execute(
            select(ContentCategory).where(ContentCategory.key == category_key)
        )
        category = result.scalar_one_or_none()
        if not category:
            logger.warning(f"Kategori bulunamadi: {category_key}")
            return 0

        # 1. Linked blocklist'lerin cache dosyalarindan domainleri oku
        bl_result = await session.execute(
            select(CategoryBlocklist.blocklist_id).where(
                CategoryBlocklist.category_id == category.id
            )
        )
        blocklist_ids = [row[0] for row in bl_result.all()]

        for bl_id in blocklist_ids:
            domains = load_domains_from_cache(bl_id)
            if domains:
                all_domains.update(domains)

        # 2. custom_domains ekle (satir basina bir domain)
        if category.custom_domains:
            for line in category.custom_domains.strip().split("\n"):
                domain = line.strip().lower()
                if domain and "." in domain and len(domain) > 3:
                    all_domains.add(domain)

        # 3. domain_count guncelle
        category.domain_count = len(all_domains)
        await session.commit()

    # 4. Redis SET'e yaz
    redis_key = f"dns:category_domains:{category_key}"
    await redis_client.delete(redis_key)
    if all_domains:
        batch = []
        for domain in all_domains:
            batch.append(domain)
            if len(batch) >= 5000:
                await redis_client.sadd(redis_key, *batch)
                batch = []
        if batch:
            await redis_client.sadd(redis_key, *batch)

    logger.info(f"Kategori '{category_key}' domain seti: {len(all_domains)} domain")
    return len(all_domains)


async def rebuild_profile_domains(profile_id: int, redis_client=None):
    """Bir profilin domain setini yeniden olustur.
    Profile.content_filters'daki kategori key'lerinden
    dns:category_domains:{key} SET'lerini birlestirir.
    -> dns:profile_domains:{profile_id} Redis SET'e yazar.
    """
    from app.models.profile import Profile

    if redis_client is None:
        from app.db.redis_client import get_redis
        redis_client = await get_redis()

    async with async_session_factory() as session:
        profile = await session.get(Profile, profile_id)
        if not profile:
            logger.warning(f"Profil bulunamadi: {profile_id}")
            return 0

        category_keys = profile.content_filters or []

    redis_key = f"dns:profile_domains:{profile_id}"

    if not category_keys:
        await redis_client.delete(redis_key)
        return 0

    # SUNIONSTORE ile kategori domain setlerini birlestir
    source_keys = [f"dns:category_domains:{key}" for key in category_keys]

    # Kaynak key'lerin var olup olmadigini kontrol et
    existing_keys = []
    for key in source_keys:
        if await redis_client.exists(key):
            existing_keys.append(key)

    if existing_keys:
        await redis_client.sunionstore(redis_key, *existing_keys)
        total = await redis_client.scard(redis_key)
    else:
        await redis_client.delete(redis_key)
        total = 0

    logger.info(
        f"Profil {profile_id} domain seti: {total} domain "
        f"({len(category_keys)} kategori)"
    )
    return total


async def rebuild_all_category_domains(redis_client=None):
    """Baslangicta tum aktif kategorilerin domain setlerini olustur."""
    from app.models.content_category import ContentCategory

    if redis_client is None:
        from app.db.redis_client import get_redis
        redis_client = await get_redis()

    async with async_session_factory() as session:
        result = await session.execute(
            select(ContentCategory).where(
                ContentCategory.enabled == True  # noqa: E712
            )
        )
        categories = result.scalars().all()

    total = 0
    for cat in categories:
        count = await rebuild_category_domains(cat.key, redis_client)
        total += count

    logger.info(
        f"Tum kategori domain setleri yuklendi: "
        f"{len(categories)} kategori, {total} toplam domain"
    )


async def rebuild_all_profile_domains(redis_client=None):
    """Baslangicta tum profillerin domain setlerini olustur."""
    from app.models.profile import Profile

    if redis_client is None:
        from app.db.redis_client import get_redis
        redis_client = await get_redis()

    async with async_session_factory() as session:
        result = await session.execute(select(Profile))
        profiles = result.scalars().all()

    for profile in profiles:
        await rebuild_profile_domains(profile.id, redis_client)

    logger.info(f"Tum profil domain setleri yuklendi: {len(profiles)} profil")


async def rebuild_device_profile_cache(redis_client=None):
    """Baslangicta tum cihaz->profil mapping'lerini Redis'e yukle."""
    from app.models.device import Device

    if redis_client is None:
        from app.db.redis_client import get_redis
        redis_client = await get_redis()

    async with async_session_factory() as session:
        result = await session.execute(
            select(Device).where(Device.profile_id.isnot(None))
        )
        devices = result.scalars().all()

    count = 0
    for device in devices:
        if device.profile_id:
            await redis_client.set(
                f"dns:device_profile:{device.id}",
                str(device.profile_id),
            )
            count += 1

    logger.info(f"Cihaz-profil cache yuklendi: {count} cihaz")


# ===== PERIYODIK WORKER =====

async def _get_next_update_interval() -> int:
    """En yakin güncelleme zamani olan listenin kalansüresini hesapla (saniye).
    Her listenin kendi update_frequency_hours degerine bakar.
    Minimum 300 saniye (5 dk), maksimum 6 saat.
    """
    min_interval = settings.DNS_BLOCKLIST_UPDATE_HOURS * 3600  # varsayilan ust sinir

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Blocklist).where(Blocklist.enabled == True)  # noqa: E712
            )
            blocklists = result.scalars().all()

            now = datetime.utcnow()
            for bl in blocklists:
                freq_seconds = (bl.update_frequency_hours or 24) * 3600
                if bl.last_updated:
                    elapsed = (now - bl.last_updated).total_seconds()
                    remaining = max(0, freq_seconds - elapsed)
                else:
                    remaining = 0  # Hic güncellenmemis, hemen güncelle

                if remaining < min_interval:
                    min_interval = remaining
    except Exception as e:
        logger.warning(f"Güncelleme aralığı hesaplanamadi: {e}")

    # Minimum 5 dk, maksimum global ayar
    return max(300, int(min_interval))


async def start_blocklist_worker(driver: BaseNetworkDriver):
    """Ana blocklist güncelleme dongusu.
    Her listenin kendi update_frequency_hours degerine göre güncelleme yapar.
    """
    logger.info("Blocklist iscisi başlatildi.")

    # Ilk yükleme: hemen calistir
    try:
        await rebuild_blocked_domains_set(driver)
    except Exception as e:
        logger.error(f"Ilk blocklist yüklemesi hatasi: {e}")

    # Periyodik güncelleme dongusu - per-blocklist frekans dikkate alinir
    while True:
        interval = await _get_next_update_interval()
        logger.debug(f"Sonraki blocklist kontrolü {interval} saniye sonra")
        await asyncio.sleep(interval)

        try:
            # Güncellenmesi gereken listeleri indir ve cache'e kaydet
            refreshed_any = False
            now = datetime.utcnow()

            async with async_session_factory() as session:
                result = await session.execute(
                    select(Blocklist).where(Blocklist.enabled == True)  # noqa: E712
                )
                for bl in result.scalars().all():
                    freq_seconds = (bl.update_frequency_hours or 24) * 3600
                    needs = not bl.last_updated or \
                        (now - bl.last_updated).total_seconds() >= freq_seconds
                    if needs:
                        try:
                            domains, content_hash = await fetch_and_parse_blocklist(bl)
                            save_domains_to_cache(bl.id, domains)
                            bl.domain_count = len(domains)
                            bl.content_hash = content_hash
                            bl.last_updated = datetime.utcnow()
                            bl.last_error = None
                            refreshed_any = True
                            logger.info(
                                f"Blocklist '{bl.name}' periyodik güncellendi: "
                                f"{len(domains)} domain"
                            )
                        except Exception as e:
                            bl.last_error = str(e)
                            logger.error(f"Blocklist '{bl.name}' güncellenemedi: {e}")

                await session.commit()

            if refreshed_any:
                # Cache'den hizli rebuild (internetten indirme yok)
                await rebuild_blocked_domains_set(driver)
            else:
                logger.debug("Tum blocklist'ler guncel, güncelleme atlaniyor")
        except Exception as e:
            logger.error(f"Blocklist worker hatasi: {e}")
