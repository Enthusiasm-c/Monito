#!/usr/bin/env python3
"""
Универсальный парсер Excel - анализирует любую структуру без предположений
"""

import pandas as pd
import re
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from .base_parser import BaseParser

logger = logging.getLogger(__name__)

class UniversalExcelParser(BaseParser):
    """Универсальный парсер Excel для любых структур прайс-листов"""
    
    def __init__(self):
        # Инициализируем базовый класс с общими паттернами и функциями
        super().__init__()
        
        self.common_units = [
            'kg', 'g', 'ml', 'l', 'pcs', 'pack', 'box', 'can', 'btl', 
            'ikat', 'gln', 'gram', 'liter', 'piece', 'кг', 'г', 'мл', 'л', 'шт'
        ]
    
    def extract_products_universal(self, file_path: str, max_products: int = 1000, use_ai: bool = True) -> Dict[str, Any]:
        """Универсальное извлечение товаров из любого Excel файла"""
        try:
            logger.info(f"🔍 Начинаем универсальный анализ файла: {file_path}")
            
            # 1. Анализируем все листы
            logger.debug(f"📋 Шаг 1: Анализ листов Excel файла...")
            sheets_data = self._analyze_all_sheets(file_path)
            
            if not sheets_data:
                logger.error(f"❌ Не удалось прочитать ни один лист файла")
                return {'error': 'Не удалось прочитать ни один лист файла'}
            
            logger.info(f"📊 Проанализировано листов: {len(sheets_data)}")
            for sheet in sheets_data:
                logger.debug(f"  • {sheet['name']}: {sheet['rows']} строк, потенциал: {sheet['potential_score']:.3f}")
            
            # 2. Находим лист с наибольшим количеством потенциальных товаров
            logger.debug(f"📋 Шаг 2: Выбор лучшего листа...")
            best_sheet_data = self._select_best_sheet(sheets_data)
            
            if not best_sheet_data:
                logger.error(f"❌ Не найдено листов с товарами среди {len(sheets_data)} листов")
                return {'error': 'Не найдено листов с товарами'}
            
            logger.info(f"📄 Выбран лист: {best_sheet_data['name']} (потенциал: {best_sheet_data['potential_score']:.3f})")
            
            # 3. НОВЫЙ AI-ПОДХОД: сначала пробуем AI анализ
            if use_ai:
                logger.info(f"🤖 Шаг 3: Попытка AI-анализа таблицы...")
                ai_result = self._try_ai_extraction(best_sheet_data['dataframe'], file_path)
                if ai_result and not ai_result.get('error'):
                    # AI успешно обработал - используем его результат
                    ai_products = ai_result.get('products', [])
                    ai_result['extraction_stats']['used_sheet'] = best_sheet_data['name']
                    ai_result['extraction_stats']['ai_enhanced'] = True
                    ai_result['extraction_stats']['total_rows'] = len(best_sheet_data['dataframe'])
                    ai_result['extraction_stats']['extracted_products'] = len(ai_products)
                    logger.info(f"✅ AI успешно извлек {len(ai_products)} товаров из {len(best_sheet_data['dataframe'])} строк Excel")
                    return ai_result
                else:
                    logger.warning(f"⚠️ AI не смог обработать таблицу, переходим к классическому парсеру")
            else:
                logger.info(f"🔧 Шаг 3: AI отключен, используем классический парсер")
            
            # 4. FALLBACK: классический анализ структуры данных
            logger.debug(f"📋 Шаг 4: Классический анализ структуры данных...")
            structure = self._analyze_data_structure(best_sheet_data['dataframe'])
            
            logger.info(f"🏗️ Обнаружена структура: {structure['type']}")
            logger.info(f"📊 Найдено столбцов: товары={len(structure['product_columns'])}, цены={len(structure['price_columns'])}, единицы={len(structure['unit_columns'])}")
            
            # 5. Извлекаем товары в зависимости от структуры
            logger.debug(f"📋 Шаг 5: Извлечение товаров по структуре {structure['type']}...")
            products = self._extract_products_by_structure(best_sheet_data['dataframe'], structure, max_products)
            
            logger.info(f"📦 Классический парсер извлек {len(products)} товаров из {len(best_sheet_data['dataframe'])} строк")
            
            # 6. Формируем результат
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
                    'extraction_method': 'manual_parser',
                    'ai_enhanced': False
                }
            }
            
            logger.info(f"✅ Извлечено {len(products)} товаров из {len(best_sheet_data['dataframe'])} строк")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка универсального парсинга: {e}")
            return {'error': f'Ошибка обработки файла: {str(e)}'}
    
    def _analyze_all_sheets(self, file_path: str) -> List[Dict]:
        """Анализ всех листов файла - оптимизированная версия"""
        sheets_data = []
        
        try:
            # Используем ExcelFile для более эффективного чтения нескольких листов
            with pd.ExcelFile(file_path, engine='openpyxl') as xls:
                for sheet_name in xls.sheet_names:
                    try:
                        # Читаем только первые 100 строк для анализа потенциала
                        df_sample = pd.read_excel(xls, sheet_name=sheet_name, nrows=100)
                        
                        if df_sample.empty or len(df_sample) < 2:
                            continue
                        
                        # Быстрая оценка потенциала листа
                        potential_score = self._calculate_sheet_potential_optimized(df_sample)
                        
                        # Читаем полный лист только если потенциал высокий
                        if potential_score > 0.1:
                            df_full = pd.read_excel(xls, sheet_name=sheet_name)
                            
                            sheets_data.append({
                                'name': sheet_name,
                                'dataframe': df_full,
                                'potential_score': potential_score,
                                'rows': len(df_full),
                                'cols': len(df_full.columns)
                            })
                            
                            logger.debug(f"📋 Лист '{sheet_name}': {len(df_full)} строк, потенциал: {potential_score:.3f}")
                        else:
                            logger.debug(f"📋 Лист '{sheet_name}' пропущен (низкий потенциал: {potential_score:.3f})")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка чтения листа {sheet_name}: {e}")
                        continue
            
            return sheets_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа файла: {e}")
            return []
    
    def _calculate_sheet_potential_optimized(self, df: pd.DataFrame) -> float:
        """Оптимизированный расчет потенциала листа - использует векторизацию Pandas"""
        if df.empty:
            return 0
        
        # Конвертируем все значения в строки и убираем NaN
        df_str = df.astype(str).replace('nan', '')
        
        # Векторизованный подсчет товаров, цен и единиц
        product_mask = df_str.map(self._looks_like_product)
        price_mask = df_str.map(self._looks_like_price) 
        unit_mask = df_str.map(self._looks_like_unit)
        
        # Подсчитываем баллы
        product_score = product_mask.sum().sum() * 2
        price_score = price_mask.sum().sum() * 1
        unit_score = unit_mask.sum().sum() * 0.5
        
        total_score = product_score + price_score + unit_score
        total_cells = (df_str != '').sum().sum()
        
        return total_score / max(total_cells, 1)
    
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
        
        # Анализируем каждый столбец с сохранением метрик качества
        column_analyses = {}
        for col in df.columns:
            col_analysis = self._analyze_column(df[col])
            column_analyses[col] = col_analysis
            
            if col_analysis['type'] == 'product':
                structure['product_columns'].append(col)
            elif col_analysis['type'] == 'price':
                structure['price_columns'].append(col)
            elif col_analysis['type'] == 'unit':
                structure['unit_columns'].append(col)
        
        # Сортируем столбцы товаров по качеству (лучшие первыми)
        if structure['product_columns']:
            structure['product_columns'].sort(
                key=lambda col: column_analyses[col].get('quality_score', 0), 
                reverse=True
            )
            
            # Логирование для отладки
            for col in structure['product_columns']:
                analysis = column_analyses[col]
                logger.debug(f"Столбец товаров '{col}': качество={analysis.get('quality_score', 0):.2f}, "
                           f"уверенность={analysis.get('confidence', 0):.2f}")
        
        # Сохраняем анализы столбцов для дальнейшего использования
        structure['column_analyses'] = column_analyses
        
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
        """Анализ отдельного столбца - оптимизированная версия с улучшенной логикой"""
        sample_values = series.dropna().head(20)
        
        if len(sample_values) == 0:
            return {'type': 'empty', 'confidence': 0}
        
        # Векторизованный анализ
        sample_str = sample_values.astype(str).str.strip()
        
        # Используем векторизованные операции Pandas
        product_mask = sample_str.apply(self._looks_like_product)
        price_mask = sample_str.apply(self._looks_like_price)
        unit_mask = sample_str.apply(self._looks_like_unit)
        
        product_score = product_mask.sum()
        price_score = price_mask.sum() 
        unit_score = unit_mask.sum()
        
        total = len(sample_values)
        
        # Дополнительный анализ качества товарных названий
        product_quality_score = 0
        if product_score > 0:
            for value in sample_str[product_mask]:
                # Премия за длинные детальные названия товаров
                if len(value) > 15:
                    product_quality_score += 2
                elif len(value) > 8:
                    product_quality_score += 1
                # Премия за наличие пробелов (составные названия)
                if ' ' in value:
                    product_quality_score += 1
                # Штраф за повторяющиеся короткие названия (бренды)
                if len(value) < 8 and sample_str.str.contains(value, regex=False).sum() > 3:
                    product_quality_score -= 2
        
        # Нормализуем качество товаров
        product_quality = product_quality_score / max(product_score, 1)
        
        # Определяем тип столбца с учетом качества
        product_confidence = product_score / total
        price_confidence = price_score / total
        unit_confidence = unit_score / total
        
        if product_confidence > 0.6:
            return {
                'type': 'product', 
                'confidence': product_confidence,
                'quality_score': product_quality
            }
        elif price_confidence > 0.7:
            return {'type': 'price', 'confidence': price_confidence, 'quality_score': 0}
        elif unit_confidence > 0.5:
            return {'type': 'unit', 'confidence': unit_confidence, 'quality_score': 0}
        else:
            return {'type': 'mixed', 'confidence': 0.3, 'quality_score': 0}
    
    def _find_data_rows(self, df: pd.DataFrame) -> List[int]:
        """Поиск строк с данными товаров - оптимизированная версия"""
        if df.empty:
            return []
        
        # Конвертируем DataFrame в строки для анализа
        df_str = df.astype(str).replace('nan', '')
        
        # Векторизованное определение типов ячеек
        product_mask = df_str.map(self._looks_like_product)
        price_mask = df_str.map(self._looks_like_price)
        
        # Подсчитываем количество товаров и цен в каждой строке
        product_counts = product_mask.sum(axis=1)
        price_counts = price_mask.sum(axis=1)
        
        # Находим строки, где есть и товары и цены
        valid_rows_mask = (product_counts >= 1) & (price_counts >= 1)
        
        return valid_rows_mask[valid_rows_mask].index.tolist()
    
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
            context = f"Excel прайс-лист из файла {Path(file_path).name}"
            
            # Анализируем через AI
            result = ai_parser.extract_products_with_ai(df, context)
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка AI извлечения: {e}")
            return None