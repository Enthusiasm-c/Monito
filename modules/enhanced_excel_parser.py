#!/usr/bin/env python3
"""
Улучшенный парсер Excel на основе анализа реальных прайс-листов
"""

import pandas as pd
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class EnhancedExcelParser:
    """Улучшенный парсер Excel для индонезийских прайс-листов"""
    
    def __init__(self):
        self.product_keywords = ['item', 'product', 'name', 'товар', 'название', 'наименование']
        self.price_keywords = ['price', 'harga', 'цена', 'стоимость']
        self.unit_keywords = ['unit', 'qnt', 'quantity', 'единица', 'ед']
        
    def analyze_file_structure(self, file_path: str) -> Dict[str, Any]:
        """Анализ структуры Excel файла"""
        try:
            xls = pd.ExcelFile(file_path)
            sheets_info = {}
            
            for sheet_name in xls.sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=20)
                    
                    if df.empty:
                        continue
                    
                    # Анализ листа
                    analysis = self._analyze_sheet_structure(df)
                    analysis['name'] = sheet_name
                    sheets_info[sheet_name] = analysis
                    
                except Exception as e:
                    logger.warning(f"Ошибка анализа листа {sheet_name}: {e}")
                    continue
            
            # Выбор лучшего листа
            best_sheet = self._select_best_sheet(sheets_info)
            
            return {
                'sheets': sheets_info,
                'recommended_sheet': best_sheet,
                'file_path': file_path
            }
            
        except Exception as e:
            return {'error': f'Ошибка анализа файла: {str(e)}'}
    
    def _analyze_sheet_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Анализ структуры отдельного листа"""
        # Определяем тип структуры
        columns = list(df.columns)
        
        # Проверяем на двухколоночную структуру (как в UD RAHAYU)
        duplicated_columns = self._find_duplicated_columns(columns)
        
        # Ищем потенциальные столбцы с товарами и ценами
        product_columns = self._find_potential_product_columns(df)
        price_columns = self._find_potential_price_columns(df)
        
        # Определяем где начинаются данные
        data_start_row = self._find_data_start_row(df)
        
        return {
            'columns': columns,
            'duplicated_structure': len(duplicated_columns) > 0,
            'duplicated_columns': duplicated_columns,
            'product_columns': product_columns,
            'price_columns': price_columns,
            'data_start_row': data_start_row,
            'potential_products': len(product_columns),
            'rows': len(df)
        }
    
    def _find_duplicated_columns(self, columns: List[str]) -> Dict[str, List[str]]:
        """Поиск дублированных столбцов (например ITEm и ITEm.1)"""
        duplicated = {}
        
        for col in columns:
            # Убираем суффиксы .1, .2 и т.д.
            base_name = re.sub(r'\.\d+$', '', str(col))
            
            if base_name not in duplicated:
                duplicated[base_name] = []
            duplicated[base_name].append(col)
        
        # Оставляем только те, где есть дубликаты
        return {k: v for k, v in duplicated.items() if len(v) > 1}
    
    def _find_potential_product_columns(self, df: pd.DataFrame) -> List[str]:
        """Поиск потенциальных столбцов с товарами"""
        candidates = []
        
        for col in df.columns:
            col_str = str(col).lower().strip()
            
            # Проверяем ключевые слова
            if any(keyword in col_str for keyword in self.product_keywords):
                candidates.append(col)
                continue
            
            # Проверяем содержимое
            if self._is_product_column_by_content(df[col]):
                candidates.append(col)
        
        return candidates
    
    def _find_potential_price_columns(self, df: pd.DataFrame) -> List[str]:
        """Поиск потенциальных столбцов с ценами"""
        candidates = []
        
        for col in df.columns:
            col_str = str(col).lower().strip()
            
            # Проверяем ключевые слова
            if any(keyword in col_str for keyword in self.price_keywords):
                candidates.append(col)
                continue
            
            # Проверяем содержимое
            if self._is_price_column_by_content(df[col]):
                candidates.append(col)
        
        return candidates
    
    def _is_product_column_by_content(self, series: pd.Series) -> bool:
        """Проверка, является ли столбец столбцом с товарами по содержимому"""
        sample_values = series.dropna().head(20)  # Больше образцов
        
        if len(sample_values) == 0:
            return False
        
        text_count = 0
        numeric_count = 0
        
        for val in sample_values:
            val_str = str(val).strip()
            
            # Проверяем, что это не число
            try:
                float(val_str.replace(',', '.'))
                numeric_count += 1
                continue
            except:
                pass
            
            # Текст длиной 3-100 символов, не служебное значение
            if (3 <= len(val_str) <= 100 and 
                val_str.lower() not in ['nan', 'none', 'null', 'unit', 'price'] and
                not val_str.replace('.', '').replace(',', '').isdigit()):
                # Дополнительная проверка - похоже ли на название товара
                if (any(c.isalpha() for c in val_str) and  # Есть буквы
                    len(val_str.split()) <= 10):  # Не слишком много слов
                    text_count += 1
        
        # Столбец товаров должен быть преимущественно текстовым
        total_values = len(sample_values)
        return (text_count >= total_values * 0.6 and  # Минимум 60% текста
                numeric_count < total_values * 0.3)   # Максимум 30% чисел
    
    def _is_price_column_by_content(self, series: pd.Series) -> bool:
        """Проверка, является ли столбец столбцом с ценами по содержимому"""
        sample_values = series.dropna().head(10)
        
        if len(sample_values) == 0:
            return False
        
        numeric_count = 0
        for val in sample_values:
            try:
                num_val = float(str(val).replace(',', '.'))
                if 100 <= num_val <= 10000000:  # Разумный диапазон цен
                    numeric_count += 1
            except:
                continue
        
        return numeric_count >= len(sample_values) * 0.7
    
    def _find_data_start_row(self, df: pd.DataFrame) -> int:
        """Поиск строки, с которой начинаются данные"""
        for i, row in df.iterrows():
            # Ищем строку где есть и текстовые и числовые данные
            text_values = 0
            numeric_values = 0
            
            for val in row:
                if pd.notna(val):
                    val_str = str(val).strip()
                    try:
                        num_val = float(val_str.replace(',', '.'))
                        if num_val > 100:
                            numeric_values += 1
                    except:
                        if len(val_str) > 2:
                            text_values += 1
            
            if text_values >= 1 and numeric_values >= 1:
                return i
        
        return 0
    
    def _select_best_sheet(self, sheets_info: Dict[str, Any]) -> Optional[str]:
        """Выбор лучшего листа для обработки"""
        if not sheets_info:
            return None
        
        # Сначала ищем листы с потенциальными товарами
        candidates = []
        for name, info in sheets_info.items():
            if info.get('potential_products', 0) > 0:
                score = info['potential_products'] * 10
                if info.get('duplicated_structure'):
                    score += 5  # Бонус за двухколоночную структуру
                candidates.append((name, score))
        
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        # Если не нашли, берем первый непустой
        for name, info in sheets_info.items():
            if info.get('rows', 0) > 0:
                return name
        
        return None
    
    def extract_products_enhanced(self, file_path: str, max_products: int = 1000) -> Dict[str, Any]:
        """Улучшенное извлечение товаров"""
        try:
            # Анализ структуры
            file_analysis = self.analyze_file_structure(file_path)
            
            if 'error' in file_analysis:
                return file_analysis
            
            # Выбираем лучший лист
            best_sheet = file_analysis.get('recommended_sheet')
            if not best_sheet:
                return {'error': 'Не найден подходящий лист с данными'}
            
            logger.info(f"Используем лист: {best_sheet}")
            
            # Читаем полные данные
            df = pd.read_excel(file_path, sheet_name=best_sheet)
            df = df.dropna(how='all')
            
            sheet_info = file_analysis['sheets'][best_sheet]
            
            # Определяем стратегию извлечения
            if sheet_info.get('duplicated_structure'):
                # Двухколоночная структура (как UD RAHAYU)
                return self._extract_from_duplicated_structure(df, sheet_info, file_path, max_products)
            else:
                # Обычная структура (как SAI FRESH)
                return self._extract_from_simple_structure(df, sheet_info, file_path, max_products)
        
        except Exception as e:
            logger.error(f"Ошибка извлечения: {e}")
            return {'error': f'Ошибка обработки файла: {str(e)}'}
    
    def _extract_from_duplicated_structure(self, df: pd.DataFrame, sheet_info: Dict, 
                                         file_path: str, max_products: int) -> Dict[str, Any]:
        """Извлечение из двухколоночной структуры"""
        products = []
        duplicated_columns = sheet_info['duplicated_columns']
        
        # Находим базовые столбцы для товаров и цен
        product_base = None
        price_base = None
        unit_base = None
        
        for base_name, columns in duplicated_columns.items():
            if any(keyword in base_name.lower() for keyword in self.product_keywords):
                product_base = base_name
            elif any(keyword in base_name.lower() for keyword in self.price_keywords):
                price_base = base_name
            elif any(keyword in base_name.lower() for keyword in self.unit_keywords):
                unit_base = base_name
        
        if not product_base or not price_base:
            return {'error': 'Не найдены столбцы товаров или цен в дублированной структуре'}
        
        # Получаем реальные названия столбцов
        product_cols = duplicated_columns[product_base]
        price_cols = duplicated_columns[price_base]
        unit_cols = duplicated_columns.get(unit_base, [])
        
        logger.info(f"Найдены столбцы товаров: {product_cols}")
        logger.info(f"Найдены столбцы цен: {price_cols}")
        
        extracted_count = 0
        
        for idx, row in df.iterrows():
            if extracted_count >= max_products:
                break
            
            # Обрабатываем каждую пару столбцов
            for i, (prod_col, price_col) in enumerate(zip(product_cols, price_cols)):
                if extracted_count >= max_products:
                    break
                
                try:
                    # Извлекаем название товара
                    product_name = self._clean_product_name(row.get(prod_col))
                    if not product_name:
                        continue
                    
                    # Извлекаем цену
                    price = self._extract_price_value(row.get(price_col))
                    if price <= 0:
                        continue
                    
                    # Извлекаем единицу
                    unit = 'pcs'
                    if i < len(unit_cols) and unit_cols[i] in row:
                        unit_val = row.get(unit_cols[i])
                        if pd.notna(unit_val):
                            unit = str(unit_val).strip()
                    
                    product = {
                        'original_name': product_name,
                        'price': price,
                        'unit': unit or 'pcs',
                        'category': 'general',
                        'row_index': idx,
                        'column_set': i + 1,
                        'confidence': 0.9
                    }
                    
                    products.append(product)
                    extracted_count += 1
                    
                except Exception as e:
                    logger.debug(f"Ошибка обработки строки {idx}, столбец {i}: {e}")
                    continue
        
        return self._create_result(products, df, file_path, best_sheet='duplicated')
    
    def _extract_from_simple_structure(self, df: pd.DataFrame, sheet_info: Dict,
                                     file_path: str, max_products: int) -> Dict[str, Any]:
        """Извлечение из простой структуры"""
        products = []
        
        # Находим столбцы
        product_columns = sheet_info['product_columns']
        price_columns = sheet_info['price_columns']
        data_start_row = sheet_info['data_start_row']
        
        if not product_columns or not price_columns:
            return {'error': 'Не найдены столбцы товаров или цен'}
        
        # Выбираем лучшие столбцы по качеству содержимого
        product_col = self._select_best_product_column(df, product_columns)
        price_col = self._select_best_price_column(df, price_columns)
        
        logger.info(f"Используем столбец товаров: {product_col}")
        logger.info(f"Используем столбец цен: {price_col}")
        logger.info(f"Начинаем с строки: {data_start_row}")
        
        # Пропускаем заголовок и извлекаем данные
        for idx in range(data_start_row, len(df)):
            if len(products) >= max_products:
                break
            
            try:
                row = df.iloc[idx]
                
                # Извлекаем название товара
                product_name = self._clean_product_name(row.get(product_col))
                if not product_name:
                    continue
                
                # Извлекаем цену
                price = self._extract_price_value(row.get(price_col))
                if price <= 0:
                    continue
                
                # Пытаемся найти единицу измерения в той же строке
                unit = self._extract_unit_from_row(row)
                
                product = {
                    'original_name': product_name,
                    'price': price,
                    'unit': unit or 'pcs',
                    'category': 'general',
                    'row_index': idx,
                    'confidence': 0.9
                }
                
                products.append(product)
                
            except Exception as e:
                logger.debug(f"Ошибка обработки строки {idx}: {e}")
                continue
        
        return self._create_result(products, df, file_path, best_sheet='simple')
    
    def _clean_product_name(self, value) -> Optional[str]:
        """Очистка названия товара"""
        if pd.isna(value):
            return None
        
        name = str(value).strip()
        
        # Пропускаем числа, короткие строки и служебные значения
        if (len(name) < 3 or 
            name.replace('.', '').replace(',', '').isdigit() or
            name.lower() in ['nan', 'none', 'null']):
            return None
        
        return name
    
    def _extract_price_value(self, value) -> float:
        """Извлечение цены из значения"""
        if pd.isna(value):
            return 0
        
        try:
            # Очищаем и преобразуем в число
            price_str = str(value).replace(',', '.').replace(' ', '')
            price_str = re.sub(r'[^\d.]', '', price_str)
            
            price = float(price_str)
            
            # Проверяем разумный диапазон
            if 10 <= price <= 10000000:
                return price
            
        except:
            pass
        
        return 0
    
    def _extract_unit_from_row(self, row) -> str:
        """Извлечение единицы измерения из строки"""
        common_units = ['kg', 'g', 'ml', 'l', 'pcs', 'pack', 'box', 'can', 'btl', 'ikat', 'gln']
        
        for value in row:
            if pd.notna(value):
                val_str = str(value).lower().strip()
                if val_str in common_units:
                    return val_str
        
        return 'pcs'
    
    def _select_best_product_column(self, df: pd.DataFrame, candidates: List[str]) -> str:
        """Выбор лучшего столбца с товарами из кандидатов"""
        if len(candidates) == 1:
            return candidates[0]
        
        best_col = candidates[0]
        best_score = 0
        
        for col in candidates:
            score = 0
            sample_values = df[col].dropna().head(20)
            
            # Подсчитываем качественные товарные названия
            for val in sample_values:
                val_str = str(val).strip()
                if (5 <= len(val_str) <= 100 and
                    any(c.isalpha() for c in val_str) and
                    not val_str.replace('.', '').replace(',', '').isdigit() and
                    val_str.lower() not in ['description', 'unit', 'price', 'no']):
                    score += 1
            
            if score > best_score:
                best_score = score
                best_col = col
        
        return best_col
    
    def _select_best_price_column(self, df: pd.DataFrame, candidates: List[str]) -> str:
        """Выбор лучшего столбца с ценами из кандидатов"""
        if len(candidates) == 1:
            return candidates[0]
        
        best_col = candidates[0]
        best_score = 0
        
        for col in candidates:
            score = 0
            sample_values = df[col].dropna().head(20)
            
            # Подсчитываем валидные цены
            for val in sample_values:
                try:
                    price = float(str(val).replace(',', '.'))
                    if 100 <= price <= 10000000:  # Разумный диапазон
                        score += 1
                except:
                    pass
            
            if score > best_score:
                best_score = score
                best_col = col
        
        return best_col
    
    def _create_result(self, products: List[Dict], df: pd.DataFrame, 
                      file_path: str, best_sheet: str) -> Dict[str, Any]:
        """Создание результата"""
        supplier_name = Path(file_path).stem
        
        return {
            'file_type': 'excel',
            'supplier': {'name': supplier_name},
            'products': products,
            'extraction_stats': {
                'total_rows': len(df),
                'extracted_products': len(products),
                'success_rate': len(products) / len(df) if len(df) > 0 else 0,
                'used_sheet': best_sheet,
                'extraction_method': 'enhanced_parser'
            }
        }