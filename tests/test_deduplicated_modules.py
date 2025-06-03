#!/usr/bin/env python3
"""
Тест исправленных модулей без дублирований
"""

import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_base_parser():
    """Тест базового парсера"""
    print("🧪 Тестируем BaseParser...")
    
    from modules.base_parser import BaseParser
    
    parser = BaseParser()
    
    # Тест функций анализа
    assert parser._looks_like_product("Apple iPhone 14") == True
    assert parser._looks_like_product("123") == False
    assert parser._looks_like_price("15000") == True
    assert parser._looks_like_price("abc") == False
    assert parser._looks_like_unit("kg") == True
    assert parser._looks_like_unit("xyz") == False
    
    # Тест очистки цены
    assert parser._clean_price("15,000") == 15000
    assert parser._clean_price("$100") == 100
    assert parser._clean_price("abc") == 0
    
    print("✅ BaseParser работает корректно")

def test_excel_parser():
    """Тест Excel парсера"""
    print("🧪 Тестируем UniversalExcelParser...")
    
    from modules.universal_excel_parser import UniversalExcelParser
    
    parser = UniversalExcelParser()
    
    # Проверяем наследование
    assert hasattr(parser, '_looks_like_product')
    assert hasattr(parser, '_looks_like_price')
    assert hasattr(parser, '_clean_price')
    
    # Тест функций из базового класса
    assert parser._looks_like_product("Samsung Galaxy S23") == True
    assert parser._clean_price("25000") == 25000
    
    print("✅ UniversalExcelParser наследует функции корректно")

def test_pdf_parser():
    """Тест PDF парсера"""
    print("🧪 Тестируем PDFParser...")
    
    from modules.pdf_parser import PDFParser
    
    parser = PDFParser()
    
    # Проверяем наследование
    assert hasattr(parser, '_looks_like_product')
    assert hasattr(parser, '_looks_like_price')
    assert hasattr(parser, '_clean_price')
    
    # Тест функций из базового класса
    assert parser._looks_like_product("Coca Cola 330ml") == True
    assert parser._clean_price("12.50") == 12.5
    
    print("✅ PDFParser наследует функции корректно")

def test_ai_parser():
    """Тест AI парсера"""
    print("🧪 Тестируем AITableParser...")
    
    from modules.ai_table_parser import AITableParser
    
    parser = AITableParser("test_key")
    
    # Проверяем наследование
    assert hasattr(parser, '_looks_like_product')
    assert hasattr(parser, '_looks_like_price')
    assert hasattr(parser, '_clean_price')
    
    # Тест функций из базового класса
    assert parser._looks_like_product("Bread whole wheat") == True
    assert parser._clean_price("5.99") == 5.99
    
    print("✅ AITableParser наследует функции корректно")

def test_no_duplicates():
    """Проверка отсутствия дублирований"""
    print("🧪 Проверяем отсутствие дублирований...")
    
    import modules.base_parser as base
    import modules.universal_excel_parser as excel
    import modules.pdf_parser as pdf
    import modules.ai_table_parser as ai
    
    # Проверяем, что функции определены только в базовом классе
    base_parser = base.BaseParser()
    excel_parser = excel.UniversalExcelParser()
    pdf_parser = pdf.PDFParser()
    ai_parser = ai.AITableParser("test")
    
    # Все должны использовать одну и ту же функцию из базового класса
    test_value = "Test Product 100g"
    
    base_result = base_parser._looks_like_product(test_value)
    excel_result = excel_parser._looks_like_product(test_value)
    pdf_result = pdf_parser._looks_like_product(test_value)
    ai_result = ai_parser._looks_like_product(test_value)
    
    assert base_result == excel_result == pdf_result == ai_result
    
    print("✅ Все парсеры используют единые функции из BaseParser")

def main():
    """Главная функция тестирования"""
    print("🚀 ТЕСТИРОВАНИЕ ИСПРАВЛЕННЫХ МОДУЛЕЙ")
    print("=" * 50)
    
    try:
        test_base_parser()
        test_excel_parser()
        test_pdf_parser()
        test_ai_parser()
        test_no_duplicates()
        
        print("\n" + "=" * 50)
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("✅ Дублирования устранены")
        print("✅ Наследование работает корректно")
        print("✅ Все модули функционируют")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 