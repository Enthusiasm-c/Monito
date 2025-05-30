#!/usr/bin/env python3
"""
MCP интеграция с Google Sheets для Price List Analyzer
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional

# Добавляем корневую директорию
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.google_sheets_manager import GoogleSheetsManager

class PriceListAnalyzerWithGoogleSheets:
    """Анализатор прайс-листов с интеграцией Google Sheets"""
    
    def __init__(self):
        self.data_dir = "data"
        self.temp_dir = "data/temp"
        self.google_sheets = GoogleSheetsManager()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Создание необходимых директорий"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def process_excel_file(self, file_path: str, supplier_name: str = None) -> Dict[str, Any]:
        """Обработка Excel файла и загрузка в Google Sheets"""
        try:
            import pandas as pd
            
            # Чтение Excel файла
            df = pd.read_excel(file_path)
            
            # Поиск колонок с товарами и ценами
            product_col = None
            price_col = None
            
            for col in df.columns:
                col_lower = str(col).lower()
                if any(keyword in col_lower for keyword in ['product', 'название', 'товар', 'item', 'name']):
                    product_col = col
                if any(keyword in col_lower for keyword in ['price', 'цена', 'cost', 'стоимость']):
                    price_col = col
            
            # Определение поставщика
            if not supplier_name:
                supplier_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Извлечение товаров
            products = []
            for idx, row in df.iterrows():
                try:
                    product_name = str(row[product_col] if product_col else row.iloc[0])
                    price_str = str(row[price_col] if price_col else row.iloc[1])
                    
                    # Очистка цены от нечисловых символов
                    import re
                    price_clean = re.sub(r'[^\d.,]', '', price_str)
                    if price_clean:
                        price = float(price_clean.replace(',', '.'))
                    else:
                        price = 0
                    
                    if len(product_name) > 3 and price > 0:
                        products.append({
                            'original_name': product_name,
                            'standardized_name': product_name,  # Упрощенная стандартизация
                            'price': price,
                            'unit': 'pcs',
                            'category': 'general',
                            'confidence': 0.8
                        })
                except Exception as e:
                    print(f"Ошибка обработки строки {idx}: {e}")
                    continue
            
            if not products:
                return {
                    'status': 'error',
                    'message': 'Не найдено товаров с ценами'
                }
            
            # Подготовка данных для Google Sheets
            standardized_data = {
                'supplier': {
                    'name': supplier_name,
                    'contact': '',
                    'confidence': 0.9
                },
                'products': products,
                'data_quality': {
                    'source_clarity': 'high',
                    'extraction_confidence': 0.8,
                    'potential_errors': []
                }
            }
            
            # Загрузка в Google Sheets
            if self.google_sheets.is_connected():
                # Обновление основной таблицы
                update_result = self.google_sheets.update_master_table(standardized_data)
                
                # Создание отдельного листа для поставщика
                supplier_sheet_created = self.google_sheets.create_supplier_summary(supplier_name, products)
                
                return {
                    'status': 'success',
                    'file_type': 'excel',
                    'supplier': supplier_name,
                    'products_found': len(products),
                    'google_sheets_result': update_result,
                    'supplier_sheet_created': supplier_sheet_created,
                    'sheet_url': self.google_sheets.get_sheet_url(),
                    'processed_at': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'partial_success',
                    'file_type': 'excel',
                    'supplier': supplier_name,
                    'products_found': len(products),
                    'products': products[:5],  # Первые 5 товаров
                    'message': 'Файл обработан, но не удалось подключиться к Google Sheets',
                    'processed_at': datetime.now().isoformat()
                }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'processed_at': datetime.now().isoformat()
            }
    
    def test_google_sheets_connection(self) -> Dict[str, Any]:
        """Тест подключения к Google Sheets"""
        return self.google_sheets.test_connection()
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        if self.google_sheets.is_connected():
            return self.google_sheets.get_stats()
        else:
            return {
                'error': 'Нет подключения к Google Sheets',
                'local_stats': {
                    'temp_files': len([f for f in os.listdir(self.temp_dir) if f.endswith(('.xlsx', '.xls'))]),
                    'last_check': datetime.now().isoformat()
                }
            }
    
    def create_demo_google_sheet(self) -> Dict[str, Any]:
        """Создание демо данных в Google Sheets"""
        try:
            # Демо данные
            demo_products = [
                {
                    'original_name': 'Apple iPhone 13 Pro 128GB',
                    'standardized_name': 'Apple iPhone 13 Pro 128GB',
                    'price': 999.99,
                    'unit': 'pcs',
                    'category': 'electronics',
                    'confidence': 0.95
                },
                {
                    'original_name': 'Samsung Galaxy S22 Ultra',
                    'standardized_name': 'Samsung Galaxy S22 Ultra',
                    'price': 1199.99,
                    'unit': 'pcs', 
                    'category': 'electronics',
                    'confidence': 0.92
                },
                {
                    'original_name': 'MacBook Pro 14" M2',
                    'standardized_name': 'MacBook Pro 14 inch M2',
                    'price': 1999.99,
                    'unit': 'pcs',
                    'category': 'computers',
                    'confidence': 0.98
                }
            ]
            
            standardized_data = {
                'supplier': {
                    'name': 'Demo Electronics Store',
                    'contact': 'demo@electronics.com',
                    'confidence': 1.0
                },
                'products': demo_products,
                'data_quality': {
                    'source_clarity': 'high',
                    'extraction_confidence': 0.95,
                    'potential_errors': []
                }
            }
            
            if self.google_sheets.is_connected():
                # Обновление основной таблицы
                update_result = self.google_sheets.update_master_table(standardized_data)
                
                # Создание листа поставщика
                supplier_sheet_created = self.google_sheets.create_supplier_summary('Demo Electronics Store', demo_products)
                
                return {
                    'status': 'success',
                    'message': 'Демо данные добавлены в Google Sheets',
                    'products_added': len(demo_products),
                    'update_result': update_result,
                    'supplier_sheet_created': supplier_sheet_created,
                    'sheet_url': self.google_sheets.get_sheet_url()
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Нет подключения к Google Sheets'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

# Глобальный экземпляр анализатора
analyzer = PriceListAnalyzerWithGoogleSheets()

# MCP функции
async def mcp_process_file(file_path: str, supplier_name: str = None) -> Dict[str, Any]:
    """MCP функция для обработки файла и загрузки в Google Sheets"""
    if not os.path.exists(file_path):
        return {'status': 'error', 'message': 'Файл не найден'}
    
    return await analyzer.process_excel_file(file_path, supplier_name)

def mcp_test_connection() -> Dict[str, Any]:
    """MCP функция для тестирования подключения к Google Sheets"""
    return analyzer.test_google_sheets_connection()

def mcp_get_stats() -> Dict[str, Any]:
    """MCP функция для получения статистики"""
    return analyzer.get_stats()

def mcp_create_demo() -> Dict[str, Any]:
    """MCP функция для создания демо данных"""
    return analyzer.create_demo_google_sheet()

# Демо для тестирования
async def demo_test():
    """Демо тест Google Sheets интеграции"""
    print("🔍 GOOGLE SHEETS ДЕМО-ТЕСТ")
    print("="*50)
    
    # Тест подключения
    print("🔗 Тест подключения к Google Sheets...")
    connection_test = mcp_test_connection()
    print(f"Статус: {connection_test['status']}")
    print(f"Сообщение: {connection_test['message']}")
    
    if connection_test['status'] == 'success':
        print(f"📊 Таблица: {connection_test['sheet_info']['title']}")
        print(f"🔗 URL: {connection_test['sheet_info']['url']}")
        
        # Создание демо данных
        print(f"\n📝 Создание демо данных...")
        demo_result = mcp_create_demo()
        print(f"Статус: {demo_result['status']}")
        
        if demo_result['status'] == 'success':
            print(f"✅ Добавлено товаров: {demo_result['products_added']}")
            print(f"🔗 Ссылка на таблицу: {demo_result['sheet_url']}")
            
            # Создание демо Excel файла и его обработка
            print(f"\n📁 Создание и обработка демо Excel файла...")
            try:
                import pandas as pd
                
                demo_excel_data = {
                    'Product Name': ['Dell XPS 13', 'HP Pavilion 15', 'Lenovo ThinkPad X1'],
                    'Price': ['$1299.99', '$699.99', '$1599.99'],
                    'Stock': [10, 25, 8]
                }
                
                df = pd.DataFrame(demo_excel_data)
                demo_file = f"{analyzer.temp_dir}/demo_supplier.xlsx"
                df.to_excel(demo_file, index=False)
                
                # Обработка файла
                process_result = await mcp_process_file(demo_file, "Tech Supplier Demo")
                print(f"Обработка: {process_result['status']}")
                
                if process_result['status'] == 'success':
                    print(f"✅ Найдено товаров: {process_result['products_found']}")
                    print(f"✅ Поставщик: {process_result['supplier']}")
                
            except Exception as e:
                print(f"❌ Ошибка создания демо файла: {e}")
        
        # Получение статистики
        print(f"\n📈 Статистика...")
        stats = mcp_get_stats()
        if 'error' not in stats:
            print(f"Всего товаров: {stats.get('total_products', 0)}")
            print(f"Поставщиков: {stats.get('total_suppliers', 0)}")
            print(f"Категорий: {len(stats.get('categories', []))}")
        
    else:
        print("❌ Нет подключения к Google Sheets")
        print("Рекомендации:")
        for suggestion in connection_test.get('suggestions', []):
            print(f"  • {suggestion}")

if __name__ == "__main__":
    asyncio.run(demo_test())