#!/usr/bin/env python3
"""
Бенчмарк для сравнения производительности оптимизированного парсера Excel
"""

import time
import pandas as pd
import logging
from pathlib import Path
from typing import Dict, Any
import sys
import os

# Добавляем модули
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules.universal_excel_parser import UniversalExcelParser

# Настройка логирования
logging.basicConfig(level=logging.WARNING)  # Минимум логов для чистых результатов
logger = logging.getLogger(__name__)

class ExcelParserBenchmark:
    """Бенчмарк для тестирования производительности парсера"""
    
    def __init__(self):
        self.parser = UniversalExcelParser()
        self.test_files = []
        self.results = []
    
    def find_test_files(self, test_dir: str = "data/temp") -> None:
        """Поиск тестовых Excel файлов"""
        test_path = Path(test_dir)
        if not test_path.exists():
            print(f"❌ Директория {test_dir} не найдена")
            return
        
        # Ищем Excel файлы
        patterns = ['*.xlsx', '*.xls']
        for pattern in patterns:
            self.test_files.extend(test_path.glob(pattern))
        
        print(f"📁 Найдено {len(self.test_files)} тестовых файлов")
        for file in self.test_files:
            print(f"   📄 {file.name} ({file.stat().st_size / 1024:.1f} KB)")
    
    def benchmark_file(self, file_path: Path) -> Dict[str, Any]:
        """Бенчмарк одного файла"""
        file_size_kb = file_path.stat().st_size / 1024
        
        print(f"\n🔍 Тестируем: {file_path.name} ({file_size_kb:.1f} KB)")
        
        # Замеряем время выполнения
        start_time = time.time()
        
        try:
            result = self.parser.extract_products_universal(str(file_path), max_products=1000)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Собираем статистику
            if 'error' in result:
                return {
                    'file': file_path.name,
                    'file_size_kb': file_size_kb,
                    'status': 'error',
                    'error': result['error'],
                    'processing_time': processing_time
                }
            
            stats = result.get('extraction_stats', {})
            products_count = len(result.get('products', []))
            
            benchmark_result = {
                'file': file_path.name,
                'file_size_kb': file_size_kb,
                'status': 'success',
                'processing_time': processing_time,
                'products_extracted': products_count,
                'total_rows': stats.get('total_rows', 0),
                'success_rate': stats.get('success_rate', 0),
                'used_sheet': stats.get('used_sheet', ''),
                'detected_structure': stats.get('detected_structure', ''),
                'kb_per_second': file_size_kb / processing_time if processing_time > 0 else 0,
                'rows_per_second': stats.get('total_rows', 0) / processing_time if processing_time > 0 else 0
            }
            
            print(f"✅ Обработано за {processing_time:.2f}с")
            print(f"   📊 Извлечено {products_count} товаров из {stats.get('total_rows', 0)} строк")
            print(f"   ⚡ Скорость: {benchmark_result['kb_per_second']:.1f} KB/с, {benchmark_result['rows_per_second']:.1f} строк/с")
            
            return benchmark_result
            
        except Exception as e:
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"❌ Ошибка: {e}")
            
            return {
                'file': file_path.name,
                'file_size_kb': file_size_kb,
                'status': 'exception',
                'error': str(e),
                'processing_time': processing_time
            }
    
    def run_benchmark(self) -> None:
        """Запуск полного бенчмарка"""
        print("🚀 ЗАПУСК БЕНЧМАРКА EXCEL ПАРСЕРА")
        print("=" * 50)
        
        if not self.test_files:
            print("❌ Нет файлов для тестирования")
            return
        
        # Тестируем каждый файл
        for file_path in self.test_files:
            result = self.benchmark_file(file_path)
            self.results.append(result)
        
        # Анализируем результаты
        self.analyze_results()
    
    def analyze_results(self) -> None:
        """Анализ результатов бенчмарка"""
        print("\n📊 РЕЗУЛЬТАТЫ БЕНЧМАРКА")
        print("=" * 50)
        
        if not self.results:
            print("❌ Нет результатов для анализа")
            return
        
        # Успешные обработки
        successful = [r for r in self.results if r['status'] == 'success']
        failed = [r for r in self.results if r['status'] != 'success']
        
        print(f"✅ Успешно обработано: {len(successful)}/{len(self.results)}")
        print(f"❌ Ошибки: {len(failed)}")
        
        if successful:
            # Статистика по времени
            times = [r['processing_time'] for r in successful]
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            print(f"\n⏱️ ВРЕМЯ ОБРАБОТКИ:")
            print(f"   Среднее: {avg_time:.2f}с")
            print(f"   Минимум: {min_time:.2f}с")
            print(f"   Максимум: {max_time:.2f}с")
            
            # Статистика по скорости
            speeds_kb = [r['kb_per_second'] for r in successful if r['kb_per_second'] > 0]
            speeds_rows = [r['rows_per_second'] for r in successful if r['rows_per_second'] > 0]
            
            if speeds_kb:
                avg_speed_kb = sum(speeds_kb) / len(speeds_kb)
                print(f"\n⚡ СКОРОСТЬ ОБРАБОТКИ:")
                print(f"   Среднее: {avg_speed_kb:.1f} KB/с")
                print(f"   Максимум: {max(speeds_kb):.1f} KB/с")
            
            if speeds_rows:
                avg_speed_rows = sum(speeds_rows) / len(speeds_rows)
                print(f"   Среднее: {avg_speed_rows:.1f} строк/с")
                print(f"   Максимум: {max(speeds_rows):.1f} строк/с")
            
            # Статистика по извлечению
            products = [r['products_extracted'] for r in successful]
            total_products = sum(products)
            avg_products = total_products / len(successful) if successful else 0
            
            print(f"\n📈 ИЗВЛЕЧЕНИЕ ДАННЫХ:")
            print(f"   Всего товаров: {total_products}")
            print(f"   Среднее на файл: {avg_products:.1f}")
            print(f"   Максимум: {max(products) if products else 0}")
        
        # Детальная таблица
        print(f"\n📋 ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
        print("-" * 100)
        print(f"{'Файл':<25} {'Размер':<10} {'Время':<8} {'Товары':<8} {'Скорость':<12} {'Статус'}")
        print("-" * 100)
        
        for r in self.results:
            status_icon = "✅" if r['status'] == 'success' else "❌"
            speed_str = f"{r.get('kb_per_second', 0):.1f} KB/с" if r['status'] == 'success' else "-"
            
            print(f"{r['file']:<25} {r['file_size_kb']:<9.1f} {r['processing_time']:<7.2f} "
                  f"{r.get('products_extracted', 0):<8} {speed_str:<12} {status_icon}")
        
        print("-" * 100)
        
        # Сохраняем результаты
        self.save_results()
    
    def save_results(self) -> None:
        """Сохранение результатов в файл"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_file = f"benchmark_results_{timestamp}.json"
        
        import json
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Результаты сохранены в {results_file}")

def main():
    """Главная функция"""
    benchmark = ExcelParserBenchmark()
    
    # Поиск тестовых файлов
    benchmark.find_test_files()
    
    if not benchmark.test_files:
        print("❌ Нет файлов для тестирования в директории data/temp/")
        print("💡 Поместите Excel файлы в data/temp/ для тестирования")
        return
    
    # Запуск бенчмарка
    benchmark.run_benchmark()

if __name__ == "__main__":
    main()