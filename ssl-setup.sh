#!/bin/bash

# Проверка аргументов
if [ $# -ne 2 ]; then
    echo "❌ Использование: $0 <домен> <email>"
    echo "   Пример: $0 example.com admin@example.com"
    exit 1
fi

DOMAIN=$1
EMAIL=$2

echo "🔒 Настройка SSL для домена: $DOMAIN"
echo "📧 Email: $EMAIL"
echo "================================"

# Проверка что домен указывает на этот сервер
echo "🔍 Проверяем DNS настройки..."
SERVER_IP=$(curl -s ifconfig.me)
DOMAIN_IP=$(dig +short $DOMAIN | tail -n1)

if [ "$SERVER_IP" != "$DOMAIN_IP" ]; then
    echo "⚠️  Внимание: Домен $DOMAIN указывает на $DOMAIN_IP, а сервер имеет IP $SERVER_IP"
    echo "   Убедитесь что DNS настройки корректны перед продолжением"
    read -p "   Продолжить? (y/N): " confirm
    if [[ $confirm != [yY] ]]; then
        exit 1
    fi
fi

# Установка Certbot
if ! command -v certbot &> /dev/null; then
    echo "📦 Устанавливаем Certbot..."
    sudo apt update
    sudo apt install -y certbot
    echo "✅ Certbot установлен"
else
    echo "✅ Certbot уже установлен"
fi

# Остановка nginx для получения сертификата
echo "🛑 Временно останавливаем nginx..."
docker-compose -f docker-compose.prod.yml stop nginx

# Получение SSL сертификата
echo "🔒 Получаем SSL сертификат..."
sudo certbot certonly --standalone \
    --preferred-challenges http \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN

# Проверка успешного получения сертификата
if [ $? -eq 0 ]; then
    echo "✅ SSL сертификат получен!"
    
    # Копирование сертификатов в папку nginx
    echo "📋 Копируем сертификаты..."
    sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem nginx/ssl/
    sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem nginx/ssl/
    sudo chmod 644 nginx/ssl/fullchain.pem
    sudo chmod 644 nginx/ssl/privkey.pem
    
    # Обновление nginx конфигурации для SSL
    echo "⚙️  Обновляем nginx конфигурацию..."
    cat > nginx/nginx.conf << EOF
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # Логирование
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;
    
    # Gzip сжатие
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # Размер загружаемых файлов
    client_max_body_size 100M;
    
    upstream backend {
        server metaparser-backend:8000;
    }
    
    upstream frontend {
        server metaparser-frontend:80;
    }
    
    # Редирект HTTP -> HTTPS
    server {
        listen 80;
        server_name $DOMAIN;
        return 301 https://\$server_name\$request_uri;
    }
    
    # HTTPS сервер
    server {
        listen 443 ssl http2;
        server_name $DOMAIN;
        
        # SSL настройки
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
        
        # API запросы проксируем на backend
        location /parse {
            proxy_pass http://backend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            
            # Для больших файлов
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }
        
        location /download {
            proxy_pass http://backend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            
            # Для больших файлов
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }
        
        location /media {
            proxy_pass http://backend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
        
        # Все остальное - статика frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
    }
}
EOF
    
    # Настройка автообновления сертификата
    echo "🔄 Настраиваем автообновление сертификата..."
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet && docker-compose -f $(pwd)/docker-compose.prod.yml restart nginx") | crontab -
    
    # Перезапуск nginx с новой конфигурацией
    echo "🔄 Перезапускаем nginx..."
    docker-compose -f docker-compose.prod.yml up -d nginx
    
    echo ""
    echo "🎉 SSL настроен успешно!"
    echo "🌐 Ваш сайт доступен по адресу: https://$DOMAIN"
    echo "🔒 SSL сертификат будет автоматически обновляться"
    
else
    echo "❌ Ошибка получения SSL сертификата"
    echo "🔄 Перезапускаем nginx без SSL..."
    docker-compose -f docker-compose.prod.yml up -d nginx
    exit 1
fi 