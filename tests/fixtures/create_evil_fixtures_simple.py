#!/usr/bin/env python3
"""
Упрощенный генератор Evil Test Fixtures для MON-S01
Без pandas зависимостей - только встроенные библиотеки Python
"""

import os
import csv
import json
import random
from pathlib import Path
from typing import List, Dict, Any

class SimpleEvilFixtureGenerator:
    """Упрощенный генератор сложных тестовых файлов"""
    
    def __init__(self, fixtures_dir: str = "tests/fixtures/evil_files"):
        self.fixtures_dir = Path(fixtures_dir)
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
        self.expected_dir = Path("tests/fixtures/expected_outputs")
        self.expected_dir.mkdir(parents=True, exist_ok=True)
        
    def create_all_fixtures(self):
        """Создает все evil fixtures"""
        print("🧪 Создание Evil Test Fixtures для MON-S01 (простая версия)...")
        
        fixtures_created = []
        
        # 1. Simple CSV with issues
        try:
            result = self.create_problematic_csv()
            fixtures_created.append(result)
            print("✅ problematic.csv создан")
        except Exception as e:
            print(f"⚠️ problematic.csv: {e}")
        
        # 2. Large CSV (имитация большого файла)
        try:
            result = self.create_large_csv()
            fixtures_created.append(result)
            print("✅ large_data.csv создан")
        except Exception as e:
            print(f"⚠️ large_data.csv: {e}")
        
        # 3. Windows-1252 CSV
        try:
            result = self.create_win1252_csv()
            fixtures_created.append(result)
            print("✅ win1252.csv создан")
        except Exception as e:
            print(f"⚠️ win1252.csv: {e}")
        
        # 4. CSV with empty rows and columns
        try:
            result = self.create_empty_gaps_csv()
            fixtures_created.append(result)
            print("✅ empty_gaps.csv создан")
        except Exception as e:
            print(f"⚠️ empty_gaps.csv: {e}")
        
        # 5. Mock PDF table
        try:
            result = self.create_mock_pdf_table()
            fixtures_created.append(result)
            print("✅ pdf_table.txt создан (mock PDF)")
        except Exception as e:
            print(f"⚠️ pdf_table.txt: {e}")
        
        # 6. Mock OCR image
        try:
            result = self.create_mock_ocr_image()
            fixtures_created.append(result)
            print("✅ ocr_table.txt создан (mock image)")
        except Exception as e:
            print(f"⚠️ ocr_table.txt: {e}")
        
        # Создаем манифест fixtures
        self.create_fixtures_manifest(fixtures_created)
        
        print(f"\n🎯 Создано {len(fixtures_created)} evil fixtures")
        return fixtures_created
    
    def create_problematic_csv(self) -> Dict[str, Any]:
        """Evil Fixture 1: CSV с проблемами в данных"""
        
        # Проблематичные данные
        data = [
            ['Название', 'Цена', 'Категория', 'Описание'],
            ['iPhone 14', '99,999', 'Смартфоны', 'Новый iPhone с камерой'],
            ['', '89999', 'Смартфоны', 'Samsung Galaxy'],  # Пустое название
            ['MacBook Pro', 'дорого', 'Ноутбуки', ''],  # Нечисловая цена, пустое описание
            ['iPad Air', '59999.99', '', 'Планшет Apple'],  # Пустая категория
            ['AirPods"Pro', '25000', 'Аксессуары', 'Наушники\nс шумоподавлением'],  # Кавычка в названии, перенос строки
            ['Товар #123', '0', 'Тестовая', 'Спецсимволы: @#$%^&*()'],  # Спецсимволы
        ]
        
        file_path = self.fixtures_dir / "problematic.csv"
        
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for row in data:
                writer.writerow(row)
        
        expected = {
            'filename': 'problematic.csv',
            'expected_rows_in': 6,  # Без заголовка
            'expected_rows_out': 4,  # После фильтрации плохих строк
            'challenges': ['Empty cells', 'Non-numeric prices', 'Special characters', 'Multiline text']
        }
        
        with open(self.expected_dir / "problematic_expected.json", 'w', encoding='utf-8') as f:
            json.dump(expected, f, indent=2, ensure_ascii=False)
        
        return expected
    
    def create_large_csv(self) -> Dict[str, Any]:
        """Evil Fixture 2: Большой CSV файл (150 строк x 20 колонок)"""
        
        categories = ['Смартфоны', 'Ноутбуки', 'Планшеты', 'Аксессуары', 'ТВ', 'Аудио']
        brands = ['Apple', 'Samsung', 'Xiaomi', 'Sony', 'LG', 'Huawei', 'ASUS', 'HP']
        
        # Заголовки
        headers = ['ID', 'Название', 'Цена', 'Категория', 'Бренд', 'Описание'] + \
                 [f'Поле_{i+1}' for i in range(14)]  # Дополнительные поля
        
        data = [headers]
        
        # Генерируем 150 строк данных
        for i in range(150):
            row = [
                f'PROD_{i+1:03d}',
                f'{random.choice(brands)} {random.choice(["Pro", "Max", "Ultra", "Mini"])} {random.randint(10,99)}',
                str(random.randint(5000, 200000)),
                random.choice(categories),
                random.choice(brands),
                f'Описание товара {i+1} с характеристиками'
            ]
            # Добавляем дополнительные поля
            for j in range(14):
                row.append(f'Значение_{j+1}_{i+1}')
            
            data.append(row)
        
        file_path = self.fixtures_dir / "large_data.csv"
        
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for row in data:
                writer.writerow(row)
        
        file_size_mb = round(os.path.getsize(file_path) / (1024*1024), 2)
        
        expected = {
            'filename': 'large_data.csv',
            'expected_rows_in': 150,
            'expected_rows_out': 150,
            'columns_count': 20,
            'file_size_mb': file_size_mb,
            'challenges': ['Large file size', 'Many columns', 'Memory usage']
        }
        
        with open(self.expected_dir / "large_data_expected.json", 'w', encoding='utf-8') as f:
            json.dump(expected, f, indent=2, ensure_ascii=False)
        
        return expected
    
    def create_win1252_csv(self) -> Dict[str, Any]:
        """Evil Fixture 3: CSV с кодировкой Windows-1252"""
        
        # Данные с символами Windows-1252
        products = [
            ['Товар', 'Цена', 'Описание'],
            ['Смартфон "iPhone"', '99 999₽', 'Флагманский смартфон—отличное качество'],
            ['Ноутбук №1', '150 000р.', 'Профессиональный ноутбук—высокая производительность'],
            ['Планшет "iPad"', '59 999₽', 'Планшет для работы—легкий и мощный'],
            ['Наушники', '25 000р.', 'Беспроводные наушники—premium качество'],
        ]
        
        file_path = self.fixtures_dir / "win1252.csv"
        
        try:
            # Пытаемся записать в Windows-1252
            with open(file_path, 'w', encoding='cp1252', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                for row in products:
                    writer.writerow(row)
            encoding_used = 'cp1252'
        except UnicodeEncodeError:
            # Fallback на UTF-8 если символы не поддерживаются
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                for row in products:
                    writer.writerow(row)
            encoding_used = 'utf-8'
        
        expected = {
            'filename': 'win1252.csv',
            'expected_rows_in': 4,
            'expected_rows_out': 4,
            'encoding': encoding_used,
            'delimiter': ';',
            'challenges': ['Encoding issues', 'Special characters', 'European CSV format']
        }
        
        with open(self.expected_dir / "win1252_expected.json", 'w', encoding='utf-8') as f:
            json.dump(expected, f, indent=2, ensure_ascii=False)
        
        return expected
    
    def create_empty_gaps_csv(self) -> Dict[str, Any]:
        """Evil Fixture 4: CSV с пропусками и пустыми строками"""
        
        data = [
            ['Название', '', 'Категория', 'Unnamed_4', 'Описание'],  # Пустой заголовок
            ['', '', '', '', ''],  # Пустая строка
            ['iPhone 14', '99999', 'Смартфоны', 'Apple', 'Новый iPhone'],
            ['', '', '', '', ''],  # Еще одна пустая строка
            ['Samsung S23', '89999', '', 'Samsung', 'Galaxy S23'],  # Пустая категория
            ['MacBook Pro', '200000', 'Ноутбуки', '', ''],  # Пустые поля
            ['', '', '', '', ''],  # Пустая строка в конце
        ]
        
        file_path = self.fixtures_dir / "empty_gaps.csv"
        
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for row in data:
                writer.writerow(row)
        
        expected = {
            'filename': 'empty_gaps.csv',
            'expected_rows_in': 3,  # Только строки с данными
            'expected_rows_out': 3,
            'challenges': ['Empty rows', 'Empty column headers', 'Missing data', 'Unnamed columns']
        }
        
        with open(self.expected_dir / "empty_gaps_expected.json", 'w', encoding='utf-8') as f:
            json.dump(expected, f, indent=2, ensure_ascii=False)
        
        return expected
    
    def create_mock_pdf_table(self) -> Dict[str, Any]:
        """Evil Fixture 5: Mock PDF table"""
        
        pdf_content = """
PDF TABLE SIMULATION
====================

ПРАЙС-ЛИСТ ТОВАРОВ 2024
Компания: ООО "Тест Системс"
Дата обновления: 15.01.2024

┌─────────────────────┬──────────┬─────────────┬──────────────┐
│ Название товара     │ Цена     │ Категория   │ Примечание   │
├─────────────────────┼──────────┼─────────────┼──────────────┤
│ iPhone 15 Pro       │ 120,000  │ Смартфоны   │ Новинка 2024 │
│ MacBook Air M2      │ 150,000  │ Ноутбуки    │ В наличии    │
│ iPad Pro 12.9"      │ 80,000   │ Планшеты    │ Под заказ    │
│ AirPods Pro 2       │ 25,000   │ Аксессуары  │ Скидка 10%   │
│ Apple Watch Ultra   │ 95,000   │ Часы        │ Водонепр.    │
└─────────────────────┴──────────┴─────────────┴──────────────┘

Итого товаров: 5
Общая стоимость: 470,000 руб.

Условия доставки:
- Москва: бесплатно от 50,000 руб.
- Регионы: 1,500 руб.

Контакты: sales@testsystems.ru
Телефон: +7 (495) 123-45-67
        """
        
        file_path = self.fixtures_dir / "pdf_table.txt"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(pdf_content)
        
        expected = {
            'filename': 'pdf_table.txt',
            'expected_rows_in': 5,
            'expected_rows_out': 5,
            'format': 'mock_pdf',
            'challenges': ['PDF table extraction', 'ASCII table parsing', 'Non-standard format', 'Mixed content']
        }
        
        with open(self.expected_dir / "pdf_table_expected.json", 'w', encoding='utf-8') as f:
            json.dump(expected, f, indent=2, ensure_ascii=False)
        
        return expected
    
    def create_mock_ocr_image(self) -> Dict[str, Any]:
        """Evil Fixture 6: Mock OCR image result"""
        
        ocr_content = """
OCR TEXT EXTRACTION RESULT
=========================

Исходное изображение: product_list.jpg
Качество OCR: 87%
Дата обработки: 2024-01-15

ИЗВЛЕЧЕННЫЙ ТЕКСТ:
-----------------

ПРАЙС-ЛИСТ (OCR)

товар:           iPhone14Pro
цена:            99999руб
категория:       смартфоны
статус:          наличии

товар:           SamsungGalaxyS23
цена:            89999
категория:       телефоны
статус:          заказ

товар:           macbookpro14
цена:            200000р
категория:       ноутбуки
статус:          наличии

товар:           ipadair
цена:            59999руб
категория:       планшеты
статус:          склад

КОНЕЦ ТАБЛИЦЫ

ПРИМЕЧАНИЯ OCR:
- Склеенные слова (характерно для OCR)
- Пропущенные пробелы
- Возможные ошибки распознавания
- Неточности в числах
- Смешанные единицы валют (руб/р)

Точность извлечения: 4 из 4 товаров распознаны
Рекомендация: Проверить цены вручную
        """
        
        file_path = self.fixtures_dir / "ocr_table.txt"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(ocr_content)
        
        expected = {
            'filename': 'ocr_table.txt',
            'expected_rows_in': 4,
            'expected_rows_out': 4,
            'format': 'mock_ocr',
            'challenges': ['OCR text extraction', 'Joined words', 'Text parsing', 'Format recognition', 'OCR errors']
        }
        
        with open(self.expected_dir / "ocr_table_expected.json", 'w', encoding='utf-8') as f:
            json.dump(expected, f, indent=2, ensure_ascii=False)
        
        return expected
    
    def create_fixtures_manifest(self, fixtures: List[Dict[str, Any]]):
        """Создает манифест всех fixtures"""
        
        manifest = {
            'mon_s01_fixtures': {
                'description': 'Simple evil test fixtures for MON-S01 regression testing',
                'generator': 'SimpleEvilFixtureGenerator',
                'total_fixtures': len(fixtures),
                'created_at': '2024-01-15',
                'fixtures': fixtures,
                'test_objectives': [
                    'Data validation robustness',
                    'Error handling',
                    'Format compatibility',
                    'Performance under load',
                    'Edge case handling',
                    'Encoding support'
                ]
            }
        }
        
        with open(self.fixtures_dir / "fixtures_manifest.json", 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"\n📋 Создан манифест fixtures: {len(fixtures)} файлов")

def main():
    """Создание всех evil fixtures"""
    print("🚀 Запуск простого генератора Evil Fixtures для MON-S01")
    
    generator = SimpleEvilFixtureGenerator()
    fixtures = generator.create_all_fixtures()
    
    print(f"\n🎯 MON-S01 Evil Fixtures готовы!")
    print(f"📁 Расположение: tests/fixtures/evil_files/")
    print(f"📊 Ожидаемые результаты: tests/fixtures/expected_outputs/")
    print(f"\n📋 Созданные файлы:")
    
    for fixture in fixtures:
        challenges = ', '.join(fixture.get('challenges', []))
        print(f"   • {fixture['filename']} - {challenges}")
    
    return fixtures

if __name__ == "__main__":
    main() 