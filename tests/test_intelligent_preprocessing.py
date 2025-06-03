#!/usr/bin/env python3
"""
Тестирование интеллектуального pre-processor для 100% анализа файлов
"""

import sys
from pathlib import Path
import time
import logging

# Добавляем модули в path
sys.path.insert(0, str(Path(__file__).parent))

# Настройка простого логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_intelligent_preprocessing():
    """Тестирует интеллектуальный pre-processor на реальных файлах"""
    
    print('🚀 ТЕСТИРОВАНИЕ ИНТЕЛЛЕКТУАЛЬНОГО PRE-PROCESSOR')
    print('=' * 80)
    print('🎯 Цель: Достижение 100% точности анализа файлов с пропусками')
    print()
    
    try:
        from modules.intelligent_preprocessor import IntelligentPreProcessor
        
        processor = IntelligentPreProcessor()
        
        # Тестируемые файлы
        test_files = [
            'LIST HARGA UD RAHAYU.xlsx',
            'DOC-20250428-WA0004..xlsx'
        ]
        
        all_results = []
        
        for file_path in test_files:
            if Path(file_path).exists():
                print(f'📊 ОБРАБАТЫВАЕМ: {file_path}')
                print('-' * 60)
                
                start_time = time.time()
                
                # Применяем интеллектуальную обработку
                result = processor.process_excel_intelligent(file_path)
                
                process_time = time.time() - start_time
                
                # Анализируем результаты
                analyze_processing_results(result, process_time)
                
                all_results.append(result)
                
                print()
            else:
                print(f'❌ Файл {file_path} не найден')
        
        # Сравнительный анализ
        if len(all_results) >= 2:
            compare_processing_results(all_results)
        
        return all_results
        
    except ImportError as e:
        print(f'❌ Ошибка импорта: {e}')
        return []
    except Exception as e:
        print(f'❌ Ошибка тестирования: {e}')
        return []

def analyze_processing_results(result: dict, process_time: float):
    """Анализирует результаты обработки"""
    
    if 'error' in result:
        print(f'❌ Ошибка обработки: {result["error"]}')
        return
    
    recovery_stats = result['recovery_stats']
    total_products = len(result['total_products'])
    total_prices = len(result['total_prices'])
    linked_pairs = len(result.get('product_price_pairs', []))
    
    print(f'⏱️  Время обработки: {process_time:.3f}s')
    print(f'🔧 Стратегия: {result.get("processing_strategy", "unknown")}')
    print(f'📋 Листов обработано: {len(result["sheets_processed"])}')
    
    print(f'\n📊 РЕЗУЛЬТАТЫ ИЗВЛЕЧЕНИЯ:')
    print(f'  📦 Товаров найдено: {total_products}')
    print(f'  💰 Цен найдено: {total_prices}')
    print(f'  🔗 Связанных пар: {linked_pairs}')
    
    print(f'\n🛠️  СТАТИСТИКА ВОССТАНОВЛЕНИЯ:')
    print(f'  ⭐ Заполнено пропусков: {recovery_stats["filled_gaps"]}')
    print(f'  💰 Восстановлено цен: {recovery_stats["recovered_prices"]}')
    print(f'  🔧 Исправлений структуры: {recovery_stats["structure_fixes"]}')
    print(f'  📈 Полнота данных: {recovery_stats["data_completeness"]:.1f}%')
    
    # Анализ качества по листам
    print(f'\n📋 АНАЛИЗ ПО ЛИСТАМ:')
    for sheet in result['sheets_processed']:
        print(f'  📄 {sheet["sheet_name"]}:')
        print(f'    • Стратегия: {sheet["strategy_used"]}')
        print(f'    • Размер: {sheet["original_dimensions"][0]}x{sheet["original_dimensions"][1]}')
        print(f'    • Товаров: {len(sheet["products"])}')
        print(f'    • Цен: {len(sheet["prices"])}')
    
    # Показываем примеры найденных товаров
    if result['total_products']:
        print(f'\n📦 ПРИМЕРЫ НАЙДЕННЫХ ТОВАРОВ:')
        for i, product in enumerate(result['total_products'][:8]):
            confidence_icon = "🟢" if product['confidence'] > 0.8 else "🟡" if product['confidence'] > 0.6 else "🔴"
            print(f'  {i+1:2d}. {confidence_icon} {product["name"][:40]:<40} (поз: {product["position"]}, ур: {product["confidence"]:.1f})')
    
    # Показываем примеры найденных цен
    if result['total_prices']:
        print(f'\n💰 ПРИМЕРЫ НАЙДЕННЫХ ЦЕН:')
        for i, price in enumerate(result['total_prices'][:8]):
            confidence_icon = "🟢" if price['confidence'] > 0.8 else "🟡" if price['confidence'] > 0.6 else "🔴"
            print(f'  {i+1:2d}. {confidence_icon} {price["value"]:>10,.0f} (поз: {price["position"]}, ур: {price["confidence"]:.1f})')
    
    # Показываем связанные пары
    if result.get('product_price_pairs'):
        print(f'\n🔗 ПРИМЕРЫ СВЯЗАННЫХ ПАР ТОВАР-ЦЕНА:')
        for i, pair in enumerate(result['product_price_pairs'][:5]):
            confidence_icon = "🟢" if pair['confidence'] > 0.8 else "🟡" if pair['confidence'] > 0.6 else "🔴"
            product_name = pair['product']['name'][:30]
            price_value = pair['price']['value']
            print(f'  {i+1}. {confidence_icon} {product_name:<30} → {price_value:>8,.0f} (ур: {pair["confidence"]:.1f})')
    
    # Оценка качества
    completeness = recovery_stats['data_completeness']
    if completeness >= 90:
        quality_status = "🎉 ОТЛИЧНОЕ"
        quality_icon = "✅"
    elif completeness >= 75:
        quality_status = "👍 ХОРОШЕЕ"
        quality_icon = "✅"
    elif completeness >= 50:
        quality_status = "⚠️ УДОВЛЕТВОРИТЕЛЬНОЕ"
        quality_icon = "⚠️"
    else:
        quality_status = "❌ ТРЕБУЕТ УЛУЧШЕНИЯ"
        quality_icon = "❌"
    
    print(f'\n{quality_icon} ИТОГОВАЯ ОЦЕНКА: {quality_status} ({completeness:.1f}%)')

def compare_processing_results(results: list):
    """Сравнивает результаты обработки разных файлов"""
    
    print('🔍 СРАВНИТЕЛЬНЫЙ АНАЛИЗ ОБРАБОТКИ')
    print('=' * 70)
    
    comparison_table = []
    
    for result in results:
        if 'error' not in result:
            file_name = Path(result['file_path']).name
            recovery_stats = result['recovery_stats']
            
            comparison_table.append({
                'file': file_name,
                'strategy': result.get('processing_strategy', 'unknown'),
                'products': len(result['total_products']),
                'prices': len(result['total_prices']),
                'pairs': len(result.get('product_price_pairs', [])),
                'completeness': recovery_stats['data_completeness'],
                'recovered': recovery_stats['recovered_prices'],
                'fixes': recovery_stats['structure_fixes']
            })
    
    # Заголовок таблицы
    print(f'{"Файл":<25} {"Стратегия":<20} {"Товары":<8} {"Цены":<8} {"Пары":<6} {"Полнота":<8} {"Восст.":<7} {"Испр.":<6}')
    print('-' * 90)
    
    # Строки таблицы
    for row in comparison_table:
        completeness_str = f"{row['completeness']:.1f}%"
        print(f'{row["file"]:<25} {row["strategy"]:<20} {row["products"]:<8} {row["prices"]:<8} {row["pairs"]:<6} {completeness_str:<8} {row["recovered"]:<7} {row["fixes"]:<6}')
    
    # Итоговая статистика
    if comparison_table:
        avg_completeness = sum(row['completeness'] for row in comparison_table) / len(comparison_table)
        total_products = sum(row['products'] for row in comparison_table)
        total_prices = sum(row['prices'] for row in comparison_table)
        total_recovered = sum(row['recovered'] for row in comparison_table)
        
        print('\n📊 ИТОГОВАЯ СТАТИСТИКА:')
        print(f'  📦 Всего товаров извлечено: {total_products}')
        print(f'  💰 Всего цен найдено: {total_prices}')
        print(f'  🛠️  Всего восстановлено: {total_recovered}')
        print(f'  📈 Средняя полнота: {avg_completeness:.1f}%')
        
        if avg_completeness >= 90:
            print(f'  🎉 РЕЗУЛЬТАТ: ПРЕВОСХОДНЫЙ - система достигла целевых 90%+ полноты!')
        elif avg_completeness >= 75:
            print(f'  ✅ РЕЗУЛЬТАТ: ХОРОШИЙ - высокое качество извлечения данных')
        else:
            print(f'  ⚠️ РЕЗУЛЬТАТ: ТРЕБУЕТ ДОРАБОТКИ - можно улучшить алгоритмы')

def demonstrate_improvement():
    """Демонстрирует улучшение по сравнению с базовой обработкой"""
    
    print('\n🔄 ДЕМОНСТРАЦИЯ УЛУЧШЕНИЙ')
    print('=' * 50)
    
    # Имитируем результаты базовой обработки (из предыдущих тестов)
    baseline_results = {
        'LIST HARGA UD RAHAYU.xlsx': {
            'products': 56,
            'prices': 63,
            'completeness': 97.8
        },
        'DOC-20250428-WA0004..xlsx': {
            'products': 10,
            'prices': 5,
            'completeness': 35.9
        }
    }
    
    print('📊 Сравнение с базовой обработкой:')
    print()
    
    # Запускаем тест интеллектуального процессора
    intelligent_results = test_intelligent_preprocessing()
    
    print('\n📈 ИТОГИ СРАВНЕНИЯ:')
    
    for result in intelligent_results:
        if 'error' not in result:
            file_name = Path(result['file_path']).name
            
            if file_name in baseline_results:
                baseline = baseline_results[file_name]
                
                new_products = len(result['total_products'])
                new_prices = len(result['total_prices'])
                new_completeness = result['recovery_stats']['data_completeness']
                
                products_improvement = ((new_products - baseline['products']) / baseline['products']) * 100
                prices_improvement = ((new_prices - baseline['prices']) / baseline['prices']) * 100
                completeness_improvement = new_completeness - baseline['completeness']
                
                print(f'\n📁 {file_name}:')
                print(f'  📦 Товары: {baseline["products"]} → {new_products} ({products_improvement:+.1f}%)')
                print(f'  💰 Цены: {baseline["prices"]} → {new_prices} ({prices_improvement:+.1f}%)')
                print(f'  📈 Полнота: {baseline["completeness"]:.1f}% → {new_completeness:.1f}% ({completeness_improvement:+.1f}%)')

if __name__ == "__main__":
    # Основной тест
    test_results = test_intelligent_preprocessing()
    
    # Демонстрация улучшений (закомментировано чтобы не дублировать вывод)
    # demonstrate_improvement() 