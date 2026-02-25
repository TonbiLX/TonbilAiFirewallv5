#!/usr/bin/env bash
# ============================================================
#  TonbilAiFirewall - Raspberry Pi Tek Komut Kurulum
# ============================================================
#  Kullanim:
#    sudo bash setup.sh
#
#  Bu script asagidakileri otomatik kurar ve yapilandirir:
#    - Sistem paketleri (Python, Node.js, MariaDB, Redis, Nginx...)
#    - Python sanal ortam + bagimliliklari
#    - Frontend bagimliliklari + build
#    - MariaDB veritabani + kullanici
#    - systemd servis dosyasi
#    - Nginx reverse proxy
# ============================================================

set -euo pipefail

# --- Renkler ---
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
NC='\033[0m'

INSTALL_DIR="/opt/tonbilaios"
DB_NAME="tonbilaios"
DB_USER="tonbilai"
DB_PASS=""
SECRET_KEY=""

banner() {
    echo -e "${CYAN}"
    echo "  ╔══════════════════════════════════════════════════╗"
    echo "  ║          TonbilAiFirewall Kurulum                ║"
    echo "  ║     AI-Powered Router Management System          ║"
    echo "  ╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info()    { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
log_error()   { echo -e "${RED}[✗]${NC} $1"; }
log_step()    { echo -e "\n${MAGENTA}━━━ $1 ━━━${NC}"; }

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Bu script root olarak calistirilmalidir: sudo bash setup.sh"
        exit 1
    fi
}

check_arch() {
    ARCH=$(uname -m)
    if [[ "$ARCH" != "aarch64" && "$ARCH" != "armv7l" && "$ARCH" != "x86_64" ]]; then
        log_warn "Desteklenmeyen mimari: $ARCH (devam ediliyor...)"
    fi
    log_info "Mimari: $ARCH, OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"')"
}

# ============================================================
# 1. SISTEM PAKETLERI
# ============================================================
install_system_packages() {
    log_step "1/8 Sistem Paketleri Kuruluyor"

    apt-get update -qq

    # Temel paketler
    PACKAGES=(
        python3 python3-venv python3-pip python3-dev
        mariadb-server mariadb-client libmariadb-dev
        redis-server
        nginx
        nftables
        dnsmasq
        wireguard wireguard-tools
        curl wget git sshpass
        build-essential libffi-dev libssl-dev
    )

    apt-get install -y -qq "${PACKAGES[@]}" 2>/dev/null
    log_info "Sistem paketleri kuruldu"

    # Node.js (eger yoksa veya eski ise)
    if ! command -v node &>/dev/null || [[ $(node -v | sed 's/v//' | cut -d. -f1) -lt 18 ]]; then
        log_info "Node.js 20.x kuruluyor..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >/dev/null 2>&1
        apt-get install -y -qq nodejs 2>/dev/null
    fi
    log_info "Node.js $(node -v), npm $(npm -v)"
    log_info "Python $(python3 --version | cut -d' ' -f2)"
}

# ============================================================
# 2. DIZIN YAPISI
# ============================================================
setup_directories() {
    log_step "2/8 Dizin Yapisi Olusturuluyor"

    # Script'in calistigi dizinden kaynak dosyalarin konumunu belirle
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
        mkdir -p "$INSTALL_DIR"
        log_info "Dosyalar $INSTALL_DIR konumuna kopyalaniyor..."
        cp -r "$SCRIPT_DIR/backend" "$INSTALL_DIR/" 2>/dev/null || true
        cp -r "$SCRIPT_DIR/frontend" "$INSTALL_DIR/" 2>/dev/null || true
        cp -r "$SCRIPT_DIR/config" "$INSTALL_DIR/" 2>/dev/null || true
        cp "$SCRIPT_DIR/.env.example" "$INSTALL_DIR/" 2>/dev/null || true
    fi

    # Log dizini
    mkdir -p "$INSTALL_DIR/backend/logs/signed"

    log_info "Dizin yapisi hazir: $INSTALL_DIR"
}

# ============================================================
# 3. MARIADB VERITABANI
# ============================================================
setup_database() {
    log_step "3/8 MariaDB Veritabani Yapilandiriliyor"

    systemctl enable mariadb --now 2>/dev/null

    # Veritabani sifresi
    if [ -z "$DB_PASS" ]; then
        DB_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
    fi

    # Veritabani ve kullanici olustur
    mysql -u root <<EOF 2>/dev/null || true
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
EOF

    log_info "Veritabani: ${DB_NAME}, Kullanici: ${DB_USER}"
}

# ============================================================
# 4. REDIS
# ============================================================
setup_redis() {
    log_step "4/8 Redis Yapilandiriliyor"

    systemctl enable redis-server --now 2>/dev/null

    if redis-cli ping 2>/dev/null | grep -q PONG; then
        log_info "Redis aktif ve calisiyor"
    else
        log_warn "Redis baslatilamadi, loglari kontrol edin"
    fi
}

# ============================================================
# 5. PYTHON BACKEND
# ============================================================
setup_backend() {
    log_step "5/8 Python Backend Kuruluyor"

    cd "$INSTALL_DIR/backend"

    # Sanal ortam
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_info "Python sanal ortam olusturuldu"
    fi

    # Bagimliliklari kur
    ./venv/bin/pip install --upgrade pip -q
    ./venv/bin/pip install -r requirements.txt -q
    log_info "Python bagimliliklari kuruldu"

    # .env dosyasi olustur
    if [ ! -f ".env" ]; then
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
        cat > .env <<ENVEOF
DATABASE_URL=mysql+aiomysql://${DB_USER}:${DB_PASS}@localhost:3306/${DB_NAME}
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=production
SECRET_KEY=${SECRET_KEY}
CORS_ORIGINS=http://localhost:5173
TRUSTED_PROXIES=172.16.0.0/12,10.0.0.0/8,192.168.0.0/16,127.0.0.1
ENVEOF
        chmod 600 .env
        log_info ".env dosyasi olusturuldu (SECRET_KEY otomatik uretildi)"
    else
        log_warn ".env dosyasi zaten mevcut, atlanıyor"
    fi
}

# ============================================================
# 6. FRONTEND BUILD
# ============================================================
setup_frontend() {
    log_step "6/8 Frontend Build Ediliyor"

    cd "$INSTALL_DIR/frontend"

    npm install --silent 2>/dev/null
    log_info "npm paketleri kuruldu"

    npm run build 2>/dev/null
    log_info "Frontend build tamamlandi → dist/"
}

# ============================================================
# 7. SYSTEMD SERVIS
# ============================================================
setup_systemd() {
    log_step "7/8 systemd Servisi Yapilandiriliyor"

    cp "$INSTALL_DIR/config/tonbilaios.service" /etc/systemd/system/tonbilaios.service
    systemctl daemon-reload
    systemctl enable tonbilaios
    log_info "tonbilaios.service aktif edildi"
}

# ============================================================
# 8. NGINX
# ============================================================
setup_nginx() {
    log_step "8/8 Nginx Yapilandiriliyor"

    # Varsayilan site'i kaldir
    rm -f /etc/nginx/sites-enabled/default 2>/dev/null

    # TonbilAiFirewall config'ini kopyala
    cp "$INSTALL_DIR/config/nginx-tonbilaios.conf" /etc/nginx/sites-available/tonbilaios
    ln -sf /etc/nginx/sites-available/tonbilaios /etc/nginx/sites-enabled/tonbilaios

    # Nginx config test
    if nginx -t 2>/dev/null; then
        systemctl enable nginx --now 2>/dev/null
        systemctl reload nginx 2>/dev/null
        log_info "Nginx yapilandirildi ve yeniden yuklendi"
    else
        log_error "Nginx yapilandirma hatasi! 'nginx -t' ile kontrol edin"
    fi
}

# ============================================================
# SERVIS BASLAT
# ============================================================
start_services() {
    echo ""
    log_step "Servisler Baslatiliyor"

    systemctl start redis-server 2>/dev/null || true
    systemctl start mariadb 2>/dev/null || true
    systemctl restart tonbilaios
    systemctl restart nginx

    sleep 3

    if systemctl is-active --quiet tonbilaios; then
        log_info "tonbilaios servisi AKTIF"
    else
        log_error "tonbilaios servisi baslatilamadi!"
        echo "  Loglari kontrol edin: journalctl -u tonbilaios -n 50"
    fi

    if systemctl is-active --quiet nginx; then
        log_info "nginx servisi AKTIF"
    else
        log_error "nginx servisi baslatilamadi!"
    fi
}

# ============================================================
# OZET
# ============================================================
print_summary() {
    # Raspberry Pi IP adresini bul
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}         ${GREEN}Kurulum Basariyla Tamamlandi!${NC}           ${CYAN}║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}                                                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Dashboard:  ${GREEN}http://${LOCAL_IP}${NC}               ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  API Docs:   ${GREEN}http://${LOCAL_IP}/docs${NC}          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Servisler:                                      ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    Backend:  systemctl status tonbilaios          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    Nginx:    systemctl status nginx               ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    MariaDB:  systemctl status mariadb             ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    Redis:    systemctl status redis-server        ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Loglar:                                         ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    journalctl -u tonbilaios -f                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Veritabani:                                     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    DB: ${DB_NAME}  User: ${DB_USER}              ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                  ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ============================================================
# ANA AKIS
# ============================================================
main() {
    banner
    check_root
    check_arch

    install_system_packages
    setup_directories
    setup_database
    setup_redis
    setup_backend
    setup_frontend
    setup_systemd
    setup_nginx
    start_services
    print_summary
}

main "$@"
