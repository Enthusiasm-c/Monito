#!/usr/bin/env python3
"""
Продвинутый парсер Excel файлов для извлечения максимального количества данных
"""

import os
import re
import logging
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class AdvancedExcelParser:
    """Продвинутый парсер Excel файлов"""
    
    def __init__(self):
        # Расширенные ключевые слова для поиска столбцов
        self.product_keywords = [
            'product', 'название', 'товар', 'item', 'name', 'наименование',
            'артикул', 'code', 'модель', 'model', 'описание', 'description',
            'номенклатура', 'sku', 'part', 'позиция'
        ]
        
        self.price_keywords = [
            'price', 'цена', 'cost', 'стоимость', 'руб', 'usd', 'eur', '$', '₽',
            'сумма', 'amount', 'тариф', 'rate', 'прайс'
        ]
        
        self.unit_keywords = [
            'unit', 'единица', 'ед', 'штука', 'шт', 'мера', 'measure',
            'количество', 'qty', 'упаковка', 'pack'
        ]
        
        self.category_keywords = [
            'category', 'категория', 'тип', 'type', 'группа', 'group',
            'класс', 'class', 'раздел', 'section'
        ]
    
    def analyze_file_structure(self, file_path: str) -> Dict[str, Any]:
        """Детальный анализ структуры Excel файла"""
        try:
            # Читаем все листы
            excel_file = pd.ExcelFile(file_path)
            sheets_info = {}
            
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=10)  # Первые 10 строк для анализа
                    
                    sheets_info[sheet_name] = {
                        'rows': len(df),
                        'columns': len(df.columns),
                        'headers': list(df.columns),
                        'sample_data': df.head(3).to_dict('records'),
                        'non_empty_rows': df.dropna(how='all').shape[0]
                    }
                except Exception as e:
                    logger.warning(f"Ошибка чтения листа {sheet_name}: {e}")
                    continue
            
            return {
                'file_path': file_path,
                'sheets': sheets_info,
                'total_sheets': len(sheets_info),
                'recommended_sheet': self._find_best_sheet(sheets_info)
            }
            
        except Exception as e:
            logger.error(f"Ошибка анализа файла {file_path}: {e}")
            return {'error': str(e)}
    
    def _find_best_sheet(self, sheets_info: Dict) -> Optional[str]:
        """Поиск наиболее подходящего листа для обработки"""
        best_sheet = None
        best_score = 0
        
        for sheet_name, info in sheets_info.items():
            score = 0
            headers = [str(h).lower() for h in info.get('headers', [])]
            
            # Бонусы за наличие нужных столбцов
            if any(keyword in ' '.join(headers) for keyword in self.product_keywords):
                score += 10
            if any(keyword in ' '.join(headers) for keyword in self.price_keywords):
                score += 10
            
            # Бонус за количество данных
            score += min(info.get('non_empty_rows', 0) / 10, 5)
            
            # Штраф за слишком мало столбцов
            if info.get('columns', 0) < 2:
                score -= 5
            
            if score > best_score:
                best_score = score
                best_sheet = sheet_name
        
        return best_sheet
    
    def find_columns(self, df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """Умный поиск столбцов с товарами, ценами и другими данными"""
        columns = {
            'product': None,
            'price': None,
            'unit': None,
            'category': None,
            'description': None
        }
        
        # Анализ заголовков
        for col in df.columns:
            col_str = str(col).lower().strip()
            
            # Поиск столбца с товарами
            if not columns['product'] and any(keyword in col_str for keyword in self.product_keywords):
                columns['product'] = col
                continue
            
            # Поиск столбца с ценами
            if not columns['price'] and any(keyword in col_str for keyword in self.price_keywords):
                columns['price'] = col
                continue
            
            # Поиск столбца с единицами
            if not columns['unit'] and any(keyword in col_str for keyword in self.unit_keywords):
                columns['unit'] = col
                continue
            
            # Поиск столбца с категориями
            if not columns['category'] and any(keyword in col_str for keyword in self.category_keywords):
                columns['category'] = col
                continue
        
        # Если не нашли явные столбцы, пробуем эвристический поиск
        if not columns['product']:
            columns['product'] = self._find_product_column_heuristic(df)
        
        if not columns['price']:
            columns['price'] = self._find_price_column_heuristic(df)
        
        logger.info(f"Найденные столбцы: {columns}")
        return columns
    
    def _find_product_column_heuristic(self, df: pd.DataFrame) -> Optional[str]:
        """Эвристический поиск столбца с товарами"""
        for col in df.columns:
            # Проверяем первые несколько строк
            sample_values = df[col].dropna().head(5).astype(str)
            
            # Ищем текстовые значения средней длины (вероятно названия товаров)
            text_lengths = [len(str(val)) for val in sample_values if str(val) != 'nan']
            
            if text_lengths:
                avg_length = sum(text_lengths) / len(text_lengths)
                # Названия товаров обычно 10-100 символов
                if 10 <= avg_length <= 100:
                    # Проверяем, что это не числа
                    numeric_count = sum(1 for val in sample_values if str(val).replace('.', '').replace(',', '').isdigit())
                    if numeric_count < len(sample_values) * 0.5:  # Менее 50% чисел
                        return col
        
        # Если не нашли, ищем столбцы с ключевыми словами и текстом
        keywords = ['item', 'product', 'name', 'товар', 'название', 'наименование']
        for col in df.columns:
            col_lower = col.lower().strip()
            # Проверяем ключевые слова в названии
            if any(keyword in col_lower for keyword in keywords):
                # Проверяем, что в столбце есть текстовые значения
                sample_values = df[col].dropna().head(5)
                if len(sample_values) > 0:
                    text_count = sum(1 for val in sample_values 
                                   if isinstance(val, str) and len(str(val).strip()) > 2)
                    if text_count > 0:
                        return col
        
        # Если не нашли, берем первый столбец с текстом (исключая числовые)
        for col in df.columns:
            if 'unnamed' in col.lower():  # Пропускаем безымянные столбцы
                continue
            sample_values = df[col].dropna().head(5)
            if len(sample_values) > 0:
                text_count = sum(1 for val in sample_values 
                               if isinstance(val, str) and len(str(val).strip()) > 2 
                               and not str(val).replace('.', '').replace(',', '').isdigit())
                if text_count >= len(sample_values) * 0.5:  # Хотя бы 50% текстовых
                    return col
        
        return None
    
    def _find_price_column_heuristic(self, df: pd.DataFrame) -> Optional[str]:
        """Эвристический поиск столбца с ценами"""
        for col in df.columns:
            sample_values = df[col].dropna().head(10)
            
            # Считаем количество числовых значений
            numeric_count = 0
            for val in sample_values:
                try:
                    # Пробуем преобразовать в число
                    str_val = str(val).replace(',', '.').replace(' ', '')
                    float_val = float(re.sub(r'[^\d.]', '', str_val))
                    if 0 < float_val < 1000000:  # Разумный диапазон цен
                        numeric_count += 1
                except:
                    continue
            
            # Если больше 70% значений - числа в разумном диапазоне
            if len(sample_values) > 0 and numeric_count / len(sample_values) > 0.7:
                return col
        
        return None
    
    def extract_products_smart(self, file_path: str, max_products: int = 1000) -> Dict[str, Any]:
        """Умное извлечение товаров из Excel файла"""
        try:
            # Анализ структуры файла
            file_analysis = self.analyze_file_structure(file_path)
            
            if 'error' in file_analysis:
                return {'error': file_analysis['error']}
            
            # Выбираем лучший лист
            best_sheet = file_analysis.get('recommended_sheet')
            if not best_sheet:
                best_sheet = list(file_analysis['sheets'].keys())[0]
            
            logger.info(f"Используем лист: {best_sheet}")
            
            # Читаем данные с выбранного листа
            df = pd.read_excel(file_path, sheet_name=best_sheet)
            
            # Пропускаем пустые строки
            df = df.dropna(how='all')
            
            # Поиск столбцов
            columns = self.find_columns(df)
            
            if not columns['product']:
                return {'error': 'Не найден столбец с названиями товаров'}
            
            # Извлечение товаров
            products = []
            skipped_rows = 0
            
            for idx, row in df.iterrows():
                try:
                    # Извлекаем название
                    product_name = self._extract_product_name(row, columns['product'])
                    if not product_name:
                        skipped_rows += 1
                        continue
                    
                    # Извлекаем цену
                    price = self._extract_price(row, columns['price'], df.columns)
                    if price <= 0:
                        skipped_rows += 1
                        continue
                    
                    # Извлекаем дополнительные данные
                    unit = self._extract_unit(row, columns['unit'])
                    category = self._extract_category(row, columns['category'])
                    
                    product = {
                        'original_name': product_name,
                        'price': price,
                        'unit': unit or 'pcs',
                        'category': category,
                        'row_index': idx,
                        'confidence': self._calculate_confidence(product_name, price, unit)
                    }
                    
                    products.append(product)
                    
                    # Ограничиваем количество товаров
                    if len(products) >= max_products:
                        logger.info(f"Достигнуто ограничение {max_products} товаров")
                        break
                        
                except Exception as e:
                    logger.debug(f"Ошибка обработки строки {idx}: {e}")
                    skipped_rows += 1
                    continue
            
            supplier_name = Path(file_path).stem
            
            result = {
                'file_type': 'excel',
                'supplier': {'name': supplier_name},
                'products': products,
                'extraction_stats': {
                    'total_rows': len(df),
                    'extracted_products': len(products),
                    'skipped_rows': skipped_rows,
                    'success_rate': len(products) / len(df) if len(df) > 0 else 0,
                    'used_sheet': best_sheet,
                    'found_columns': columns
                }
            }
            
            logger.info(f"Извлечено {len(products)} товаров из {len(df)} строк (успешность: {result['extraction_stats']['success_rate']:.1%})")
            
            # Детальная отладочная информация при низкой успешности
            if len(products) == 0 and len(df) > 0:
                logger.warning("🔍 ДЕТАЛЬНАЯ ДИАГНОСТИКА: товары не извлечены")
                logger.warning(f"Найденные столбцы: {columns}")
                logger.warning(f"Заголовки файла: {list(df.columns)}")
                logger.warning(f"Первые 3 строки данных:")
                for i, (idx, row) in enumerate(df.head(3).iterrows()):
                    logger.warning(f"Строка {idx}: {dict(row)}")
                    if i >= 2:
                        break
                        
                # Тестируем парсинг первых строк
                logger.warning("Тест парсинга первых строк:")
                for idx, row in df.head(5).iterrows():
                    name = self._extract_product_name(row, columns['product'])
                    price = self._extract_price(row, columns['price'], df.columns)
                    logger.warning(f"Строка {idx}: name='{name}', price={price}, valid={bool(name and price > 0)}")
            elif len(products) < len(df) * 0.1:  # Если успешность менее 10%
                logger.warning(f"⚠️ Низкая успешность извлечения: {len(products)}/{len(df)} ({result['extraction_stats']['success_rate']:.1%})")
                logger.warning(f"Найденные столбцы: {columns}")
                
            return result
            
        except Exception as e:
            logger.error(f"Ошибка извлечения данных из {file_path}: {e}")
            return {'error': str(e)}
    
    def _extract_product_name(self, row: pd.Series, product_col: str) -> Optional[str]:
        """Извлечение названия товара"""
        if not product_col:
            return None
        
        try:
            name = str(row[product_col]).strip()
            
            # Пропускаем очевидно невалидные значения
            if name.lower() in ['nan', 'none', '', 'null', 'undefined']:
                return None
            
            # Пропускаем слишком короткие названия
            if len(name) < 2:  # Уменьшили с 3 до 2
                return None
            
            # Пропускаем чистые числа, но разрешаем товары с номерами
            if name.replace('.', '').replace(',', '').replace(' ', '').isdigit():
                return None
            
            # Пропускаем заголовки и служебные строки
            skip_keywords = ['total', 'sum', 'итого', 'всего', 'header', 'title']
            if any(keyword in name.lower() for keyword in skip_keywords):
                return None
            
            return name
            
        except Exception:
            return None
    
    def _extract_price(self, row: pd.Series, price_col: Optional[str], all_columns: List[str]) -> float:
        """Извлечение цены с несколькими стратегиями"""
        # Стратегия 1: Используем найденный столбец цены
        if price_col:
            try:
                price_str = str(row[price_col])
                price = self._parse_price_string(price_str)
                if price > 0:
                    return price
            except Exception:
                pass
        
        # Стратегия 2: Ищем в других столбцах
        for col in all_columns:
            try:
                value_str = str(row[col])
                price = self._parse_price_string(value_str)
                if price > 0:
                    return price
            except Exception:
                continue
        
        return 0
    
    def _parse_price_string(self, price_str: str) -> float:
        """Улучшенный парсинг строки с ценой"""
        if not price_str or price_str.lower() in ['nan', 'none', '', 'null', 'undefined']:
            return 0
        
        # Конвертируем в строку если это число
        price_str = str(price_str).strip()
        
        # Проверяем, может это уже число
        try:
            direct_float = float(price_str)
            if 0 < direct_float < 10000000:
                return direct_float
        except ValueError:
            pass
        
        # Удаляем валютные символы и лишние пробелы
        clean_str = price_str.replace('$', '').replace('₽', '').replace('руб', '').replace('рub', '').replace(' ', '')
        
        # Удаляем все кроме цифр, точек и запятых
        clean_str = re.sub(r'[^\d.,]', '', clean_str)
        
        if not clean_str:
            return 0
        
        # Определяем разделители
        # Если есть и запятая, и точка, последняя - десятичный разделитель
        if ',' in clean_str and '.' in clean_str:
            last_comma = clean_str.rfind(',')
            last_dot = clean_str.rfind('.')
            
            if last_comma > last_dot:
                # Запятая последняя - она десятичный разделитель
                clean_str = clean_str.replace('.', '').replace(',', '.')
            else:
                # Точка последняя - она десятичный разделитель
                clean_str = clean_str.replace(',', '')
        elif ',' in clean_str:
            # Только запятая - может быть разделителем тысяч или десятичным
            parts = clean_str.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Вероятно десятичный разделитель
                clean_str = clean_str.replace(',', '.')
            else:
                # Вероятно разделитель тысяч
                clean_str = clean_str.replace(',', '')
        
        # Обрабатываем множественные точки (разделители тысяч)
        if clean_str.count('.') > 1:
            parts = clean_str.split('.')
            if len(parts[-1]) <= 2:  # Последняя часть - десятичная
                clean_str = ''.join(parts[:-1]) + '.' + parts[-1]
            else:
                clean_str = clean_str.replace('.', '')
        
        try:
            price = float(clean_str)
            # Расширенная проверка разумности цены
            if 0.01 <= price <= 50000000:  # От 1 копейки до 50 млн
                return price
        except ValueError:
            pass
        
        return 0
    
    def _extract_unit(self, row: pd.Series, unit_col: Optional[str]) -> Optional[str]:
        """Извлечение единицы измерения"""
        if not unit_col:
            return None
        
        try:
            unit = str(row[unit_col]).strip().lower()
            
            # Стандартизация единиц
            unit_mapping = {
                'шт': 'pcs', 'штука': 'pcs', 'штук': 'pcs', 'piece': 'pcs',
                'кг': 'kg', 'килограмм': 'kg', 'кило': 'kg',
                'л': 'l', 'литр': 'l', 'liter': 'l',
                'м': 'm', 'метр': 'm', 'meter': 'm',
                'коробка': 'box', 'упаковка': 'pack', 'пачка': 'pack',
                'пара': 'pair', 'комплект': 'set', 'набор': 'set'
            }
            
            return unit_mapping.get(unit, unit)
            
        except Exception:
            return None
    
    def _extract_category(self, row: pd.Series, category_col: Optional[str]) -> Optional[str]:
        """Извлечение категории"""
        if not category_col:
            return None
        
        try:
            category = str(row[category_col]).strip()
            if category.lower() not in ['nan', 'none', '', 'null']:
                return category
        except Exception:
            pass
        
        return None
    
    def _calculate_confidence(self, name: str, price: float, unit: Optional[str]) -> float:
        """Расчет уверенности в качестве извлеченных данных"""
        confidence = 0.5  # Базовая уверенность
        
        # Бонусы
        if name and len(name) > 5:
            confidence += 0.2
        
        if 1 <= price <= 100000:  # Разумная цена
            confidence += 0.2
        
        if unit and unit in ['pcs', 'kg', 'l', 'm', 'box', 'pack']:
            confidence += 0.1
        
        return min(confidence, 1.0)