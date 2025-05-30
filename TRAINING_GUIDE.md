# 🎓 Руководство по обучению и тестированию системы

## 📋 Обзор системы обучения

Система позволяет создавать эталонные данные для обучения и тестирования качества распознавания прайс-листов.

### 🔧 Компоненты системы:

1. **TrainingDataManager** - управление эталонными данными
2. **create_training_example.py** - создание эталонных примеров  
3. **test_against_reference.py** - тестирование против эталонов

## 📁 Структура данных обучения

```
training_data/
├── original_files/          # Оригинальные Excel файлы
│   ├── example1.xlsx
│   └── example2.xlsx
├── reference_data/          # Эталонные JSON данные  
│   ├── example1_reference.json
│   └── example2_reference.json
└── comparison_results/      # Результаты сравнений
    ├── example1_comparison_20231201_143022.json
    └── example2_comparison_20231201_143156.json
```

## 🚀 Как использовать систему

### 1. Создание эталонного примера

#### Способ A: Интерактивное создание
```bash
python3 create_training_example.py
# Выберите пункт 1
```

Система попросит:
- Название примера (например: `indonesia_food_supplier`)
- Путь к Excel файлу
- Данные поставщика (название, телефон, email, адрес)
- Данные товаров (название, бренд, размер, цена, категория)

#### Способ B: Загрузка из готового JSON
```bash
python3 create_training_example.py  
# Выберите пункт 2
```

Подготовьте JSON файл по шаблону (см. ниже).

#### Способ C: Получение шаблона
```bash
python3 create_training_example.py
# Выберите пункт 3
```

Получите файл `reference_template.json` для заполнения.

### 2. Тестирование системы

```bash
python3 test_against_reference.py
```

Опции:
- **Тест одного примера** - детальное сравнение
- **Тест всех примеров** - сводный отчет
- **Список примеров** - просмотр доступных эталонов

## 📝 Формат эталонных данных

### JSON структура:

```json
{
  "supplier": {
    "name": "PT GLOBAL ANUGRAH PASIFIK",
    "phone": "(0361) 9075914", 
    "whatsapp": "+856 755 3319",
    "email": "sales@gap-indo.com",
    "address": "Bali, Indonesia"
  },
  "products": [
    {
      "original_name": "SAPORITO Baked Bean in tomato sauce 2.65 Kg",
      "brand": "SAPORITO",
      "standardized_name": "SAPORITO Baked Beans in Tomato Sauce",
      "size": "2.65",
      "unit": "kg", 
      "price": 90000,
      "currency": "IDR",
      "category": "canned_food",
      "confidence": 0.95
    }
  ],
  "metadata": {
    "document_type": "price_list",
    "language": "indonesian/english", 
    "total_pages": 4,
    "notes": "Дополнительные заметки"
  }
}
```

### Обязательные поля товаров:
- `original_name` - точное название из документа
- `standardized_name` - стандартизированное название на английском
- `price` - числовая цена
- `unit` - единица измерения (g, ml, kg, l, pcs, box)
- `category` - категория товара

### Рекомендуемые поля:
- `brand` - бренд товара
- `size` - размер/вес
- `currency` - валюта (IDR, USD, EUR)
- `confidence` - уверенность (0.0-1.0)

## 📊 Метрики качества

### Показатели поставщика:
- Точность извлечения названия компании
- Точность контактных данных (телефон, email)
- Точность адреса

### Показатели товаров:
- **Процент обнаружения** - сколько товаров найдено из эталонных
- **Точность брендов** - правильность извлечения брендов
- **Точность названий** - качество стандартизации названий
- **Точность цен** - правильность распознавания цен
- **Точность размеров** - извлечение размеров и весов
- **Точность категорий** - правильность категоризации

### Общая оценка:
- 🟢 **Отлично** (80-100%) - система работает очень хорошо
- 🟡 **Хорошо** (60-79%) - требуются небольшие улучшения  
- 🔴 **Плохо** (<60%) - нужны серьезные доработки

## 💡 Советы по созданию качественных эталонов

### 1. Выбор файлов:
- Используйте реальные прайс-листы поставщиков
- Включайте файлы разной сложности
- Покрывайте разные категории товаров
- Добавляйте файлы с разными языками

### 2. Качество эталонных данных:
- **Точность** - все данные должны быть абсолютно корректными
- **Полнота** - включайте все товары из документа
- **Консистентность** - используйте единые стандарты названий
- **Детальность** - заполняйте все доступные поля

### 3. Стандартизация названий:
- Переводите на английский язык
- Сохраняйте бренды как есть (COCA COLA, INDOMIE)
- Используйте понятные описания (Chicken Flavor Noodles)
- Стандартизируйте единицы (g, ml, kg, l, pcs)

### 4. Категоризация:
Используйте стандартные категории:
- `canned_food` - консервы
- `pasta_noodles` - макароны и лапша
- `beverages` - напитки
- `cooking_oil` - масла для готовки
- `spices_seasonings` - специи и приправы
- `dairy_products` - молочные продукты
- `snacks` - снеки и закуски

## 🔄 Процесс улучшения системы

### 1. Анализ результатов:
- Регулярно тестируйте на эталонных данных
- Анализируйте типичные ошибки
- Выявляйте слабые места системы

### 2. Улучшение промптов:
- Добавляйте специфичные инструкции для проблемных случаев
- Включайте примеры типичных ошибок
- Уточняйте правила стандартизации

### 3. Расширение эталонов:
- Добавляйте новые типы документов
- Включайте edge cases
- Покрывайте разные регионы и языки

## 📈 Мониторинг качества

### Регулярные проверки:
1. **Еженедельно** - тест всех эталонных примеров
2. **После изменений** - полное тестирование
3. **Новые эталоны** - добавление сложных случаев

### Целевые показатели:
- Обнаружение товаров: >90%
- Точность извлечения брендов: >85%
- Точность цен: >95%
- Общая точность: >80%

## 🎯 Быстрый старт

1. **Создайте первый эталон:**
   ```bash
   python3 create_training_example.py
   ```

2. **Протестируйте систему:**
   ```bash  
   python3 test_against_reference.py
   ```

3. **Анализируйте результаты** и улучшайте промпты

4. **Добавляйте новые эталоны** для покрытия edge cases

Система готова к обучению на ваших данных! 🚀