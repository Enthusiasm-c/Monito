# 🏝️ Monito Unified Price Management API

**Версия 3.0** - Современный REST API для unified системы управления ценами поставщиков острова Бали

## 🚀 Быстрый старт

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Настройка конфигурации

```bash
# Скопируйте пример конфигурации
cp api.env.example .env

# Отредактируйте настройки в .env файле
nano .env
```

### Запуск API сервера

```bash
# Запуск в режиме разработки
python api_server.py

# Или через uvicorn напрямую
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Проверка работоспособности

```bash
# Проверка здоровья API
curl http://localhost:8000/health

# Простой ping
curl http://localhost:8000/health/ping
```

## 📖 Документация

### Интерактивная документация

После запуска API документация доступна по адресам:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Основные эндпоинты

#### 🏥 Health Check
- `GET /health` - Проверка состояния системы
- `GET /health/detailed` - Детальная диагностика
- `GET /health/ping` - Простая проверка доступности
- `GET /health/ready` - Проверка готовности к работе

#### 🔍 Unified Catalog
- `GET /api/v1/catalog/search` - Поиск товаров с лучшими ценами
- `GET /api/v1/catalog/top-deals` - Топовые предложения с экономией
- `GET /api/v1/catalog/categories` - Список категорий со статистикой
- `POST /api/v1/catalog/procurement-recommendations` - Рекомендации по закупкам

#### 📦 Products
- `GET /api/v1/products` - Управление товарами
- `POST /api/v1/products` - Добавление товаров
- `PUT /api/v1/products/{id}` - Обновление товаров

#### 🏬 Suppliers
- `GET /api/v1/suppliers` - Список поставщиков
- `GET /api/v1/suppliers/{id}/performance` - Статистика поставщика

#### 💰 Prices
- `GET /api/v1/prices` - Управление ценами
- `POST /api/v1/prices` - Добавление цен
- `GET /api/v1/prices/history` - История изменения цен

#### 📊 Analytics
- `GET /api/v1/analytics/overview` - Общая статистика
- `GET /api/v1/analytics/trends` - Анализ трендов

#### 🔄 Migration
- `GET /api/v1/migration/status` - Статус миграции
- `POST /api/v1/migration/import` - Импорт legacy данных

### 🤖 Telegram Bot API

Unified API включает полную интеграцию с Telegram ботом через webhook:

```bash
# Информация о webhook
curl http://localhost:8000/api/v1/telegram/webhook/info

# Установка webhook
curl -X POST http://localhost:8000/api/v1/telegram/webhook/setup \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://yourdomain.com/api/v1/telegram/webhook"}'

# Проверка статуса
curl http://localhost:8000/api/v1/telegram/webhook/status

# Тестовое сообщение
curl -X POST http://localhost:8000/api/v1/telegram/test-message \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 123456789, "message": "Привет от Monito!"}'
```

**Поддерживаемые команды бота:**
- `/start` - Приветствие и основные возможности
- `/search [товар]` - Поиск товаров в unified каталоге
- `/catalog` - Browse каталог по категориям
- `/deals` - Топовые предложения с экономией
- `/categories` - Список всех категорий
- `/recommend` - AI-рекомендации по закупкам
- `/stats` - Статистика unified системы
- `/help` - Подробная справка

**Inline клавиатуры:** Бот поддерживает интерактивные кнопки для удобной навигации.

## 🏗️ Архитектура

### Компоненты системы

```
api/
├── main.py                 # Основное FastAPI приложение
├── config.py              # Конфигурация приложения
├── middleware/             # Middleware компоненты
│   ├── logging.py         # Логирование запросов
│   ├── auth.py            # Аутентификация
│   └── rate_limiting.py   # Ограничение скорости
├── routers/               # API роутеры
│   ├── health.py          # Health check эндпоинты
│   ├── catalog.py         # Unified каталог
│   ├── products.py        # Управление товарами
│   ├── suppliers.py       # Управление поставщиками
│   ├── prices.py          # Управление ценами
│   ├── analytics.py       # Аналитика
│   └── migration.py       # Инструменты миграции
└── schemas/               # Pydantic схемы
    ├── base.py            # Базовые схемы
    ├── products.py        # Схемы товаров
    ├── suppliers.py       # Схемы поставщиков
    └── ...
```

### Интеграция с Unified System

API использует следующие компоненты unified системы:

- **UnifiedDatabaseManager** - Управление базой данных
- **ProductMatchingEngine** - Сопоставление товаров
- **PriceComparisonEngine** - Анализ цен
- **UnifiedCatalogManager** - Генерация каталога
- **LegacyIntegrationAdapter** - Интеграция с legacy системой

## ⚙️ Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `MONITO_DEBUG` | Режим отладки | `false` |
| `MONITO_API_HOST` | Хост API | `0.0.0.0` |
| `MONITO_API_PORT` | Порт API | `8000` |
| `MONITO_DATABASE_URL` | URL базы данных | `sqlite:///./monito_unified.db` |
| `MONITO_ENABLE_AUTH` | Включить аутентификацию | `false` |
| `MONITO_API_KEY` | API ключ | `None` |
| `MONITO_RATE_LIMIT_PER_MINUTE` | Лимит запросов | `100` |

### Настройка базы данных

По умолчанию используется SQLite база данных. Для production рекомендуется PostgreSQL:

```bash
# PostgreSQL
MONITO_DATABASE_URL=postgresql://user:password@localhost/monito_unified

# MySQL
MONITO_DATABASE_URL=mysql://user:password@localhost/monito_unified
```

## 🔐 Аутентификация

API поддерживает опциональную аутентификацию через API ключи:

```bash
# Включить аутентификацию
MONITO_ENABLE_AUTH=true
MONITO_API_KEY=your-secret-key

# Использование
curl -H "Authorization: Bearer your-secret-key" http://localhost:8000/api/v1/catalog/search
curl -H "X-API-Key: your-secret-key" http://localhost:8000/api/v1/catalog/search
```

## 📊 Мониторинг

### Rate Limiting

API автоматически ограничивает количество запросов:

- По умолчанию: 100 запросов в минуту на IP
- Настраивается через `MONITO_RATE_LIMIT_PER_MINUTE`
- Заголовки ответа содержат информацию о лимитах

### Логирование

Все запросы логируются с уникальными ID для трассировки:

```
🔵 [req_123456789] GET /api/v1/catalog/search - IP: 192.168.1.1
✅ [req_123456789] 200 - 0.145s
```

### Health Checks

Множественные эндпоинты для мониторинга:

- `/health` - Базовая проверка
- `/health/detailed` - Детальная диагностика
- `/health/ready` - Готовность к работе

## 🌐 Примеры использования

### Поиск товаров в каталоге

```bash
# Поиск напитков с ценой до 15000 IDR
curl "http://localhost:8000/api/v1/catalog/search?query=cola&category=beverages&price_max=15000"

# Топ 10 лучших предложений
curl "http://localhost:8000/api/v1/catalog/top-deals?limit=10"
```

### Рекомендации по закупкам

```bash
curl -X POST "http://localhost:8000/api/v1/catalog/procurement-recommendations" \
     -H "Content-Type: application/json" \
     -d '{
       "required_products": [
         {"name": "Coca-Cola 330ml", "quantity": 100},
         {"name": "Bintang Beer 330ml", "quantity": 50}
       ],
       "budget_limit": 2000000,
       "optimize_for": "cost"
     }'
```

### Получение категорий

```bash
curl "http://localhost:8000/api/v1/catalog/categories"
```

## 🚢 Развертывание

### Docker (рекомендуется)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "api_server.py"]
```

### Production сервер

```bash
# Gunicorn для production
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 🔧 Разработка

### Добавление новых эндпоинтов

1. Создайте схемы в `api/schemas/`
2. Добавьте роутер в `api/routers/`
3. Подключите роутер в `api/main.py`
4. Обновите документацию

### Тестирование

```bash
# Запуск тестов API
pytest tests/api/

# Тестирование с покрытием
pytest --cov=api tests/api/
```

## 📝 TODO

- [ ] Реализация полных CRUD операций для товаров
- [ ] Расширенная аналитика и отчеты
- [ ] WebSocket для real-time обновлений
- [ ] Интеграция с внешними API поставщиков
- [ ] Система уведомлений о изменении цен
- [ ] Экспорт данных в различные форматы

## 🆘 Поддержка

При возникновении проблем:

1. Проверьте логи API сервера
2. Используйте `/health/detailed` для диагностики
3. Убедитесь что unified система инициализирована
4. Проверьте подключение к базе данных

## 📄 Лицензия

Monito Unified API - часть системы Monito версии 3.0 

```bash
# API настройки
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=true
API_LOG_LEVEL=INFO

# Database
DATABASE_URL=sqlite:///./data/unified_catalog.db

# Опциональная аутентификация
ENABLE_AUTH=false
API_KEY=your-secret-api-key

# Rate limiting
ENABLE_RATE_LIMITING=true
RATE_LIMIT_PER_MINUTE=100

# CORS
CORS_ORIGINS=["*"]

# Документация
ENABLE_DOCS=true

# Telegram интеграция
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/api/v1/telegram/webhook
``` 