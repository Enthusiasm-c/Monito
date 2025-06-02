#!/usr/bin/env python3
"""
PDF парсер с использованием Camelot для извлечения таблиц из прайс-листов
Исправлена архитектура - убраны дублирования функций
"""

import pandas as pd
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import tempfile
import os
from .base_parser import BaseParser

logger = logging.getLogger(__name__)

class PDFParser(BaseParser):
    """Парсер PDF файлов для извлечения прайс-листов с использованием Camelot"""
    
    def __init__(self):
        # Инициализируем базовый класс с общими паттернами и функциями
        super().__init__()
        
        # Пытаемся импортировать camelot
        try:
            import camelot
            self.camelot = camelot
            self.camelot_available = True
            logger.info("✅ Camelot успешно загружен")
        except ImportError as e:
            logger.warning(f"⚠️ Camelot не установлен: {e}")
            self.camelot = None
            self.camelot_available = False
            
        # Пытаемся импортировать fallback библиотеки
        try:
            import tabula
            self.tabula = tabula
            self.tabula_available = True
            logger.info("✅ Tabula доступна как fallback")
        except ImportError:
            self.tabula = None
            self.tabula_available = False
            
        try:
            import pdfplumber
            self.pdfplumber = pdfplumber
            self.pdfplumber_available = True
            logger.info("✅ PDFplumber доступен как fallback")
        except ImportError:
            self.pdfplumber = None
            self.pdfplumber_available = False
    
    def extract_products_from_pdf(self, file_path: str, max_products: int = 1000, use_ai: bool = True) -> Dict[str, Any]:
        """Основная функция извлечения товаров из PDF с AI поддержкой"""
        try:
            logger.info(f"🔍 Начинаем анализ PDF файла: {file_path}")
            
            # Проверяем существование файла
            if not os.path.exists(file_path):
                return {'error': f'Файл не найден: {file_path}'}
            
            # Пытаемся извлечь таблицы разными методами
            tables_data = self._extract_tables_multi_method(file_path)
            
            if not tables_data:
                return {'error': 'Не удалось извлечь таблицы из PDF'}
            
            # Находим лучшую таблицу для обработки
            best_table = self._select_best_table(tables_data)
            
            if best_table is None:
                return {'error': 'Не найдено подходящих таблиц с товарами'}
            
            # Конвертируем в DataFrame и анализируем
            df = self._table_to_dataframe(best_table)
            
            if df.empty:
                return {'error': 'Не удалось преобразовать таблицу в DataFrame'}
            
            # НОВЫЙ AI-ПОДХОД: сначала пробуем AI анализ
            if use_ai:
                ai_result = self._try_ai_extraction(df, file_path)
                if ai_result and not ai_result.get('error'):
                    # AI успешно обработал - используем его результат
                    ai_result['extraction_stats']['used_method'] = best_table.get('extraction_method', 'camelot')
                    ai_result['extraction_stats']['ai_enhanced'] = True
                    logger.info(f"🤖 AI успешно извлек данные из PDF")
                    return ai_result
                else:
                    logger.warning(f"⚠️ AI не смог обработать таблицу, используем классический парсер")
            
            # FALLBACK: классический ручной парсинг
            from .universal_excel_parser import UniversalExcelParser
            excel_parser = UniversalExcelParser()
            
            # Анализируем структуру данных
            structure = excel_parser._analyze_data_structure(df)
            
            # Извлекаем товары
            products = excel_parser._extract_products_by_structure(df, structure, max_products)
            
            # Формируем результат
            supplier_name = Path(file_path).stem
            
            result = {
                'file_type': 'pdf',
                'supplier': {'name': supplier_name},
                'products': products,
                'extraction_stats': {
                    'total_rows': len(df),
                    'extracted_products': len(products),
                    'success_rate': len(products) / len(df) if len(df) > 0 else 0,
                    'used_method': best_table.get('extraction_method', 'camelot'),
                    'detected_structure': structure['type'],
                    'extraction_method': 'manual_parser',
                    'ai_enhanced': False
                }
            }
            
            logger.info(f"✅ Извлечено {len(products)} товаров из {len(df)} строк PDF (ручной парсер)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга PDF: {e}")
            return {'error': f'Ошибка обработки PDF файла: {str(e)}'}
    
    def _extract_tables_multi_method(self, file_path: str) -> List[Dict]:
        """Извлечение таблиц несколькими методами"""
        all_tables = []
        
        # Метод 1: Camelot (самый точный для таблиц)
        if self.camelot_available:
            try:
                camelot_tables = self._extract_with_camelot(file_path)
                all_tables.extend(camelot_tables)
                logger.info(f"📊 Camelot извлек {len(camelot_tables)} таблиц")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка Camelot: {e}")
        
        # Метод 2: Tabula (fallback)
        if self.tabula_available and len(all_tables) == 0:
            try:
                tabula_tables = self._extract_with_tabula(file_path)
                all_tables.extend(tabula_tables)
                logger.info(f"📊 Tabula извлекла {len(tabula_tables)} таблиц")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка Tabula: {e}")
        
        # Метод 3: PDFplumber (последний fallback)
        if self.pdfplumber_available and len(all_tables) == 0:
            try:
                pdfplumber_tables = self._extract_with_pdfplumber(file_path)
                all_tables.extend(pdfplumber_tables)
                logger.info(f"📊 PDFplumber извлек {len(pdfplumber_tables)} таблиц")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка PDFplumber: {e}")
        
        return all_tables
    
    def _extract_with_camelot(self, file_path: str) -> List[Dict]:
        """Извлечение таблиц с помощью Camelot"""
        tables_data = []
        
        try:
            # Пробуем разные методы Camelot
            methods = ['lattice', 'stream']
            
            for method in methods:
                try:
                    tables = self.camelot.read_pdf(file_path, flavor=method, pages='all')
                    
                    for i, table in enumerate(tables):
                        if not table.df.empty:
                            # Оценка качества таблицы
                            accuracy = getattr(table, 'accuracy', 0)
                            
                            tables_data.append({
                                'data': table.df,
                                'extraction_method': f'camelot_{method}',
                                'page': getattr(table, 'page', 1),
                                'accuracy': accuracy,
                                'quality_score': self._calculate_table_quality(table.df)
                            })
                            
                            logger.debug(f"Camelot {method}: таблица {i+1}, точность: {accuracy:.2f}")
                    
                    if tables_data:
                        break  # Если нашли таблицы, не пробуем другой метод
                        
                except Exception as e:
                    logger.debug(f"Ошибка Camelot {method}: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Общая ошибка Camelot: {e}")
        
        return tables_data
    
    def _extract_with_tabula(self, file_path: str) -> List[Dict]:
        """Извлечение таблиц с помощью Tabula"""
        tables_data = []
        
        try:
            # Tabula извлекает все таблицы
            dfs = self.tabula.read_pdf(file_path, pages='all', multiple_tables=True)
            
            for i, df in enumerate(dfs):
                if not df.empty:
                    tables_data.append({
                        'data': df,
                        'extraction_method': 'tabula',
                        'page': i + 1,
                        'accuracy': 0.8,  # Примерная оценка
                        'quality_score': self._calculate_table_quality(df)
                    })
                    
        except Exception as e:
            logger.warning(f"Ошибка Tabula: {e}")
        
        return tables_data
    
    def _extract_with_pdfplumber(self, file_path: str) -> List[Dict]:
        """Извлечение таблиц с помощью PDFplumber"""
        tables_data = []
        
        try:
            with self.pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    
                    for table in tables:
                        if table and len(table) > 1:
                            # Конвертируем в DataFrame
                            df = pd.DataFrame(table[1:], columns=table[0])
                            
                            if not df.empty:
                                tables_data.append({
                                    'data': df,
                                    'extraction_method': 'pdfplumber',
                                    'page': page_num + 1,
                                    'accuracy': 0.7,  # Примерная оценка
                                    'quality_score': self._calculate_table_quality(df)
                                })
                                
        except Exception as e:
            logger.warning(f"Ошибка PDFplumber: {e}")
        
        return tables_data
    
    def _calculate_table_quality(self, df: pd.DataFrame) -> float:
        """Расчет качества таблицы для выбора лучшей"""
        if df.empty:
            return 0
        
        score = 0
        total_cells = df.size
        filled_cells = df.count().sum()
        
        # Процент заполненности
        fill_ratio = filled_cells / total_cells if total_cells > 0 else 0
        score += fill_ratio * 0.3
        
        # Количество потенциальных товаров и цен
        product_count = 0
        price_count = 0
        
        for _, row in df.head(10).iterrows():  # Анализируем только первые 10 строк
            for value in row:
                if pd.notna(value):
                    value_str = str(value).strip()
                    
                    # Используем методы из базового класса
                    if self._looks_like_product(value_str):
                        product_count += 1
                    elif self._looks_like_price(value_str):
                        price_count += 1
        
        # Нормализуем по количеству ячеек
        sample_size = min(df.size, 10 * len(df.columns))
        if sample_size > 0:
            score += (product_count / sample_size) * 0.4
            score += (price_count / sample_size) * 0.3
        
        return min(score, 1.0)
    
    def _select_best_table(self, tables_data: List[Dict]) -> Optional[Dict]:
        """Выбор лучшей таблицы для обработки"""
        if not tables_data:
            return None
        
        # Сортируем по качеству
        sorted_tables = sorted(tables_data, key=lambda x: x['quality_score'], reverse=True)
        
        # Возвращаем лучшую таблицу
        best_table = sorted_tables[0]
        logger.info(f"📊 Выбрана таблица: метод={best_table['extraction_method']}, "
                   f"качество={best_table['quality_score']:.3f}")
        
        return best_table
    
    def _table_to_dataframe(self, table_info: Dict) -> pd.DataFrame:
        """Конвертация таблицы в DataFrame с очисткой"""
        df = table_info['data'].copy()
        
        # Очистка данных
        df = df.dropna(how='all')  # Удаляем полностью пустые строки
        df = df.dropna(axis=1, how='all')  # Удаляем полностью пустые столбцы
        
        # Сброс индексов
        df = df.reset_index(drop=True)
        
        # Очистка заголовков
        df.columns = [f'col_{i}' if pd.isna(col) or str(col).strip() == '' 
                     else str(col).strip() for i, col in enumerate(df.columns)]
        
        return df
    
    def _try_ai_extraction(self, df: pd.DataFrame, file_path: str) -> Optional[Dict]:
        """Попытка извлечения данных через AI"""
        try:
            # Импортируем AI парсер
            from .ai_table_parser import AITableParser
            
            # Проверяем наличие API ключа
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.debug("OpenAI API key не найден, пропускаем AI анализ")
                return None
            
            # Создаем AI парсер
            ai_parser = AITableParser(api_key)
            
            # Формируем контекст
            context = f"PDF прайс-лист из файла {Path(file_path).name}"
            
            # Анализируем через AI
            result = ai_parser.extract_products_with_ai(df, context)
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка AI извлечения: {e}")
            return None
    
    def get_supported_formats(self) -> List[str]:
        """Возвращает список поддерживаемых форматов"""
        formats = []
        
        if self.camelot_available or self.tabula_available or self.pdfplumber_available:
            formats.append('pdf')
            
        return formats
    
    def is_available(self) -> bool:
        """Проверка доступности PDF парсера"""
        return (self.camelot_available or 
                self.tabula_available or 
                self.pdfplumber_available) 