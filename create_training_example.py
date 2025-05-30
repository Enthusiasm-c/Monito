#!/usr/bin/env python3
"""
Интерфейс для создания эталонных примеров обучения
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.training_data_manager import TrainingDataManager

def interactive_reference_creation():
    """Интерактивное создание эталонных данных"""
    print("🎓 СОЗДАНИЕ ЭТАЛОННОГО ПРИМЕРА ДЛЯ ОБУЧЕНИЯ")
    print("=" * 60)
    
    trainer = TrainingDataManager()
    
    # Запрашиваем название примера
    example_name = input("📝 Введите название примера (например, 'indonesia_food_supplier'): ").strip()
    if not example_name:
        print("❌ Название не может быть пустым")
        return
    
    # Запрашиваем путь к файлу
    file_path = input("📁 Введите путь к оригинальному файлу Excel: ").strip()
    if not os.path.exists(file_path):
        print("❌ Файл не найден")
        return
    
    print(f"\n📊 Создание эталонных данных для: {example_name}")
    print("Следуйте инструкциям для создания правильного эталона...")
    
    # Создаем шаблон
    reference_template = trainer.create_reference_template()
    
    # Информация о поставщике
    print("\n🏪 ДАННЫЕ ПОСТАВЩИКА:")
    supplier_data = {}
    
    supplier_data['name'] = input("Название компании: ").strip()
    supplier_data['phone'] = input("Телефон: ").strip()
    supplier_data['whatsapp'] = input("WhatsApp: ").strip()
    supplier_data['email'] = input("Email: ").strip()
    supplier_data['address'] = input("Адрес: ").strip()
    
    reference_template['supplier'] = supplier_data
    
    # Товары
    print("\n📦 ТОВАРЫ:")
    print("Введите данные для каждого товара. Введите 'stop' для завершения.")
    
    products = []
    while True:
        print(f"\n--- Товар {len(products) + 1} ---")
        
        original_name = input("Оригинальное название: ").strip()
        if original_name.lower() == 'stop':
            break
        
        if not original_name:
            continue
        
        brand = input("Бренд: ").strip()
        standardized_name = input("Стандартизированное название (EN): ").strip()
        size = input("Размер/вес: ").strip()
        unit = input("Единица измерения (g/ml/kg/l/pcs): ").strip()
        
        price_str = input("Цена (только число): ").strip()
        try:
            price = float(price_str) if price_str else 0
        except:
            price = 0
        
        currency = input("Валюта (IDR/USD/EUR): ").strip() or "IDR"
        category = input("Категория: ").strip()
        
        product = {
            "original_name": original_name,
            "brand": brand or "unknown",
            "standardized_name": standardized_name or original_name,
            "size": size or "unknown",
            "unit": unit or "pcs",
            "price": price,
            "currency": currency,
            "category": category or "general",
            "confidence": 0.95
        }
        
        products.append(product)
        print(f"✅ Товар добавлен: {original_name}")
    
    reference_template['products'] = products
    
    # Метаданные
    print("\n📋 МЕТАДАННЫЕ:")
    reference_template['metadata']['document_type'] = input("Тип документа: ").strip() or "price_list"
    reference_template['metadata']['language'] = input("Язык документа: ").strip() or "mixed"
    
    pages_str = input("Количество страниц: ").strip()
    try:
        reference_template['metadata']['total_pages'] = int(pages_str) if pages_str else 1
    except:
        reference_template['metadata']['total_pages'] = 1
    
    reference_template['metadata']['notes'] = input("Дополнительные заметки: ").strip()
    
    # Сохранение
    print(f"\n💾 Сохранение эталонного примера...")
    result_file = trainer.save_training_example(file_path, reference_template, example_name)
    
    if result_file:
        print(f"✅ Эталонный пример сохранен!")
        print(f"📁 Файл: {result_file}")
        print(f"📦 Товаров: {len(products)}")
        print(f"🏪 Поставщик: {supplier_data.get('name', 'N/A')}")
        
        # Показываем структуру
        print(f"\n📊 Структура сохраненных данных:")
        print(f"training_data/")
        print(f"├── original_files/{example_name}.xlsx")
        print(f"├── reference_data/{example_name}_reference.json")
        print(f"└── comparison_results/ (будут созданы при тестировании)")
    else:
        print("❌ Ошибка сохранения")

def load_from_json():
    """Загрузка эталонных данных из готового JSON файла"""
    print("📁 ЗАГРУЗКА ЭТАЛОННЫХ ДАННЫХ ИЗ JSON")
    print("=" * 50)
    
    trainer = TrainingDataManager()
    
    example_name = input("📝 Название примера: ").strip()
    json_file = input("📁 Путь к JSON файлу с эталонными данными: ").strip()
    original_file = input("📁 Путь к оригинальному Excel файлу: ").strip()
    
    if not os.path.exists(json_file):
        print("❌ JSON файл не найден")
        return
    
    if not os.path.exists(original_file):
        print("❌ Оригинальный файл не найден")
        return
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            reference_data = json.load(f)
        
        result_file = trainer.save_training_example(original_file, reference_data, example_name)
        
        if result_file:
            print(f"✅ Эталонный пример загружен и сохранен!")
            print(f"📁 Файл: {result_file}")
        else:
            print("❌ Ошибка сохранения")
            
    except Exception as e:
        print(f"❌ Ошибка загрузки JSON: {e}")

def show_template():
    """Показ шаблона JSON для эталонных данных"""
    print("📋 ШАБЛОН JSON ДЛЯ ЭТАЛОННЫХ ДАННЫХ")
    print("=" * 50)
    
    trainer = TrainingDataManager()
    template = trainer.create_reference_template()
    
    print("Скопируйте и заполните этот шаблон:")
    print(json.dumps(template, indent=2, ensure_ascii=False))
    
    # Сохраняем шаблон в файл
    template_file = "reference_template.json"
    with open(template_file, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Шаблон сохранен в файл: {template_file}")

def list_examples():
    """Список существующих эталонных примеров"""
    print("📚 СУЩЕСТВУЮЩИЕ ЭТАЛОННЫЕ ПРИМЕРЫ")
    print("=" * 50)
    
    trainer = TrainingDataManager()
    examples = trainer.get_training_examples_list()
    
    if examples:
        for i, example in enumerate(examples, 1):
            print(f"{i}. {example}")
            
            # Показываем краткую информацию
            ref_data = trainer.load_reference_data(example)
            if ref_data:
                supplier_name = ref_data.get('supplier', {}).get('name', 'N/A')
                products_count = len(ref_data.get('products', []))
                print(f"   Поставщик: {supplier_name}")
                print(f"   Товаров: {products_count}")
            print()
    else:
        print("📭 Нет сохраненных эталонных примеров")

def main():
    """Главное меню"""
    while True:
        print("\n🎓 МЕНЕДЖЕР ЭТАЛОННЫХ ДАННЫХ")
        print("=" * 40)
        print("1. Создать эталонный пример интерактивно")
        print("2. Загрузить из готового JSON файла")
        print("3. Показать шаблон JSON")
        print("4. Список существующих примеров")
        print("5. Выход")
        
        choice = input("\nВыберите действие (1-5): ").strip()
        
        if choice == '1':
            interactive_reference_creation()
        elif choice == '2':
            load_from_json()
        elif choice == '3':
            show_template()
        elif choice == '4':
            list_examples()
        elif choice == '5':
            break
        else:
            print("❌ Неверный выбор")

if __name__ == "__main__":
    main()