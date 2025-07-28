#!/bin/bash

echo "🚀 MetaParser - Скрипт деплоя на VPS"
echo "==================================="

# Проверка sudo прав
# if [[ $EUID -eq 0 ]]; then
#   echo "❌ Не запускайте этот скрипт от root пользователя"
#   exit 1
# fi

# Установка Docker если не установлен
if ! command -v docker &> /dev/null; then
    echo "📦 Устанавливаем Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "✅ Docker установлен"
else
    echo "✅ Docker уже установлен"
fi

# Установка Docker Compose если не установлен
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Устанавливаем Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose установлен"
else
    echo "✅ Docker Compose уже установлен"
fi

# Создание папки для SSL сертификатов
echo "📁 Создаем папки для SSL..."
mkdir -p nginx/ssl

# Проверка наличия файлов конфигурации
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ Файл docker-compose.prod.yml не найден!"
    exit 1
fi

if [ ! -f "nginx/nginx.conf" ]; then
    echo "❌ Файл nginx/nginx.conf не найден!"
    exit 1
fi

# Остановка старых контейнеров
echo "🛑 Останавливаем старые контейнеры..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

# Сборка и запуск
echo "🔨 Собираем контейнеры..."
docker-compose -f docker-compose.prod.yml build --no-cache

echo "🚀 Запускаем приложение..."
docker-compose -f docker-compose.prod.yml up -d

echo ""
echo "✅ Деплой завершен!"
echo ""
echo "📋 Статус контейнеров:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🌐 Ваше приложение доступно по адресу:"
echo "   http://$(curl -s ifconfig.me)"
echo ""
echo "📝 Для настройки SSL сертификата используйте:"
echo "   ./ssl-setup.sh your-domain.com your-email@example.com"
echo ""
echo "📊 Просмотр логов:"
echo "   docker-compose -f docker-compose.prod.yml logs -f" 
