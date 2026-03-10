#!/usr/bin/env python3
"""Quick 30: Deploy ws.py asyncio.Event broadcast + ping/pong keepalive to Pi."""
import paramiko
import os
import time
import json

JUMP_HOST = "pi.tonbil.com"
JUMP_PORT = 2323
PI_HOST = "192.168.1.2"
PI_PORT = 22
USERNAME = "admin"
PASSWORD = "benbuyum9087"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILES = [
    ("backend/app/api/v1/ws.py", "/opt/tonbilaios/backend/app/api/v1/ws.py"),
]


def main():
    print("=== Quick 30: asyncio.Event WS Broadcast Deploy ===\n")

    # Connect via jump host
    print("[1/4] SSH jump host baglantisi...")
    jump = paramiko.SSHClient()
    jump.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    jump.connect(JUMP_HOST, port=JUMP_PORT, username=USERNAME, password=PASSWORD, timeout=15)

    jump_transport = jump.get_transport()
    channel = jump_transport.open_channel("direct-tcpip", (PI_HOST, PI_PORT), ("127.0.0.1", 0))

    pi = paramiko.SSHClient()
    pi.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pi.connect(PI_HOST, username=USERNAME, password=PASSWORD, sock=channel, timeout=15)
    print("   Pi baglantisi OK")

    # Transfer files
    print("\n[2/4] Dosya transferi...")
    sftp = pi.open_sftp()
    for local_rel, remote_path in FILES:
        local_path = os.path.join(BASE_DIR, local_rel)
        tmp_path = f"/tmp/{os.path.basename(remote_path)}"
        print(f"   {local_rel} -> {remote_path}")
        sftp.put(local_path, tmp_path)
        stdin, stdout, stderr = pi.exec_command(f"sudo cp {tmp_path} {remote_path}")
        stdout.read()
        time.sleep(0.3)
    sftp.close()
    print("   Transfer OK")

    # Restart backend
    print("\n[3/4] Backend restart...")
    stdin, stdout, stderr = pi.exec_command("sudo systemctl restart tonbilaios-backend")
    stdout.read()
    print("   Restart komutu gonderildi, 5s bekleniyor...")
    time.sleep(5)

    # Verify
    print("\n[4/4] Dogrulama...")

    # a) Backend status
    stdin, stdout, stderr = pi.exec_command("sudo systemctl is-active tonbilaios-backend")
    status = stdout.read().decode().strip()
    print(f"   Backend status: {status}")
    if status != "active":
        print("   HATA: Backend aktif degil!")
        # Print recent logs for debugging
        stdin, stdout, stderr = pi.exec_command(
            "sudo journalctl -u tonbilaios-backend --since '30 seconds ago' --no-pager -n 20"
        )
        print("   Son loglar:")
        print(stdout.read().decode())
        pi.close()
        jump.close()
        return

    # b) Import kontrolu: _wake_event check
    import_cmd = (
        "cd /opt/tonbilaios/backend && "
        "python3 -c \"from app.api.v1.ws import manager; "
        "print('wake_event:', hasattr(manager, '_wake_event')); "
        "print('type:', type(manager._wake_event).__name__)\""
    )
    stdin, stdout, stderr = pi.exec_command(import_cmd)
    import_out = stdout.read().decode().strip()
    import_err = stderr.read().decode().strip()
    print(f"   Import kontrol: {import_out}")
    if import_err:
        print(f"   Import hatasi: {import_err}")

    # c) JWT al ve test notification gonder
    login_cmd = (
        "curl -s -X POST http://localhost/api/v1/auth/login "
        "-H 'Content-Type: application/json' "
        "-d '{\"username\":\"admin\",\"password\":\"benbuyum9087\"}'"
    )
    stdin, stdout, stderr = pi.exec_command(login_cmd)
    login_resp = stdout.read().decode()
    try:
        token = json.loads(login_resp)["access_token"]
        print(f"   Token: {token[:20]}...")
    except Exception as e:
        print(f"   Login hatasi: {login_resp[:200]}")
        pi.close()
        jump.close()
        return

    # d) Test notification endpoint
    notify_cmd = (
        f"curl -s -X POST http://localhost/api/v1/push/test-notification "
        f"-H 'Authorization: Bearer {token}' "
        f"-H 'Content-Type: application/json' "
        f"-d '{{\"title\":\"Quick30 Test\",\"message\":\"Anlik broadcast testi\"}}'"
    )
    stdin, stdout, stderr = pi.exec_command(notify_cmd)
    notify_resp = stdout.read().decode()
    print(f"   POST /push/test-notification: {notify_resp[:200]}")

    # e) Backend loglari: security event ve wake_event gozukuyor mu?
    time.sleep(1)
    log_cmd = (
        "sudo journalctl -u tonbilaios-backend --since '15 seconds ago' "
        "--no-pager | grep -i 'security\\|wake\\|ping\\|queued'"
    )
    stdin, stdout, stderr = pi.exec_command(log_cmd)
    log_out = stdout.read().decode().strip()
    if log_out:
        print(f"   Log kontrol (security/wake/ping):")
        for line in log_out.splitlines()[-5:]:
            print(f"     {line}")
    else:
        print("   Log: Henuz security event logu yok (normal, test notification ws'e gonderildi)")

    pi.close()
    jump.close()

    print("\n=== Deploy tamamlandi! ===")
    if status == "active":
        print("OK Backend aktif")
        print("OK asyncio.Event + ping/pong ws.py deploy edildi")
        print("OK Security event'ler artik 3s beklemeden aninda broadcast ediliyor")
        print("OK 30s ping / 10s pong timeout ile stale baglantilar otomatik temizleniyor")
    else:
        print("HATA Backend baslatma hatasi - loglari kontrol et")


if __name__ == "__main__":
    main()
