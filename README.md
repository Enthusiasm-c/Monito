# 🤖 Monito - Advanced Price List Analyzer

Универсальная система анализа прайс-листов с использованием ИИ, Telegram бота и автоматической обработки Excel файлов.

## 🚀 Возможности

### 📊 Универсальный парсинг Excel
- **Автоматическое определение структуры** любых прайс-листов
- **Поддержка многоколоночных структур** (товары в нескольких столбцах)
- **Умный поиск данных** по паттернам, а не по позиции
- **Обработка смешанных языков** (индонезийский, английский, русский)

### 🤖 ИИ обработка через GPT-4o
- **Пакетная обработка** больших объемов данных
- **Стандартизация названий** товаров на английский
- **Автоматическое извлечение** брендов, размеров, единиц измерения
- **Определение категорий** товаров

### 📱 Telegram Bot интерфейс
- **Простая загрузка файлов** через чат
- **Реальное время обработки** с подробными логами
- **Автоматические отчеты** о результатах
- **Поддержка файлов до 20 МБ**

## 📋 Быстрый старт

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения
Создайте файл `.env`:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
GOOGLE_SHEETS_ID=your_google_sheets_id
```

### 3. Запуск Telegram бота
```bash
python3 telegram_bot_advanced.py
```

## 📁 Основные файлы

```
├── modules/                           # Основные модули
│   ├── universal_excel_parser.py      # 📊 Универсальный парсер Excel
│   ├── batch_chatgpt_processor.py     # 🤖 Пакетная обработка через GPT
│   ├── google_sheets_manager.py       # 💾 Управление Google Sheets
│   ├── training_data_manager.py       # 🧪 Система обучения
│   └── system_monitor_simple.py       # 📈 Мониторинг системы
├── telegram_bot_advanced.py           # 📱 Главный Telegram бот
├── upload_and_process.py             # 📁 Прямая обработка файлов
├── quick_reference_creator.py        # ✏️ Создание эталонов
├── test_against_reference.py         # 🧪 Тестирование качества
└── requirements.txt                   # 📦 Зависимости
```

## 🚀 Использование

### Telegram бот (основной способ)
```bash
python3 telegram_bot_advanced.py
```

### Прямая обработка файлов
```bash
python3 upload_and_process.py
```

### Создание эталонных данных
```bash
python3 quick_reference_creator.py
```

### Тестирование системы
```bash
python3 test_against_reference.py
```

## 🎯 Система готова обрабатывать любые прайс-листы!