#!/bin/bash
# Скрипт для деплоя на production сервер
# Использование: ./deploy/scripts/deploy.sh

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Конфигурация
SERVER_USER="${DEPLOY_USER:-root}"
SERVER_HOST="${DEPLOY_HOST:-}"
SERVER_PORT="${DEPLOY_PORT:-22}"
DEPLOY_DIR="/var/www/fastpay_connect"
BACKUP_DIR="/var/backups/fastpay_connect"

echo -e "${YELLOW}🚀 FastPay Connect Deployment Script${NC}"
echo "=================================="

# Проверка переменных окружения
if [ -z "$SERVER_HOST" ]; then
    echo -e "${RED}❌ Ошибка: SERVER_HOST не установлен${NC}"
    echo "Установите переменную окружения: export DEPLOY_HOST=your.server.com"
    exit 1
fi

echo -e "${GREEN}✅ Подключение к серверу: ${SERVER_USER}@${SERVER_HOST}:${SERVER_PORT}${NC}"

# Функция для выполнения команд на сервере
run_remote() {
    ssh -p "$SERVER_PORT" -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" "$1"
}

# Функция для копирования файлов на сервер
copy_to_server() {
    scp -P "$SERVER_PORT" -r "$1" "$SERVER_USER@$SERVER_HOST:$2"
}

# Создание резервной копии
echo -e "${YELLOW}📦 Создание резервной копии...${NC}"
run_remote "mkdir -p $BACKUP_DIR && \
    if [ -d $DEPLOY_DIR ]; then \
        cp -r $DEPLOY_DIR $BACKUP_DIR/backup_\$(date +%Y%m%d_%H%M%S); \
    fi"

# Деплой приложения
echo -e "${YELLOW}📤 Копирование файлов на сервер...${NC}"
copy_to_server "." "$SERVER_USER@$SERVER_HOST:$DEPLOY_DIR"

# Установка зависимостей и запуск
echo -e "${YELLOW}⚙️  Установка зависимостей и запуск...${NC}"
run_remote "cd $DEPLOY_DIR && \
    docker-compose -f docker-compose.prod.yml pull && \
    docker-compose -f docker-compose.prod.yml up -d --build"

# Проверка здоровья
echo -e "${YELLOW}🏥 Проверка здоровья приложения...${NC}"
sleep 10
HEALTH_STATUS=$(run_remote "curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/health")

if [ "$HEALTH_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ Деплой успешно завершён!${NC}"
    echo -e "${GREEN}📊 Health check: HTTP $HEALTH_STATUS${NC}"
else
    echo -e "${RED}❌ Деплой завершён с ошибками!${NC}"
    echo -e "${RED}📊 Health check: HTTP $HEALTH_STATUS${NC}"
    exit 1
fi

# Очистка старых образов
echo -e "${YELLOW}🧹 Очистка старых Docker образов...${NC}"
run_remote "docker image prune -f --filter 'until=24h'"

echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}🎉 Деплой завершён!${NC}"
echo -e "${GREEN}🌐 URL: https://${SERVER_HOST}${NC}"
echo -e "${GREEN}📊 Health: http://${SERVER_HOST}:8080/health${NC}"
