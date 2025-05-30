#!/usr/bin/env python3
"""
Демо-тест основных компонентов системы без внешних API
"""

import os
import sys
import asyncio
from datetime import datetime

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_config():
    """Тест загрузки конфигурации"""
    print("🔧 Тест конфигурации...")
    try:
        from config import MASTER_TABLE_PATH, PDF_CONFIG, GPT_CONFIG
        print(f"✅ Конфигурация загружена")
        print(f"   - Путь к основной таблице: {MASTER_TABLE_PATH}")
        print(f"   - PDF DPI: {PDF_CONFIG['DPI']}")
        print(f"   - GPT модель: {GPT_CONFIG['MODEL']}")
        return True
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return False

def test_utils():
    """Тест утилитарных функций"""
    print("\n🔧 Тест утилит...")
    try:
        from modules.utils import validate_file, clean_text, calculate_similarity
        
        # Тест валидации файла
        result = validate_file("test.xlsx", 1024*1024)  # 1MB
        print(f"✅ Валидация файла: {result['valid']}")
        
        # Тест очистки текста
        cleaned = clean_text("  Тест   текста  \n\r")
        print(f"✅ Очистка текста: '{cleaned}'")
        
        # Тест similarity
        similarity = calculate_similarity("Apple iPhone 13", "iPhone 13 Apple")
        print(f"✅ Similarity: {similarity:.2f}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка утилит: {e}")
        return False

def test_data_manager():
    """Тест менеджера данных"""
    print("\n💾 Тест менеджера данных...")
    try:
        from modules.data_manager import DataManager
        
        dm = DataManager()
        
        # Тест получения статистики
        stats = dm.get_processing_stats()
        print(f"✅ Статистика получена: {len(stats)} параметров")
        
        # Тест сводки таблицы
        summary = dm.get_table_summary()
        print(f"✅ Сводка таблицы: {summary.get('total_products', 0)} товаров")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка менеджера данных: {e}")
        return False

async def test_file_processor():
    """Тест обработчика файлов (без реальных файлов)"""
    print("\n📊 Тест обработчика файлов...")
    try:
        from modules.file_processor import FileProcessor
        
        fp = FileProcessor()
        
        # Тест определения типа PDF (без файла)
        print("✅ FileProcessor инициализирован")
        print(f"   - Поддерживаемые расширения: {fp.supported_extensions}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка обработчика файлов: {e}")
        return False

def test_monitoring():
    """Тест системы мониторинга"""
    print("\n📈 Тест мониторинга...")
    try:
        from monitoring.metrics import MetricsCollector
        
        mc = MetricsCollector()
        
        # Тест сбора системных метрик
        system_metrics = mc.collect_system_metrics()
        print(f"✅ Системные метрики: CPU {system_metrics.cpu_percent:.1f}%")
        
        # Тест сбора бизнес метрик
        business_metrics = mc.collect_business_metrics()
        print(f"✅ Бизнес метрики: {business_metrics.total_products} товаров")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка мониторинга: {e}")
        return False

def create_demo_excel_file():
    """Создание демо Excel файла для тестирования"""
    print("\n📁 Создание демо файла...")
    try:
        import pandas as pd
        
        # Создание демо данных
        demo_data = {
            'Product Name': [
                'Apple iPhone 13 128GB',
                'Samsung Galaxy S21',
                'MacBook Pro 13"',
                'Dell XPS 15',
                'AirPods Pro'
            ],
            'Price': [699.99, 599.99, 1299.99, 1199.99, 249.99],
            'Unit': ['pcs', 'pcs', 'pcs', 'pcs', 'pcs'],
            'Stock': [50, 30, 15, 8, 100]
        }
        
        df = pd.DataFrame(demo_data)
        
        # Сохранение файла
        os.makedirs('data/temp', exist_ok=True)
        demo_file = 'data/temp/demo_price_list.xlsx'
        df.to_excel(demo_file, index=False)
        
        print(f"✅ Демо файл создан: {demo_file}")
        print(f"   - Товаров: {len(demo_data['Product Name'])}")
        
        return demo_file
    except Exception as e:
        print(f"❌ Ошибка создания демо файла: {e}")
        return None

async def test_file_processing_with_demo():
    """Тест обработки демо файла"""
    print("\n🔄 Тест обработки демо файла...")
    
    # Создаем демо файл
    demo_file = create_demo_excel_file()
    if not demo_file:
        return False
    
    try:
        from modules.file_processor import FileProcessor
        
        fp = FileProcessor()
        
        # Обработка демо файла
        result = await fp.process_file(demo_file)
        
        print(f"✅ Файл обработан успешно:")
        print(f"   - Тип файла: {result.get('file_type')}")
        print(f"   - Товаров извлечено: {len(result.get('products', []))}")
        print(f"   - Поставщик: {result.get('supplier', {}).get('name', 'Неизвестен')}")
        
        # Показать первый товар
        if result.get('products'):
            first_product = result['products'][0]
            print(f"   - Первый товар: {first_product.get('original_name')} - ${first_product.get('price')}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка обработки файла: {e}")
        return False

def print_setup_instructions():
    """Инструкции по настройке для полного тестирования"""
    print("\n" + "="*60)
    print("🚀 ИНСТРУКЦИИ ПО ПОЛНОЙ НАСТРОЙКЕ")
    print("="*60)
    print()
    print("Для полного тестирования системы выполните:")
    print()
    print("1️⃣ Получите Telegram Bot Token:")
    print("   • Напишите @BotFather в Telegram")
    print("   • Отправьте /newbot")
    print("   • Следуйте инструкциям")
    print("   • Скопируйте полученный токен")
    print()
    print("2️⃣ Получите OpenAI API Key:")
    print("   • Зайдите на https://platform.openai.com/api-keys")
    print("   • Создайте новый ключ")
    print("   • Убедитесь что у вас есть credits")
    print()
    print("3️⃣ Заполните .env файл:")
    print("   TELEGRAM_BOT_TOKEN=ваш_токен_бота")
    print("   OPENAI_API_KEY=ваш_ключ_openai")
    print("   ENVIRONMENT=development")
    print("   LOG_LEVEL=DEBUG")
    print()
    print("4️⃣ Установите Tesseract для PDF:")
    print("   # Ubuntu/Debian:")
    print("   sudo apt install tesseract-ocr tesseract-ocr-eng")
    print("   # macOS:")
    print("   brew install tesseract")
    print("   # Windows: скачайте с GitHub")
    print()
    print("5️⃣ Запустите систему:")
    print("   python main.py")
    print()
    print("="*60)

async def main():
    """Главная функция демо-теста"""
    print("🔍 ДЕМО-ТЕСТ СИСТЕМЫ АНАЛИЗА ПРАЙС-ЛИСТОВ")
    print("="*60)
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Список тестов
    tests = [
        ("Конфигурация", test_config),
        ("Утилиты", test_utils),
        ("Менеджер данных", test_data_manager),
        ("Обработчик файлов", test_file_processor),
        ("Мониторинг", test_monitoring),
        ("Обработка демо файла", test_file_processing_with_demo),
    ]
    
    passed = 0
    failed = 0
    
    # Выполнение тестов
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте '{test_name}': {e}")
            failed += 1
    
    # Результаты
    print(f"\n{'='*60}")
    print(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print(f"{'='*60}")
    print(f"✅ Пройдено: {passed}")
    print(f"❌ Не пройдено: {failed}")
    print(f"📈 Процент успеха: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print(f"\n🎉 Все базовые компоненты работают корректно!")
        print(f"💡 Система готова к настройке внешних API")
    else:
        print(f"\n⚠️  Обнаружены проблемы в {failed} компонентах")
        print(f"🔧 Проверьте установку зависимостей")
    
    # Инструкции по настройке
    print_setup_instructions()

if __name__ == "__main__":
    asyncio.run(main())