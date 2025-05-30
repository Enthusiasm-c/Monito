#!/usr/bin/env python3
"""
Универсальный парсер Excel - анализирует любую структуру без предположений
"""

import pandas as pd
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class UniversalExcelParser:
    """Универсальный парсер Excel для любых структур прайс-листов"""
    
    def __init__(self):
        # Паттерны для поиска товаров и цен
        self.product_patterns = [
            r'[а-яёa-z]{3,}.*\d+.*[а-яёa-z]',  # Текст с числами и буквами
            r'[а-яёa-z]{5,}',  # Просто текст длиннее 5 символов
            r'.*[а-яёa-z]{3,}.*[а-яёa-z]{3,}',  # Несколько слов
        ]
        
        self.price_patterns = [
            r'^\d{3,}\.?\d*$',  # Числа от 100
            r'^\d{1,3}[\s,]\d{3}.*$',  # Числа с разделителями
        ]
        
        self.common_units = [
            'kg', 'g', 'ml', 'l', 'pcs', 'pack', 'box', 'can', 'btl', 
            'ikat', 'gln', 'gram', 'liter', 'piece', 'кг', 'г', 'мл', 'л', 'шт'
        ]
    
    def extract_products_universal(self, file_path: str, max_products: int = 1000) -> Dict[str, Any]:
        """Универсальное извлечение товаров из любого Excel файла"""
        try:
            logger.info(f"🔍 Начинаем универсальный анализ файла: {file_path}")
            
            # 1. Анализируем все листы
            sheets_data = self._analyze_all_sheets(file_path)
            
            if not sheets_data:
                return {'error': 'Не удалось прочитать ни один лист файла'}
            
            # 2. Находим лист с наибольшим количеством потенциальных товаров
            best_sheet_data = self._select_best_sheet(sheets_data)
            
            if not best_sheet_data:
                return {'error': 'Не найдено листов с товарами'}
            
            logger.info(f"📄 Выбран лист: {best_sheet_data['name']}")
            
            # 3. Анализируем структуру данных
            structure = self._analyze_data_structure(best_sheet_data['dataframe'])
            
            logger.info(f"🏗️ Обнаружена структура: {structure['type']}")
            
            # 4. Извлекаем товары в зависимости от структуры
            products = self._extract_products_by_structure(best_sheet_data['dataframe'], structure, max_products)
            
            # 5. Формируем результат
            supplier_name = Path(file_path).stem
            
            result = {
                'file_type': 'excel',
                'supplier': {'name': supplier_name},
                'products': products,
                'extraction_stats': {
                    'total_rows': len(best_sheet_data['dataframe']),
                    'extracted_products': len(products),
                    'success_rate': len(products) / len(best_sheet_data['dataframe']) if len(best_sheet_data['dataframe']) > 0 else 0,
                    'used_sheet': best_sheet_data['name'],
                    'detected_structure': structure['type'],
                    'extraction_method': 'universal_parser'
                }
            }
            
            logger.info(f"✅ Извлечено {len(products)} товаров из {len(best_sheet_data['dataframe'])} строк")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка универсального парсинга: {e}")
            return {'error': f'Ошибка обработки файла: {str(e)}'}
    
    def _analyze_all_sheets(self, file_path: str) -> List[Dict]:
        """Анализ всех листов файла"""
        sheets_data = []
        
        try:
            xls = pd.ExcelFile(file_path)
            
            for sheet_name in xls.sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    if df.empty or len(df) < 2:
                        continue
                    
                    # Быстрая оценка потенциала листа
                    potential_score = self._calculate_sheet_potential(df)
                    
                    sheets_data.append({
                        'name': sheet_name,
                        'dataframe': df,
                        'potential_score': potential_score,
                        'rows': len(df),
                        'cols': len(df.columns)
                    })
                    
                    logger.debug(f"📋 Лист '{sheet_name}': {len(df)} строк, потенциал: {potential_score}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка чтения листа {sheet_name}: {e}")
                    continue
            
            return sheets_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа файла: {e}")
            return []
    
    def _calculate_sheet_potential(self, df: pd.DataFrame) -> float:
        """Расчет потенциала листа для содержания товаров"""
        score = 0
        total_cells = 0
        
        # Анализируем только первые 50 строк для скорости
        sample_df = df.head(50)
        
        for _, row in sample_df.iterrows():
            for value in row:
                if pd.notna(value):
                    total_cells += 1
                    value_str = str(value).strip()
                    
                    # Проверяем на товар
                    if self._looks_like_product(value_str):
                        score += 2
                    
                    # Проверяем на цену
                    elif self._looks_like_price(value_str):
                        score += 1
                    
                    # Проверяем на единицу измерения
                    elif self._looks_like_unit(value_str):
                        score += 0.5
        
        return score / max(total_cells, 1)  # Нормализуем
    
    def _looks_like_product(self, value: str) -> bool:
        """Проверка, похоже ли значение на название товара"""
        if len(value) < 3 or len(value) > 200:
            return False
        
        # Пропускаем числа и служебные слова
        if (value.replace('.', '').replace(',', '').isdigit() or
            value.lower() in ['unit', 'price', 'no', 'description', 'total', 'sum', 'nan', 'none']):
            return False
        
        # Должно содержать буквы
        if not any(c.isalpha() for c in value):
            return False
        
        # Проверяем паттерны товаров
        for pattern in self.product_patterns:
            if re.search(pattern, value.lower()):
                return True
        
        return False
    
    def _looks_like_price(self, value: str) -> bool:
        """Проверка, похоже ли значение на цену"""
        try:
            # Очищаем от символов и пробуем преобразовать
            clean_value = re.sub(r'[^\d.]', '', str(value))
            if not clean_value:
                return False
            
            num_value = float(clean_value)
            
            # Разумный диапазон цен
            return 10 <= num_value <= 50000000
            
        except:
            return False
    
    def _looks_like_unit(self, value: str) -> bool:
        """Проверка, похоже ли значение на единицу измерения"""
        value_lower = str(value).lower().strip()
        return value_lower in self.common_units
    
    def _select_best_sheet(self, sheets_data: List[Dict]) -> Optional[Dict]:
        """Выбор лучшего листа для обработки"""
        if not sheets_data:
            return None
        
        # Сортируем по потенциалу
        sheets_data.sort(key=lambda x: x['potential_score'], reverse=True)
        
        return sheets_data[0]
    
    def _analyze_data_structure(self, df: pd.DataFrame) -> Dict:
        """Анализ структуры данных в листе"""
        structure = {
            'type': 'unknown',
            'product_columns': [],
            'price_columns': [],
            'unit_columns': [],
            'data_rows': [],
            'header_rows': []
        }
        
        # Анализируем каждый столбец
        for col in df.columns:
            col_analysis = self._analyze_column(df[col])
            
            if col_analysis['type'] == 'product':
                structure['product_columns'].append(col)
            elif col_analysis['type'] == 'price':
                structure['price_columns'].append(col)
            elif col_analysis['type'] == 'unit':
                structure['unit_columns'].append(col)
        
        # Анализируем строки для определения где начинаются данные
        structure['data_rows'] = self._find_data_rows(df)
        
        # Определяем тип структуры
        if len(structure['product_columns']) > 1:
            structure['type'] = 'multi_column'  # Несколько колонок товаров
        elif len(structure['product_columns']) == 1 and len(structure['price_columns']) >= 1:
            structure['type'] = 'standard'  # Стандартная структура
        else:
            structure['type'] = 'mixed'  # Смешанная/неопределенная
        
        logger.info(f"🔍 Найдено: товары={len(structure['product_columns'])}, цены={len(structure['price_columns'])}")
        
        return structure
    
    def _analyze_column(self, series: pd.Series) -> Dict:
        """Анализ отдельного столбца"""
        sample_values = series.dropna().head(20)
        
        if len(sample_values) == 0:
            return {'type': 'empty', 'confidence': 0}
        
        product_score = 0
        price_score = 0
        unit_score = 0
        
        for value in sample_values:
            value_str = str(value).strip()
            
            if self._looks_like_product(value_str):
                product_score += 1
            elif self._looks_like_price(value_str):
                price_score += 1
            elif self._looks_like_unit(value_str):
                unit_score += 1
        
        total = len(sample_values)
        
        # Определяем тип столбца
        if product_score / total > 0.6:
            return {'type': 'product', 'confidence': product_score / total}
        elif price_score / total > 0.7:
            return {'type': 'price', 'confidence': price_score / total}
        elif unit_score / total > 0.5:
            return {'type': 'unit', 'confidence': unit_score / total}
        else:
            return {'type': 'mixed', 'confidence': 0.3}
    
    def _find_data_rows(self, df: pd.DataFrame) -> List[int]:
        """Поиск строк с данными товаров"""
        data_rows = []
        
        for idx, row in df.iterrows():
            # Считаем сколько в строке похоже на товарные данные
            product_count = 0
            price_count = 0
            
            for value in row:
                if pd.notna(value):
                    value_str = str(value).strip()
                    
                    if self._looks_like_product(value_str):
                        product_count += 1
                    elif self._looks_like_price(value_str):
                        price_count += 1
            
            # Если в строке есть и товар и цена - это строка с данными
            if product_count >= 1 and price_count >= 1:
                data_rows.append(idx)
        
        return data_rows
    
    def _extract_products_by_structure(self, df: pd.DataFrame, structure: Dict, max_products: int) -> List[Dict]:
        """Извлечение товаров в зависимости от структуры"""
        products = []
        
        if structure['type'] == 'multi_column':
            products = self._extract_multi_column(df, structure, max_products)
        elif structure['type'] == 'standard':
            products = self._extract_standard(df, structure, max_products)
        else:
            products = self._extract_mixed(df, structure, max_products)
        
        return products
    
    def _extract_multi_column(self, df: pd.DataFrame, structure: Dict, max_products: int) -> List[Dict]:
        """Извлечение из многоколоночной структуры"""
        products = []
        product_cols = structure['product_columns']
        price_cols = structure['price_columns']
        
        # Обрабатываем только строки с данными
        data_rows = structure['data_rows'] if structure['data_rows'] else range(len(df))
        
        for row_idx in data_rows:
            if len(products) >= max_products:
                break
                
            row = df.iloc[row_idx]
            
            # Обрабатываем каждую пару товар-цена
            for prod_col in product_cols:
                for price_col in price_cols:
                    try:
                        product_name = self._clean_product_name(row.get(prod_col))
                        price = self._clean_price(row.get(price_col))
                        
                        if product_name and price > 0:
                            unit = self._find_unit_in_row(row, structure['unit_columns'])
                            
                            products.append({
                                'original_name': product_name,
                                'price': price,
                                'unit': unit or 'pcs',
                                'category': 'general',
                                'row_index': row_idx,
                                'confidence': 0.8
                            })
                            
                            if len(products) >= max_products:
                                return products
                                
                    except Exception as e:
                        logger.debug(f"Ошибка обработки строки {row_idx}: {e}")
                        continue
        
        return products
    
    def _extract_standard(self, df: pd.DataFrame, structure: Dict, max_products: int) -> List[Dict]:
        """Извлечение из стандартной структуры"""
        products = []
        
        if not structure['product_columns'] or not structure['price_columns']:
            return products
        
        product_col = structure['product_columns'][0]
        price_col = structure['price_columns'][0]
        
        # Обрабатываем только строки с данными
        data_rows = structure['data_rows'] if structure['data_rows'] else range(len(df))
        
        for row_idx in data_rows:
            if len(products) >= max_products:
                break
                
            try:
                row = df.iloc[row_idx]
                
                product_name = self._clean_product_name(row.get(product_col))
                price = self._clean_price(row.get(price_col))
                
                if product_name and price > 0:
                    unit = self._find_unit_in_row(row, structure['unit_columns'])
                    
                    products.append({
                        'original_name': product_name,
                        'price': price,
                        'unit': unit or 'pcs',
                        'category': 'general',
                        'row_index': row_idx,
                        'confidence': 0.9
                    })
                    
            except Exception as e:
                logger.debug(f"Ошибка обработки строки {row_idx}: {e}")
                continue
        
        return products
    
    def _extract_mixed(self, df: pd.DataFrame, structure: Dict, max_products: int) -> List[Dict]:
        """Извлечение из смешанной/неопределенной структуры"""
        products = []
        
        # Просто ищем по всем ячейкам потенциальные товары и цены
        for row_idx, row in df.iterrows():
            if len(products) >= max_products:
                break
            
            potential_products = []
            potential_prices = []
            potential_units = []
            
            # Собираем все потенциальные элементы из строки
            for value in row:
                if pd.notna(value):
                    value_str = str(value).strip()
                    
                    if self._looks_like_product(value_str):
                        potential_products.append(value_str)
                    elif self._looks_like_price(value_str):
                        try:
                            price = self._clean_price(value)
                            if price > 0:
                                potential_prices.append(price)
                        except:
                            pass
                    elif self._looks_like_unit(value_str):
                        potential_units.append(value_str)
            
            # Если нашли и товар и цену в одной строке
            if potential_products and potential_prices:
                for product_name in potential_products:
                    for price in potential_prices:
                        unit = potential_units[0] if potential_units else 'pcs'
                        
                        products.append({
                            'original_name': product_name,
                            'price': price,
                            'unit': unit,
                            'category': 'general',
                            'row_index': row_idx,
                            'confidence': 0.7
                        })
                        
                        if len(products) >= max_products:
                            return products
        
        return products
    
    def _clean_product_name(self, value) -> Optional[str]:
        """Очистка названия товара"""
        if pd.isna(value):
            return None
        
        name = str(value).strip()
        
        if not self._looks_like_product(name):
            return None
        
        return name
    
    def _clean_price(self, value) -> float:
        """Очистка и извлечение цены"""
        if pd.isna(value):
            return 0
        
        try:
            # Убираем все кроме цифр и точки
            clean_value = re.sub(r'[^\d.]', '', str(value))
            if not clean_value:
                return 0
            
            price = float(clean_value)
            return price if 10 <= price <= 50000000 else 0
            
        except:
            return 0
    
    def _find_unit_in_row(self, row, unit_columns: List[str]) -> Optional[str]:
        """Поиск единицы измерения в строке"""
        # Сначала проверяем специальные столбцы единиц
        for col in unit_columns:
            if col in row and pd.notna(row[col]):
                unit = str(row[col]).strip().lower()
                if unit in self.common_units:
                    return unit
        
        # Потом ищем по всей строке
        for value in row:
            if pd.notna(value):
                value_str = str(value).strip().lower()
                if value_str in self.common_units:
                    return value_str
        
        return None