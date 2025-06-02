#!/usr/bin/env python3
"""
Прямая загрузка и обработка файла через систему
"""

import os
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.universal_excel_parser import UniversalExcelParser
from modules.pdf_parser import PDFParser
from modules.batch_chatgpt_processor import BatchChatGPTProcessor
from modules.google_sheets_manager import GoogleSheetsManager
from dotenv import load_dotenv

load_dotenv()

async def process_file_directly(file_path: str):
    """Прямая обработка файла"""
    print("📁 ПРЯМАЯ ОБРАБОТКА ФАЙЛА")
    print("=" * 40)
    
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        return None
    
    print(f"📄 Файл: {file_path}")
    
    # 1. Определение типа файла и парсинг
    print("\n🔍 Анализ файла...")
    file_extension = Path(file_path).suffix.lower()
    
    if file_extension == '.pdf':
        print("📄 Обрабатываю PDF файл (с AI-анализом)...")
        parser = PDFParser()
        extracted_data = parser.extract_products_from_pdf(file_path, max_products=1000, use_ai=True)
    elif file_extension in ['.xlsx', '.xls']:
        print("📊 Обрабатываю Excel файл (с AI-анализом)...")
        parser = UniversalExcelParser()
        extracted_data = parser.extract_products_universal(file_path, max_products=1000, use_ai=True)
    else:
        print(f"❌ Неподдерживаемый формат файла: {file_extension}")
        return None
    
    if 'error' in extracted_data:
        print(f"❌ Ошибка парсинга: {extracted_data['error']}")
        return None
    
    products = extracted_data.get('products', [])
    stats = extracted_data.get('extraction_stats', {})
    
    print(f"✅ Извлечено товаров: {len(products)}")
    print(f"📊 Успешность: {stats.get('success_rate', 0):.1%}")
    print(f"🔧 Метод извлечения: {stats.get('extraction_method', 'N/A')}")
    print(f"🤖 AI Enhanced: {stats.get('ai_enhanced', False)}")
    if stats.get('used_sheet'):
        print(f"📋 Использован лист: {stats.get('used_sheet', 'N/A')}")
    
    if not products:
        print("❌ Товары не найдены")
        return None
    
    # Показываем примеры
    print(f"\n📦 Примеры извлеченных товаров:")
    for i, product in enumerate(products[:3]):
        print(f"{i+1}. {product['original_name']} | {product['price']} | {product['unit']}")
    
    # 2. Обработка через ChatGPT
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        print(f"\n🤖 Обработка через GPT-4.1...")
        
        processor = BatchChatGPTProcessor(openai_key)
        supplier_name = extracted_data.get('supplier', {}).get('name', 'Unknown')
        
        try:
            # Ограничиваем для демо
            demo_products = products[:20] if len(products) > 20 else products
            
            result = await processor.process_all_products(demo_products, supplier_name)
            
            if 'error' not in result:
                processed_products = result.get('products', [])
                processing_stats = result.get('processing_stats', {})
                
                print(f"✅ Обработано товаров: {len(processed_products)}")
                print(f"📈 Успешность: {processing_stats.get('success_rate', 0):.1%}")
                print(f"🎯 Токенов использовано: {processing_stats.get('estimated_tokens', 0)}")
                
                # Показываем обработанные товары
                print(f"\n🎯 Примеры обработанных товаров:")
                for i, product in enumerate(processed_products[:3]):
                    print(f"{i+1}. ИСХОДНОЕ: {product.get('original_name', '')[:50]}...")
                    print(f"   БРЕНД: {product.get('brand', 'unknown')}")
                    print(f"   СТАНДАРТ: {product.get('standardized_name', '')[:50]}...")
                    print(f"   РАЗМЕР: {product.get('size', 'unknown')} {product.get('unit', 'pcs')}")
                    print(f"   ЦЕНА: {product.get('price', 0)} {product.get('currency', 'USD')}")
                    print(f"   КАТЕГОРИЯ: {product.get('category', 'general')}")
                    print()
                
                # 3. Сохранение в Google Sheets
                gm = GoogleSheetsManager()
                if gm.is_connected():
                    print("💾 Сохранение в Google Sheets...")
                    
                    sheets_result = gm.update_master_table(result)
                    
                    if 'error' not in sheets_result:
                        print(f"✅ Сохранено в Google Sheets:")
                        print(f"  • Новых товаров: {sheets_result.get('new_products', 0)}")
                        print(f"  • Обновленных цен: {sheets_result.get('updated_prices', 0)}")
                        print(f"🔗 Таблица: {gm.get_sheet_url()}")
                        
                        # Создаем лист поставщика
                        gm.create_supplier_summary(supplier_name, processed_products)
                        print(f"📋 Создан лист поставщика: Supplier_{supplier_name}")
                    else:
                        print(f"❌ Ошибка сохранения: {sheets_result['error']}")
                else:
                    print("❌ Нет подключения к Google Sheets")
                
                return result
            else:
                print(f"❌ Ошибка ChatGPT: {result['error']}")
                return extracted_data
        
        except Exception as e:
            print(f"❌ Ошибка обработки ChatGPT: {e}")
            return extracted_data
    else:
        print("⚠️ OpenAI ключ не настроен - пропускаем ChatGPT обработку")
        return extracted_data

def interactive_file_upload():
    """Интерактивная загрузка файла"""
    print("📁 ИНТЕРАКТИВНАЯ ЗАГРУЗКА ФАЙЛА")
    print("=" * 40)
    
    while True:
        print("\nВыберите способ загрузки:")
        print("1. Ввести путь к файлу")
        print("2. Выбрать из папки data/temp")
        print("3. Выход")
        
        choice = input("\nВыбор (1-3): ").strip()
        
        if choice == '1':
            file_path = input("📁 Введите полный путь к Excel файлу: ").strip()
            if file_path:
                return file_path
        
        elif choice == '2':
            temp_dir = Path("data/temp")
            if temp_dir.exists():
                excel_files = list(temp_dir.glob("*.xlsx")) + list(temp_dir.glob("*.xls"))
                
                if excel_files:
                    print("\n📂 Доступные файлы:")
                    for i, file_path in enumerate(excel_files, 1):
                        print(f"{i}. {file_path.name}")
                    
                    try:
                        idx = int(input(f"\nВыберите файл (1-{len(excel_files)}): ")) - 1
                        if 0 <= idx < len(excel_files):
                            return str(excel_files[idx])
                        else:
                            print("❌ Неверный номер")
                    except ValueError:
                        print("❌ Введите число")
                else:
                    print("📭 Нет Excel файлов в папке data/temp")
            else:
                print("📭 Папка data/temp не существует")
        
        elif choice == '3':
            return None
        
        else:
            print("❌ Неверный выбор")

async def main():
    """Главная функция"""
    print("🚀 СИСТЕМА ПРЯМОЙ ОБРАБОТКИ ФАЙЛОВ")
    print("=" * 50)
    
    file_path = interactive_file_upload()
    
    if file_path:
        result = await process_file_directly(file_path)
        
        if result:
            print(f"\n✅ ФАЙЛ УСПЕШНО ОБРАБОТАН!")
            print(f"📊 Результат сохранен в Google Sheets")
            
            # Предлагаем создать эталонные данные
            create_reference = input("\n❓ Создать эталонные данные для этого файла? (y/n): ").strip().lower()
            
            if create_reference == 'y':
                print(f"\n📝 Для создания эталонных данных:")
                print(f"1. Запустите: python3 create_training_example.py")
                print(f"2. Выберите пункт 2 (загрузка из JSON)")
                print(f"3. Подготовьте JSON с правильными данными")
                print(f"4. Используйте файл: {file_path}")
        else:
            print(f"\n❌ Ошибка обработки файла")
    else:
        print("👋 До свидания!")

if __name__ == "__main__":
    asyncio.run(main())