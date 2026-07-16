#!/bin/bash

# Monitoring Setup Script

set -e

echo "📊 İzleme ve Logging Kurulumu"
echo "=============================="

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

echo -e "${YELLOW}1. Docker stats monitoring kurulması...${NC}"
# Prometheus ve Node Exporter kurulması (opsiyonel)
# Bu kısım özel gereksinimler için uyarlanabilir

echo -e "${YELLOW}2. Application logging yapılandırması...${NC}"
mkdir -p /root/career-planner-agent/logs
touch /root/career-planner-agent/logs/career-planner.log
touch /root/career-planner-agent/logs/error.log

echo -e "${YELLOW}3. Monitoring script oluşturuluyor...${NC}"
cat > /root/career-planner-agent/deploy-scripts/monitor.sh <<'EOF'
#!/bin/bash

# Career Planner Agent Monitoring Script

CONTAINER_NAME="career-planner-agent"
LOG_FILE="/root/career-planner-agent/logs/monitor.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Monitoring kontrolü başlatılıyor..." >> $LOG_FILE

# Container durumunu kontrol et
if docker ps | grep -q $CONTAINER_NAME; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ Container çalışıyor" >> $LOG_FILE
    
    # Container stats
    docker stats --no-stream $CONTAINER_NAME >> $LOG_FILE 2>&1
    
    # Container logs son 50 satır
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Son loglar:" >> $LOG_FILE
    docker logs --tail 50 $CONTAINER_NAME >> $LOG_FILE 2>&1
    
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✗ UYARI: Container çalışmıyor!" >> $LOG_FILE
    systemctl status career-planner >> $LOG_FILE 2>&1
fi

# Disk kullanımı
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Disk Kullanımı:" >> $LOG_FILE
df -h >> $LOG_FILE

# Memory kullanımı
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Memory Kullanımı:" >> $LOG_FILE
free -h >> $LOG_FILE

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Monitoring kontrolü tamamlandı" >> $LOG_FILE
echo "---" >> $LOG_FILE
EOF

chmod +x /root/career-planner-agent/deploy-scripts/monitor.sh

echo -e "${YELLOW}4. Cron job: Saat başı monitoring...${NC}"
cat > /etc/cron.hourly/career-planner-monitor <<'EOF'
#!/bin/bash
/root/career-planner-agent/deploy-scripts/monitor.sh
EOF

chmod +x /etc/cron.hourly/career-planner-monitor

echo -e "${YELLOW}5. Alert script oluşturuluyor...${NC}"
cat > /root/career-planner-agent/deploy-scripts/check-health.sh <<'EOF'
#!/bin/bash

CONTAINER_NAME="career-planner-agent"
EMAIL="admin@example.com"
THRESHOLD_MEMORY=80
THRESHOLD_DISK=90

# Container kontrol
if ! docker ps | grep -q $CONTAINER_NAME; then
    echo "ALERT: Career Planner container çalışmıyor!" | \
    mail -s "🚨 Career Planner Alert" $EMAIL
    systemctl restart career-planner
fi

# Memory kontrol
MEMORY_USAGE=$(docker stats --no-stream --format "{{.MemPerc}}" $CONTAINER_NAME | sed 's/%//')
if (( $(echo "$MEMORY_USAGE > $THRESHOLD_MEMORY" | bc -l) )); then
    echo "ALERT: High memory usage: $MEMORY_USAGE%" | \
    mail -s "⚠️ Memory Alert" $EMAIL
fi

# Disk kontrol
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt $THRESHOLD_DISK ]; then
    echo "ALERT: High disk usage: $DISK_USAGE%" | \
    mail -s "⚠️ Disk Alert" $EMAIL
fi
EOF

chmod +x /root/career-planner-agent/deploy-scripts/check-health.sh

echo -e "${YELLOW}6. Health check cron job kurulması (her 15 dakika)...${NC}"
(crontab -l 2>/dev/null; echo "*/15 * * * * /root/career-planner-agent/deploy-scripts/check-health.sh") | crontab -

echo -e "${GREEN}✅ Monitoring kurulumu tamamlandı!${NC}"
echo ""
echo -e "${YELLOW}Komutlar:${NC}"
echo "Monitoring manuel çalıştır: /root/career-planner-agent/deploy-scripts/monitor.sh"
echo "Health kontrol et: /root/career-planner-agent/deploy-scripts/check-health.sh"
echo "Container logları: docker logs -f career-planner-agent"
echo "Sistem logları: journalctl -u career-planner -f"
echo "Monitoring logları: tail -f /root/career-planner-agent/logs/monitor.log"
