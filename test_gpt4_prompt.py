#!/usr/bin/env python3
"""
Тест нового промпта GPT-4.1 для анализа прайс-листов
"""

import os
import sys
import asyncio
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.batch_chatgpt_processor import BatchChatGPTProcessor
from modules.google_sheets_manager import GoogleSheetsManager
from dotenv import load_dotenv

load_dotenv()

def create_complex_test_file():
    """Создание тестового файла с различными сложностями"""
    print("📊 Создание комплексного тестового файла...")
    
    # Имитируем данные из индонезийского прайс-листа
    test_data = {
        'Brand': [
            'SAPORITO', 'BARILLA', 'MAGGI', 'INDOMIE', '', 'HEINZ', 'DEL MONTE',
            'BLUE BAND', 'TROPICANA', 'COCA COLA', 'PEPSI', 'AQUA', 'BIMOLI'
        ],
        'Product Description': [
            'Baked Bean in tomato sauce 2.65 Kg',
            'Spaghetti No.5 500gr',
            'Seasoning Powder Ayam 1kg',
            'Mi Goreng Rasa Ayam 85g',
            'Minyak Goreng Kelapa Sawit 1L',
            'Tomato Ketchup 340ml',
            'Pineapple Chunks in Syrup 567g',
            'Margarine 200g',
            'Orange Juice 1L',
            'Coca Cola 330ml Can',
            'Pepsi 600ml Bottle',
            'Mineral Water 600ml',
            'Cooking Oil 2L'
        ],
        'Size/Weight': [
            '2.65 kg', '500 gr', '1 kg', '85 gr', '1 L',
            '340 ml', '567 g', '200 g', '1 L', '330 ml',
            '600 ml', '600 ml', '2 L'
        ],
        'Price (Rp)': [
            '90.000', '25.500', '15.750', '3.200', '18.900',
            '12.400', '28.600', '8.500', '35.000', '4.500',
            '7.200', '3.000', '35.800'
        ],
        'Unit': [
            'per piece', 'per piece', 'per piece', 'per piece', 'per piece',
            'per piece', 'per piece', 'per piece', 'per piece', 'per piece',
            'per piece', 'per piece', 'per piece'
        ]
    }
    
    df = pd.DataFrame(test_data)
    
    # Сохраняем файл
    os.makedirs('data/temp', exist_ok=True)
    test_file = 'data/temp/indonesia_price_list_test.xlsx'
    df.to_excel(test_file, index=False, sheet_name='Product List')
    
    print(f"✅ Создан файл: {test_file}")
    print(f"📦 Товаров: {len(df)}")
    print("📋 Образец данных:")
    print(df.head())
    
    return test_file

async def test_gpt4_processing():
    """Тест обработки с новым промптом GPT-4.1"""
    print("\n🤖 ТЕСТ НОВОГО ПРОМПТА GPT-4.1")
    print("=" * 50)
    
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ OpenAI ключ не найден")
        return False
    
    # Создаем тестовые данные
    test_file = create_complex_test_file()
    
    # Читаем созданный файл
    df = pd.read_excel(test_file)
    
    # Подготавливаем данные для обработки
    products = []
    for idx, row in df.iterrows():
        product_name = f"{row.get('Brand', '')} {row.get('Product Description', '')}".strip()
        price_str = str(row.get('Price (Rp)', '0')).replace('.', '').replace(',', '')
        
        try:
            price = float(price_str)
        except:
            price = 0
        
        products.append({
            'original_name': product_name,
            'price': price,
            'unit': 'pcs'
        })
    
    print(f"📦 Подготовлено {len(products)} товаров для обработки")
    
    # Создаем процессор с новым промптом
    processor = BatchChatGPTProcessor(openai_key)
    supplier_name = "PT. GLOBAL ANUGRAH PASIFIK"
    
    print(f"🚀 Обработка через GPT-4.1 с улучшенным промптом...")
    
    # Обрабатываем один пакет для тестирования
    try:
        result = await processor.process_products_batch(products, supplier_name, 0)
        
        if result and 'products' in result:
            processed_products = result.get('products', [])
            
            print(f"✅ Успешно обработано {len(processed_products)} товаров")
            print("\n📄 Примеры обработанных товаров:")
            
            for i, product in enumerate(processed_products[:5]):
                print(f"\n{i+1}. ИСХОДНЫЙ: {product.get('original_name', 'N/A')}")
                print(f"   СТАНДАРТ: {product.get('standardized_name', 'N/A')}")
                print(f"   БРЕНД: {product.get('brand', 'N/A')}")
                print(f"   РАЗМЕР: {product.get('size', 'N/A')}")
                print(f"   ЦЕНА: {product.get('price', 0)} {product.get('currency', 'N/A')}")
                print(f"   КАТЕГОРИЯ: {product.get('category', 'N/A')}")
                print(f"   УВЕРЕННОСТЬ: {product.get('confidence', 0):.2f}")
            
            return result
        else:
            print("❌ Ошибка обработки или пустой результат")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

async def test_google_sheets_integration(processed_data):
    """Тест интеграции с обновленными Google Sheets"""
    print("\n💾 ТЕСТ ОБНОВЛЕННОЙ ИНТЕГРАЦИИ GOOGLE SHEETS")
    print("=" * 50)
    
    if not processed_data:
        print("❌ Нет данных для сохранения")
        return False
    
    gm = GoogleSheetsManager()
    if not gm.is_connected():
        print("❌ Нет подключения к Google Sheets")
        return False
    
    print("✅ Подключение к Google Sheets активно")
    
    # Сохранение данных с новыми полями
    print("💾 Сохранение данных с расширенными полями...")
    
    try:
        sheets_result = gm.update_master_table(processed_data)
        
        if 'error' in sheets_result:
            print(f"❌ Ошибка сохранения: {sheets_result['error']}")
            return False
        
        print(f"✅ Данные сохранены успешно:")
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
        
    except Exception as e:
        print(f"❌ Ошибка интеграции: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТ СИСТЕМЫ С НОВЫМ ПРОМПТОМ GPT-4.1")
    print("=" * 60)
    
    try:
        # 1. Тест обработки GPT-4.1
        processed_data = await test_gpt4_processing()
        
        if not processed_data:
            print("❌ Тест GPT-4.1 не пройден")
            return
        
        # 2. Тест Google Sheets
        sheets_success = await test_google_sheets_integration(processed_data)
        
        # Итоговый отчет
        print("\n" + "=" * 60)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        print("=" * 60)
        
        print("✅ Новый промпт GPT-4.1: РАБОТАЕТ")
        print(f"{'✅' if sheets_success else '❌'} Обновленная интеграция Google Sheets: {'РАБОТАЕТ' if sheets_success else 'ОШИБКА'}")
        
        if processed_data and sheets_success:
            print("\n🎉 СИСТЕМА ГОТОВА К РАБОТЕ С УЛУЧШЕННЫМ ПРОМПТОМ!")
            print("🔗 Новые возможности:")
            print("  • Детальный анализ брендов и размеров")
            print("  • Улучшенная обработка цен и валют")
            print("  • Специализированная обработка азиатских прайс-листов")
            print("  • Расширенная структура данных в Google Sheets")
        else:
            print("\n⚠️ Требуется дополнительная настройка")
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())