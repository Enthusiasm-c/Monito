#!/usr/bin/env python3
"""
Test script to demonstrate detailed logging for tracking data losses and failures
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

# Enhanced logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('detailed_processing.log', mode='w', encoding='utf-8')
    ]
)

from upload_and_process import process_file_directly

async def test_with_detailed_logging():
    """Test file processing with comprehensive logging"""
    print("🔍 ТЕСТ С ДЕТАЛЬНЫМ ЛОГИРОВАНИЕМ")
    print("=" * 60)
    print("📝 Лог сохраняется в: detailed_processing.log")
    print("=" * 60)
    
    # Test file
    test_file = "/Users/denisdomashenko/price_list_analyzer/DOC-20250428-WA0004..xlsx"
    
    if not os.path.exists(test_file):
        print(f"❌ Файл не найден: {test_file}")
        # Try to find any Excel file
        import glob
        excel_files = glob.glob("**/*.xlsx", recursive=True) + glob.glob("**/*.xls", recursive=True)
        if excel_files:
            test_file = excel_files[0]
            print(f"📄 Используем файл: {os.path.basename(test_file)}")
        else:
            print("❌ Нет Excel файлов для тестирования")
            return
    
    print(f"\n🚀 Запускаем обработку с детальным логированием...")
    print(f"📄 Файл: {os.path.basename(test_file)}")
    print(f"🔍 Следите за логами в консоли и файле 'detailed_processing.log'")
    print("-" * 60)
    
    try:
        result = await process_file_directly(test_file)
        
        print("\n" + "=" * 60)
        print("📊 АНАЛИЗ РЕЗУЛЬТАТОВ:")
        
        if result:
            extraction_stats = result.get('extraction_stats', {})
            processing_stats = result.get('processing_stats', {})
            
            print(f"✅ Обработка завершена успешно")
            print(f"🔧 Метод извлечения: {extraction_stats.get('extraction_method', 'N/A')}")
            print(f"🤖 AI Enhanced: {extraction_stats.get('ai_enhanced', False)}")
            
            if processing_stats:
                print(f"📦 Товаров в ChatGPT: {processing_stats.get('total_input_products', 0)} → {processing_stats.get('total_output_products', 0)}")
                print(f"📊 Успешность ChatGPT: {processing_stats.get('success_rate', 0):.1%}")
                print(f"💔 Провалившихся пакетов: {processing_stats.get('total_batches', 0) - processing_stats.get('successful_batches', 0)}")
        else:
            print(f"❌ Обработка не удалась")
        
        print(f"\n📝 Детальные логи сохранены в файл: detailed_processing.log")
        print(f"🔍 Откройте файл для анализа точных причин потерь")
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    asyncio.run(test_with_detailed_logging())

if __name__ == "__main__":
    main()