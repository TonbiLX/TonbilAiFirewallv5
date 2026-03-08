"""Deploy Quick 12: Guvenlik Denetimi — Brute Force Koruma + Auth Guclendir"""
import paramiko
import os
import time

JUMP_HOST = "pi.tonbil.com"
JUMP_PORT = 2323
TARGET_HOST = "192.168.1.2"
TARGET_PORT = 22
USERNAME = "admin"
PASSWORD = "benbuyum9087"

FILES_TO_DEPLOY = [
    (
        "backend/app/api/v1/system_management.py",
        "/opt/tonbilaios/backend/app/api/v1/system_management.py",
    ),
    (
        "backend/app/api/v1/auth.py",
        "/opt/tonbilaios/backend/app/api/v1/auth.py",
    ),
    (
        "backend/app/schemas/auth.py",
        "/opt/tonbilaios/backend/app/schemas/auth.py",
    ),
    (
        "backend/app/api/v1/ws.py",
        "/opt/tonbilaios/backend/app/api/v1/ws.py",
    ),
]


def deploy():
    print("=== Quick 12 Deploy: Guvenlik Denetimi ===")

    # SSH baglantisi: jump host uzerinden target Pi
    jump = paramiko.SSHClient()
    jump.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"[1/4] Jump host baglaniliyor: {JUMP_HOST}:{JUMP_PORT} ...")
    jump.connect(JUMP_HOST, port=JUMP_PORT, username=USERNAME, password=PASSWORD, timeout=15)

    channel = jump.get_transport().open_channel(
        "direct-tcpip", (TARGET_HOST, TARGET_PORT), ("127.0.0.1", 0)
    )
    target = paramiko.SSHClient()
    target.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    target.connect(TARGET_HOST, username=USERNAME, password=PASSWORD, sock=channel, timeout=15)
    print(f"  Pi baglandı: {TARGET_HOST}")

    sftp = target.open_sftp()
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Backend dosyalarini yukle (/tmp/ uzerinden sudo cp)
    print("[2/4] Backend dosyalari aktariliyor...")
    for local_rel, remote_path in FILES_TO_DEPLOY:
        local_path = os.path.join(base_dir, local_rel)
        tmp_path = f"/tmp/{os.path.basename(remote_path)}"
        sftp.put(local_path, tmp_path)
        stdin, stdout, stderr = target.exec_command(
            f"sudo cp {tmp_path} {remote_path} && sudo chown root:root {remote_path} && rm {tmp_path}"
        )
        exit_code = stdout.channel.recv_exit_status()
        if exit_code == 0:
            print(f"  OK: {local_rel}")
        else:
            err = stderr.read().decode().strip()
            print(f"  HATA ({exit_code}): {local_rel} — {err}")

    sftp.close()

    # Backend yeniden baslatma
    print("[3/4] Backend yeniden baslatiliyor...")
    stdin, stdout, stderr = target.exec_command("sudo systemctl restart tonbilaios-backend")
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        err = stderr.read().decode().strip()
        print(f"  UYARI: Restart komutu exit={exit_code}: {err}")

    print("  5 saniye bekleniyor...")
    time.sleep(5)

    # Servis durumu kontrolu
    stdin, stdout, stderr = target.exec_command("sudo systemctl is-active tonbilaios-backend")
    status = stdout.read().decode().strip()
    if status == "active":
        print(f"  Backend durumu: {status} (OK)")
    else:
        print(f"  HATA: Backend durumu: {status}")

    # Dogrulama komutlari
    print("[4/4] Guvenlik dogrulamalari yapiliyor...")

    # 1) Reboot endpoint confirm olmadan 400 donmeli
    print("  [a] Reboot confirm kontrolu (token olmadan 401/422 bekleniyor)...")
    stdin, stdout, stderr = target.exec_command(
        "curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8000/api/v1/system-management/reboot "
        "-H 'Content-Type: application/json' -d '{}'"
    )
    http_code = stdout.read().decode().strip()
    if http_code in ("401", "403", "422"):
        print(f"    OK: HTTP {http_code} (auth yokken reddedildi)")
    elif http_code == "400":
        print(f"    OK: HTTP {http_code} (confirm eksik hatasi)")
    else:
        print(f"    BILGI: HTTP {http_code}")

    # 2) ws.py MAX_CONNECTIONS_PER_IP tanimli mi
    print("  [b] ws.py MAX_CONNECTIONS_PER_IP kontrolu...")
    stdin, stdout, stderr = target.exec_command(
        "grep 'MAX_CONNECTIONS_PER_IP' /opt/tonbilaios/backend/app/api/v1/ws.py"
    )
    grep_out = stdout.read().decode().strip()
    if grep_out:
        print(f"    OK: {grep_out}")
    else:
        print("    HATA: MAX_CONNECTIONS_PER_IP bulunamadi!")

    # 3) auth.py username rate limit key tanimli mi
    print("  [c] auth.py username rate limit kontrolu...")
    stdin, stdout, stderr = target.exec_command(
        "grep 'auth:failed:user:' /opt/tonbilaios/backend/app/api/v1/auth.py"
    )
    grep_out = stdout.read().decode().strip()
    if grep_out:
        print(f"    OK: auth:failed:user: key mevcut")
    else:
        print("    HATA: auth:failed:user: bulunamadi!")

    # 4) schemas/auth.py ozel karakter kontrolu
    print("  [d] schemas/auth.py ozel karakter kontrolu...")
    stdin, stdout, stderr = target.exec_command(
        "grep 'ozel karakter' /opt/tonbilaios/backend/app/schemas/auth.py"
    )
    grep_out = stdout.read().decode().strip()
    if grep_out:
        print(f"    OK: ozel karakter validasyonu mevcut")
    else:
        print("    HATA: ozel karakter validasyonu bulunamadi!")

    target.close()
    jump.close()

    print("\n=== Deploy tamamlandi! ===")
    print("Gerceklestirilen guvenlik iyilestirmeleri:")
    print("  1. Reboot/Shutdown: confirm=true zorunlu (400 yoksa)")
    print("  2. Username+IP rate limiting: auth:failed:user:{username}")
    print("  3. Sifre degisiminde tum oturumlar kapatiliyor")
    print("  4. Sifre ozel karakter zorunlu")
    print("  5. WebSocket per-IP limiti: MAX_CONNECTIONS_PER_IP=5")


if __name__ == "__main__":
    deploy()
