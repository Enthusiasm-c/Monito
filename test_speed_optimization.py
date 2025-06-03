#!/usr/bin/env python3
"""
Тест оптимизации скорости обработки
"""

import os
import sys
import asyncio
import time
import logging
from dotenv import load_dotenv

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

# Краткое логирование
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

from upload_and_process import process_file_directly

async def test_speed_optimization():
    """Тест оптимизации скорости"""
    print("⚡ ТЕСТ ОПТИМИЗАЦИИ СКОРОСТИ")
    print("=" * 60)
    
    # Test file
    test_file = "/Users/denisdomashenko/price_list_analyzer/DOC-20250428-WA0004..xlsx"
    
    if not os.path.exists(test_file):
        print(f"❌ Файл не найден: {test_file}")
        return
    
    print(f"📄 Тестируем файл: {os.path.basename(test_file)}")
    print(f"🎯 Цель: сократить время с ~157 сек до ~60-80 сек")
    print("-" * 60)
    
    # Засекаем время
    total_start_time = time.time()
    
    try:
        result = await process_file_directly(test_file)
        
        total_time = time.time() - total_start_time
        
        print("\n" + "=" * 60)
        print("⚡ РЕЗУЛЬТАТЫ ОПТИМИЗАЦИИ СКОРОСТИ:")
        print("=" * 60)
        
        if result:
            extraction_stats = result.get('extraction_stats', {})
            processing_stats = result.get('processing_stats', {})
            
            print(f"✅ Обработка завершена успешно!")
            print(f"⏱️  ОБЩЕЕ ВРЕМЯ: {total_time:.1f} секунд")
            
            # Сравнение с предыдущим результатом
            old_time = 157.7
            improvement = old_time - total_time
            improvement_percent = (improvement / old_time) * 100
            
            print(f"📊 СРАВНЕНИЕ:")
            print(f"   🔺 Было: {old_time:.1f}с")
            print(f"   🔻 Стало: {total_time:.1f}с") 
            print(f"   🚀 Ускорение: {improvement:+.1f}с ({improvement_percent:+.1f}%)")
            
            if total_time < 80:
                print(f"🎉 ЦЕЛЬ ДОСТИГНУТА! Время меньше 80 секунд")
            elif total_time < 100:
                print(f"✅ Хорошее улучшение! Почти достигли цели")
            else:
                print(f"⚠️ Требуется дополнительная оптимизация")
            
            print(f"\n📦 ДЕТАЛИ ОБРАБОТКИ:")
            print(f"   🤖 AI Enhanced: {extraction_stats.get('ai_enhanced', False)}")
            print(f"   📊 Извлечено товаров: {extraction_stats.get('extracted_products', 0)}")
            
            if processing_stats:
                print(f"   🔥 Успешных пакетов: {processing_stats.get('successful_batches', 0)}/{processing_stats.get('total_batches', 0)}")
                print(f"   ⚡ Успешность: {processing_stats.get('success_rate', 0):.1%}")
                print(f"   🪙 Токенов: {processing_stats.get('estimated_tokens', 0)}")
            
            # Анализ времени по этапам
            print(f"\n🔍 АНАЛИЗ ПРОИЗВОДИТЕЛЬНОСТИ:")
            if total_time < 60:
                print(f"   🚀 ОТЛИЧНАЯ скорость (<60с)")
            elif total_time < 90:
                print(f"   ✅ ХОРОШАЯ скорость (60-90с)")
            elif total_time < 120:
                print(f"   ⚠️ ПРИЕМЛЕМАЯ скорость (90-120с)")
            else:
                print(f"   ❌ МЕДЛЕННАЯ скорость (>120с)")
        else:
            print(f"❌ Обработка не удалась за {total_time:.1f}с")
            
    except Exception as e:
        total_time = time.time() - total_start_time
        print(f"❌ Ошибка тестирования за {total_time:.1f}с: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    asyncio.run(test_speed_optimization())

if __name__ == "__main__":
    main()