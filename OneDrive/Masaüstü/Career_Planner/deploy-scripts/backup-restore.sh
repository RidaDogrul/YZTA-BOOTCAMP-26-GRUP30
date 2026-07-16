#!/bin/bash

# Backup and Restore Script for Career Planner Agent

set -e

# Renk tanımları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BACKUP_DIR="/backup/career-planner"
APP_DIR="/root/career-planner-agent"
DATE=$(date +%Y%m%d_%H%M%S)

# Menü
show_menu() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Backup ve Restore Menüsü${NC}"
    echo -e "${BLUE}================================${NC}"
    echo "1) Backup oluştur"
    echo "2) Backup'ı geri yükle"
    echo "3) Backup listesini göster"
    echo "4) Çık"
    echo ""
}

# Backup oluştur
create_backup() {
    echo -e "${YELLOW}Backup oluşturuluyor...${NC}"
    
    mkdir -p $BACKUP_DIR
    
    tar -czf $BACKUP_DIR/career-planner-backup-$DATE.tar.gz \
        -C $APP_DIR \
        memory.json \
        schedule.json \
        schedule.txt \
        .env \
        2>/dev/null || true
    
    if [ -f "$BACKUP_DIR/career-planner-backup-$DATE.tar.gz" ]; then
        SIZE=$(du -h "$BACKUP_DIR/career-planner-backup-$DATE.tar.gz" | awk '{print $1}')
        echo -e "${GREEN}✓ Backup başarılı: $DATE (Size: $SIZE)${NC}"
    else
        echo -e "${RED}✗ Backup oluşturulamadı${NC}"
        return 1
    fi
}

# Backup'ı geri yükle
restore_backup() {
    echo -e "${YELLOW}Mevcut backup'lar:${NC}"
    ls -lh $BACKUP_DIR/*.tar.gz 2>/dev/null | awk '{print $9, "(" $5 ")"}' | nl
    
    echo ""
    read -p "Geri yüklemek istediğiniz backup numarasını girin: " backup_num
    
    # Dosya adını al
    backup_file=$(ls -1 $BACKUP_DIR/*.tar.gz 2>/dev/null | sed -n "${backup_num}p")
    
    if [ -z "$backup_file" ]; then
        echo -e "${RED}✗ Geçersiz seçim${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}$backup_file geri yükleniyor...${NC}"
    
    # Container'ı durdur
    echo -e "${YELLOW}Container durduruluyor...${NC}"
    systemctl stop career-planner || docker stop career-planner-agent || true
    
    # Backup'ı geri yükle
    tar -xzf "$backup_file" -C $APP_DIR
    
    # Container'ı başlat
    echo -e "${YELLOW}Container başlatılıyor...${NC}"
    systemctl start career-planner || docker-compose -f $APP_DIR/docker-compose.prod.yml up -d
    
    echo -e "${GREEN}✓ Restore başarılı${NC}"
}

# Backup listesi göster
list_backups() {
    echo -e "${BLUE}Mevcut Backup'lar:${NC}"
    echo ""
    if [ -d "$BACKUP_DIR" ]; then
        ls -lh $BACKUP_DIR/*.tar.gz 2>/dev/null | awk '{print $9, "\t(" $5 ")"}'
    else
        echo -e "${YELLOW}Henüz backup yok${NC}"
    fi
    echo ""
}

# Ana loop
main() {
    while true; do
        show_menu
        read -p "Seçiminizi yapın (1-4): " choice
        
        case $choice in
            1) create_backup ;;
            2) restore_backup ;;
            3) list_backups ;;
            4) 
                echo -e "${GREEN}Çıkılıyor...${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Geçersiz seçim${NC}"
                ;;
        esac
        
        echo ""
        read -p "Devam etmek için Enter tuşuna basın..."
        clear
    done
}

# Root kontrolü
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Bu script root olarak çalıştırılmalıdır${NC}"
    exit 1
fi

# Ana fonksiyon çalıştır
main
