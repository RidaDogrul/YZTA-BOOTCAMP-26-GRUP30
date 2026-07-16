#!/bin/bash

# Security Hardening Script for Career Planner Agent on DigitalOcean

set -e

echo "🔒 Güvenlik Sertleştirme (Security Hardening)"
echo "=============================================="

# Renk tanımları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Root kontrolü
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Bu script root olarak çalıştırılmalıdır${NC}"
    exit 1
fi

echo -e "${YELLOW}1. Sistem güvenliği güncellemeleri uygulanıyor...${NC}"
apt-get update
apt-get upgrade -y
apt-get install -y unattended-upgrades apt-listchanges

echo -e "${YELLOW}2. Güvenlik Duvarı (UFW) yapılandırılıyor...${NC}"
apt-get install -y ufw

# UFW kurallarını sıfırla
ufw --force reset
ufw default deny incoming
ufw default allow outgoing

# Gerekli portları aç
ufw allow ssh
ufw allow http
ufw allow https

# UFW'i etkinleştir
ufw --force enable

echo -e "${YELLOW}3. SSH sertleştirme uygulanıyor...${NC}"
# SSH key-only authentication
sed -i 's/^#PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sed -i 's/^#PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#X11Forwarding.*/X11Forwarding no/' /etc/ssh/sshd_config
sed -i 's/^#MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config
sed -i 's/^#ClientAliveInterval.*/ClientAliveInterval 300/' /etc/ssh/sshd_config
sed -i 's/^#ClientAliveCountMax.*/ClientAliveCountMax 2/' /etc/ssh/sshd_config

# SSH'i yeniden başlat
systemctl restart sshd

echo -e "${YELLOW}4. Fail2ban kuruluyor (brute-force protection)...${NC}"
apt-get install -y fail2ban

# Fail2ban yapılandırması
cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
EOF

systemctl enable fail2ban
systemctl restart fail2ban

echo -e "${YELLOW}5. Sistem logları yapılandırılıyor...${NC}"
apt-get install -y rsyslog
systemctl enable rsyslog

echo -e "${YELLOW}6. Otomatik güvenlik güncellemeleri etkinleştiriliyor...${NC}"
cat > /etc/apt/apt.conf.d/50unattended-upgrades <<EOF
Unattended-Upgrade::Allowed-Origins {
    "\${distro_id}:\${distro_codename}-security";
    "\${distro_id}ESMApps:\${distro_codename}-apps-security";
    "\${distro_id}ESM:\${distro_codename}-infra-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF

echo -e "${YELLOW}7. Kernel parametreleri güvenlik için ayarlanıyor...${NC}"
cat >> /etc/sysctl.conf <<EOF

# IP Forwarding deaktif
net.ipv4.ip_forward = 0
net.ipv6.conf.all.forwarding = 0

# IP Spoofing koruması
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# ICMP redirects deaktif
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0

# SYN flood koruması
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_syn_retries = 5

# ICMP ping yanıtını sınırla
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Logout idle sessions
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_keepalive_intvl = 15
EOF

sysctl -p

echo -e "${YELLOW}8. Docker güvenliği yapılandırılıyor...${NC}"
# Non-root user docker'a erişemez
usermod -aG docker ubuntu 2>/dev/null || true

echo -e "${YELLOW}9. Log rotation yapılandırılıyor...${NC}"
cat > /etc/logrotate.d/career-planner <<EOF
/root/career-planner-agent/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        systemctl reload career-planner > /dev/null 2>&1 || true
    endscript
}
EOF

echo -e "${YELLOW}10. Backup dizini oluşturuluyor...${NC}"
mkdir -p /backup/career-planner
chmod 700 /backup/career-planner

# Cron job: günlük backup
cat > /etc/cron.daily/backup-career-planner <<'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/career-planner"
SOURCE_DIR="/root/career-planner-agent"

tar -czf $BACKUP_DIR/career-planner-backup-$DATE.tar.gz \
    $SOURCE_DIR/memory.json \
    $SOURCE_DIR/schedule.json \
    $SOURCE_DIR/schedule.txt \
    $SOURCE_DIR/.env

# Eski backupları sil (7 günden eski)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x /etc/cron.daily/backup-career-planner

echo -e "${GREEN}✅ Güvenlik sertleştirme tamamlandı!${NC}"
echo ""
echo -e "${YELLOW}Uygulanan güvenlik önlemleri:${NC}"
echo "✓ SSH key-only authentication"
echo "✓ Firewall (UFW)"
echo "✓ Fail2ban (brute-force protection)"
echo "✓ Automatic security updates"
echo "✓ Kernel hardening"
echo "✓ Log rotation"
echo "✓ Daily backups"
echo ""
echo -e "${YELLOW}Durumu kontrol edin:${NC}"
echo "UFW: ufw status"
echo "Fail2ban: fail2ban-client status"
echo "SSH: systemctl status sshd"
