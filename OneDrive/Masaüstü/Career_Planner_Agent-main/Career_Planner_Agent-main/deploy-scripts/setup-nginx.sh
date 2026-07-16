#!/bin/bash

# Nginx ve SSL setup script

set -e

echo "🔒 Nginx ve SSL Setup"
echo "===================="

# Root kontrolü
if [ "$EUID" -ne 0 ]; then 
    echo "Bu script root olarak çalıştırılmalıdır"
    exit 1
fi

# Renk tanımları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Domain adı sorulması
read -p "Lütfen domain adınızı girin (örn: career-planner.example.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}Domain adı boş bırakılamaz${NC}"
    exit 1
fi

echo -e "${YELLOW}Nginx kuruluyor...${NC}"
apt-get install -y nginx

echo -e "${YELLOW}Nginx konfigürasyonu güncelleniyor...${NC}"
cp /root/career-planner-agent/nginx.conf /etc/nginx/conf.d/career-planner.conf

# Nginx konfigürasyon dosyasını düzelt
sed -i "s/your-domain.com/$DOMAIN/g" /etc/nginx/conf.d/career-planner.conf

echo -e "${YELLOW}Nginx konfigürasyonu test ediliyor...${NC}"
nginx -t

echo -e "${YELLOW}Nginx başlatılıyor...${NC}"
systemctl start nginx
systemctl enable nginx

echo -e "${YELLOW}Let's Encrypt sertifikası alınıyor...${NC}"
certbot certonly --standalone -d $DOMAIN -n --agree-tos --email admin@$DOMAIN

echo -e "${YELLOW}SSL sertifikası nginx'e uygulanıyor...${NC}"
sed -i "s|/etc/letsencrypt/live/your-domain.com/fullchain.pem|/etc/letsencrypt/live/$DOMAIN/fullchain.pem|g" /etc/nginx/conf.d/career-planner.conf
sed -i "s|/etc/letsencrypt/live/your-domain.com/privkey.pem|/etc/letsencrypt/live/$DOMAIN/privkey.pem|g" /etc/nginx/conf.d/career-planner.conf

echo -e "${YELLOW}Nginx yeniden başlatılıyor...${NC}"
systemctl restart nginx

# Auto-renewal kurulması
echo -e "${YELLOW}SSL otomatik yenileme ayarlanıyor...${NC}"
systemctl enable certbot.timer
systemctl start certbot.timer

echo -e "${GREEN}✅ Nginx ve SSL kurulumu tamamlandı!${NC}"
echo ""
echo -e "${YELLOW}Bilgiler:${NC}"
echo "Domain: https://$DOMAIN"
echo "Sertifika konumu: /etc/letsencrypt/live/$DOMAIN/"
echo ""
echo -e "${YELLOW}Uygulamayı başlatın:${NC}"
echo "systemctl start career-planner"
