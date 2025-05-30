#!/usr/bin/env python3
"""
Полное тестирование обработки файла с ChatGPT и Google Sheets
"""

import os
import sys
import json
import asyncio
import pandas as pd
from datetime import datetime

# Добавляем корневую директорию
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from modules.google_sheets_manager import GoogleSheetsManager

def test_chatgpt_simple():
    """Простой тест ChatGPT без сложных библиотек"""
    import requests
    
    print("🤖 Тест ChatGPT API...")
    
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ OpenAI ключ не найден")
        return False
    
    headers = {
        'Authorization': f'Bearer {openai_key}',
        'Content-Type': 'application/json'
    }
    
    # Тест с реальными данными прайс-листа
    test_data = """
Product Name: Apple iPhone 13 128GB
Price: 699.99
Unit: pcs

Product Name: Samsung Galaxy S21
Price: 599.99  
Unit: pcs
    """
    
    prompt = f"""Проанализируй данные прайс-листа и верни JSON:

{test_data}

Верни JSON в формате:
{{
  "supplier": {{"name": "Test Supplier"}},
  "products": [
    {{
      "original_name": "исходное название",
      "standardized_name": "Standard Product Name EN", 
      "price": 100.50,
      "unit": "pcs",
      "category": "electronics",
      "confidence": 0.95
    }}
  ]
}}"""
    
    data = {
        'model': 'gpt-3.5-turbo',
        'messages': [
            {'role': 'system', 'content': 'Ты эксперт по стандартизации товарных данных. Отвечай только JSON.'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 500,
        'temperature': 0.1
    }
    
    try:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print("✅ ChatGPT ответил:")
            print(content[:200] + "..." if len(content) > 200 else content)
            
            # Попытка парсинга JSON
            try:
                parsed = json.loads(content)
                print("✅ JSON валидный")
                return True
            except json.JSONDecodeError:
                print("⚠️ Ответ не является валидным JSON")
                return False
        else:
            print(f"❌ Ошибка API: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return False

async def test_excel_processing():
    """Тест обработки Excel файла"""
    print("\n📊 Тест обработки Excel файла...")
    
    # Создание тестового Excel файла
    test_data = {
        'Product Name': [
            'Apple iPhone 14 Pro 128GB',
            'Samsung Galaxy S23 Ultra',
            'MacBook Pro 14" M2',
            'iPad Air 5th Gen',
            'AirPods Pro 2nd Gen'
        ],
        'Price': [999.99, 1199.99, 1999.99, 599.99, 249.99],
        'Unit': ['pcs', 'pcs', 'pcs', 'pcs', 'pcs'],
        'Category': ['phone', 'phone', 'laptop', 'tablet', 'accessory']
    }
    
    df = pd.DataFrame(test_data)
    test_file = 'data/temp/test_processing.xlsx'
    os.makedirs('data/temp', exist_ok=True)
    df.to_excel(test_file, index=False)
    print(f"✅ Создан тестовый файл: {test_file}")
    
    # Чтение и парсинг файла
    df_read = pd.read_excel(test_file)
    print(f"✅ Файл прочитан: {len(df_read)} строк")
    
    # Поиск столбцов
    product_col = None
    price_col = None
    
    for col in df_read.columns:
        col_lower = str(col).lower()
        if 'product' in col_lower or 'name' in col_lower:
            product_col = col
        if 'price' in col_lower:
            price_col = col
    
    print(f"Найдены столбцы - товары: {product_col}, цены: {price_col}")
    
    # Извлечение данных
    products = []
    for idx, row in df_read.iterrows():
        name = str(row[product_col]) if product_col else str(row.iloc[0])
        price = float(row[price_col]) if price_col else 0
        
        if len(name) > 3 and price > 0:
            products.append({
                'original_name': name,
                'price': price,
                'unit': 'pcs'
            })
    
    print(f"✅ Извлечено товаров: {len(products)}")
    return products

async def test_google_sheets_save(products):
    """Тест сохранения в Google Sheets"""
    print("\n💾 Тест сохранения в Google Sheets...")
    
    gm = GoogleSheetsManager()
    if not gm.is_connected():
        print("❌ Нет подключения к Google Sheets")
        return False
    
    # Подготовка данных для сохранения
    standardized_data = {
        'supplier': {
            'name': 'Test Electronics Store',
            'contact': 'test@example.com',
            'confidence': 0.9
        },
        'products': [
            {
                'original_name': p['original_name'],
                'standardized_name': p['original_name'],  # Упрощенная стандартизация
                'price': p['price'],
                'unit': p['unit'],
                'category': 'electronics',
                'confidence': 0.8
            }
            for p in products
        ],
        'data_quality': {
            'extraction_confidence': 0.85,
            'source_clarity': 'high',
            'potential_errors': []
        }
    }
    
    print(f"Подготовлено товаров для сохранения: {len(standardized_data['products'])}")
    
    # Сохранение в Google Sheets
    try:
        result = gm.update_master_table(standardized_data)
        print(f"✅ Результат сохранения: {result}")
        
        # Создание листа поставщика
        supplier_result = gm.create_supplier_summary(
            'Test Electronics Store', 
            standardized_data['products']
        )
        print(f"✅ Лист поставщика создан: {supplier_result}")
        
        # Проверка сохранения
        stats = gm.get_stats()
        print(f"📊 Обновленная статистика:")
        print(f"  Товаров: {stats.get('total_products', 0)}")
        print(f"  Поставщиков: {stats.get('total_suppliers', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_complete_workflow():
    """Полный тест рабочего процесса"""
    print("🔍 ПОЛНЫЙ ТЕСТ СИСТЕМЫ")
    print("="*50)
    
    # 1. Тест ChatGPT
    chatgpt_ok = test_chatgpt_simple()
    
    # 2. Тест Excel обработки
    products = await test_excel_processing()
    excel_ok = len(products) > 0
    
    # 3. Тест Google Sheets
    sheets_ok = await test_google_sheets_save(products) if excel_ok else False
    
    print("\n" + "="*50)
    print("📋 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print("="*50)
    print(f"🤖 ChatGPT API: {'✅' if chatgpt_ok else '❌'}")
    print(f"📊 Excel обработка: {'✅' if excel_ok else '❌'}")
    print(f"💾 Google Sheets: {'✅' if sheets_ok else '❌'}")
    
    if all([chatgpt_ok, excel_ok, sheets_ok]):
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система работает полностью.")
        print("🔗 Проверьте Google Sheets таблицу:")
        
        gm = GoogleSheetsManager()
        print(gm.get_sheet_url())
    else:
        print("\n⚠️ Есть проблемы, которые нужно исправить.")

if __name__ == "__main__":
    asyncio.run(test_complete_workflow())