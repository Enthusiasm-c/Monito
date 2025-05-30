#!/usr/bin/env python3
"""
Тестирование системы против эталонных данных
"""

import os
import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.training_data_manager import TrainingDataManager
from modules.advanced_excel_parser import AdvancedExcelParser
from modules.batch_chatgpt_processor import BatchChatGPTProcessor
from dotenv import load_dotenv

load_dotenv()

async def test_single_example(example_name: str, trainer: TrainingDataManager):
    """Тестирование одного эталонного примера"""
    print(f"\n🧪 ТЕСТИРОВАНИЕ: {example_name}")
    print("=" * 50)
    
    # Загружаем эталонные данные
    reference_data = trainer.load_reference_data(example_name)
    if not reference_data:
        print(f"❌ Не найдены эталонные данные для {example_name}")
        return None
    
    # Ищем оригинальный файл
    original_file = None
    for ext in ['.xlsx', '.xls']:
        file_path = trainer.original_files_dir / f"{example_name}{ext}"
        if file_path.exists():
            original_file = str(file_path)
            break
    
    if not original_file:
        print(f"❌ Не найден оригинальный файл для {example_name}")
        return None
    
    print(f"📁 Файл: {original_file}")
    print(f"🎯 Эталон: {len(reference_data.get('products', []))} товаров")
    
    # 1. Тестируем парсер Excel
    print("\n📊 Тест парсера Excel...")
    parser = AdvancedExcelParser()
    extracted_data = parser.extract_products_smart(original_file, max_products=1000)
    
    if 'error' in extracted_data:
        print(f"❌ Ошибка парсера: {extracted_data['error']}")
        return None
    
    extracted_products = extracted_data.get('products', [])
    print(f"✅ Извлечено товаров: {len(extracted_products)}")
    
    # 2. Тестируем ChatGPT обработку
    print("\n🤖 Тест ChatGPT обработки...")
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ OpenAI ключ не найден")
        return None
    
    processor = BatchChatGPTProcessor(openai_key)
    supplier_name = reference_data.get('supplier', {}).get('name', 'Test Supplier')
    
    # Ограничиваем для теста
    test_products = extracted_products[:50] if len(extracted_products) > 50 else extracted_products
    
    try:
        chatgpt_result = await processor.process_all_products(test_products, supplier_name)
        
        if 'error' in chatgpt_result:
            print(f"❌ Ошибка ChatGPT: {chatgpt_result['error']}")
            return None
        
        processed_products = chatgpt_result.get('products', [])
        print(f"✅ Обработано товаров: {len(processed_products)}")
        
    except Exception as e:
        print(f"❌ Ошибка ChatGPT обработки: {e}")
        return None
    
    # 3. Сравнение с эталоном
    print("\n🔍 Сравнение с эталоном...")
    comparison = trainer.compare_results(chatgpt_result, reference_data, example_name)
    
    # Показываем результаты
    print_comparison_results(comparison)
    
    return comparison

def print_comparison_results(comparison: dict):
    """Красивый вывод результатов сравнения"""
    print(f"\n📊 РЕЗУЛЬТАТЫ СРАВНЕНИЯ")
    print("=" * 40)
    
    # Общие метрики
    overall = comparison.get('overall_metrics', {})
    print(f"📈 Общие метрики:")
    print(f"  • Точность поставщика: {overall.get('supplier_accuracy', 0):.1%}")
    print(f"  • Точность полей товаров: {overall.get('products_field_accuracy', 0):.1%}")
    print(f"  • Процент обнаружения товаров: {overall.get('products_detection_rate', 0):.1%}")
    
    # Поставщик
    supplier_comp = comparison.get('supplier_comparison', {})
    print(f"\n🏪 Данные поставщика:")
    for field, data in supplier_comp.items():
        score = data.get('match_score', 0)
        status = "✅" if score >= 0.8 else "⚠️" if score >= 0.5 else "❌"
        print(f"  {status} {field}: {score:.1%}")
        if data.get('reference') and data.get('actual') != data.get('reference'):
            print(f"      Эталон: {data.get('reference')}")
            print(f"      Факт: {data.get('actual')}")
    
    # Товары
    products_comp = comparison.get('products_comparison', {})
    print(f"\n📦 Товары:")
    print(f"  • Эталонных: {products_comp.get('total_reference', 0)}")
    print(f"  • Найденных: {products_comp.get('total_actual', 0)}")
    print(f"  • Сопоставленных: {len(products_comp.get('matched_products', []))}")
    
    # Точность полей
    field_accuracy = products_comp.get('field_accuracy', {})
    print(f"\n🎯 Точность полей товаров:")
    for field, data in field_accuracy.items():
        score = data.get('average_score', 0)
        count = data.get('total_comparisons', 0)
        status = "✅" if score >= 0.8 else "⚠️" if score >= 0.5 else "❌"
        print(f"  {status} {field}: {score:.1%} ({count} сравнений)")
    
    # Проблемы
    missing = products_comp.get('missing_products', [])
    extra = products_comp.get('extra_products', [])
    
    if missing:
        print(f"\n❌ Пропущенные товары ({len(missing)}):")
        for product in missing[:5]:
            print(f"  • {product}")
        if len(missing) > 5:
            print(f"  • ... и еще {len(missing) - 5}")
    
    if extra:
        print(f"\n➕ Лишние товары ({len(extra)}):")
        for product in extra[:5]:
            print(f"  • {product}")
        if len(extra) > 5:
            print(f"  • ... и еще {len(extra) - 5}")

async def test_all_examples():
    """Тестирование всех эталонных примеров"""
    print("🧪 ТЕСТИРОВАНИЕ ВСЕХ ЭТАЛОННЫХ ПРИМЕРОВ")
    print("=" * 60)
    
    trainer = TrainingDataManager()
    examples = trainer.get_training_examples_list()
    
    if not examples:
        print("📭 Нет эталонных примеров для тестирования")
        return
    
    results = []
    
    for example in examples:
        try:
            result = await test_single_example(example, trainer)
            if result:
                results.append({
                    'name': example,
                    'metrics': result.get('overall_metrics', {})
                })
        except Exception as e:
            print(f"❌ Ошибка тестирования {example}: {e}")
            continue
    
    # Сводный отчет
    if results:
        print(f"\n📊 СВОДНЫЙ ОТЧЕТ ПО {len(results)} ПРИМЕРАМ")
        print("=" * 60)
        
        # Средние метрики
        avg_supplier = sum(r['metrics'].get('supplier_accuracy', 0) for r in results) / len(results)
        avg_products = sum(r['metrics'].get('products_field_accuracy', 0) for r in results) / len(results)
        avg_detection = sum(r['metrics'].get('products_detection_rate', 0) for r in results) / len(results)
        
        print(f"📈 Средние показатели:")
        print(f"  • Точность поставщика: {avg_supplier:.1%}")
        print(f"  • Точность полей товаров: {avg_products:.1%}")
        print(f"  • Процент обнаружения товаров: {avg_detection:.1%}")
        
        print(f"\n📋 По примерам:")
        for result in results:
            metrics = result['metrics']
            overall_score = (
                metrics.get('supplier_accuracy', 0) + 
                metrics.get('products_field_accuracy', 0) + 
                metrics.get('products_detection_rate', 0)
            ) / 3
            
            status = "🟢" if overall_score >= 0.8 else "🟡" if overall_score >= 0.6 else "🔴"
            print(f"  {status} {result['name']}: {overall_score:.1%}")

def create_sample_reference():
    """Создание примера эталонных данных"""
    print("📝 СОЗДАНИЕ ПРИМЕРА ЭТАЛОННЫХ ДАННЫХ")
    print("=" * 50)
    
    trainer = TrainingDataManager()
    
    # Создаем пример индонезийского прайс-листа
    sample_reference = {
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
            },
            {
                "original_name": "BARILLA Spaghetti No.5 500gr",
                "brand": "BARILLA", 
                "standardized_name": "BARILLA Spaghetti No.5",
                "size": "500",
                "unit": "g",
                "price": 25500,
                "currency": "IDR",
                "category": "pasta_noodles",
                "confidence": 0.95
            },
            {
                "original_name": "INDOMIE Mi Goreng Rasa Ayam 85g",
                "brand": "INDOMIE",
                "standardized_name": "INDOMIE Mi Goreng Chicken Flavor",
                "size": "85",
                "unit": "g", 
                "price": 3200,
                "currency": "IDR",
                "category": "pasta_noodles",
                "confidence": 0.95
            }
        ],
        "metadata": {
            "document_type": "price_list",
            "language": "indonesian/english",
            "total_pages": 4,
            "notes": "Образец индонезийского прайс-листа с продуктами питания"
        }
    }
    
    # Сохраняем как пример
    sample_file = "sample_reference.json"
    with open(sample_file, 'w', encoding='utf-8') as f:
        json.dump(sample_reference, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Создан пример эталонных данных: {sample_file}")
    print("\n📋 Содержимое:")
    print(json.dumps(sample_reference, indent=2, ensure_ascii=False))
    
    print(f"\n💡 Для использования:")
    print(f"1. Создайте соответствующий Excel файл")
    print(f"2. Запустите: python3 create_training_example.py")
    print(f"3. Выберите пункт 2 для загрузки из JSON")

async def main():
    """Главное меню тестирования"""
    trainer = TrainingDataManager()
    
    while True:
        print("\n🧪 СИСТЕМА ТЕСТИРОВАНИЯ НА ЭТАЛОННЫХ ДАННЫХ")
        print("=" * 50)
        print("1. Тестировать один пример")
        print("2. Тестировать все примеры")
        print("3. Список доступных примеров")
        print("4. Создать образец эталонных данных")
        print("5. Выход")
        
        choice = input("\nВыберите действие (1-5): ").strip()
        
        if choice == '1':
            examples = trainer.get_training_examples_list()
            if not examples:
                print("📭 Нет доступных примеров")
                continue
            
            print("\nДоступные примеры:")
            for i, example in enumerate(examples, 1):
                print(f"{i}. {example}")
            
            try:
                idx = int(input(f"\nВыберите пример (1-{len(examples)}): ")) - 1
                if 0 <= idx < len(examples):
                    await test_single_example(examples[idx], trainer)
                else:
                    print("❌ Неверный номер")
            except ValueError:
                print("❌ Введите число")
                
        elif choice == '2':
            await test_all_examples()
            
        elif choice == '3':
            examples = trainer.get_training_examples_list()
            if examples:
                print(f"\n📚 Доступных примеров: {len(examples)}")
                for i, example in enumerate(examples, 1):
                    print(f"{i}. {example}")
            else:
                print("📭 Нет доступных примеров")
                
        elif choice == '4':
            create_sample_reference()
            
        elif choice == '5':
            break
        else:
            print("❌ Неверный выбор")

if __name__ == "__main__":
    asyncio.run(main())