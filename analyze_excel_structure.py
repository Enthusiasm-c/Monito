#!/usr/bin/env python3
"""
Анализ структуры Excel файла - где находятся товары
"""

import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def analyze_excel_structure():
    """Анализ структуры Excel файла"""
    
    file_path = "/Users/denisdomashenko/price_list_analyzer/DOC-20250428-WA0004..xlsx"
    
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        return
    
    print("🔍 АНАЛИЗ СТРУКТУРЫ EXCEL ФАЙЛА")
    print("=" * 60)
    
    try:
        # Читаем Excel файл
        df = pd.read_excel(file_path, sheet_name='Sheet1')
        
        print(f"📊 Общее количество строк: {len(df)}")
        print(f"📊 Общее количество столбцов: {len(df.columns)}")
        print(f"📋 Названия столбцов: {list(df.columns)}")
        
        print(f"\n📄 ПЕРВЫЕ 10 СТРОК:")
        print("-" * 40)
        for i in range(min(10, len(df))):
            row_data = []
            for col in df.columns:
                value = str(df.iloc[i][col]) if pd.notna(df.iloc[i][col]) else ""
                if len(value) > 30:
                    value = value[:27] + "..."
                row_data.append(value)
            print(f"Строка {i}: {' | '.join(row_data)}")
        
        print(f"\n📄 СТРОКИ 15-25 (где AI останавливается):")
        print("-" * 40)
        for i in range(15, min(25, len(df))):
            row_data = []
            for col in df.columns:
                value = str(df.iloc[i][col]) if pd.notna(df.iloc[i][col]) else ""
                if len(value) > 30:
                    value = value[:27] + "..."
                row_data.append(value)
            print(f"Строка {i}: {' | '.join(row_data)}")
        
        print(f"\n📄 СРЕДНИЕ СТРОКИ (50-60):")
        print("-" * 40)
        for i in range(50, min(60, len(df))):
            row_data = []
            for col in df.columns:
                value = str(df.iloc[i][col]) if pd.notna(df.iloc[i][col]) else ""
                if len(value) > 30:
                    value = value[:27] + "..."
                row_data.append(value)
            print(f"Строка {i}: {' | '.join(row_data)}")
        
        print(f"\n📄 ПОСЛЕДНИЕ 10 СТРОК:")
        print("-" * 40)
        start_idx = max(0, len(df) - 10)
        for i in range(start_idx, len(df)):
            row_data = []
            for col in df.columns:
                value = str(df.iloc[i][col]) if pd.notna(df.iloc[i][col]) else ""
                if len(value) > 30:
                    value = value[:27] + "..."
                row_data.append(value)
            print(f"Строка {i}: {' | '.join(row_data)}")
        
        # Анализ потенциальных товаров по всему файлу
        print(f"\n🔍 АНАЛИЗ ТОВАРОВ ПО ДИАПАЗОНАМ:")
        print("-" * 40)
        
        from modules.universal_excel_parser import UniversalExcelParser
        parser = UniversalExcelParser()
        
        # Анализируем разные диапазоны
        ranges = [
            (0, 20, "Первые 20 строк (AI видит)"),
            (20, 50, "Строки 20-50"),
            (50, 100, "Строки 50-100"),
            (100, len(df), "Строки 100+")
        ]
        
        for start, end, desc in ranges:
            if start >= len(df):
                continue
            
            end = min(end, len(df))
            df_slice = df.iloc[start:end].copy()
            
            if df_slice.empty:
                continue
            
            product_count = 0
            price_count = 0
            
            for _, row in df_slice.iterrows():
                for value in row:
                    if pd.notna(value):
                        value_str = str(value).strip()
                        
                        if parser._looks_like_product(value_str):
                            product_count += 1
                        elif parser._looks_like_price(value_str):
                            price_count += 1
            
            print(f"{desc}: товаров={product_count}, цен={price_count}")
        
        print(f"\n💡 ВЫВОД:")
        print("   Если AI анализирует только первые 20 строк,")
        print("   он может пропустить основную массу товаров!")
        
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_excel_structure()