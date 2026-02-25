"""Frontend dist/ klasörünü Pi'ya deploy et + kaynak dosyaları güncelle."""
import paramiko
import base64
import os
import sys

HOST = "pi.tonbil.com"
PORT = 2323
USER = "admin"
PASS = "benbuyum9087"

DIST_LOCAL = r"E:\Nextcloud-Yeni\TonbilAiFirewallV41\frontend\dist"
DIST_REMOTE = "/opt/tonbilaios/frontend/dist"

SRC_LOCAL = r"E:\Nextcloud-Yeni\TonbilAiFirewallV41\frontend\src"
SRC_REMOTE = "/opt/tonbilaios/frontend/src"

CHUNK_SIZE = 800


def run_cmd(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    rc = stdout.channel.recv_exit_status()
    return rc, out, err


def transfer_file(ssh, local_path, remote_path, binary=False):
    """Base64 chunked transfer ile dosya gonder."""
    if binary:
        with open(local_path, "rb") as f:
            content_bytes = f.read()
    else:
        with open(local_path, "r", encoding="utf-8") as f:
            content_bytes = f.read().encode("utf-8")

    b64 = base64.b64encode(content_bytes).decode("ascii")
    tmp = f"/tmp/deploy_{os.path.basename(remote_path)}.b64"

    # Hedef klasoru olustur
    remote_dir = os.path.dirname(remote_path)
    run_cmd(ssh, f"sudo mkdir -p {remote_dir}")

    # Temp dosyayi temizle
    run_cmd(ssh, f"rm -f {tmp}")

    # Base64'u parca parca yaz
    for i in range(0, len(b64), CHUNK_SIZE):
        chunk = b64[i:i + CHUNK_SIZE]
        run_cmd(ssh, f"echo -n '{chunk}' >> {tmp}")

    # Decode et ve yerlestir
    rc, out, err = run_cmd(ssh, f"base64 -d {tmp} | sudo tee {remote_path} > /dev/null")
    if rc != 0:
        print(f"  HATA: {err}")
        return False

    # Temizle
    run_cmd(ssh, f"rm -f {tmp}")

    # Dogrula
    rc, out, _ = run_cmd(ssh, f"wc -c < {remote_path}")
    remote_size = out.strip()
    local_size = len(content_bytes)
    ok = str(local_size) == remote_size
    print(f"  {'OK' if ok else 'BOYUT FARKLI'} ({local_size} -> {remote_size})")
    return ok


def main():
    print(f"{HOST}:{PORT} adresine baglaniliyor...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=15)
    print("Baglandi!\n")

    # Hedef klasorleri olustur
    print("Hedef klasorler olusturuluyor...")
    run_cmd(ssh, f"sudo mkdir -p {DIST_REMOTE}/assets")
    run_cmd(ssh, f"sudo mkdir -p {SRC_REMOTE}/components/dashboard")
    run_cmd(ssh, f"sudo mkdir -p {SRC_REMOTE}/config")
    run_cmd(ssh, f"sudo mkdir -p {SRC_REMOTE}/hooks")
    run_cmd(ssh, f"sudo mkdir -p {SRC_REMOTE}/pages")
    run_cmd(ssh, f"sudo mkdir -p {SRC_REMOTE}/types")

    # 1) dist/ dosyalarini transfer et
    print("\n=== DIST DOSYALARI ===")
    dist_files = []
    for root, dirs, files in os.walk(DIST_LOCAL):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, DIST_LOCAL).replace(os.sep, "/")
            dist_files.append((full, f"{DIST_REMOTE}/{rel}"))

    all_ok = True
    for local_path, remote_path in dist_files:
        print(f"Transfer: {os.path.relpath(local_path, DIST_LOCAL)}")
        is_binary = local_path.endswith((".js", ".css", ".html", ".png", ".jpg", ".ico", ".svg", ".woff", ".woff2"))
        if not transfer_file(ssh, local_path, remote_path, binary=True):
            all_ok = False

    # 2) Degisen kaynak dosyalarini transfer et
    print("\n=== KAYNAK DOSYALARI ===")
    src_files = [
        "components/dashboard/DashboardGrid.tsx",
        "components/dashboard/WidgetWrapper.tsx",
        "components/dashboard/WidgetToggleMenu.tsx",
        "config/widgetRegistry.tsx",
        "config/systemMonitorWidgetRegistry.tsx",
        "types/dashboard-grid.ts",
        "hooks/useDashboardLayout.ts",
        "hooks/useSystemMonitorLayout.ts",
        "pages/SystemMonitorPage.tsx",
    ]
    for rel in src_files:
        local_path = os.path.join(SRC_LOCAL, rel.replace("/", os.sep))
        remote_path = f"{SRC_REMOTE}/{rel}"
        print(f"Transfer: {rel}")
        if os.path.exists(local_path):
            if not transfer_file(ssh, local_path, remote_path):
                all_ok = False
        else:
            print(f"  ATLA - dosya bulunamadi")

    # Izinleri duzelt
    print("\nDosya izinleri duzeltiliyor...")
    run_cmd(ssh, f"sudo chown -R www-data:www-data {DIST_REMOTE}")
    run_cmd(ssh, f"sudo chmod -R 755 {DIST_REMOTE}")

    if all_ok:
        print("\nDeploy basarili! Tum dosyalar transfer edildi.")
    else:
        print("\nBazi dosyalarda sorun olustu, kontrol edin.")

    ssh.close()
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
