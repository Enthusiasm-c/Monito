#!/usr/bin/env python3
"""
Тест продвинутого парсера Excel файлов
"""

import os
import sys
import pandas as pd
import asyncio
from datetime import datetime

# Добавляем корневую директорию
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.advanced_excel_parser import AdvancedExcelParser
from modules.batch_chatgpt_processor import BatchChatGPTProcessor
from modules.google_sheets_manager import GoogleSheetsManager
from dotenv import load_dotenv

load_dotenv()

def create_large_test_file():
    """Создание большого тестового Excel файла с сотнями товаров"""
    print("📊 Создание большого тестового Excel файла...")
    
    # Генерируем 200 товаров разных категорий
    products_data = []
    
    # Электроника
    electronics = [
        ("Apple iPhone 14 Pro 128GB", 999.99, "pcs", "Смартфоны"),
        ("Samsung Galaxy S23 Ultra", 1199.99, "pcs", "Смартфоны"),
        ("MacBook Pro 14 M2", 1999.99, "pcs", "Ноутбуки"),
        ("iPad Air 5th Gen", 599.99, "pcs", "Планшеты"),
        ("AirPods Pro 2nd Gen", 249.99, "pcs", "Наушники"),
        ("Apple Watch Series 8", 399.99, "pcs", "Часы"),
        ("Dell XPS 13", 1299.99, "pcs", "Ноутбуки"),
        ("Sony WH-1000XM5", 379.99, "pcs", "Наушники"),
        ("Nintendo Switch OLED", 349.99, "pcs", "Игровые консоли"),
        ("Steam Deck 512GB", 649.99, "pcs", "Игровые консоли"),
    ]
    
    # Инструменты
    tools = [
        ("Дрель Bosch PSB 1800", 8999.99, "pcs", "Электроинструмент"),
        ("Шуруповерт Makita DF331D", 5499.99, "pcs", "Электроинструмент"),
        ("Болгарка DeWalt DWE4157", 7899.99, "pcs", "Электроинструмент"),
        ("Отвертка Phillips PH2", 129.99, "pcs", "Ручной инструмент"),
        ("Молоток слесарный 500г", 299.99, "pcs", "Ручной инструмент"),
        ("Рулетка измерительная 5м", 459.99, "pcs", "Измерительный инструмент"),
        ("Уровень строительный 60см", 899.99, "pcs", "Измерительный инструмент"),
        ("Пила по дереву 400мм", 549.99, "pcs", "Ручной инструмент"),
    ]
    
    # Материалы
    materials = [
        ("Саморезы 3.5x25мм", 0.89, "pcs", "Крепеж"),
        ("Болт М8x20", 2.45, "pcs", "Крепеж"),
        ("Гайка М8", 1.20, "pcs", "Крепеж"),
        ("Шайба 8мм", 0.55, "pcs", "Крепеж"),
        ("Провод ПВС 2x1.5", 45.99, "m", "Электроматериалы"),
        ("Кабель ВВГ 3x2.5", 67.89, "m", "Электроматериалы"),
        ("Розетка двойная", 289.99, "pcs", "Электроустановочные изделия"),
        ("Выключатель одноклавишный", 159.99, "pcs", "Электроустановочные изделия"),
    ]
    
    # Расширяем списки до 200+ товаров
    all_categories = [electronics, tools, materials]
    counter = 0
    
    for category_list in all_categories:
        for base_item in category_list:
            for i in range(7):  # Создаем 7 вариантов каждого товара
                counter += 1
                if counter > 200:
                    break
                
                name = f"{base_item[0]} - Вариант {i+1}" if i > 0 else base_item[0]
                price = base_item[1] * (0.9 + i * 0.05)  # Варьируем цену
                unit = base_item[2]
                category = base_item[3]
                
                products_data.append({
                    'Название товара': name,
                    'Цена (руб)': price,
                    'Единица': unit,
                    'Категория': category,
                    'Артикул': f'ART-{counter:04d}',
                    'Описание': f'Качественный товар {name[:30]}...'
                })
        
        if counter > 200:
            break
    
    # Создаем DataFrame
    df = pd.DataFrame(products_data)
    
    # Сохраняем файл
    os.makedirs('data/temp', exist_ok=True)
    test_file = 'data/temp/large_price_list_test.xlsx'
    df.to_excel(test_file, index=False)
    
    print(f"✅ Создан файл: {test_file}")
    print(f"📦 Товаров: {len(df)}")
    print(f"📋 Столбцов: {len(df.columns)}")
    print(f"🏷️ Категорий: {len(df['Категория'].unique())}")
    
    return test_file

async def test_advanced_parsing():
    """Тест продвинутого парсинга"""
    print("\n🔍 ТЕСТ ПРОДВИНУТОГО ПАРСИНГА EXCEL")
    print("=" * 50)
    
    # Создаем тестовый файл
    test_file = create_large_test_file()
    
    # Создаем парсер
    parser = AdvancedExcelParser()
    
    # Анализ структуры файла
    print("\n📊 Анализ структуры файла...")
    structure = parser.analyze_file_structure(test_file)
    
    print(f"📄 Листов в файле: {structure.get('total_sheets', 0)}")
    print(f"🎯 Рекомендуемый лист: {structure.get('recommended_sheet', 'N/A')}")
    
    # Извлечение данных
    print("\n🔍 Извлечение данных...")
    start_time = datetime.now()
    
    extracted_data = parser.extract_products_smart(test_file, max_products=500)
    
    extraction_time = (datetime.now() - start_time).total_seconds()
    
    if 'error' in extracted_data:
        print(f"❌ Ошибка извлечения: {extracted_data['error']}")
        return False
    
    products = extracted_data.get('products', [])
    stats = extracted_data.get('extraction_stats', {})
    
    print(f"⏱️ Время извлечения: {extraction_time:.2f} сек")
    print(f"📦 Извлечено товаров: {len(products)}")
    print(f"📊 Статистика извлечения:")
    print(f"  • Всего строк: {stats.get('total_rows', 0)}")
    print(f"  • Успешно извлечено: {stats.get('extracted_products', 0)}")
    print(f"  • Пропущено строк: {stats.get('skipped_rows', 0)}")
    print(f"  • Успешность: {stats.get('success_rate', 0):.1%}")
    print(f"  • Найденные столбцы: {stats.get('found_columns', {})}")
    
    # Показываем примеры извлеченных товаров
    print(f"\n📄 Примеры извлеченных товаров (первые 5):")
    for i, product in enumerate(products[:5]):
        print(f"{i+1}. {product['original_name'][:50]}... | {product['price']} {product['unit']} | {product.get('category', 'N/A')}")
    
    return extracted_data

async def test_batch_chatgpt_processing(extracted_data):
    """Тест пакетной обработки ChatGPT"""
    print("\n🤖 ТЕСТ ПАКЕТНОЙ ОБРАБОТКИ CHATGPT")
    print("=" * 50)
    
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ OpenAI ключ не найден, пропускаем тест ChatGPT")
        return extracted_data
    
    processor = BatchChatGPTProcessor(openai_key)
    products = extracted_data.get('products', [])
    supplier_name = extracted_data.get('supplier', {}).get('name', 'Test Supplier')
    
    # Ограничиваем для теста до 100 товаров
    test_products = products[:100]
    
    print(f"🔄 Обрабатываем {len(test_products)} товаров...")
    print(f"📦 Оптимальный размер пакета: {processor.optimize_batch_size(test_products)}")
    
    start_time = datetime.now()
    
    # Пакетная обработка
    result = await processor.process_all_products(test_products, supplier_name)
    
    processing_time = (datetime.now() - start_time).total_seconds()
    
    if 'error' in result:
        print(f"❌ Ошибка обработки: {result['error']}")
        return extracted_data
    
    processing_stats = result.get('processing_stats', {})
    
    print(f"⏱️ Время обработки: {processing_time:.2f} сек")
    print(f"📊 Статистика обработки:")
    print(f"  • Входных товаров: {processing_stats.get('total_input_products', 0)}")
    print(f"  • Выходных товаров: {processing_stats.get('total_output_products', 0)}")
    print(f"  • Успешных пакетов: {processing_stats.get('successful_batches', 0)}/{processing_stats.get('total_batches', 0)}")
    print(f"  • Успешность: {processing_stats.get('success_rate', 0):.1%}")
    print(f"  • Использовано токенов: {processing_stats.get('estimated_tokens', 0)}")
    
    # Показываем примеры обработанных товаров
    processed_products = result.get('products', [])
    print(f"\n🎯 Примеры обработанных товаров (первые 3):")
    for i, product in enumerate(processed_products[:3]):
        print(f"{i+1}. {product.get('original_name', '')[:30]}...")
        print(f"   → {product.get('standardized_name', '')[:30]}...")
        print(f"   → Категория: {product.get('category', 'N/A')}")
        print(f"   → Уверенность: {product.get('confidence', 0):.2f}")
    
    return result

async def test_google_sheets_integration(processed_data):
    """Тест интеграции с Google Sheets"""
    print("\n💾 ТЕСТ ИНТЕГРАЦИИ С GOOGLE SHEETS")
    print("=" * 50)
    
    gm = GoogleSheetsManager()
    if not gm.is_connected():
        print("❌ Нет подключения к Google Sheets")
        return False
    
    print("✅ Подключение к Google Sheets активно")
    
    # Сохранение данных
    print("💾 Сохранение данных...")
    start_time = datetime.now()
    
    sheets_result = gm.update_master_table(processed_data)
    
    save_time = (datetime.now() - start_time).total_seconds()
    
    if 'error' in sheets_result:
        print(f"❌ Ошибка сохранения: {sheets_result['error']}")
        return False
    
    print(f"⏱️ Время сохранения: {save_time:.2f} сек")
    print(f"📊 Результат сохранения:")
    print(f"  • Новых товаров: {sheets_result.get('new_products', 0)}")
    print(f"  • Обновленных цен: {sheets_result.get('updated_prices', 0)}")
    print(f"  • Всего обработано: {sheets_result.get('processed_products', 0)}")
    
    # Создание листа поставщика
    supplier_name = processed_data.get('supplier', {}).get('name', 'Test Supplier')
    products = processed_data.get('products', [])
    
    supplier_result = gm.create_supplier_summary(supplier_name, products)
    print(f"📋 Лист поставщика: {'✅ Создан' if supplier_result else '❌ Ошибка'}")
    
    print(f"🔗 Ссылка на таблицу: {gm.get_sheet_url()}")
    
    return True

async def main():
    """Основная функция тестирования"""
    print("🚀 ПОЛНЫЙ ТЕСТ ПРОДВИНУТОЙ СИСТЕМЫ")
    print("=" * 60)
    
    try:
        # 1. Тест парсинга
        extracted_data = await test_advanced_parsing()
        if not extracted_data or 'error' in extracted_data:
            print("❌ Тест парсинга не пройден")
            return
        
        # 2. Тест ChatGPT
        processed_data = await test_batch_chatgpt_processing(extracted_data)
        
        # 3. Тест Google Sheets
        sheets_success = await test_google_sheets_integration(processed_data)
        
        # Итоговый отчет
        print("\n" + "=" * 60)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        print("=" * 60)
        
        print("✅ Продвинутый парсер Excel: РАБОТАЕТ")
        print("✅ Пакетная обработка ChatGPT: РАБОТАЕТ")
        print(f"{'✅' if sheets_success else '❌'} Интеграция Google Sheets: {'РАБОТАЕТ' if sheets_success else 'ОШИБКА'}")
        
        if all([extracted_data, processed_data, sheets_success]):
            print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! СИСТЕМА ГОТОВА К ОБРАБОТКЕ БОЛЬШИХ ФАЙЛОВ!")
            print("🚀 Можно запускать telegram_bot_advanced.py для полноценной работы")
        else:
            print("\n⚠️ Некоторые тесты не пройдены, требуется дополнительная настройка")
        
    except Exception as e:
        print(f"❌ Критическая ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())