#!/usr/bin/env python3
"""
Отладка парсера для диагностики проблем с извлечением данных
"""

import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.advanced_excel_parser import AdvancedExcelParser

def debug_excel_parsing():
    """Отладка парсинга Excel файла"""
    print("🔍 ДИАГНОСТИКА ПАРСЕРА EXCEL")
    print("=" * 50)
    
    # Создаем тестовый файл с проблемными данными
    test_data = {
        'Unnamed: 0': ['Product A', 'Product B', 'Product C', '', 'nan', 123, 'Good Product'],
        '    Prices': [100.50, '200,30', '$300.00', '', 'nan', 'invalid', 450],
        'unit': ['pcs', 'kg', '', 'pcs', 'nan', '', 'box'],
        'category': ['electronics', 'food', '', '', '', '', 'tools']
    }
    
    df = pd.DataFrame(test_data)
    
    # Сохраняем тестовый файл
    os.makedirs('data/temp', exist_ok=True)
    test_file = 'data/temp/debug_test.xlsx'
    df.to_excel(test_file, index=False)
    
    print(f"📊 Создан тестовый файл: {test_file}")
    print(f"📋 Данные для тестирования:")
    print(df)
    print()
    
    # Создаем парсер
    parser = AdvancedExcelParser()
    
    # Анализ структуры
    print("🔍 Анализ структуры файла...")
    structure = parser.analyze_file_structure(test_file)
    print(f"Структура: {structure}")
    print()
    
    # Читаем файл
    df_read = pd.read_excel(test_file)
    print("📄 Прочитанные данные:")
    print(df_read)
    print()
    
    # Поиск столбцов
    print("🔎 Поиск столбцов...")
    columns = parser.find_columns(df_read)
    print(f"Найденные столбцы: {columns}")
    print()
    
    # Тестируем извлечение для каждой строки
    print("📦 Тестирование извлечения товаров:")
    for idx, row in df_read.iterrows():
        print(f"Строка {idx}:")
        
        # Название
        name = parser._extract_product_name(row, columns['product'])
        print(f"  Название: '{row[columns['product']]}' → '{name}'")
        
        # Цена
        price = parser._extract_price(row, columns['price'], df_read.columns)
        print(f"  Цена: '{row[columns['price']]}' → {price}")
        
        # Единица
        unit = parser._extract_unit(row, columns['unit'])
        print(f"  Единица: '{row[columns['unit']]}' → '{unit}'")
        
        # Валидность
        valid = name and len(str(name)) > 1 and price > 0
        print(f"  ✅ Валидный товар: {valid}")
        print()
    
    # Полное извлечение
    print("🚀 Полное извлечение товаров:")
    result = parser.extract_products_smart(test_file)
    
    if 'error' in result:
        print(f"❌ Ошибка: {result['error']}")
    else:
        products = result.get('products', [])
        stats = result.get('extraction_stats', {})
        
        print(f"📊 Статистика извлечения:")
        print(f"  Всего строк: {stats.get('total_rows', 0)}")
        print(f"  Извлечено товаров: {stats.get('extracted_products', 0)}")
        print(f"  Пропущено строк: {stats.get('skipped_rows', 0)}")
        print(f"  Успешность: {stats.get('success_rate', 0):.1%}")
        
        print(f"\n📦 Извлеченные товары:")
        for i, product in enumerate(products):
            print(f"  {i+1}. {product['original_name']} | {product['price']} {product['unit']}")

def test_price_parsing():
    """Тест парсинга различных форматов цен"""
    print("\n💰 ТЕСТ ПАРСИНГА ЦЕН")
    print("=" * 50)
    
    parser = AdvancedExcelParser()
    
    test_prices = [
        "100.50",
        "1,000.50", 
        "1.000,50",
        "$100.00",
        "200 руб",
        "300₽",
        "1 234,56",
        "1.234.567,89",
        "",
        "nan",
        "invalid",
        "0",
        "-100",
        "999999999",
        100.50,  # число
        "1.23.45"  # неясный формат
    ]
    
    for price_str in test_prices:
        result = parser._parse_price_string(str(price_str))
        print(f"'{price_str}' → {result}")

if __name__ == "__main__":
    debug_excel_parsing()
    test_price_parsing()