#!/bin/bash

# Career Planner Agent - DigitalOcean Setup Script
# Bu script DigitalOcean droplet'ında uygulamayı kurmak için kullanılır

set -e

echo "🚀 Career Planner Agent - Setup Script"
echo "========================================"

# Renk tanımları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Root kontrolü
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Bu script root olarak çalıştırılmalıdır${NC}"
    exit 1
fi

echo -e "${YELLOW}1. Sistem paketleri güncelleniyor...${NC}"
apt-get update
apt-get upgrade -y

echo -e "${YELLOW}2. Docker ve Docker Compose kuruluyor...${NC}"
# Docker kurulumu
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# Docker Compose kurulumu
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Docker hizmeti başlatılması
systemctl start docker
systemctl enable docker

echo -e "${YELLOW}3. Git kuruluyor...${NC}"
apt-get install -y git

echo -e "${YELLOW}4. Certbot (Let's Encrypt) kuruluyor...${NC}"
apt-get install -y certbot python3-certbot-nginx

echo -e "${YELLOW}5. Uygulama dizini oluşturuluyor...${NC}"
mkdir -p /root/career-planner-agent
mkdir -p /root/career-planner-agent/data
mkdir -p /root/career-planner-agent/logs

echo -e "${YELLOW}6. Repository klonlanıyor...${NC}"
cd /root/career-planner-agent
git clone https://github.com/elifkeskin/-Career-Planner-with-AI-Agent.git .

echo -e "${YELLOW}7. Environment dosyası hazırlanıyor...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  .env dosyası oluşturuldu. Lütfen OPENAI_API_KEY'i ekleyin:${NC}"
    echo "nano /root/career-planner-agent/.env"
fi

echo -e "${YELLOW}8. Docker imajı oluşturuluyor...${NC}"
docker-compose build

echo -e "${YELLOW}9. Systemd service kuruluyor...${NC}"
cp career-planner.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable career-planner.service

echo -e "${GREEN}✅ Setup tamamlandı!${NC}"
echo ""
echo -e "${YELLOW}Sonraki adımlar:${NC}"
echo "1. .env dosyasını düzenleyin ve OPENAI_API_KEY ekleyin:"
echo "   nano /root/career-planner-agent/.env"
echo ""
echo "2. Nginx'i yapılandırın ve SSL sertifikası alın:"
echo "   ./deploy-scripts/setup-nginx.sh"
echo ""
echo "3. Uygulamayı başlatın:"
echo "   systemctl start career-planner"
echo ""
echo "4. Durumunu kontrol edin:"
echo "   systemctl status career-planner"
echo ""
echo "5. Logları görüntüleyin:"
echo "   journalctl -u career-planner -f"
