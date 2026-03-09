"""
Deploy Quick-13: ip_reputation.py auto_block_ip entegrasyonu Pi'ye yukle.
SSH: dogrudan 192.168.1.2:22 (jump yok)
"""
import time
import paramiko

JUMP_HOST = "pi.tonbil.com"
JUMP_PORT = 2323
PI_HOST   = "192.168.1.2"
PI_PORT   = 22
USER      = "admin"
PASS      = "benbuyum9087"

LOCAL_FILE  = "backend/app/workers/ip_reputation.py"
REMOTE_TMP  = "/tmp/ip_reputation.py"
REMOTE_DEST = "/opt/tonbilaios/backend/app/workers/ip_reputation.py"

def run_cmd(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    return out, err

def main():
    print("=== Quick-13 Deploy: ip_reputation.py ===")

    # ProxyJump tunnel
    print(f"[1] Jump host baglaniliyor: {JUMP_HOST}:{JUMP_PORT}")
    jump = paramiko.SSHClient()
    jump.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    jump.connect(JUMP_HOST, port=JUMP_PORT, username=USER, password=PASS, timeout=15)

    print(f"[2] Pi'ye tunnel aciliyor: {PI_HOST}:{PI_PORT}")
    jump_transport = jump.get_transport()
    channel = jump_transport.open_channel(
        "direct-tcpip", (PI_HOST, PI_PORT), ("127.0.0.1", 0)
    )

    pi = paramiko.SSHClient()
    pi.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pi.connect(PI_HOST, port=PI_PORT, username=USER, password=PASS, sock=channel, timeout=15)
    print("    Pi baglantisi kuruldu.")

    # SFTP upload
    print(f"[3] Dosya yukleniyor: {LOCAL_FILE} -> {REMOTE_TMP}")
    sftp = pi.open_sftp()
    sftp.put(LOCAL_FILE, REMOTE_TMP)
    sftp.close()
    print("    Yukleme tamamlandi.")

    # sudo cp
    print(f"[4] Hedef dizine kopyalaniyor: {REMOTE_DEST}")
    out, err = run_cmd(pi, f"echo '{PASS}' | sudo -S cp {REMOTE_TMP} {REMOTE_DEST}")
    if err and "password" not in err.lower():
        print(f"    UYARI: {err}")
    else:
        print("    Kopyalama tamam.")

    # Backend restart
    print("[5] Backend yeniden baslatiliyor...")
    out, err = run_cmd(pi, f"echo '{PASS}' | sudo -S systemctl restart tonbilaios-backend")
    print("    Restart komutu gonderildi.")

    # Bekle
    print("[6] 5 saniye bekleniyor...")
    time.sleep(5)

    # Servis durumu
    out, err = run_cmd(pi, "sudo systemctl is-active tonbilaios-backend")
    status = out.strip()
    print(f"[7] Servis durumu: {status}")

    # Journalctl
    print("[8] Son 30 log satiri:")
    out, err = run_cmd(pi, "sudo journalctl -u tonbilaios-backend --since '40 seconds ago' --no-pager -n 30")
    print(out)

    pi.close()
    jump.close()

    if status == "active":
        print("\n=== DEPLOY BASARILI: Backend aktif ===")
    else:
        print(f"\n=== DIKKAT: Backend durumu '{status}' ===")

if __name__ == "__main__":
    main()
