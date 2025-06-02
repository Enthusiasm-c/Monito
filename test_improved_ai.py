#!/usr/bin/env python3
"""
Тест улучшенного AI парсера с увеличенным лимитом строк
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

# Enhanced logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from modules.universal_excel_parser import UniversalExcelParser

def test_improved_ai():
    """Тест улучшенного AI парсера"""
    print("🚀 ТЕСТ УЛУЧШЕННОГО AI ПАРСЕРА")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY не установлен")
        return
    
    # Test file
    test_file = "/Users/denisdomashenko/price_list_analyzer/DOC-20250428-WA0004..xlsx"
    
    if not os.path.exists(test_file):
        print(f"❌ Файл не найден: {test_file}")
        return
    
    print(f"📄 Тестируем файл: {os.path.basename(test_file)}")
    
    # Create parser
    parser = UniversalExcelParser()
    
    print(f"\n🤖 ТЕСТ УЛУЧШЕННОГО AI (100 строк vs 20)")
    print("-" * 50)
    
    try:
        result = parser.extract_products_universal(test_file, max_products=200, use_ai=True)
        
        if 'error' in result:
            print(f"❌ Ошибка: {result['error']}")
        else:
            products = result.get('products', [])
            stats = result.get('extraction_stats', {})
            
            print(f"✅ AI извлечение с новыми параметрами:")
            print(f"   📦 Товаров найдено: {len(products)}")
            print(f"   📊 Метод: {stats.get('extraction_method', 'N/A')}")
            print(f"   🤖 AI Enhanced: {stats.get('ai_enhanced', False)}")
            print(f"   📋 Всего строк: {stats.get('total_rows', 0)}")
            print(f"   🎯 Покрытие: {len(products)}/{stats.get('total_rows', 1)*100:.1f}% строк")
            
            # Показываем примеры из разных частей
            print(f"\n🎯 ПРИМЕРЫ ИЗВЛЕЧЕННЫХ ТОВАРОВ:")
            for i, product in enumerate(products[:10]):
                print(f"{i+1}. {product.get('original_name', 'N/A')} | {product.get('price', 0)} | {product.get('unit', 'N/A')}")
                if 'brand' in product:
                    print(f"   🏷️ Бренд: {product.get('brand')}")
                if 'size' in product:
                    print(f"   📏 Размер: {product.get('size')}")
                print()
            
            if len(products) > 10:
                print(f"   ... и еще {len(products) - 10} товаров")
            
            # Сравнение с предыдущим результатом
            expected_improvement = len(products) - 8  # Было 8 товаров
            print(f"\n📈 УЛУЧШЕНИЕ:")
            print(f"   🔺 Было товаров: 8")
            print(f"   🔺 Стало товаров: {len(products)}")
            print(f"   🚀 Прирост: +{expected_improvement} товаров ({expected_improvement/8*100:.0f}% улучшение)")
    
    except Exception as e:
        print(f"❌ Ошибка теста: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    test_improved_ai()

if __name__ == "__main__":
    main()