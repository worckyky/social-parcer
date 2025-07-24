# 🚀 Деплой MetaParser на VPS

Пошаговая инструкция для развертывания MetaParser на любом VPS сервере.

## 📋 Требования

- **VPS сервер** с Ubuntu 18.04+ или CentOS 7+
- **Минимум 1GB RAM** и 10GB свободного места
- **Домен** (для SSL сертификата)
- **SSH доступ** к серверу

## 🔧 Автоматический деплой

### 1. Подключение к VPS
```bash
ssh your-user@your-server-ip
```

### 2. Загрузка проекта
```bash
# Клонируем проект
git clone https://github.com/your-username/MetaParser.git
cd MetaParser

# Или загружаем архив
wget https://github.com/your-username/MetaParser/archive/main.zip
unzip main.zip
cd MetaParser-main
```

### 3. Запуск деплоя
```bash
# Делаем скрипт исполняемым
chmod +x deploy.sh

# Запускаем деплой
./deploy.sh
```

Скрипт автоматически:
- ✅ Установит Docker и Docker Compose
- ✅ Соберет и запустит все контейнеры
- ✅ Настроит nginx с правильной конфигурацией
- ✅ Покажет статус всех сервисов

### 4. Настройка SSL (опционально)
```bash
# Делаем скрипт исполняемым
chmod +x ssl-setup.sh

# Настраиваем SSL для вашего домена
./ssl-setup.sh your-domain.com your-email@example.com
```

**❗ Важно:** Убедитесь что ваш домен указывает на IP сервера в DNS настройках.

## 🌐 Проверка работы

После деплоя ваше приложение будет доступно:
- **HTTP:** `http://your-server-ip`
- **HTTPS:** `https://your-domain.com` (если настроили SSL)

## 📊 Управление сервисом

### Просмотр логов
```bash
# Все логи
docker-compose -f docker-compose.prod.yml logs -f

# Логи конкретного сервиса
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend
docker-compose -f docker-compose.prod.yml logs -f nginx
```

### Перезапуск сервисов
```bash
# Перезапуск всех сервисов
docker-compose -f docker-compose.prod.yml restart

# Перезапуск конкретного сервиса
docker-compose -f docker-compose.prod.yml restart backend
```

### Остановка/Запуск
```bash
# Остановка
docker-compose -f docker-compose.prod.yml down

# Запуск
docker-compose -f docker-compose.prod.yml up -d
```

### Обновление приложения
```bash
# Загружаем новый код
git pull origin main

# Пересобираем и перезапускаем
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

## 🔒 Безопасность

### Настройка файрвола (Ubuntu)
```bash
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### Настройка автоматических обновлений
```bash
sudo apt update
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades
```

## 📁 Структура файлов на сервере

```
MetaParser/
├── docker-compose.prod.yml    # Production конфигурация
├── nginx/
│   ├── nginx.conf            # Nginx конфигурация
│   └── ssl/                  # SSL сертификаты
├── backend/
│   ├── media/               # Загруженные файлы
│   └── ...
├── deploy.sh                # Скрипт деплоя
├── ssl-setup.sh            # Скрипт настройки SSL
└── production.env          # Переменные окружения
```

## 🛠 Ручная настройка (альтернатива)

Если автоматический деплой не работает:

### 1. Установка Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### 2. Установка Docker Compose
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 3. Создание конфигурации
```bash
mkdir -p nginx/ssl
```

### 4. Запуск приложения
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## ❓ Решение проблем

### Порты заняты
```bash
# Найти процесс на порту 80/443
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :443

# Остановить Apache/Nginx если установлены
sudo systemctl stop apache2
sudo systemctl stop nginx
```

### Проблемы с правами
```bash
# Добавить пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

### Недостаточно места
```bash
# Очистка старых Docker образов
docker system prune -a
```

### SSL сертификат не работает
```bash
# Проверка DNS
dig your-domain.com

# Принудительное обновление сертификата
sudo certbot renew --force-renewal
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи контейнеров
2. Убедитесь что все порты открыты
3. Проверьте DNS настройки домена
4. Убедитесь что у пользователя есть права Docker 