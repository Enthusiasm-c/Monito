#!/usr/bin/env python3
"""
Полный тест интеграции с ChatGPT с мониторингом
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
from modules.system_monitor_simple import monitor

def clean_chatgpt_response(content: str) -> str:
    """Улучшенная очистка ответа ChatGPT"""
    content = content.strip()
    
    # Удаление markdown блоков кода
    if content.startswith('```json'):
        content = content[7:]
    elif content.startswith('```'):
        content = content[3:]
        
    if content.endswith('```'):
        content = content[:-3]
    
    content = content.strip()
    
    # Поиск JSON блока в тексте
    import re
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        content = json_match.group(0)
    
    return content

async def test_chatgpt_processing():
    """Тест полной цепочки обработки через ChatGPT"""
    print("🔍 ПОЛНЫЙ ТЕСТ ИНТЕГРАЦИИ С CHATGPT")
    print("=" * 50)
    
    # 1. Проверка API ключа
    print("🔑 Проверка OpenAI API ключа...")
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ OpenAI ключ не найден в .env")
        return False
    print("✅ OpenAI ключ найден")
    
    # 2. Создание тестовых данных
    print("\n📊 Создание тестового Excel файла...")
    test_data = {
        'Product Name': [
            'Apple iPhone 14 Pro 128GB',
            'Samsung Galaxy S23 Ultra',
            'MacBook Pro 14" M2',
            'AirPods Pro 2nd Gen',
            'iPad Air 5th Gen'
        ],
        'Price': [999.99, 1199.99, 1999.99, 249.99, 599.99],
        'Unit': ['pcs', 'pcs', 'pcs', 'pcs', 'pcs']
    }
    
    df = pd.DataFrame(test_data)
    test_file = 'data/temp/test_chatgpt_integration.xlsx'
    os.makedirs('data/temp', exist_ok=True)
    df.to_excel(test_file, index=False)
    print(f"✅ Создан тестовый файл: {test_file}")
    
    # 3. Извлечение данных из Excel
    print("\n📄 Извлечение данных из Excel...")
    supplier_name = "ChatGPT_Test_Store"
    
    products = []
    for idx, row in df.iterrows():
        products.append({
            'original_name': row['Product Name'],
            'price': row['Price'],
            'unit': row['Unit']
        })
    
    extracted_data = {
        'file_type': 'excel',
        'supplier': {'name': supplier_name},
        'products': products
    }
    
    print(f"✅ Извлечено товаров: {len(products)}")
    monitor.record_file_processing('excel', True)
    
    # 4. Обработка через ChatGPT
    print("\n🤖 Обработка данных через ChatGPT...")
    try:
        import requests
        
        # Подготовка данных для ChatGPT
        products_text = ""
        for i, product in enumerate(products, 1):
            products_text += f"{i}. {product['original_name']} | {product['price']} | {product['unit']}\n"
        
        prompt = f"""Проанализируй прайс-лист поставщика "{supplier_name}" и стандартизируй данные.

ТОВАРЫ:
{products_text}

Верни JSON в строгом формате:
{{
  "supplier": {{
    "name": "стандартизированное название поставщика",
    "contact": "",
    "confidence": 0.9
  }},
  "products": [
    {{
      "original_name": "исходное название",
      "standardized_name": "Стандартизированное название на английском",
      "price": цена_число,
      "unit": "стандартная_единица(pcs/kg/l/m/box)",
      "category": "категория_товара",
      "confidence": 0.95
    }}
  ],
  "data_quality": {{
    "extraction_confidence": 0.9,
    "source_clarity": "high",
    "potential_errors": []
  }}
}}

ПРАВИЛА:
- Переводи названия товаров на английский
- Стандартизируй единицы: шт→pcs, кг→kg, л→l, м→m
- Определи категории: electronics, food, materials, etc.
- Убери лишние символы и сокращения
- Сохраняй оригинальные названия в original_name"""
        
        headers = {
            'Authorization': f'Bearer {openai_key}',
            'Content-Type': 'application/json'
        }
        
        data_payload = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {'role': 'system', 'content': 'Ты эксперт по стандартизации товарных данных. Отвечай только валидным JSON без комментариев.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 2000,
            'temperature': 0.1
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data_payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Очистка ответа
            content = clean_chatgpt_response(content)
            
            print("✅ ChatGPT ответил успешно")
            print("📄 Ответ (первые 300 символов):")
            print(content[:300] + "..." if len(content) > 300 else content)
            
            # Парсинг JSON
            try:
                standardized_data = json.loads(content)
                products_count = len(standardized_data.get('products', []))
                tokens_used = result.get('usage', {}).get('total_tokens', 0)
                
                print(f"✅ JSON валидный")
                print(f"📦 Обработано товаров: {products_count}")
                print(f"🎯 Токенов использовано: {tokens_used}")
                
                monitor.record_chatgpt_request(True, tokens_used)
                
            except json.JSONDecodeError as e:
                print(f"❌ Невалидный JSON: {e}")
                print("📄 Полный ответ:")
                print(content)
                monitor.record_chatgpt_request(False, 0, f"JSON Error: {e}")
                return False
                
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            print(f"❌ Ошибка ChatGPT API: {error_msg}")
            monitor.record_chatgpt_request(False, 0, error_msg)
            return False
    
    except Exception as e:
        error_msg = f"Request Error: {e}"
        print(f"❌ Ошибка запроса: {error_msg}")
        monitor.record_chatgpt_request(False, 0, error_msg)
        return False
    
    # 5. Сохранение в Google Sheets
    print("\n💾 Сохранение в Google Sheets...")
    try:
        gm = GoogleSheetsManager()
        if not gm.is_connected():
            print("❌ Нет подключения к Google Sheets")
            monitor.record_sheets_update(False, 0, "No connection")
            return False
        
        # Обновление основной таблицы
        sheets_result = gm.update_master_table(standardized_data)
        
        if 'error' in sheets_result:
            print(f"❌ Ошибка сохранения: {sheets_result['error']}")
            monitor.record_sheets_update(False, 0, sheets_result['error'])
            return False
        
        # Создание листа поставщика
        supplier_name = standardized_data.get('supplier', {}).get('name', 'Unknown')
        gm.create_supplier_summary(supplier_name, standardized_data.get('products', []))
        
        print(f"✅ Данные сохранены в Google Sheets")
        print(f"📊 Новых товаров: {sheets_result.get('new_products', 0)}")
        print(f"📊 Обновленных цен: {sheets_result.get('updated_prices', 0)}")
        print(f"🔗 Таблица: {gm.get_sheet_url()}")
        
        monitor.record_sheets_update(True, len(standardized_data.get('products', [])))
        
    except Exception as e:
        error_msg = f"Sheets Error: {e}"
        print(f"❌ Ошибка Google Sheets: {error_msg}")
        monitor.record_sheets_update(False, 0, error_msg)
        return False
    
    # 6. Финальная статистика
    print("\n" + "=" * 50)
    print("📊 РЕЗУЛЬТАТЫ ПОЛНОГО ТЕСТА")
    print("=" * 50)
    print(monitor.get_formatted_report())
    
    print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("✅ ChatGPT интеграция работает полностью")
    print("✅ Google Sheets интеграция функциональна")
    print("✅ Мониторинг записывает статистику")
    
    return True

async def main():
    """Основная функция"""
    try:
        success = await test_chatgpt_processing()
        
        if success:
            print("\n🚀 Система готова к полноценной работе!")
        else:
            print("\n⚠️ Требуются дополнительные исправления")
            
    except Exception as e:
        print(f"❌ Критическая ошибка теста: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())