#!/usr/bin/env python3
"""Deploy Security Settings feature to Raspberry Pi via SSH ProxyJump."""

import paramiko
import time
import os
import sys

JUMP_HOST = "pi.tonbil.com"
JUMP_PORT = 2323
TARGET_HOST = "192.168.1.2"
TARGET_PORT = 22
USERNAME = "admin"
PASSWORD = "benbuyum9087"

LOCAL_BASE = r"E:\Nextcloud-Yeni\TonbilAiFirevallv5"

# (local_relative_path, remote_path)
FILES = [
    # Backend NEW
    ("backend/app/models/security_config.py", "/opt/tonbilaios/backend/app/models/security_config.py"),
    ("backend/app/schemas/security_config.py", "/opt/tonbilaios/backend/app/schemas/security_config.py"),
    ("backend/app/api/v1/security_settings.py", "/opt/tonbilaios/backend/app/api/v1/security_settings.py"),
    # Backend MODIFIED
    ("backend/app/models/__init__.py", "/opt/tonbilaios/backend/app/models/__init__.py"),
    ("backend/app/api/v1/router.py", "/opt/tonbilaios/backend/app/api/v1/router.py"),
    ("backend/app/main.py", "/opt/tonbilaios/backend/app/main.py"),
    ("backend/app/workers/threat_analyzer.py", "/opt/tonbilaios/backend/app/workers/threat_analyzer.py"),
    ("backend/app/workers/dns_proxy.py", "/opt/tonbilaios/backend/app/workers/dns_proxy.py"),
    ("backend/app/services/ddos_service.py", "/opt/tonbilaios/backend/app/services/ddos_service.py"),
    ("backend/app/services/dns_fingerprint.py", "/opt/tonbilaios/backend/app/services/dns_fingerprint.py"),
    # Frontend NEW
    ("frontend/src/services/securityApi.ts", "/opt/tonbilaios/frontend/src/services/securityApi.ts"),
    ("frontend/src/pages/SecuritySettingsPage.tsx", "/opt/tonbilaios/frontend/src/pages/SecuritySettingsPage.tsx"),
    # Frontend MODIFIED
    ("frontend/src/types/index.ts", "/opt/tonbilaios/frontend/src/types/index.ts"),
    ("frontend/src/App.tsx", "/opt/tonbilaios/frontend/src/App.tsx"),
    ("frontend/src/components/layout/Sidebar.tsx", "/opt/tonbilaios/frontend/src/components/layout/Sidebar.tsx"),
]


def run_cmd(client, cmd, timeout=120):
    """Run command and return (exit_code, stdout, stderr)."""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return exit_code, out, err


def main():
    print("=" * 60)
    print("  Security Settings Deploy Script")
    print("=" * 60)

    # --- Verify local files ---
    print("\n[1/6] Yerel dosyalar kontrol ediliyor...")
    missing = []
    for local_rel, _ in FILES:
        full = os.path.join(LOCAL_BASE, local_rel)
        if not os.path.isfile(full):
            missing.append(full)
    if missing:
        print("HATA: Eksik dosyalar:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)
    print(f"  OK - {len(FILES)} dosya mevcut.")

    # --- Connect via ProxyJump ---
    print("\n[2/6] SSH baglantisi kuruluyor (ProxyJump)...")
    jump = paramiko.SSHClient()
    jump.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    jump.connect(JUMP_HOST, port=JUMP_PORT, username=USERNAME, password=PASSWORD)
    print(f"  Jump host baglandı: {JUMP_HOST}:{JUMP_PORT}")

    jump_transport = jump.get_transport()
    channel = jump_transport.open_channel("direct-tcpip", (TARGET_HOST, TARGET_PORT), ("127.0.0.1", 0))

    target = paramiko.SSHClient()
    target.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    target.connect(TARGET_HOST, username=USERNAME, password=PASSWORD, sock=channel)
    print(f"  Hedef baglandı: {TARGET_HOST}:{TARGET_PORT}")

    # --- Backup ---
    print("\n[3/6] Yedek alınıyor...")
    timestamp_cmd = "date +%Y%m%d-%H%M"
    _, ts, _ = run_cmd(target, timestamp_cmd)
    backup_dir = f"/opt/tonbilaios/backup-security-{ts}"

    backup_cmds = [
        f"sudo mkdir -p {backup_dir}/backend-app",
        f"sudo mkdir -p {backup_dir}/frontend-src",
        f"sudo cp -r /opt/tonbilaios/backend/app/* {backup_dir}/backend-app/",
        f"sudo cp -r /opt/tonbilaios/frontend/src/* {backup_dir}/frontend-src/",
    ]
    for cmd in backup_cmds:
        code, out, err = run_cmd(target, cmd)
        if code != 0:
            print(f"  UYARI: {cmd} -> {err}")
    print(f"  Yedek: {backup_dir}")

    # --- Upload files ---
    print("\n[4/6] Dosyalar yukleniyor (SFTP)...")
    sftp = target.open_sftp()

    for i, (local_rel, remote_path) in enumerate(FILES, 1):
        local_full = os.path.join(LOCAL_BASE, local_rel)
        filename = os.path.basename(local_rel)
        tmp_path = f"/tmp/deploy_security_{filename}"

        # Ensure remote directory exists
        remote_dir = os.path.dirname(remote_path).replace("\\", "/")
        run_cmd(target, f"sudo mkdir -p {remote_dir}")

        # Upload to /tmp
        sftp.put(local_full, tmp_path)

        # Copy to final location with sudo
        code, out, err = run_cmd(target, f"sudo cp {tmp_path} {remote_path}")
        if code != 0:
            print(f"  HATA [{i}/{len(FILES)}]: {remote_path} -> {err}")
        else:
            print(f"  [{i:2d}/{len(FILES)}] OK: {remote_path}")

        # Cleanup tmp
        run_cmd(target, f"rm -f {tmp_path}")

    sftp.close()

    # --- Frontend build ---
    print("\n[5/6] Frontend build ediliyor...")
    code, out, err = run_cmd(target, "cd /opt/tonbilaios/frontend && sudo npm run build", timeout=180)
    if code != 0:
        print(f"  HATA: Frontend build basarisiz!")
        print(f"  STDERR: {err[-500:] if len(err) > 500 else err}")
        print(f"  STDOUT: {out[-500:] if len(out) > 500 else out}")
    else:
        # Show last few lines of build output
        lines = out.split("\n")
        for line in lines[-5:]:
            if line.strip():
                safe_line = line.strip().encode("ascii", errors="replace").decode("ascii")
                print(f"  {safe_line}")
        print("  Frontend build OK.")

    # --- Restart backend ---
    print("\n[6/6] Backend yeniden baslatılıyor...")
    code, out, err = run_cmd(target, "sudo systemctl restart tonbilaios-backend")
    if code != 0:
        print(f"  HATA: restart basarisiz -> {err}")

    print("  5 saniye bekleniyor...")
    time.sleep(5)

    code, out, err = run_cmd(target, "sudo systemctl is-active tonbilaios-backend")
    status = out.strip()
    if status == "active":
        print(f"  Backend durumu: {status} [OK]")
    else:
        print(f"  Backend durumu: {status} [HATA]")
        # Get journal logs for debugging
        _, journal, _ = run_cmd(target, "sudo journalctl -u tonbilaios-backend --no-pager -n 20")
        print(f"  Son loglar:\n{journal}")

    # --- Cleanup ---
    target.close()
    channel.close()
    jump.close()

    print("\n" + "=" * 60)
    if status == "active":
        print("  DEPLOY BASARILI!")
    else:
        print("  DEPLOY TAMAMLANDI (backend durumunu kontrol edin)")
    print(f"  Yedek: {backup_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
