#!/usr/bin/env python3
"""
Test AI-powered PDF parsing on the problematic PDF file
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from modules.pdf_parser import PDFParser

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ai_pdf_parsing():
    """Test AI parsing on the problematic PDF file"""
    print("🤖 ТЕСТ AI-ПАРСИНГА PDF ФАЙЛА")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY не установлен")
        return
    
    # PDF file path
    pdf_file = "/Users/denisdomashenko/price_list_analyzer/1. PT. Global Anugrah Pasifik (groceries item).pdf"
    
    if not os.path.exists(pdf_file):
        print(f"❌ PDF файл не найден: {pdf_file}")
        return
    
    print(f"📄 Тестируем файл: {os.path.basename(pdf_file)}")
    
    # Create PDF parser
    parser = PDFParser()
    
    # Test AI parsing
    print("\n🤖 ТЕСТ 1: AI-powered парсинг")
    print("-" * 40)
    
    try:
        result_ai = parser.extract_products_from_pdf(pdf_file, max_products=50, use_ai=True)
        
        if 'error' in result_ai:
            print(f"❌ Ошибка AI парсинга: {result_ai['error']}")
        else:
            products_ai = result_ai.get('products', [])
            stats_ai = result_ai.get('extraction_stats', {})
            
            print(f"✅ AI извлечение успешно!")
            print(f"📦 Товаров найдено: {len(products_ai)}")
            print(f"🎯 Метод извлечения: {stats_ai.get('extraction_method', 'N/A')}")
            print(f"🔧 AI Enhanced: {stats_ai.get('ai_enhanced', False)}")
            print(f"📊 Успешность: {stats_ai.get('success_rate', 0):.1%}")
            
            # Show examples
            print(f"\n🎯 ПРИМЕРЫ ТОВАРОВ (AI):")
            for i, product in enumerate(products_ai[:5]):
                print(f"{i+1}. {product.get('original_name', 'N/A')}")
                print(f"   💰 Цена: {product.get('price', 0)}")
                print(f"   📦 Единица: {product.get('unit', 'N/A')}")
                print(f"   🏷️ Бренд: {product.get('brand', 'N/A')}")
                print(f"   📏 Размер: {product.get('size', 'N/A')}")
                print()
    
    except Exception as e:
        print(f"❌ Ошибка AI теста: {e}")
    
    # Test manual parsing for comparison
    print("\n🔧 ТЕСТ 2: Классический парсинг (для сравнения)")
    print("-" * 40)
    
    try:
        result_manual = parser.extract_products_from_pdf(pdf_file, max_products=50, use_ai=False)
        
        if 'error' in result_manual:
            print(f"❌ Ошибка классического парсинга: {result_manual['error']}")
        else:
            products_manual = result_manual.get('products', [])
            stats_manual = result_manual.get('extraction_stats', {})
            
            print(f"✅ Классическое извлечение успешно!")
            print(f"📦 Товаров найдено: {len(products_manual)}")
            print(f"🎯 Метод извлечения: {stats_manual.get('extraction_method', 'N/A')}")
            print(f"📊 Успешность: {stats_manual.get('success_rate', 0):.1%}")
            
            # Show examples
            print(f"\n🎯 ПРИМЕРЫ ТОВАРОВ (Классический):")
            for i, product in enumerate(products_manual[:5]):
                print(f"{i+1}. {product.get('original_name', 'N/A')}")
                print(f"   💰 Цена: {product.get('price', 0)}")
                print(f"   📦 Единица: {product.get('unit', 'N/A')}")
                print()
    
    except Exception as e:
        print(f"❌ Ошибка классического теста: {e}")
    
    # Comparison
    print("\n📊 СРАВНЕНИЕ РЕЗУЛЬТАТОВ")
    print("-" * 40)
    
    try:
        if 'products_ai' in locals() and 'products_manual' in locals():
            print(f"🤖 AI парсинг: {len(products_ai)} товаров")
            print(f"🔧 Классический: {len(products_manual)} товаров")
            print(f"📈 Улучшение: {((len(products_ai) - len(products_manual)) / max(len(products_manual), 1) * 100):+.1f}%")
            
            # Quality comparison - check if AI found more meaningful product names
            if products_ai and products_manual:
                ai_avg_name_length = sum(len(p.get('original_name', '')) for p in products_ai) / len(products_ai)
                manual_avg_name_length = sum(len(p.get('original_name', '')) for p in products_manual) / len(products_manual)
                
                print(f"📝 Средняя длина названий:")
                print(f"   🤖 AI: {ai_avg_name_length:.1f} символов")
                print(f"   🔧 Классический: {manual_avg_name_length:.1f} символов")
    except:
        pass

def main():
    """Main function"""
    test_ai_pdf_parsing()

if __name__ == "__main__":
    main()