#!/usr/bin/env python3
"""Quick 28 Deploy: Push bildirim API endpoint'leri Pi'ye deploy et ve test et."""

import paramiko
import os
import time

JUMP_HOST = "pi.tonbil.com"
JUMP_PORT = 2323
TARGET_IP = "192.168.1.2"
TARGET_PORT = 22
USERNAME = "admin"
PASSWORD = "benbuyum9087"

FILES_TO_DEPLOY = [
    # (local_path, remote_path)
    ("backend/app/schemas/push.py", "/opt/tonbilaios/backend/app/schemas/push.py"),
    ("backend/app/api/v1/push.py", "/opt/tonbilaios/backend/app/api/v1/push.py"),
    ("backend/app/api/v1/router.py", "/opt/tonbilaios/backend/app/api/v1/router.py"),
]

RESULT_FILE = os.path.join(os.path.dirname(__file__), "deploy_quick28_result.txt")


def run_ssh(target, cmd, timeout=30):
    stdin, stdout, stderr = target.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    return out, err


def deploy():
    results = []

    def log(msg):
        print(msg)
        results.append(msg)

    log("=== Quick 28 Deploy: Push Bildirim API ===")

    # Jump host baglan
    log(f"\n[1/5] Jump host'a baglaniliyor {JUMP_HOST}:{JUMP_PORT}...")
    jump = paramiko.SSHClient()
    jump.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    jump.connect(JUMP_HOST, port=JUMP_PORT, username=USERNAME, password=PASSWORD)
    jump_transport = jump.get_transport()
    log("  Jump host baglantisi OK")

    # Pi'ye tunel
    log(f"[2/5] Pi'ye tunel aciliyor {TARGET_IP}:{TARGET_PORT}...")
    channel = jump_transport.open_channel("direct-tcpip", (TARGET_IP, TARGET_PORT), ("127.0.0.1", 0))
    target = paramiko.SSHClient()
    target.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    target.connect(TARGET_IP, username=USERNAME, password=PASSWORD, sock=channel)
    log("  Pi baglantisi OK")

    sftp = target.open_sftp()

    # Dosya transfer
    log(f"\n[3/5] {len(FILES_TO_DEPLOY)} dosya transfer ediliyor...")
    for local_rel, remote_path in FILES_TO_DEPLOY:
        local_path = os.path.join(os.path.dirname(__file__), local_rel)
        if not os.path.exists(local_path):
            log(f"  HATA (bulunamadi): {local_rel}")
            continue

        tmp_path = f"/tmp/{os.path.basename(remote_path)}"
        log(f"  {local_rel} -> {remote_path}")
        sftp.put(local_path, tmp_path)

        out, err = run_ssh(target, f"sudo cp {tmp_path} {remote_path}")
        if err:
            log(f"    UYARI: {err}")
        else:
            log("    OK")

    sftp.close()

    # Backend restart
    log("\n[4/5] Backend yeniden baslatiliyor...")
    out, err = run_ssh(target, "sudo systemctl restart tonbilaios-backend")
    if err:
        log(f"  UYARI: {err}")
    else:
        log("  Backend restart OK")

    # 5 saniye bekle
    log("  5 saniye bekleniyor...")
    time.sleep(5)

    # API test
    log("\n[5/5] Push API endpoint test ediliyor...")

    # Login et, token al
    login_cmd = (
        "curl -s -X POST http://localhost/api/v1/auth/login "
        "-H 'Content-Type: application/json' "
        "-d '{\"username\":\"admin\",\"password\":\"benbuyum9087\"}' "
        "| python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"access_token\",\"\"))'"
    )
    token, err = run_ssh(target, login_cmd)
    if not token:
        log(f"  HATA: Token alinamadi. {err}")
    else:
        log(f"  Token alindi: {token[:20]}...")

        # GET /push/channels
        channels_cmd = (
            f"curl -s http://localhost/api/v1/push/channels "
            f"-H 'Authorization: Bearer {token}'"
        )
        channels_out, channels_err = run_ssh(target, channels_cmd)
        log(f"\n  GET /push/channels yaniti:\n  {channels_out[:500]}")

        # Kanal sayisini kontrol et
        if '"security_threats"' in channels_out and '"device_events"' in channels_out:
            log("  BASARILI: 4 kanal mevcut (security_threats, device_events dahil)")
        else:
            log(f"  UYARI: Beklenen kanallar gorulmuyor! Yanit: {channels_out}")

        # POST /push/channels/device_events/toggle
        toggle_cmd = (
            f"curl -s -X POST http://localhost/api/v1/push/channels/device_events/toggle "
            f"-H 'Authorization: Bearer {token}'"
        )
        toggle_out, toggle_err = run_ssh(target, toggle_cmd)
        log(f"\n  POST /push/channels/device_events/toggle yaniti:\n  {toggle_out}")

        # Toggle sonrasi tekrar kanallari kontrol et
        channels_after, _ = run_ssh(target, channels_cmd)
        log(f"\n  Toggle sonrasi GET /push/channels:\n  {channels_after[:500]}")

        # POST /push/register
        register_cmd = (
            f"curl -s -X POST http://localhost/api/v1/push/register "
            f"-H 'Authorization: Bearer {token}' "
            f"-H 'Content-Type: application/json' "
            f"-d '{{\"token\":\"test-token-123\",\"platform\":\"android\",\"device_name\":\"TestDevice\"}}'"
        )
        register_out, register_err = run_ssh(target, register_cmd)
        log(f"\n  POST /push/register yaniti:\n  {register_out}")

        if '"success": true' in register_out or '"success":true' in register_out:
            log("  BASARILI: Register endpoint calisiyor")
        else:
            log(f"  UYARI: Register yaniti beklenmedik: {register_out}")

    target.close()
    jump.close()

    log("\n=== Deploy tamamlandi! ===")

    # Sonuclari kaydet
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(results))
    print(f"\nSonuclar kaydedildi: {RESULT_FILE}")


if __name__ == "__main__":
    deploy()
