#!/usr/bin/env python3
"""
Быстрое создание эталонных данных
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.training_data_manager import TrainingDataManager

def create_reference_from_template():
    """Создание эталона по шаблону"""
    print("📝 БЫСТРОЕ СОЗДАНИЕ ЭТАЛОННЫХ ДАННЫХ")
    print("=" * 50)
    
    # Шаблон для быстрого заполнения
    template = {
        "supplier": {
            "name": "",
            "phone": "",
            "whatsapp": "",
            "email": "", 
            "address": ""
        },
        "products": [],
        "metadata": {
            "document_type": "price_list",
            "language": "mixed",
            "total_pages": 1,
            "notes": ""
        }
    }
    
    print("Введите данные (Enter для пропуска):")
    
    # Данные поставщика
    print(f"\n🏪 ПОСТАВЩИК:")
    template["supplier"]["name"] = input("Название компании: ").strip()
    template["supplier"]["phone"] = input("Телефон: ").strip()
    template["supplier"]["whatsapp"] = input("WhatsApp: ").strip() 
    template["supplier"]["email"] = input("Email: ").strip()
    template["supplier"]["address"] = input("Адрес: ").strip()
    
    # Товары (упрощенный ввод)
    print(f"\n📦 ТОВАРЫ:")
    print("Формат: название | бренд | стандарт_название | размер | единица | цена | валюта | категория")
    print("Пример: COCA COLA 330ml | COCA COLA | COCA COLA Can | 330 | ml | 4500 | IDR | beverages")
    print("Введите 'stop' для завершения")
    
    while True:
        product_input = input(f"\nТовар {len(template['products']) + 1}: ").strip()
        
        if product_input.lower() == 'stop':
            break
        
        if not product_input:
            continue
        
        try:
            parts = [p.strip() for p in product_input.split('|')]
            
            if len(parts) >= 6:
                product = {
                    "original_name": parts[0],
                    "brand": parts[1] if len(parts) > 1 and parts[1] else "unknown",
                    "standardized_name": parts[2] if len(parts) > 2 and parts[2] else parts[0],
                    "size": parts[3] if len(parts) > 3 and parts[3] else "unknown",
                    "unit": parts[4] if len(parts) > 4 and parts[4] else "pcs",
                    "price": float(parts[5]) if len(parts) > 5 and parts[5] else 0,
                    "currency": parts[6] if len(parts) > 6 and parts[6] else "USD",
                    "category": parts[7] if len(parts) > 7 and parts[7] else "general",
                    "confidence": 0.95
                }
                
                template["products"].append(product)
                print(f"✅ Добавлен: {parts[0]}")
            else:
                print("❌ Недостаточно данных. Нужно минимум: название|бренд|стандарт|размер|единица|цена")
        
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    if not template["products"]:
        print("❌ Нет товаров для сохранения")
        return
    
    # Метаданные
    template["metadata"]["notes"] = input(f"\nЗаметки о файле: ").strip()
    
    # Сохранение
    example_name = input(f"\nНазвание примера: ").strip()
    if not example_name:
        example_name = "quick_example"
    
    file_path = input(f"Путь к оригинальному Excel файлу: ").strip()
    
    # Создаем JSON файл
    json_file = f"{example_name}_reference.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Эталонные данные сохранены: {json_file}")
    print(f"📦 Товаров: {len(template['products'])}")
    
    # Сохранение в системе обучения
    if file_path and os.path.exists(file_path):
        trainer = TrainingDataManager()
        result = trainer.save_training_example(file_path, template, example_name)
        if result:
            print(f"✅ Пример добавлен в систему обучения")
            print(f"🧪 Для тестирования: python3 test_against_reference.py")
    else:
        print(f"⚠️ Файл не найден, эталон сохранен только как JSON")

def load_from_csv_like():
    """Загрузка из CSV-подобного формата"""
    print("📊 ЗАГРУЗКА ИЗ CSV-ПОДОБНОГО ФОРМАТА")
    print("=" * 50)
    
    print("Создайте текстовый файл со строками вида:")
    print("название;бренд;стандарт;размер;единица;цена;валюта;категория")
    print("")
    print("Пример:")
    print("COCA COLA 330ml;COCA COLA;COCA COLA Can;330;ml;4500;IDR;beverages")
    print("INDOMIE Mi Goreng;INDOMIE;INDOMIE Fried Noodles;85;g;3200;IDR;pasta_noodles")
    
    csv_file = input("\nПуть к CSV файлу: ").strip()
    
    if not os.path.exists(csv_file):
        print("❌ Файл не найден")
        return
    
    products = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = [p.strip() for p in line.split(';')]
                
                if len(parts) >= 6:
                    product = {
                        "original_name": parts[0],
                        "brand": parts[1] if len(parts) > 1 else "unknown",
                        "standardized_name": parts[2] if len(parts) > 2 else parts[0],
                        "size": parts[3] if len(parts) > 3 else "unknown",
                        "unit": parts[4] if len(parts) > 4 else "pcs",
                        "price": float(parts[5]) if len(parts) > 5 else 0,
                        "currency": parts[6] if len(parts) > 6 else "USD",
                        "category": parts[7] if len(parts) > 7 else "general",
                        "confidence": 0.95
                    }
                    products.append(product)
                else:
                    print(f"⚠️ Строка {line_num} пропущена: недостаточно данных")
    
    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
        return
    
    if not products:
        print("❌ Не найдено валидных товаров")
        return
    
    print(f"✅ Загружено товаров: {len(products)}")
    
    # Данные поставщика
    print(f"\n🏪 Данные поставщика:")
    supplier = {
        "name": input("Название: ").strip(),
        "phone": input("Телефон: ").strip(),
        "email": input("Email: ").strip(),
        "address": input("Адрес: ").strip()
    }
    
    # Создание полного объекта
    reference_data = {
        "supplier": supplier,
        "products": products,
        "metadata": {
            "document_type": "price_list",
            "language": "mixed",
            "total_pages": 1,
            "notes": f"Импорт из CSV файла {csv_file}"
        }
    }
    
    # Сохранение
    example_name = input(f"\nНазвание примера: ").strip() or "csv_import"
    excel_file = input(f"Путь к соответствующему Excel файлу: ").strip()
    
    # JSON файл
    json_file = f"{example_name}_reference.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(reference_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Сохранен файл: {json_file}")
    
    # В систему обучения
    if excel_file and os.path.exists(excel_file):
        trainer = TrainingDataManager()
        result = trainer.save_training_example(excel_file, reference_data, example_name)
        if result:
            print(f"✅ Добавлено в систему обучения")

def show_examples():
    """Примеры форматов данных"""
    print("📚 ПРИМЕРЫ ФОРМАТОВ ДАННЫХ")
    print("=" * 40)
    
    print("1️⃣ Быстрый ввод (через |):")
    print("COCA COLA 330ml | COCA COLA | COCA COLA Can | 330 | ml | 4500 | IDR | beverages")
    print("INDOMIE Mi Goreng | INDOMIE | INDOMIE Fried Noodles | 85 | g | 3200 | IDR | pasta_noodles")
    
    print("\n2️⃣ CSV формат (через ;):")
    print("COCA COLA 330ml;COCA COLA;COCA COLA Can;330;ml;4500;IDR;beverages")
    print("INDOMIE Mi Goreng;INDOMIE;INDOMIE Fried Noodles;85;g;3200;IDR;pasta_noodles")
    
    print("\n3️⃣ JSON структура:")
    example_json = {
        "supplier": {
            "name": "PT GLOBAL ANUGRAH PASIFIK",
            "phone": "(0361) 9075914",
            "email": "sales@gap-indo.com"
        },
        "products": [
            {
                "original_name": "COCA COLA 330ml",
                "brand": "COCA COLA",
                "standardized_name": "COCA COLA Can",
                "size": "330",
                "unit": "ml",
                "price": 4500,
                "currency": "IDR",
                "category": "beverages"
            }
        ]
    }
    
    print(json.dumps(example_json, indent=2, ensure_ascii=False))
    
    print("\n📋 Категории товаров:")
    categories = [
        "beverages", "canned_food", "pasta_noodles", "cooking_oil",
        "spices_seasonings", "dairy_products", "snacks", "rice_grains"
    ]
    for cat in categories:
        print(f"  • {cat}")

def main():
    """Главное меню"""
    while True:
        print("\n📝 БЫСТРОЕ СОЗДАНИЕ ЭТАЛОННЫХ ДАННЫХ")
        print("=" * 50)
        print("1. Создать эталон (быстрый ввод)")
        print("2. Загрузить из CSV-подобного файла")
        print("3. Показать примеры форматов")
        print("4. Выход")
        
        choice = input("\nВыбор (1-4): ").strip()
        
        if choice == '1':
            create_reference_from_template()
        elif choice == '2':
            load_from_csv_like()
        elif choice == '3':
            show_examples()
        elif choice == '4':
            break
        else:
            print("❌ Неверный выбор")

if __name__ == "__main__":
    main()