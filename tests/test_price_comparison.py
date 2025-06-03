#!/usr/bin/env python3
"""
Тест создания сводного прайс-листа с сравнением цен
"""

import sys
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Добавляем модули в path
sys.path.insert(0, str(Path(__file__).parent))

def test_price_comparison():
    """Тестирует создание сводного прайс-листа"""
    
    print('🔍 ТЕСТИРОВАНИЕ СВОДНОГО ПРАЙС-ЛИСТА')
    print('=' * 80)
    
    try:
        # Подключаемся к Google Sheets
        print('📊 Подключение к Google Sheets...')
        from modules.google_sheets_manager import GoogleSheetsManager
        
        sheets = GoogleSheetsManager()
        if not sheets.is_connected():
            print('❌ Нет подключения к Google Sheets')
            return False
        
        print('✅ Подключение установлено')
        
        # Создаем сводный прайс-лист
        print('\n🔄 Создание сводного прайс-листа...')
        result = sheets.create_unified_price_comparison()
        
        if 'error' in result:
            print(f'❌ Ошибка: {result["error"]}')
            return False
        
        # Выводим статистику
        stats = result.get('stats', {})
        print('\n✅ СВОДНЫЙ ПРАЙС-ЛИСТ СОЗДАН УСПЕШНО!')
        print(f'📦 Товаров с ценами: {stats.get("products_with_prices", 0)}')
        print(f'🏪 Поставщиков: {stats.get("suppliers_count", 0)}')
        print(f'📈 Средний разброс цен: {stats.get("average_price_difference", 0):.1f}%')
        print(f'📋 Лист создан: {result.get("worksheet_name", "N/A")}')
        print(f'🔗 Ссылка: {result.get("sheet_url", "N/A")}')
        
        # Получаем краткую сводку
        print('\n📋 Получение краткой сводки...')
        summary = sheets.get_price_comparison_summary()
        
        if 'error' in summary:
            print(f'⚠️ Предупреждение при получении сводки: {summary["error"]}')
        else:
            print(f'📊 Общая статистика:')
            print(f'   • Всего товаров: {summary.get("total_products", 0)}')
            print(f'   • Поставщиков: {summary.get("suppliers_count", 0)}')
            print(f'   • Категорий: {summary.get("categories", 0)}')
            
            categories = summary.get('categories_breakdown', {})
            if categories:
                print(f'📂 По категориям:')
                for cat, info in categories.items():
                    print(f'   • {cat}: {info["count"]} товаров')
            
            suppliers = summary.get('suppliers', [])
            if suppliers:
                print(f'🏪 Поставщики: {", ".join(suppliers)}')
        
        print('\n🎯 ЧТО ДАЕТ СВОДНАЯ ТАБЛИЦА:')
        print('• Сравнение цен между всеми поставщиками')
        print('• Выделение лучших цен для каждого товара')
        print('• Расчет процента экономии')
        print('• Средние цены по товарам')
        print('• Информация о количестве поставщиков товара')
        print('• Даты обновления цен')
        
        print('\n💡 ПРЕИМУЩЕСТВА:')
        print('• Быстрое сравнение цен')
        print('• Выявление самых выгодных предложений')
        print('• Оптимизация закупок')
        print('• Анализ конкурентоспособности поставщиков')
        
        return True
        
    except Exception as e:
        logger.error(f'❌ Ошибка тестирования: {e}', exc_info=True)
        return False

def main():
    """Главная функция"""
    print('🚀 НАЧАЛО ТЕСТИРОВАНИЯ СВОДНОГО ПРАЙС-ЛИСТА')
    print()
    
    success = test_price_comparison()
    
    print('\n' + '=' * 80)
    if success:
        print('✅ ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!')
        print('🎯 Сводный прайс-лист готов к использованию')
        print('💡 Используйте команду /compare_prices в боте')
    else:
        print('❌ ТЕСТЫ ПРОВАЛЕНЫ')
        print('🔧 Проверьте подключение и данные')
    
    print('=' * 80)

if __name__ == '__main__':
    main() 