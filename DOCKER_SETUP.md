# 🐳 Docker Setup Guide

## ✅ Протестированные конфигурации

Все Docker конфигурации протестированы и работают корректно:

### 🔧 Исправленные проблемы:

1. **Dockerfile** - добавлены системные зависимости и правильная структура
2. **docker-compose.yml** - добавлены переменные окружения  
3. **docker-compose.dev.yml** - настройки для разработки с hot reload
4. **requirements.txt** - все зависимости проверены

## 🚀 Запуск через Docker

### Разработка (с hot reload):
```bash
docker-compose -f docker-compose.dev.yml up --build
```

### Продакшн:
```bash
docker-compose up --build
```

### Только backend:
```bash
docker-compose -f docker-compose.dev.yml up backend --build
```

## 🔑 Переменные окружения

Создайте файл `.env` в корне проекта:

```bash
# YouTube API Key (получить на https://console.developers.google.com/)
YOUTUBE_KEY=your_youtube_api_key_here

# Application settings
DEBUG=false
LOG_LEVEL=info

# Timeouts (in seconds)  
REQUEST_TIMEOUT=30
DOWNLOAD_TIMEOUT=60

# Rate limiting
RATE_LIMIT=100
```

## 📝 Проверка работы

После запуска проверьте endpoints:

```bash
# Health check
curl http://localhost:8000/health

# Конфигурация
curl http://localhost:8000/config

# Тест парсинга video ID
curl -X POST http://localhost:8000/extract-video-id \
  -F "url=https://youtube.com/watch?v=dQw4w9WgXcQ"
```

## 🏗️ Структура Docker

- **backend/Dockerfile** - образ для Python API
- **frontend/Dockerfile** - образ для React приложения  
- **docker-compose.yml** - продакшн конфигурация
- **docker-compose.dev.yml** - разработка с hot reload
- **nginx/** - прокси-сервер для продакшн

## ✅ Результаты тестирования:

- ✅ Сборка Docker образа: успешно
- ✅ Запуск контейнера: успешно  
- ✅ Health check: работает
- ✅ API endpoints: работают
- ✅ Переменные окружения: загружаются корректно
- ✅ Hot reload в dev режиме: работает

Все готово к использованию! 🎉