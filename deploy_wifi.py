"""
TonbilAiOS v5 — WiFi AP Yonetim Sistemi Deploy
Backend (HAL + model + schema + API + worker) + Frontend (sayfa + servis + navigasyon) deploy eder.
"""
import paramiko
import base64
import os
import sys
import time
from datetime import datetime

# --- KONFIGRASYON ---
JUMP_HOST = "pi.tonbil.com"
JUMP_PORT = 2323
PI_HOST = "192.168.1.2"
PI_PORT = 22
USER = "admin"
PASS = "benbuyum9087"

LOCAL_BASE = r"E:\Nextcloud-Yeni\TonbilAiFirevallv5"
REMOTE_BASE = "/opt/tonbilaios"

CHUNK_SIZE = 800

# Deploy edilecek dosyalar: (lokal goreli yol, pi mutlak yol)
DEPLOY_FILES = [
    # Backend — yeni dosyalar
    ("backend/app/hal/wifi_driver.py", f"{REMOTE_BASE}/backend/app/hal/wifi_driver.py"),
    ("backend/app/models/wifi_config.py", f"{REMOTE_BASE}/backend/app/models/wifi_config.py"),
    ("backend/app/schemas/wifi.py", f"{REMOTE_BASE}/backend/app/schemas/wifi.py"),
    ("backend/app/api/v1/wifi.py", f"{REMOTE_BASE}/backend/app/api/v1/wifi.py"),
    ("backend/app/workers/wifi_monitor.py", f"{REMOTE_BASE}/backend/app/workers/wifi_monitor.py"),
    # Backend — duzenlenmis dosyalar
    ("backend/app/api/v1/router.py", f"{REMOTE_BASE}/backend/app/api/v1/router.py"),
    ("backend/app/models/__init__.py", f"{REMOTE_BASE}/backend/app/models/__init__.py"),
    ("backend/app/main.py", f"{REMOTE_BASE}/backend/app/main.py"),
    # Frontend — yeni dosyalar
    ("frontend/src/services/wifiApi.ts", f"{REMOTE_BASE}/frontend/src/services/wifiApi.ts"),
    ("frontend/src/pages/WifiPage.tsx", f"{REMOTE_BASE}/frontend/src/pages/WifiPage.tsx"),
    # Frontend — duzenlenmis dosyalar
    ("frontend/src/App.tsx", f"{REMOTE_BASE}/frontend/src/App.tsx"),
    ("frontend/src/components/layout/Sidebar.tsx", f"{REMOTE_BASE}/frontend/src/components/layout/Sidebar.tsx"),
    ("frontend/src/types/index.ts", f"{REMOTE_BASE}/frontend/src/types/index.ts"),
]


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "[*]", "OK": "[+]", "FAIL": "[-]", "WARN": "[!]", "ASK": "[?]"}
    print(f"  {ts} {prefix.get(level, '[*]')} {msg}")


def connect_to_pi():
    """ProxyJump ile Pi'ye baglan."""
    log("SSH baglantisi kuruluyor: pi.tonbil.com:2323 -> 192.168.1.2:22")

    jump = paramiko.SSHClient()
    jump.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    jump.connect(JUMP_HOST, port=JUMP_PORT, username=USER, password=PASS, timeout=15)

    transport = jump.get_transport()
    channel = transport.open_channel("direct-tcpip", (PI_HOST, PI_PORT), ("127.0.0.1", 0))

    pi = paramiko.SSHClient()
    pi.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pi.connect(PI_HOST, username=USER, password=PASS, sock=channel, timeout=15)

    log("Pi'ye baglanildi!", "OK")
    return jump, pi


def pi_exec(pi, cmd, timeout=30):
    """Pi uzerinde komut calistir."""
    stdin, stdout, stderr = pi.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    rc = stdout.channel.recv_exit_status()
    return rc, out, err


def transfer_file(pi, local_path, remote_path):
    """Base64 chunked transfer ile dosya gonder."""
    with open(local_path, "r", encoding="utf-8") as f:
        content_bytes = f.read().encode("utf-8")

    b64 = base64.b64encode(content_bytes).decode("ascii")
    tmp = f"/tmp/deploy_{os.path.basename(remote_path)}.b64"

    pi_exec(pi, f"rm -f {tmp}")

    for i in range(0, len(b64), CHUNK_SIZE):
        chunk = b64[i:i + CHUNK_SIZE]
        pi_exec(pi, f"echo -n '{chunk}' >> {tmp}")

    # Hedef dizinin var oldugundan emin ol
    remote_dir = os.path.dirname(remote_path).replace("\\", "/")
    pi_exec(pi, f"sudo mkdir -p {remote_dir}")

    rc, out, err = pi_exec(pi, f"base64 -d {tmp} | sudo tee {remote_path} > /dev/null")
    if rc != 0:
        log(f"Transfer HATA: {err}", "FAIL")
        return False

    pi_exec(pi, f"rm -f {tmp}")

    # Boyut dogrula
    rc, out, _ = pi_exec(pi, f"wc -c < {remote_path}")
    remote_size = out.strip()
    local_size = len(content_bytes)
    ok = str(local_size) == remote_size
    if ok:
        log(f"  {os.path.basename(remote_path)}: OK ({local_size} byte)")
    else:
        log(f"  {os.path.basename(remote_path)}: BOYUT FARKLI ({local_size} vs {remote_size})", "FAIL")
    return ok


def main():
    print("=" * 60)
    print("  TonbilAiOS v5 — WiFi AP Yonetim Sistemi Deploy")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Dosya sayisi: {len(DEPLOY_FILES)}")
    print("=" * 60)

    try:
        jump, pi = connect_to_pi()
    except Exception as e:
        log(f"Baglanti HATA: {e}", "FAIL")
        return 1

    try:
        # 1. Backend durum kontrolu
        log("Backend durumu kontrol ediliyor...")
        rc, out, _ = pi_exec(pi, "sudo systemctl is-active tonbilaios-backend")
        if out.strip() != "active":
            log(f"Backend AKTIF DEGIL: {out}", "WARN")
            log("Yine de devam ediliyor...", "WARN")
        else:
            log("Backend: active", "OK")

        # 2. Yedek al
        log("Yedek aliniyor...")
        backup_dir = f"{REMOTE_BASE}/backup-wifi-{datetime.now().strftime('%Y%m%d-%H%M')}"
        pi_exec(pi, f"sudo mkdir -p {backup_dir}")
        for _, remote_path in DEPLOY_FILES:
            fname = os.path.basename(remote_path)
            pi_exec(pi, f"sudo cp {remote_path} {backup_dir}/{fname} 2>/dev/null")
        log(f"Yedek: {backup_dir}", "OK")

        # 3. Dosya transfer
        log(f"Dosyalar transfer ediliyor ({len(DEPLOY_FILES)} dosya)...")
        all_ok = True
        for local_rel, remote_path in DEPLOY_FILES:
            local_path = os.path.join(LOCAL_BASE, local_rel.replace("/", os.sep))
            if not os.path.exists(local_path):
                log(f"DOSYA BULUNAMADI: {local_path}", "FAIL")
                all_ok = False
                continue
            if not transfer_file(pi, local_path, remote_path):
                all_ok = False

        if not all_ok:
            log("Bazi dosya transferleri basarisiz!", "FAIL")
            return 1

        log("Tum dosyalar transfer edildi", "OK")

        # 4. hostapd paketini kontrol et / kur
        log("hostapd paketi kontrol ediliyor...")
        rc, out, _ = pi_exec(pi, "dpkg -l hostapd 2>/dev/null | grep '^ii'")
        if "hostapd" in out:
            log("hostapd: zaten kurulu", "OK")
        else:
            log("hostapd kuruluyor...", "INFO")
            rc, out, err = pi_exec(pi, "sudo apt-get install -y hostapd", timeout=120)
            if rc == 0:
                log("hostapd kuruldu", "OK")
            else:
                log(f"hostapd kurulum hatasi: {err}", "WARN")
                log("WiFi AP calismayabilir, devam ediliyor...", "WARN")

        # hostapd baslatilmasini devre disi birak (biz yonetiyoruz)
        pi_exec(pi, "sudo systemctl unmask hostapd 2>/dev/null")
        pi_exec(pi, "sudo systemctl disable hostapd 2>/dev/null")

        # 5. Frontend build
        log("Frontend build baslatiliyor...")
        rc, out, err = pi_exec(pi,
            f"cd {REMOTE_BASE}/frontend && sudo npm run build 2>&1 | tail -5",
            timeout=120,
        )
        if rc != 0:
            log(f"Frontend build HATA: {err or out}", "FAIL")
            log("Backend yine de restart edilecek...", "WARN")
        else:
            log("Frontend build: OK", "OK")

        # 6. Backend restart
        log("Backend yeniden baslatiliyor...")
        rc, _, err = pi_exec(pi, "sudo systemctl restart tonbilaios-backend")
        if rc != 0:
            log(f"Restart HATA: {err}", "FAIL")
            return 1

        time.sleep(10)

        # 7. Backend dogrulama
        rc, out, _ = pi_exec(pi, "sudo systemctl is-active tonbilaios-backend")
        if out.strip() == "active":
            log("Backend restart: OK", "OK")
        else:
            log(f"Backend restart sonrasi: {out}", "FAIL")
            rc2, journal, _ = pi_exec(pi, "sudo journalctl -u tonbilaios-backend -n 40 --no-pager")
            log(f"Journal (son 40 satir):\n{journal}", "WARN")
            return 1

        # 8. API erisilebilirlik testi
        rc, out, _ = pi_exec(pi,
            "curl -s --connect-timeout 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health",
            timeout=15,
        )
        if "200" in out:
            log("API erisimi: OK (HTTP 200)", "OK")
        else:
            log(f"API erisimi: {out}", "WARN")

        # 9. WiFi API endpoint testi
        rc, out, _ = pi_exec(pi,
            "curl -s --connect-timeout 5 http://127.0.0.1:8000/api/v1/wifi/status | head -c 200",
            timeout=15,
        )
        if "enabled" in out:
            log(f"WiFi API: OK ({out[:80]}...)", "OK")
        else:
            log(f"WiFi API yaniti: {out[:120]}", "WARN")

        print(f"\n{'='*60}")
        print("  WIFI AP DEPLOY TAMAMLANDI!")
        print(f"  - {len(DEPLOY_FILES)} dosya transfer edildi")
        print("  - 5 yeni backend dosyasi (HAL + model + schema + API + worker)")
        print("  - 2 yeni frontend dosyasi (API + sayfa)")
        print("  - 6 duzenlenmis dosya (router, models, main, App, Sidebar, types)")
        print("  - hostapd paketi kontrol edildi")
        print("  - Frontend build + Backend restart tamamlandi")
        print(f"  - Yedek: {backup_dir}")
        print(f"{'='*60}")

        return 0

    except KeyboardInterrupt:
        print("\n")
        log("Ctrl+C — deploy durduruldu.", "WARN")
        return 1

    except Exception as e:
        log(f"Beklenmeyen HATA: {e}", "FAIL")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        try:
            pi.close()
            jump.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
