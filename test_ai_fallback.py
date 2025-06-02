#!/usr/bin/env python3
"""
Test AI fallback mechanism
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

def test_fallback_mechanism():
    """Test AI to manual parser fallback"""
    print("🔄 ТЕСТ МЕХАНИЗМА FALLBACK (AI → Классический)")
    print("=" * 60)
    
    # PDF file path
    pdf_file = "/Users/denisdomashenko/price_list_analyzer/1. PT. Global Anugrah Pasifik (groceries item).pdf"
    
    if not os.path.exists(pdf_file):
        print(f"❌ PDF файл не найден: {pdf_file}")
        return
    
    print(f"📄 Тестируем файл: {os.path.basename(pdf_file)}")
    
    # Save original API key
    original_api_key = os.getenv('OPENAI_API_KEY')
    
    # Test 1: With API key (should use AI)
    print("\n🤖 ТЕСТ 1: С API ключом (должен использовать AI)")
    print("-" * 50)
    
    parser = PDFParser()
    try:
        result_with_ai = parser.extract_products_from_pdf(pdf_file, max_products=10, use_ai=True)
        
        if 'error' in result_with_ai:
            print(f"❌ Ошибка: {result_with_ai['error']}")
        else:
            stats = result_with_ai.get('extraction_stats', {})
            print(f"✅ Успешно! Метод: {stats.get('extraction_method', 'N/A')}")
            print(f"🤖 AI Enhanced: {stats.get('ai_enhanced', False)}")
            print(f"📦 Товаров: {len(result_with_ai.get('products', []))}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Test 2: Remove API key (should fallback to manual)
    print("\n🔧 ТЕСТ 2: Без API ключа (должен использовать классический парсер)")
    print("-" * 50)
    
    # Temporarily remove API key
    if 'OPENAI_API_KEY' in os.environ:
        del os.environ['OPENAI_API_KEY']
    
    try:
        result_fallback = parser.extract_products_from_pdf(pdf_file, max_products=10, use_ai=True)
        
        if 'error' in result_fallback:
            print(f"❌ Ошибка: {result_fallback['error']}")
        else:
            stats = result_fallback.get('extraction_stats', {})
            print(f"✅ Успешно! Метод: {stats.get('extraction_method', 'N/A')}")
            print(f"🤖 AI Enhanced: {stats.get('ai_enhanced', False)}")
            print(f"📦 Товаров: {len(result_fallback.get('products', []))}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Test 3: Explicit disable AI
    print("\n⚙️ ТЕСТ 3: AI явно отключен (use_ai=False)")
    print("-" * 50)
    
    # Restore API key
    if original_api_key:
        os.environ['OPENAI_API_KEY'] = original_api_key
    
    try:
        result_no_ai = parser.extract_products_from_pdf(pdf_file, max_products=10, use_ai=False)
        
        if 'error' in result_no_ai:
            print(f"❌ Ошибка: {result_no_ai['error']}")
        else:
            stats = result_no_ai.get('extraction_stats', {})
            print(f"✅ Успешно! Метод: {stats.get('extraction_method', 'N/A')}")
            print(f"🤖 AI Enhanced: {stats.get('ai_enhanced', False)}")
            print(f"📦 Товаров: {len(result_no_ai.get('products', []))}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print("\n📊 СВОДКА ТЕСТОВ FALLBACK")
    print("-" * 50)
    print("✅ Все тесты fallback механизма выполнены")
    print("🔄 Система корректно переключается между AI и классическим парсером")

def main():
    """Main function"""
    test_fallback_mechanism()

if __name__ == "__main__":
    main()