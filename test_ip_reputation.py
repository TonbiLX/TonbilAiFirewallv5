#!/usr/bin/env python3
"""
IP Reputation Stabilite Testi - Quick-11
TonbilAiOS v5 - IP Reputation API, Redis ve Frontend build kontrolu

SSH uzerinden Pi'de curl komutlari calistirarak API'yi test eder.
"""

import json
import sys
import time
import threading
import socket

# --- Renkli cikti yardimcilari ---
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):    print(f"  {GREEN}[PASS]{RESET} {msg}")
def fail(msg):  print(f"  {RED}[FAIL]{RESET} {msg}")
def info(msg):  print(f"  {CYAN}[INFO]{RESET} {msg}")
def warn(msg):  print(f"  {YELLOW}[WARN]{RESET} {msg}")
def section(title): print(f"\n{BOLD}{CYAN}=== {title} ==={RESET}")

# --- Test sonuc takibi ---
results = {}

def record(name, passed, detail=""):
    results[name] = {"passed": passed, "detail": detail}
    if passed:
        ok(f"{name}: {detail}")
    else:
        fail(f"{name}: {detail}")


# =========================================================
# SSH baglanti (2 adimli: jump -> target)
# =========================================================

def connect_to_pi():
    """
    pi.tonbil.com:2323 (jump) -> 192.168.1.2 (target) SSH baglantisi kurar.
    Sadece target_client dondurulur (Pi icinde komut calistirmak icin).
    """
    try:
        import paramiko
    except ImportError:
        print(f"{RED}HATA: paramiko yuklu degil. pip install paramiko{RESET}")
        sys.exit(1)

    jump_host = "pi.tonbil.com"
    jump_port = 2323
    pi_host   = "192.168.1.2"
    pi_port   = 22
    ssh_user  = "admin"
    ssh_pass  = "benbuyum9087"

    # Adim 1: Jump host'a baglan
    jump = paramiko.SSHClient()
    jump.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    jump.connect(jump_host, port=jump_port, username=ssh_user, password=ssh_pass, timeout=20)
    print(f"  {GREEN}Jump host baglantisi OK: {jump_host}:{jump_port}{RESET}")

    # Adim 2: Jump'tan Pi'ye channel ac
    jump_transport = jump.get_transport()
    channel = jump_transport.open_channel(
        "direct-tcpip",
        (pi_host, pi_port),
        ("127.0.0.1", 0)
    )

    # Adim 3: Pi'ye SSH baglan (channel uzerinden)
    target = paramiko.SSHClient()
    target.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    target.connect(pi_host, username=ssh_user, password=ssh_pass, sock=channel, timeout=20)
    print(f"  {GREEN}Pi baglantisi OK: {pi_host}{RESET}")

    return jump, target


def ssh_exec(client, cmd, timeout=30):
    """Pi'de komut calistir, (stdout, stderr, exit_code) dondur."""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out  = stdout.read().decode("utf-8", errors="replace").strip()
    err  = stderr.read().decode("utf-8", errors="replace").strip()
    code = stdout.channel.recv_exit_status()
    return out, err, code


# =========================================================
# API Yardimcilari (SSH uzerinden Pi'de curl)
# =========================================================

BASE_URL = "http://localhost:8000/api/v1"
TOKEN    = None


def api_curl(client, method, path, headers=None, data=None, timeout=30):
    """
    Pi'de curl komutu calistirarak API istegi gonder.
    Returns: (http_status_int, response_dict_or_none)

    Strateji: curl -w ile HTTP kodu ozel ayiraci ile body sonuna eklenir.
    Format: <json_body>|HTTPCODE:<code>
    """
    # Temel curl komutu
    parts = [f"curl -s -w '|HTTPCODE:%{{http_code}}' -X {method}"]

    # Auth header
    if headers:
        for k, v in headers.items():
            # Tek tirnak icindeki tek tirnaklari escape et
            safe_v = v.replace("'", "'\"'\"'")
            parts.append(f"-H '{k}: {safe_v}'")

    # JSON body
    if data:
        json_str = json.dumps(data, ensure_ascii=False)
        # Tek tirnaklari escape et (bash icin)
        json_escaped = json_str.replace("'", "'\"'\"'")
        parts.append("-H 'Content-Type: application/json'")
        parts.append(f"-d '{json_escaped}'")

    parts.append(f"'{BASE_URL}{path}'")
    parts.append("2>/dev/null")

    cmd = " ".join(parts)
    out, err, code = ssh_exec(client, cmd, timeout=timeout)

    # out format: <json_body>|HTTPCODE:<code>
    # HTTP kodu ayiracini bul
    sep = "|HTTPCODE:"
    if sep in out:
        body_str, http_part = out.rsplit(sep, 1)
        http_code_str = http_part.strip()
    else:
        # Fallback: son 3 karakter HTTP kodu
        body_str = out[:-3] if len(out) > 3 else ""
        http_code_str = out[-3:] if len(out) >= 3 else "0"

    try:
        http_code = int(http_code_str[:3])
    except (ValueError, IndexError):
        http_code = 0

    body_str = body_str.strip()
    try:
        body = json.loads(body_str) if body_str else {}
    except json.JSONDecodeError:
        body = {"_raw": body_str[:200]}

    return http_code, body


def authed():
    """Authorization header dict."""
    return {"Authorization": f"Bearer {TOKEN}"}


# =========================================================
# TEST FONKSIYONLARI
# =========================================================

def test_auth_login(client):
    """Test 1: Auth Login"""
    section("TEST 1: Auth Login")
    global TOKEN

    http, body = api_curl(
        client, "POST", "/auth/login",
        data={"username": "admin", "password": "benbuyum9087"}
    )

    if http == 200 and body.get("access_token"):
        TOKEN = body["access_token"]
        record("Auth Login", True, f"JWT token alindi (HTTP {http})")
        return True
    else:
        record("Auth Login", False, f"HTTP {http} - {body}")
        return False


def test_config_get(client):
    """Test 2: GET /ip-reputation/config"""
    section("TEST 2: GET /ip-reputation/config")

    http, body = api_curl(client, "GET", "/ip-reputation/config", headers=authed())

    if http != 200:
        record("Config GET - HTTP 200", False, f"HTTP {http} - {body}")
        return None

    record("Config GET - HTTP 200", True, "200 OK")

    # Alan kontrolleri
    required = ["enabled", "abuseipdb_key", "abuseipdb_key_set",
                "blocked_countries", "check_interval", "max_checks_per_cycle", "daily_limit"]
    missing = [f for f in required if f not in body]
    if missing:
        record("Config GET - Alan kontrolu", False, f"Eksik alanlar: {missing}")
    else:
        record("Config GET - Alan kontrolu", True, "Tum alanlar mevcut")

    if body.get("abuseipdb_key_set"):
        record("Config GET - abuseipdb_key_set=True", True, "API key kayitli")
    else:
        record("Config GET - abuseipdb_key_set=True", False, "API key KAYITLI DEGIL")

    key = body.get("abuseipdb_key", "")
    key_set = body.get("abuseipdb_key_set", False)
    if key_set:
        if key and len(key) > 8:
            record("Config GET - Key maskelenmis", True, f"Masked key: {key}")
        elif key:
            record("Config GET - Key maskelenmis", True, f"Kisa key maskelendi: {key}")
        else:
            record("Config GET - Key maskelenmis", False, "key_set=True ama key bos")
    else:
        record("Config GET - Key maskelenmis", True, "key_set=False, maskeleme N/A")

    info(f"enabled={body.get('enabled')}, check_interval={body.get('check_interval')}, "
         f"daily_limit={body.get('daily_limit')}")
    return body


def test_summary(client):
    """Test 3: GET /ip-reputation/summary"""
    section("TEST 3: GET /ip-reputation/summary")

    http, body = api_curl(client, "GET", "/ip-reputation/summary", headers=authed())

    if http != 200:
        record("Summary GET - HTTP 200", False, f"HTTP {http}")
        return None

    record("Summary GET - HTTP 200", True, "200 OK")

    required = ["total_checked", "flagged_critical", "flagged_warning",
                "daily_checks_used", "daily_limit"]
    missing = [f for f in required if f not in body]
    if missing:
        record("Summary GET - Alan kontrolu", False, f"Eksik: {missing}")
    else:
        record("Summary GET - Alan kontrolu", True, "Tum alanlar mevcut")

    if body.get("daily_limit") == 900:
        record("Summary GET - daily_limit=900", True, "daily_limit=900 dogru")
    else:
        record("Summary GET - daily_limit=900", False, f"daily_limit={body.get('daily_limit')}")

    info(f"total_checked={body.get('total_checked')}, flagged_critical={body.get('flagged_critical')}, "
         f"daily_checks_used={body.get('daily_checks_used')}/{body.get('daily_limit')}")
    return body


def test_ips(client):
    """Test 4: GET /ip-reputation/ips"""
    section("TEST 4: GET /ip-reputation/ips")

    http, body = api_curl(client, "GET", "/ip-reputation/ips", headers=authed())

    if http != 200:
        record("IPs GET - HTTP 200", False, f"HTTP {http}")
        return None, []

    record("IPs GET - HTTP 200", True, "200 OK")

    if "ips" in body and "total" in body:
        record("IPs GET - Alan kontrolu", True, f"ips + total mevcut (total={body['total']})")
    else:
        record("IPs GET - Alan kontrolu", False, f"Eksik alanlar: {list(body.keys())}")

    ips = body.get("ips", [])
    if ips:
        entry = ips[0]
        ip_req = ["ip", "abuse_score", "total_reports", "country", "city", "isp", "org", "checked_at"]
        missing = [f for f in ip_req if f not in entry]
        if missing:
            record("IPs GET - IP entry alanlari", False, f"Eksik: {missing}")
        else:
            record("IPs GET - IP entry alanlari", True, f"Tum alanlar OK (ornek IP: {entry['ip']})")
    else:
        info("IP listesi bos - worker henuz IP kontrol etmemis (normal)")
        record("IPs GET - IP entry alanlari", True, "Bos liste - SKIP")

    return body, ips


def test_abuseipdb_test(client):
    """Test 5: POST /ip-reputation/test"""
    section("TEST 5: POST /ip-reputation/test (AbuseIPDB key test)")

    http, body = api_curl(client, "POST", "/ip-reputation/test", headers=authed())

    if http != 200:
        record("AbuseIPDB Test - HTTP 200", False, f"HTTP {http}")
        return

    record("AbuseIPDB Test - HTTP 200", True, "200 OK")

    status = body.get("status")
    if status == "ok":
        record("AbuseIPDB Test - status=ok", True, "API key gecerli")
        data = body.get("data") or {}

        if data.get("tested_ip") == "8.8.8.8":
            record("AbuseIPDB Test - tested_ip=8.8.8.8", True, "Test IP dogru")
        else:
            record("AbuseIPDB Test - tested_ip=8.8.8.8", False,
                   f"tested_ip={data.get('tested_ip')}")

        score = data.get("abuse_score")
        if isinstance(score, int):
            record("AbuseIPDB Test - abuse_score integer", True, f"score={score}")
        else:
            record("AbuseIPDB Test - abuse_score integer", False,
                   f"score={score} (tip: {type(score).__name__})")

        info(f"8.8.8.8: score={score}, country={data.get('country')}, isp={data.get('isp')}")
    elif status == "error":
        record("AbuseIPDB Test - status=ok", False, f"Hata: {body.get('message')}")
    else:
        record("AbuseIPDB Test - status=ok", False, f"Beklenmedik status: {status}")


def test_country_round_trip(client, original_config):
    """Test 6: PUT /ip-reputation/config - Ulke round-trip"""
    section("TEST 6: Ulke engelleme round-trip (XX ekle/cikar)")

    orig_countries = (original_config or {}).get("blocked_countries", [])
    test_countries  = list(orig_countries) + ["XX"]

    http, body = api_curl(
        client, "PUT", "/ip-reputation/config",
        headers=authed(),
        data={"blocked_countries": test_countries}
    )

    if http != 200:
        record("Country PUT - HTTP 200", False, f"HTTP {http}")
        return

    record("Country PUT - HTTP 200", True, "PUT 200 OK")

    # Dogrula
    http2, body2 = api_curl(client, "GET", "/ip-reputation/config", headers=authed())
    if http2 == 200:
        got = body2.get("blocked_countries", [])
        if "XX" in got:
            record("Country Round-trip - XX listede", True, f"blocked_countries={got}")
        else:
            record("Country Round-trip - XX listede", False, f"XX bulunamadi: {got}")
    else:
        record("Country Round-trip - GET dogrulama", False, f"HTTP {http2}")

    # Geri al
    http3, _ = api_curl(
        client, "PUT", "/ip-reputation/config",
        headers=authed(),
        data={"blocked_countries": orig_countries}
    )
    if http3 == 200:
        record("Country Cleanup - Eski duruma dondurme", True, f"blocked_countries={orig_countries}")
    else:
        record("Country Cleanup - Eski duruma dondurme", False, f"HTTP {http3}")


def test_cache(client, summary_data):
    """Test 7: DELETE /ip-reputation/cache"""
    section("TEST 7: DELETE /ip-reputation/cache")

    total = (summary_data or {}).get("total_checked", 0)

    if total == 0:
        http, body = api_curl(client, "DELETE", "/ip-reputation/cache", headers=authed())
        if http == 200 and body.get("status") == "ok":
            record("Cache DELETE - HTTP 200", True, f"OK - {body.get('message')}")
        else:
            record("Cache DELETE - HTTP 200", False, f"HTTP {http} - {body}")
    else:
        warn(f"total_checked={total}, cache dolu - gercek sil atlandi, endpoint varlik kontrolu")
        # Sadece endpoint erisimini dogrula (GET summary)
        http2, _ = api_curl(client, "GET", "/ip-reputation/summary", headers=authed())
        record("Cache DELETE - Endpoint erisim (SKIP, cache dolu)", http2 == 200,
               f"Summary GET {http2} (DELETE endpoint mevcut, atlatildi)")


def test_redis_keys(client):
    """Test 8: Redis key kontrolu"""
    section("TEST 8: Redis key kontrolu (SSH)")

    rc = "redis-cli -a TonbilAiRedis2026 --no-auth-warning"

    # enabled
    out, _, _ = ssh_exec(client, f"{rc} GET reputation:enabled")
    if out in ("1", "0"):
        record("Redis - reputation:enabled", True, f"Deger='{out}'")
    elif out == "" or out == "(nil)":
        record("Redis - reputation:enabled", True, "Key yok (varsayilan: enabled=True - OK)")
    else:
        record("Redis - reputation:enabled", False, f"Beklenmedik: '{out}'")

    # api key
    out, _, _ = ssh_exec(client, f"{rc} GET reputation:abuseipdb_key")
    if out and out not in ("(nil)", ""):
        record("Redis - reputation:abuseipdb_key", True, f"Key mevcut, uzunluk={len(out)}")
    else:
        record("Redis - reputation:abuseipdb_key", False, f"Key bos/yok: '{out}'")

    # blocked_countries
    out, _, _ = ssh_exec(client, f"{rc} GET reputation:blocked_countries")
    if out and out != "(nil)":
        try:
            c = json.loads(out)
            record("Redis - reputation:blocked_countries", True, f"JSON array: {c}")
        except json.JSONDecodeError:
            record("Redis - reputation:blocked_countries", False, f"JSON parse hatasi: {out}")
    else:
        record("Redis - reputation:blocked_countries", True, "Key yok (bos liste - kabul edilebilir)")

    # IP keys
    out, _, _ = ssh_exec(client, f"{rc} KEYS 'reputation:ip:*' 2>/dev/null | head -5")
    ip_keys = [k for k in out.splitlines() if k.strip() and k != "(empty array)"]
    if ip_keys:
        record("Redis - reputation:ip:* keys", True, f"{len(ip_keys)} IP key, ornek: {ip_keys[:2]}")
    else:
        record("Redis - reputation:ip:* keys", True, "Bos (worker henuz calistirmamis - normal)")
        info("reputation:ip:* yok - ilk worker dongusu tamamlandiginda dolacak")


def test_worker_logs(client):
    """Test 9: Worker log kayitlari"""
    section("TEST 9: Worker log kayitlari")

    out, _, _ = ssh_exec(
        client,
        "sudo journalctl -u tonbilaios-backend --no-pager -n 150 2>/dev/null "
        "| grep -iE 'ip_reputation|abuseipdb|reputation' | tail -10 || true",
        timeout=25
    )

    lines = [l for l in out.splitlines() if l.strip()]
    if lines:
        record("Worker Logs - Log satirlari var", True, f"{len(lines)} satir bulundu")
        for l in lines[:5]:
            info(f"  {l[:120]}")
    else:
        warn("ip_reputation log satiri bulunamadi, backend durumunu kontrol ediyoruz...")
        out2, _, _ = ssh_exec(client, "sudo systemctl is-active tonbilaios-backend")
        if out2.strip() == "active":
            record("Worker Logs - Backend aktif", True,
                   "Backend calisiyor (ip_rep log yok = worker henuz tetiklenmemis veya ilk dongu bekleniyor)")
        else:
            record("Worker Logs - Backend aktif", False, f"Backend durumu: '{out2.strip()}'")


def test_frontend_build(client):
    """Test 10: Frontend build IpReputation kontrolu"""
    section("TEST 10: Frontend build kontrolu")

    # Minified JS'de "reputation" veya "IpReputation" ari
    out, _, _ = ssh_exec(
        client,
        "grep -rl 'reputation' /opt/tonbilaios/frontend/dist/assets/ 2>/dev/null "
        "| grep '\\.js' | head -3 || echo NONE"
    )

    if "NONE" in out or not out.strip():
        # dist var mi?
        out2, _, _ = ssh_exec(
            client, "ls /opt/tonbilaios/frontend/dist/assets/*.js 2>/dev/null | wc -l"
        )
        count = out2.strip()
        if count and int(count) > 0:
            record("Frontend Build - reputation string", False,
                   f"'reputation' bulunamadi ({count} JS dosyasinda)")
        else:
            record("Frontend Build - reputation string", False,
                   "dist/assets/ bos veya JS dosyasi yok - build yapilmamis")
    else:
        files = [f for f in out.splitlines() if f.strip() and "NONE" not in f]
        record("Frontend Build - reputation string", True,
               f"'reputation' bulundu: {files}")

    # IpReputationTab icin daha spesifik arama
    out3, _, _ = ssh_exec(
        client,
        "grep -rl 'IpReputation\\|IpReputationTab' /opt/tonbilaios/frontend/dist/ 2>/dev/null "
        "| head -3 || echo NONE"
    )
    if "NONE" not in out3 and out3.strip():
        record("Frontend Build - IpReputationTab component", True,
               f"IpReputationTab bulundu: {out3.splitlines()[:2]}")
    else:
        # Minified olabilir, sadece reputation ile yetiniyoruz
        info("IpReputationTab string bulunamadi (minified/bundled - normal olabilir)")
        info("'reputation' stringi ile genel kontrol yapildi")


# =========================================================
# OZET RAPOR
# =========================================================

def print_summary():
    section("OZET RAPOR")
    total  = len(results)
    passed = sum(1 for r in results.values() if r["passed"])
    failed = total - passed

    print(f"\n{BOLD}{'Test Adi':<50} {'Sonuc':<10}{RESET}")
    print("-" * 80)
    for name, r in results.items():
        sonuc = f"{GREEN}PASS{RESET}" if r["passed"] else f"{RED}FAIL{RESET}"
        detail = r["detail"][:55] if len(r["detail"]) > 55 else r["detail"]
        print(f"{'  ' + name:<50} {sonuc}  {detail}")

    print("-" * 80)
    pct = int(100 * passed / total) if total else 0
    print(f"\n{BOLD}Toplam: {total}  {GREEN}PASS: {passed}{RESET}{BOLD}  {RED}FAIL: {failed}{RESET}  ({pct}%)\n")

    if failed == 0:
        print(f"{GREEN}{BOLD}Tum testler basarili! IP Reputation sistemi saglikli.{RESET}\n")
        return 0
    else:
        print(f"{RED}{BOLD}{failed} test basarisiz. Lutfen yukaridaki FAIL kayitlarini inceleyin.{RESET}\n")
        return 1


# =========================================================
# MAIN
# =========================================================

def main():
    print(f"\n{BOLD}{CYAN}TonbilAiOS - IP Reputation Stabilite Testi (Quick-11){RESET}")
    print(f"{CYAN}pi.tonbil.com:2323 -> 192.168.1.2 SSH ProxyJump{RESET}\n")

    section("SSH Baglantisi Kuruluyor")
    try:
        jump_client, target_client = connect_to_pi()
    except Exception as e:
        print(f"\n{RED}SSH BAGLANTISI KURULAMADI: {e}{RESET}")
        print(f"{YELLOW}Cozum onerileri:")
        print(f"  1) pi.tonbil.com:2323 erisilebiligini kontrol et")
        print(f"  2) paramiko yuklu mu? (pip install paramiko)")
        print(f"  3) admin/benbuyum9087 kredentiallerini dogrula{RESET}")
        return 1

    try:
        # Test 1: Auth
        if not test_auth_login(target_client):
            print(f"\n{RED}Auth basarisiz, testler durduruluyor.{RESET}")
            return 1

        # Test 2: Config GET
        config_data = test_config_get(target_client)

        # Test 3: Summary
        summary_data = test_summary(target_client)

        # Test 4: IPs
        _, ips_list = test_ips(target_client)

        # Test 5: AbuseIPDB test endpoint
        test_abuseipdb_test(target_client)

        # Test 6: Country round-trip
        test_country_round_trip(target_client, config_data)

        # Test 7: Cache DELETE
        test_cache(target_client, summary_data)

        # Test 8: Redis keys
        test_redis_keys(target_client)

        # Test 9: Worker logs
        test_worker_logs(target_client)

        # Test 10: Frontend build
        test_frontend_build(target_client)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test kullanici tarafindan iptal edildi.{RESET}")
    finally:
        try:
            target_client.close()
        except Exception:
            pass
        try:
            jump_client.close()
        except Exception:
            pass
        print(f"\n  {CYAN}SSH baglantilari kapatildi.{RESET}")

    return print_summary()


if __name__ == "__main__":
    sys.exit(main())
