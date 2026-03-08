"""Deploy quick-7 changes to Pi: redis_client, bandwidth_monitor, flow_tracker + eth1 ring buffer."""
import paramiko
import os
import time

# SSH jump host -> Pi tunnel
jump_client = paramiko.SSHClient()
jump_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
jump_client.connect("pi.tonbil.com", port=2323, username="admin", password="benbuyum9087")
jump_transport = jump_client.get_transport()
channel = jump_transport.open_channel("direct-tcpip", ("192.168.1.2", 22), ("127.0.0.1", 0))
target_client = paramiko.SSHClient()
target_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
target_client.connect("192.168.1.2", username="admin", password="benbuyum9087", sock=channel)


def run_cmd(cmd, show=True):
    """Run SSH command and return output."""
    stdin, stdout, stderr = target_client.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if show:
        if out:
            print(f"  stdout: {out}")
        if err:
            print(f"  stderr: {err}")
    return exit_code, out, err


# 1. SFTP file transfer
sftp = target_client.open_sftp()
files_to_deploy = [
    ("backend/app/db/redis_client.py", "/opt/tonbilaios/backend/app/db/redis_client.py"),
    ("backend/app/workers/bandwidth_monitor.py", "/opt/tonbilaios/backend/app/workers/bandwidth_monitor.py"),
    ("backend/app/workers/flow_tracker.py", "/opt/tonbilaios/backend/app/workers/flow_tracker.py"),
]

cwd = os.getcwd()
for local_rel, remote_path in files_to_deploy:
    local_path = os.path.join(cwd, local_rel)
    tmp_path = "/tmp/" + os.path.basename(local_path)
    print(f"Uploading {local_rel} -> {tmp_path}")
    sftp.put(local_path, tmp_path)
    code, out, err = run_cmd(f"sudo cp {tmp_path} {remote_path}", show=False)
    if code != 0:
        print(f"  ERROR: {err}")
    else:
        print(f"  OK -> {remote_path}")
    run_cmd(f"rm -f {tmp_path}", show=False)

sftp.close()
print("\n=== Files deployed ===\n")

# 2. eth1 ring buffer
print("--- eth1 ring buffer ---")
run_cmd("sudo ethtool -G eth1 rx 4096 2>&1 || true")

print("\nVerify:")
run_cmd("sudo ethtool -g eth1 2>&1 | head -12")

# 3. RPS check
print("\n--- RPS check ---")
for iface in ["eth0", "eth1"]:
    code, val, _ = run_cmd(f"cat /sys/class/net/{iface}/queues/rx-0/rps_cpus 2>&1", show=False)
    print(f"  {iface} rps_cpus = {val}")
    if val not in ("f", "0f", "00000000f", "0000000f"):
        print(f"  Setting {iface} rps_cpus to f...")
        run_cmd(f"echo f | sudo tee /sys/class/net/{iface}/queues/rx-0/rps_cpus")

# 4. Make eth1 ring buffer persistent
print("\n--- Making eth1 ring buffer persistent ---")
code, rc_content, _ = run_cmd("cat /etc/rc.local 2>&1", show=False)
if "ethtool -G eth1" in rc_content:
    print("  Already in rc.local, skipping")
else:
    if "exit 0" in rc_content:
        cmd = r"sudo sed -i '/^exit 0$/i # eth1 LAN ring buffer\nethtool -G eth1 rx 4096' /etc/rc.local"
        run_cmd(cmd)
        print("  Added before 'exit 0'")
    else:
        run_cmd('echo -e "\n# eth1 LAN ring buffer\nethtool -G eth1 rx 4096" | sudo tee -a /etc/rc.local')
        print("  Appended to rc.local")

# Verify rc.local
print("  rc.local eth1 lines:")
run_cmd("grep -n eth1 /etc/rc.local 2>&1 || echo 'not found'")

# 5. Restart backend
print("\n--- Restarting backend ---")
code, _, _ = run_cmd("sudo systemctl restart tonbilaios-backend")
print(f"  Restart: {'OK' if code == 0 else 'FAILED'}")

time.sleep(4)

code, status, _ = run_cmd("sudo systemctl is-active tonbilaios-backend", show=False)
print(f"  Backend status: {status}")

# 6. Verify Redis connections
print("\n--- Redis connection check ---")
run_cmd("redis-cli -a TonbilAiRedis2026 CLIENT LIST 2>/dev/null | wc -l")

# 7. Final verification
print("\n--- Final eth1 ring buffer ---")
run_cmd("sudo ethtool -g eth1 2>&1 | grep -A2 'Current'")

print("\n=== Deploy complete ===")

target_client.close()
jump_client.close()
