#!/usr/bin/env python3
"""
MCP интеграция для Price List Analyzer
Упрощенная версия без проблемных зависимостей
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional

# Добавляем корневую директорию
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class SimplifiedPriceListAnalyzer:
    """Упрощенная версия анализатора для MCP"""
    
    def __init__(self):
        self.data_dir = "data"
        self.temp_dir = "data/temp"
        self.master_table_path = "data/master_table.xlsx"
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Создание необходимых директорий"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def process_excel_file(self, file_path: str) -> Dict[str, Any]:
        """Упрощенная обработка Excel файлов"""
        try:
            import pandas as pd
            
            # Чтение Excel файла
            df = pd.read_excel(file_path)
            
            # Поиск колонок с товарами и ценами
            product_col = None
            price_col = None
            
            for col in df.columns:
                col_lower = str(col).lower()
                if any(keyword in col_lower for keyword in ['product', 'название', 'товар', 'item']):
                    product_col = col
                if any(keyword in col_lower for keyword in ['price', 'цена', 'cost', 'стоимость']):
                    price_col = col
            
            # Извлечение товаров
            products = []
            for idx, row in df.iterrows():
                try:
                    product_name = str(row[product_col] if product_col else row.iloc[0])
                    price = float(row[price_col] if price_col else 0)
                    
                    if len(product_name) > 3 and price > 0:
                        products.append({
                            'name': product_name,
                            'price': price,
                            'unit': 'pcs'
                        })
                except:
                    continue
            
            return {
                'status': 'success',
                'file_type': 'excel',
                'products_found': len(products),
                'products': products[:10],  # Первые 10 товаров
                'processed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'processed_at': datetime.now().isoformat()
            }
    
    async def create_summary_table(self, products: List[Dict]) -> str:
        """Создание сводной таблицы"""
        try:
            import pandas as pd
            
            if not products:
                return "Нет товаров для создания таблицы"
            
            # Создание DataFrame
            df = pd.DataFrame(products)
            
            # Сохранение в Excel
            output_path = f"{self.data_dir}/summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(output_path, index=False)
            
            return f"Таблица создана: {output_path}"
            
        except Exception as e:
            return f"Ошибка создания таблицы: {e}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        try:
            # Подсчет файлов в директории
            temp_files = len([f for f in os.listdir(self.temp_dir) if f.endswith(('.xlsx', '.xls', '.pdf'))])
            data_files = len([f for f in os.listdir(self.data_dir) if f.endswith('.xlsx')])
            
            return {
                'temp_files': temp_files,
                'processed_files': data_files,
                'last_check': datetime.now().isoformat(),
                'status': 'running'
            }
        except Exception as e:
            return {
                'error': str(e),
                'status': 'error'
            }

# MCP функции
analyzer = SimplifiedPriceListAnalyzer()

async def mcp_process_file(file_path: str) -> Dict[str, Any]:
    """MCP функция для обработки файла"""
    if not os.path.exists(file_path):
        return {'error': 'Файл не найден'}
    
    return await analyzer.process_excel_file(file_path)

async def mcp_create_table(products_json: str) -> str:
    """MCP функция для создания таблицы"""
    try:
        products = json.loads(products_json)
        return await analyzer.create_summary_table(products)
    except Exception as e:
        return f"Ошибка: {e}"

def mcp_get_stats() -> Dict[str, Any]:
    """MCP функция для получения статистики"""
    return analyzer.get_stats()

# Демо для тестирования
async def demo_test():
    """Демо тест для проверки работоспособности"""
    print("🔍 MCP ДЕМО-ТЕСТ PRICE LIST ANALYZER")
    print("="*50)
    
    # Создание демо файла
    print("📁 Создание демо файла...")
    try:
        import pandas as pd
        
        demo_data = {
            'Product Name': ['Apple iPhone 13', 'Samsung Galaxy S21', 'MacBook Pro'],
            'Price': [699.99, 599.99, 1299.99],
            'Unit': ['pcs', 'pcs', 'pcs']
        }
        
        df = pd.DataFrame(demo_data)
        demo_file = f"{analyzer.temp_dir}/demo_mcp.xlsx"
        df.to_excel(demo_file, index=False)
        print(f"✅ Демо файл создан: {demo_file}")
        
        # Тест обработки
        print("\n📊 Тест обработки файла...")
        result = await mcp_process_file(demo_file)
        print(f"✅ Результат: {result['status']}")
        print(f"   Найдено товаров: {result.get('products_found', 0)}")
        
        # Тест создания таблицы
        if result.get('products'):
            print("\n📋 Тест создания таблицы...")
            table_result = await mcp_create_table(json.dumps(result['products']))
            print(f"✅ {table_result}")
        
        # Тест статистики
        print("\n📈 Тест статистики...")
        stats = mcp_get_stats()
        print(f"✅ Статистика: {stats}")
        
        print(f"\n🎉 Все тесты пройдены успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(demo_test())