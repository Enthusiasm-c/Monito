#!/usr/bin/env python3
"""
Universal Excel Parser V2 - с интеграцией MON-002 Pre-Processor
Основные улучшения:
- Использует PreProcessor для ускоренного чтения (3x быстрее)
- Автоматическая нормализация данных
- Сохраняет совместимость с существующим API
"""

import pandas as pd
import re
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from .base_parser import BaseParser
from .pre_processor import PreProcessor, ProcessingStats

logger = logging.getLogger(__name__)

class UniversalExcelParserV2(BaseParser):
    """
    Универсальный парсер Excel V2 с интеграцией MON-002 Pre-Processor
    
    Ключевые улучшения:
    - ⚡ 3x быстрее чтение через calamine
    - 🔧 Автоматическая нормализация данных
    - 🧮 Вычисление формул
    - 📊 Детальная статистика обработки
    """
    
    def __init__(self):
        # Инициализируем базовый класс
        super().__init__()
        
        # Интегрируем PreProcessor для MON-002
        self.preprocessor = PreProcessor()
        
        # Статистика для отчетов
        self.processing_stats = None
        
        logger.info("✅ UniversalExcelParserV2 инициализирован с PreProcessor")
    
    def extract_products_universal(self, file_path: str, max_products: int = 1000, use_ai: bool = True) -> Dict[str, Any]:
        """
        Универсальное извлечение товаров с использованием MON-002 оптимизаций
        
        Args:
            file_path: Путь к Excel файлу
            max_products: Максимальное количество товаров
            use_ai: Использовать ИИ анализ
        
        Returns:
            Dict с извлеченными товарами и статистикой
        """
        try:
            logger.info(f"🚀 UniversalExcelParserV2: Начинаем обработку {Path(file_path).name}")
            
            # Шаг 1: Быстрая предобработка через MON-002
            df, preprocessing_stats = self.preprocessor.process_excel_file(file_path)
            self.processing_stats = preprocessing_stats
            
            logger.info(f"✅ MON-002 предобработка завершена за {preprocessing_stats.total_time_ms}ms:")
            logger.info(f"   📖 Чтение: {preprocessing_stats.read_time_ms}ms")
            logger.info(f"   🔢 Нормализация: {preprocessing_stats.cells_normalized} ячеек")
            
            if df.empty:
                logger.warning("⚠️ Файл пуст или не удалось прочитать")
                return self._create_empty_result(file_path, "Файл пуст")
            
            # Шаг 2: Анализ всех листов (если не указан конкретный)
            sheets_analysis = self._analyze_all_sheets_from_df(df, file_path)
            
            # Шаг 3: Выбор лучшего листа
            best_sheet = self._select_best_sheet(sheets_analysis)
            if not best_sheet:
                logger.warning("⚠️ Не найдено подходящих листов с данными")
                return self._create_empty_result(file_path, "Нет подходящих данных")
            
            # Шаг 4: Извлечение товаров из лучшего листа
            products = self._extract_products_from_sheet(df, best_sheet, max_products)
            
            # Шаг 5: AI анализ (если включен)
            if use_ai and products:
                ai_result = self._try_ai_extraction_v2(df, file_path)
                if ai_result and ai_result.get('products'):
                    logger.info("🤖 AI анализ успешен, используем AI результат")
                    products = ai_result['products'][:max_products]
            
            result = {
                'success': True,
                'products': products,
                'total_products': len(products),
                'file_info': {
                    'name': Path(file_path).name,
                    'size_mb': round(os.path.getsize(file_path) / 1024 / 1024, 2),
                    'rows': len(df),
                    'columns': len(df.columns)
                },
                'processing_stats': {
                    'preprocessing_time_ms': preprocessing_stats.total_time_ms,
                    'read_time_ms': preprocessing_stats.read_time_ms,
                    'cells_normalized': preprocessing_stats.cells_normalized,
                    'formulas_evaluated': preprocessing_stats.formulas_evaluated,
                    'method': 'UniversalExcelParserV2_with_MON002'
                },
                'extraction_method': 'smart_analysis',
                'confidence': 0.9 if products else 0.0
            }
            
            logger.info(f"✅ Извлечение завершено: {len(products)} товаров за {preprocessing_stats.total_time_ms}ms")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения товаров: {e}")
            return self._create_empty_result(file_path, str(e))
    
    def _analyze_all_sheets_from_df(self, df: pd.DataFrame, file_path: str) -> List[Dict]:
        """Анализ данных из предобработанного DataFrame"""
        try:
            # Поскольку у нас уже есть обработанный DataFrame, анализируем его
            sheet_analysis = {
                'name': 'processed_sheet',
                'df': df,
                'data_quality': self._calculate_data_quality(df),
                'product_columns': self._find_product_columns(df),
                'price_columns': self._find_price_columns(df),
                'row_count': len(df),
                'col_count': len(df.columns)
            }
            
            return [sheet_analysis]
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа листов: {e}")
            return []
    
    def _calculate_data_quality(self, df: pd.DataFrame) -> float:
        """Расчет качества данных в листе"""
        if df.empty:
            return 0.0
        
        try:
            # Подсчет непустых ячеек
            total_cells = len(df) * len(df.columns)
            non_empty_cells = df.count().sum()
            
            # Подсчет ячеек, похожих на товары
            product_like_cells = 0
            price_like_cells = 0
            
            for col in df.columns:
                for value in df[col].dropna():
                    if isinstance(value, str):
                        if self._looks_like_product(value):
                            product_like_cells += 1
                        elif self._looks_like_price(str(value)):
                            price_like_cells += 1
            
            # Итоговое качество
            fill_ratio = non_empty_cells / total_cells if total_cells > 0 else 0
            product_ratio = product_like_cells / max(non_empty_cells, 1)
            price_ratio = price_like_cells / max(non_empty_cells, 1)
            
            quality = (fill_ratio * 0.3 + product_ratio * 0.4 + price_ratio * 0.3)
            
            logger.debug(f"📊 Качество данных: {quality:.3f} "
                        f"(заполнено: {fill_ratio:.2f}, товары: {product_ratio:.2f}, цены: {price_ratio:.2f})")
            
            return min(quality, 1.0)
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета качества: {e}")
            return 0.0
    
    def _find_product_columns(self, df: pd.DataFrame) -> List[str]:
        """Поиск столбцов с товарами"""
        product_columns = []
        
        try:
            for col in df.columns:
                product_count = 0
                sample_size = min(len(df), 20)  # Анализируем первые 20 строк
                
                for value in df[col].head(sample_size).dropna():
                    if isinstance(value, str) and self._looks_like_product(value):
                        product_count += 1
                
                # Если больше 30% строк похожи на товары
                if product_count / max(sample_size, 1) > 0.3:
                    product_columns.append(col)
                    logger.debug(f"📦 Найден столбец товаров: {col} ({product_count}/{sample_size})")
            
            return product_columns
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска столбцов товаров: {e}")
            return []
    
    def _find_price_columns(self, df: pd.DataFrame) -> List[str]:
        """Поиск столбцов с ценами"""
        price_columns = []
        
        try:
            for col in df.columns:
                price_count = 0
                sample_size = min(len(df), 20)
                
                for value in df[col].head(sample_size).dropna():
                    if self._looks_like_price(str(value)):
                        price_count += 1
                
                # Если больше 40% строк похожи на цены
                if price_count / max(sample_size, 1) > 0.4:
                    price_columns.append(col)
                    logger.debug(f"💰 Найден столбец цен: {col} ({price_count}/{sample_size})")
            
            return price_columns
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска столбцов цен: {e}")
            return []
    
    def _select_best_sheet(self, sheets_analysis: List[Dict]) -> Optional[Dict]:
        """Выбор лучшего листа для обработки"""
        if not sheets_analysis:
            return None
        
        try:
            # Сортируем по качеству данных
            sorted_sheets = sorted(sheets_analysis, key=lambda x: x['data_quality'], reverse=True)
            
            best_sheet = sorted_sheets[0]
            logger.info(f"📊 Выбран лист: {best_sheet['name']} "
                       f"(качество: {best_sheet['data_quality']:.3f})")
            
            return best_sheet
            
        except Exception as e:
            logger.error(f"❌ Ошибка выбора листа: {e}")
            return None
    
    def _extract_products_from_sheet(self, df: pd.DataFrame, sheet_info: Dict, max_products: int) -> List[Dict]:
        """Извлечение товаров из листа"""
        products = []
        
        try:
            product_cols = sheet_info.get('product_columns', [])
            price_cols = sheet_info.get('price_columns', [])
            
            logger.info(f"📦 Столбцы товаров: {product_cols}")
            logger.info(f"💰 Столбцы цен: {price_cols}")
            
            # Если не найдены автоматически, используем эвристику
            if not product_cols:
                product_cols = [df.columns[0]] if len(df.columns) > 0 else []
            if not price_cols:
                # Ищем столбцы с числами
                for col in df.columns:
                    if df[col].dtype in ['int64', 'float64'] or 'price' in str(col).lower():
                        price_cols.append(col)
                        break
            
            # Извлекаем товары построчно
            for idx, row in df.iterrows():
                if len(products) >= max_products:
                    break
                
                product = self._extract_product_from_row(row, product_cols, price_cols)
                if product:
                    products.append(product)
            
            logger.info(f"✅ Извлечено {len(products)} товаров из {len(df)} строк")
            return products
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения товаров: {e}")
            return []
    
    def _extract_product_from_row(self, row: pd.Series, product_cols: List[str], price_cols: List[str]) -> Optional[Dict]:
        """Извлечение одного товара из строки"""
        try:
            # Извлекаем название товара
            product_name = None
            for col in product_cols:
                if col in row and pd.notna(row[col]):
                    value = str(row[col]).strip()
                    if value and self._looks_like_product(value):
                        product_name = self._clean_product_name(value)
                        break
            
            if not product_name:
                return None
            
            # Извлекаем цену
            price = 0.0
            for col in price_cols:
                if col in row and pd.notna(row[col]):
                    price_value = self._clean_price(str(row[col]))
                    if price_value > 0:
                        price = price_value
                        break
            
            # Извлекаем единицу измерения
            unit = 'pcs'
            for value in row:
                if pd.notna(value) and self._looks_like_unit(str(value)):
                    unit = str(value).strip().lower()
                    break
            
            return {
                'original_name': product_name,
                'standardized_name': product_name,  # Будет стандартизировано позже
                'price': price,
                'unit': unit,
                'brand': 'unknown',
                'size': 'unknown',
                'category': 'general',
                'confidence': 0.8
            }
            
        except Exception as e:
            logger.debug(f"⚠️ Ошибка извлечения товара из строки: {e}")
            return None
    
    def _try_ai_extraction_v2(self, df: pd.DataFrame, file_path: str) -> Optional[Dict]:
        """Попытка AI извлечения с учетом предобработки"""
        try:
            # Импортируем AI парсер
            from .ai_table_parser import AITableParser
            
            # Создаем временный файл с предобработанными данными
            temp_file = f"{file_path}_preprocessed.xlsx"
            df.to_excel(temp_file, index=False, engine='openpyxl')
            
            try:
                # Используем AI парсер
                openai_key = os.getenv('OPENAI_API_KEY')
                if not openai_key:
                    logger.info("🤖 OpenAI API ключ не найден, пропускаем AI анализ")
                    return None
                
                ai_parser = AITableParser(openai_key)
                ai_result = ai_parser.extract_products_with_ai(df, context=f"Файл: {Path(file_path).name}")
                
                return ai_result
                
            finally:
                # Удаляем временный файл
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            
        except Exception as e:
            logger.warning(f"⚠️ AI анализ не удался: {e}")
            return None
    
    def _create_empty_result(self, file_path: str, error_message: str) -> Dict[str, Any]:
        """Создание пустого результата при ошибке"""
        return {
            'success': False,
            'products': [],
            'total_products': 0,
            'error': error_message,
            'file_info': {
                'name': Path(file_path).name,
                'size_mb': round(os.path.getsize(file_path) / 1024 / 1024, 2) if os.path.exists(file_path) else 0
            },
            'processing_stats': {
                'preprocessing_time_ms': self.processing_stats.total_time_ms if self.processing_stats else 0,
                'method': 'UniversalExcelParserV2_error'
            },
            'extraction_method': 'error',
            'confidence': 0.0
        }
    
    def get_processing_report(self) -> Dict[str, Any]:
        """Получение отчета о обработке с учетом MON-002 статистики"""
        if not self.processing_stats:
            return {}
        
        return {
            'preprocessing': {
                'total_time_ms': self.processing_stats.total_time_ms,
                'read_time_ms': self.processing_stats.read_time_ms,
                'unmerge_time_ms': self.processing_stats.unmerge_time_ms,
                'formula_eval_time_ms': self.processing_stats.formula_eval_time_ms,
                'normalize_time_ms': self.processing_stats.normalize_time_ms,
                'rows_processed': self.processing_stats.rows_processed,
                'cells_normalized': self.processing_stats.cells_normalized,
                'formulas_evaluated': self.processing_stats.formulas_evaluated
            },
            'performance_metrics': {
                'read_speed_acceptable': self.processing_stats.read_time_ms <= 700,
                'processing_efficient': self.processing_stats.total_time_ms <= 5000,
                'normalization_active': self.processing_stats.cells_normalized > 0
            },
            'version': 'UniversalExcelParserV2_with_MON002'
        }


# Backward compatibility
class UniversalExcelParser(UniversalExcelParserV2):
    """
    Обратная совместимость со старым API
    Перенаправляет на новую версию с MON-002 оптимизациями
    """
    
    def __init__(self):
        super().__init__()
        logger.info("🔄 Используется UniversalExcelParser V2 с MON-002 оптимизациями") 