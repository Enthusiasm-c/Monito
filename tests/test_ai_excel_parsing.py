#!/usr/bin/env python3
"""
Test AI-powered Excel parsing
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from modules.universal_excel_parser import UniversalExcelParser

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ai_excel_parsing():
    """Test AI parsing on Excel files"""
    print("🤖 ТЕСТ AI-ПАРСИНГА EXCEL ФАЙЛОВ")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY не установлен")
        return
    
    # Find Excel files
    import glob
    excel_files = glob.glob("**/*.xlsx", recursive=True) + glob.glob("**/*.xls", recursive=True)
    
    if not excel_files:
        print("❌ Excel файлы не найдены")
        return
    
    # Take first Excel file
    excel_file = excel_files[0]
    print(f"📄 Тестируем файл: {os.path.basename(excel_file)}")
    
    # Create Excel parser
    parser = UniversalExcelParser()
    
    # Test AI parsing
    print("\n🤖 ТЕСТ: AI-powered парсинг Excel")
    print("-" * 40)
    
    try:
        result_ai = parser.extract_products_universal(excel_file, max_products=20, use_ai=True)
        
        if 'error' in result_ai:
            print(f"❌ Ошибка AI парсинга: {result_ai['error']}")
        else:
            products_ai = result_ai.get('products', [])
            stats_ai = result_ai.get('extraction_stats', {})
            
            print(f"✅ AI извлечение: {len(products_ai)} товаров")
            print(f"🎯 Метод: {stats_ai.get('extraction_method', 'N/A')}")
            print(f"🤖 AI Enhanced: {stats_ai.get('ai_enhanced', False)}")
            print(f"📊 Успешность: {stats_ai.get('success_rate', 0):.1%}")
            
            # Show examples
            print(f"\n🎯 ПРИМЕРЫ ТОВАРОВ:")
            for i, product in enumerate(products_ai[:3]):
                print(f"{i+1}. {product.get('original_name', 'N/A')}")
                print(f"   💰 Цена: {product.get('price', 0)}")
                print(f"   📦 Единица: {product.get('unit', 'N/A')}")
                if product.get('brand'):
                    print(f"   🏷️ Бренд: {product.get('brand')}")
                if product.get('size'):
                    print(f"   📏 Размер: {product.get('size')}")
                print()
    
    except Exception as e:
        print(f"❌ Ошибка AI теста: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    test_ai_excel_parsing()

if __name__ == "__main__":
    main()