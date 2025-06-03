#!/usr/bin/env python3
"""
Тест полного пайплайна обработки Excel файлов:
IntelligentPreProcessor → DataAdapter → GoogleSheetsManager
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Добавляем модули в path
sys.path.insert(0, str(Path(__file__).parent))

def test_complete_pipeline():
    """Тестирует полный пайплайн обработки файла"""
    
    print('🚀 ТЕСТИРОВАНИЕ ПОЛНОГО ПАЙПЛАЙНА ОБРАБОТКИ')
    print('=' * 80)
    print('📊 Пайплайн: IntelligentPreProcessor → DataAdapter → GoogleSheetsManager')
    print()
    
    try:
        # Этап 1: Интеллектуальный препроцессор
        print('🔍 ЭТАП 1: ИНТЕЛЛЕКТУАЛЬНЫЙ АНАЛИЗ ФАЙЛА')
        print('-' * 60)
        
        from modules.intelligent_preprocessor import IntelligentPreProcessor
        processor = IntelligentPreProcessor()
        
        file_path = 'DOC-20250428-WA0004..xlsx'
        if not Path(file_path).exists():
            print(f'❌ Файл не найден: {file_path}')
            return False
        
        print(f'📁 Обрабатываем файл: {file_path}')
        intelligent_result = processor.process_excel_intelligent(file_path)
        
        if 'error' in intelligent_result:
            print(f'❌ Ошибка интеллектуального анализа: {intelligent_result["error"]}')
            return False
        
        total_products = len(intelligent_result['total_products'])
        total_prices = len(intelligent_result['total_prices'])
        linked_pairs = len(intelligent_result.get('product_price_pairs', []))
        completeness = intelligent_result['recovery_stats']['data_completeness']
        
        print(f'✅ Интеллектуальный анализ завершен:')
        print(f'   📦 Товаров найдено: {total_products}')
        print(f'   💰 Цен извлечено: {total_prices}')
        print(f'   🔗 Связанных пар: {linked_pairs}')
        print(f'   📈 Полнота данных: {completeness:.1f}%')
        print()
        
        # Этап 2: Адаптер данных
        print('🔄 ЭТАП 2: ПРЕОБРАЗОВАНИЕ ДАННЫХ')
        print('-' * 60)
        
        from modules.data_adapter import DataAdapter
        adapter = DataAdapter()
        
        supplier_name = f"SAI_FRESH_TEST_{datetime.now().strftime('%Y%m%d_%H%M')}"
        sheets_data = adapter.convert_intelligent_to_sheets_format(intelligent_result, supplier_name)
        
        if 'error' in sheets_data:
            print(f'❌ Ошибка преобразования данных: {sheets_data["error"]}')
            return False
        
        adapted_products = len(sheets_data.get('products', []))
        success_rate = sheets_data.get('processing_stats', {}).get('success_rate', 0)
        
        print(f'✅ Преобразование данных завершено:')
        print(f'   🔄 Товаров для Google Sheets: {adapted_products}')
        print(f'   📊 Успешность адаптации: {success_rate:.1f}%')
        print()
        
        # Показываем примеры преобразованных товаров
        print('📦 ПРИМЕРЫ ПРЕОБРАЗОВАННЫХ ТОВАРОВ:')
        for i, product in enumerate(sheets_data.get('products', [])[:5]):
            print(f'  {i+1}. {product["standardized_name"]} - {product["price"]:.0f} {product["currency"]} ({product["unit"]}) [{product["category"]}]')
        print()
        
        # Этап 3: Сохранение в Google Sheets
        print('💾 ЭТАП 3: СОХРАНЕНИЕ В GOOGLE SHEETS')
        print('-' * 60)
        
        from modules.google_sheets_manager import GoogleSheetsManager
        sheets_manager = GoogleSheetsManager()
        
        if not sheets_manager.is_connected():
            print('❌ Нет подключения к Google Sheets')
            return False
        
        print('✅ Подключение к Google Sheets установлено')
        
        # Сохраняем данные
        print('📊 Сохраняем данные в основную таблицу...')
        sheets_result = sheets_manager.update_master_table(sheets_data)
        
        if 'error' in sheets_result:
            print(f'❌ Ошибка сохранения в Google Sheets: {sheets_result["error"]}')
            return False
        
        print(f'✅ Данные сохранены в Google Sheets:')
        print(f'   📦 Новых товаров: {sheets_result.get("new_products", 0)}')
        print(f'   🔄 Обновленных цен: {sheets_result.get("updated_prices", 0)}')
        print(f'   📊 Всего обработано: {sheets_result.get("processed_products", 0)}')
        
        # Создаем лист поставщика
        print('📋 Создаем лист поставщика...')
        if sheets_manager.create_supplier_summary(supplier_name, sheets_data.get('products', [])):
            print(f'✅ Лист поставщика создан: Supplier_{supplier_name}')
        else:
            print('⚠️ Не удалось создать лист поставщика')
        
        # Получаем ссылку на таблицу
        sheets_url = sheets_manager.get_sheet_url()
        print(f'🔗 Ссылка на таблицу: {sheets_url}')
        print()
        
        # Итоговая статистика
        print('🎉 ИТОГОВАЯ СТАТИСТИКА ПАЙПЛАЙНА')
        print('=' * 60)
        print(f'📁 Исходный файл: {file_path}')
        print(f'🔍 Стратегия анализа: {intelligent_result.get("processing_strategy", "unknown")}')
        print(f'📊 Полнота извлечения: {completeness:.1f}%')
        print(f'🔄 Успешность адаптации: {success_rate:.1f}%')
        print(f'💾 Товаров в Google Sheets: {sheets_result.get("processed_products", 0)}')
        print(f'🏪 Поставщик: {supplier_name}')
        print()
        
        # Оценка качества
        if completeness >= 90 and success_rate >= 80 and sheets_result.get("processed_products", 0) > 0:
            print('🏆 РЕЗУЛЬТАТ: ОТЛИЧНЫЙ - полный пайплайн работает идеально!')
        elif completeness >= 70 and success_rate >= 60:
            print('✅ РЕЗУЛЬТАТ: ХОРОШИЙ - пайплайн работает с минимальными потерями')
        else:
            print('⚠️ РЕЗУЛЬТАТ: ТРЕБУЕТ ДОРАБОТКИ - есть проблемы в пайплайне')
        
        print()
        print('🔗 Проверьте результаты в Google Sheets:')
        print(f'   {sheets_url}')
        
        return True
        
    except Exception as e:
        logger.error(f'❌ Критическая ошибка в пайплайне: {e}', exc_info=True)
        print(f'❌ КРИТИЧЕСКАЯ ОШИБКА: {e}')
        return False

def test_data_quality():
    """Дополнительный тест качества данных"""
    
    print('\n🔍 ДОПОЛНИТЕЛЬНЫЙ ТЕСТ КАЧЕСТВА ДАННЫХ')
    print('=' * 50)
    
    try:
        from modules.intelligent_preprocessor import IntelligentPreProcessor
        from modules.data_adapter import DataAdapter
        
        processor = IntelligentPreProcessor()
        adapter = DataAdapter()
        
        file_path = 'DOC-20250428-WA0004..xlsx'
        
        # Получаем результат анализа
        result = processor.process_excel_intelligent(file_path)
        converted = adapter.convert_intelligent_to_sheets_format(result, "QUALITY_TEST")
        
        products = converted.get('products', [])
        
        # Анализ качества
        valid_prices = sum(1 for p in products if p.get('price', 0) > 0)
        valid_names = sum(1 for p in products if len(p.get('standardized_name', '')) > 2)
        categorized = sum(1 for p in products if p.get('category', 'general') != 'general')
        
        print(f'📊 Анализ качества данных:')
        print(f'   📦 Всего товаров: {len(products)}')
        print(f'   💰 С валидными ценами: {valid_prices} ({valid_prices/max(len(products),1)*100:.1f}%)')
        print(f'   📝 С валидными названиями: {valid_names} ({valid_names/max(len(products),1)*100:.1f}%)')
        print(f'   🏷️ С определенной категорией: {categorized} ({categorized/max(len(products),1)*100:.1f}%)')
        
        # Показываем проблемные товары
        problematic = [p for p in products if p.get('price', 0) <= 0 or len(p.get('standardized_name', '')) <= 2]
        if problematic:
            print(f'\n⚠️ Проблемные товары ({len(problematic)}):')
            for i, p in enumerate(problematic[:3]):
                print(f'  {i+1}. {p.get("standardized_name", "N/A")} - цена: {p.get("price", 0)}')
        
        return len(products) > 0 and valid_prices/max(len(products),1) > 0.5
        
    except Exception as e:
        print(f'❌ Ошибка теста качества: {e}')
        return False

if __name__ == "__main__":
    print('🧪 Запуск полного тестирования системы...')
    print()
    
    # Основной тест пайплайна
    pipeline_success = test_complete_pipeline()
    
    # Тест качества данных
    quality_success = test_data_quality()
    
    print('\n' + '='*80)
    print('📋 ФИНАЛЬНЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ')
    print('='*80)
    
    if pipeline_success and quality_success:
        print('🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!')
        print('✅ Полный пайплайн работает корректно')
        print('✅ Качество данных соответствует требованиям')
        print('💾 Данные успешно сохранены в Google Sheets')
    elif pipeline_success:
        print('⚠️ ЧАСТИЧНЫЙ УСПЕХ')
        print('✅ Основной пайплайн работает')
        print('⚠️ Есть проблемы с качеством данных')
    else:
        print('❌ ТЕСТЫ ПРОВАЛЕНЫ')
        print('❌ Есть критические проблемы в пайплайне')
    
    print('\n🔗 Проверьте результаты в Google Sheets таблице!') 