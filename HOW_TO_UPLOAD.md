# 📁 Как загрузить файл и эталонные данные

## 🚀 БЫСТРЫЙ СТАРТ (3 способа)

### **Способ 1: Telegram бот** ⭐ (самый простой)
```
1. Найдите бота в Telegram
2. Отправьте команду /start  
3. Перетащите Excel файл в чат
4. Получите результат анализа
```

### **Способ 2: Прямая загрузка файла**
```bash
python3 upload_and_process.py
```

### **Способ 3: Создание эталонных данных** 
```bash
python3 quick_reference_creator.py
```

---

## 📂 ДЕТАЛЬНЫЕ ИНСТРУКЦИИ

### 🤖 **1. Через Telegram бота**

**Что делать:**
1. Запустите бота (он уже работает)
2. Отправьте `/start`
3. Загрузите Excel файл
4. Дождитесь обработки

**Что получите:**
- Анализ структуры файла
- Извлеченные товары и цены
- Обработку через GPT-4.1
- Сохранение в Google Sheets
- Детальный отчет

### 💻 **2. Прямая загрузка файла**

**Запуск:**
```bash
python3 upload_and_process.py
```

**Процесс:**
1. Выберите способ загрузки:
   - Ввести путь к файлу
   - Выбрать из папки data/temp
2. Система автоматически:
   - Проанализирует Excel файл
   - Обработает через ChatGPT
   - Сохранит в Google Sheets
3. Получите детальный отчет

### 📝 **3. Создание эталонных данных**

#### A. Быстрое создание
```bash
python3 quick_reference_creator.py
```

**Формат ввода:**
```
название | бренд | стандарт | размер | единица | цена | валюта | категория
```

**Пример:**
```
COCA COLA 330ml | COCA COLA | COCA COLA Can | 330 | ml | 4500 | IDR | beverages
INDOMIE Mi Goreng | INDOMIE | INDOMIE Fried Noodles | 85 | g | 3200 | IDR | pasta_noodles
```

#### B. Полное создание
```bash
python3 create_training_example.py
```

**Возможности:**
- Интерактивный ввод всех данных
- Загрузка из готового JSON
- Получение шаблона

#### C. Из CSV файла

**Создайте файл с данными:**
```csv
COCA COLA 330ml;COCA COLA;COCA COLA Can;330;ml;4500;IDR;beverages
INDOMIE Mi Goreng;INDOMIE;INDOMIE Fried Noodles;85;g;3200;IDR;pasta_noodles
BARILLA Spaghetti;BARILLA;BARILLA Spaghetti No.5;500;g;25500;IDR;pasta_noodles
```

Затем запустите:
```bash
python3 quick_reference_creator.py
# Выберите пункт 2
```

---

## 📋 **ФОРМАТЫ ДАННЫХ**

### Excel файл (любой формат)
- ✅ Любые названия столбцов
- ✅ Товары и цены в любом формате  
- ✅ Несколько листов
- ✅ Размер до 20 МБ

### Эталонные данные (JSON)
```json
{
  "supplier": {
    "name": "PT GLOBAL ANUGRAH PASIFIK",
    "phone": "(0361) 9075914",
    "email": "sales@gap-indo.com",
    "address": "Bali, Indonesia"
  },
  "products": [
    {
      "original_name": "COCA COLA 330ml",
      "brand": "COCA COLA", 
      "standardized_name": "COCA COLA Can",
      "size": "330",
      "unit": "ml",
      "price": 4500,
      "currency": "IDR",
      "category": "beverages",
      "confidence": 0.95
    }
  ]
}
```

### Единицы измерения
```
g, ml, kg, l, pcs, box, pack, set, pair
```

### Категории товаров
```
beverages, canned_food, pasta_noodles, cooking_oil,
spices_seasonings, dairy_products, snacks, rice_grains,
electronics, tools, office_supplies
```

---

## 🧪 **ТЕСТИРОВАНИЕ СИСТЕМЫ**

### После создания эталонных данных:
```bash
python3 test_against_reference.py
```

**Что получите:**
- Сравнение с эталоном
- Метрики качества (точность, полнота)
- Выявление ошибок
- Рекомендации по улучшению

### Метрики качества:
- 📊 **Точность поставщика** - правильность извлечения контактов
- 📦 **Обнаружение товаров** - сколько товаров найдено
- 🏷️ **Точность брендов** - правильность извлечения брендов
- 💰 **Точность цен** - правильность распознавания цен
- 📏 **Точность размеров** - извлечение размеров/весов

---

## 💡 **ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ**

### 1. Быстрое тестирование файла
```bash
# Загрузите файл через Telegram бота
# Или запустите:
python3 upload_and_process.py
```

### 2. Создание эталона для обучения
```bash
# Быстрый способ:
python3 quick_reference_creator.py

# Подробный способ:
python3 create_training_example.py
```

### 3. Тестирование качества
```bash
python3 test_against_reference.py
```

### 4. Проверка системы
```bash
# В Telegram боте:
/test
/stats
```

---

## 🎯 **РЕКОМЕНДОВАННЫЙ WORKFLOW**

1. **Загрузите файл** через бота или напрямую
2. **Изучите результат** - что система извлекла
3. **Создайте эталон** с правильными данными
4. **Протестируйте качество** - сравните с эталоном
5. **Улучшите промпты** при необходимости
6. **Повторите тестирование**

**Система готова к работе! Начните с любого удобного способа! 🚀**