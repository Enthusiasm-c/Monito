import os
import re
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

import pandas as pd
import pdfplumber
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import PyPDF2
import tabula
from openpyxl import load_workbook

from config import (
    PDF_CONFIG, 
    PDF_SETTINGS, 
    TESSERACT_CONFIG,
    QUALITY_THRESHOLDS
)
from modules.utils import (
    clean_text, 
    detect_language, 
    validate_price,
    extract_supplier_info
)

logger = logging.getLogger(__name__)

class FileProcessor:
    """Процессор для обработки Excel и PDF файлов"""
    
    def __init__(self):
        self.supported_extensions = ['.xlsx', '.xls', '.pdf']
        
    async def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Основной метод обработки файла
        Возвращает структурированные данные для передачи в GPT
        """
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if file_extension in ['.xlsx', '.xls']:
                return await self._process_excel(file_path)
            elif file_extension == '.pdf':
                return await self._process_pdf(file_path)
            else:
                raise ValueError(f"Неподдерживаемый формат файла: {file_extension}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки файла {file_path}: {e}")
            raise

    async def _process_excel(self, file_path: str) -> Dict[str, Any]:
        """Обработка Excel файлов"""
        logger.info(f"Начинаю обработку Excel файла: {file_path}")
        
        try:
            # Чтение всех листов
            excel_data = pd.read_excel(file_path, sheet_name=None, header=None)
            
            result = {
                'file_type': 'excel',
                'file_name': os.path.basename(file_path),
                'extraction_method': 'pandas',
                'sheets_processed': len(excel_data),
                'supplier': None,
                'products': [],
                'raw_data': {}
            }
            
            # Поиск поставщика в метаданных файла
            supplier_info = await self._extract_supplier_from_excel_metadata(file_path)
            result['supplier'] = supplier_info
            
            products = []
            
            # Обработка каждого листа
            for sheet_name, df in excel_data.items():
                logger.info(f"Обрабатываю лист: {sheet_name}")
                
                # Очистка данных
                df = self._clean_dataframe(df)
                
                # Поиск заголовков таблицы
                header_row = self._find_table_headers(df)
                
                if header_row is not None:
                    # Установка заголовков
                    df.columns = df.iloc[header_row]
                    df = df.iloc[header_row + 1:].reset_index(drop=True)
                    
                    # Извлечение продуктов
                    sheet_products = self._extract_products_from_dataframe(df, sheet_name)
                    products.extend(sheet_products)
                
                # Сохранение сырых данных для анализа
                result['raw_data'][sheet_name] = df.head(20).to_dict('records')
            
            result['products'] = products
            result['total_products'] = len(products)
            
            logger.info(f"Извлечено {len(products)} товаров из Excel файла")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка обработки Excel файла: {e}")
            raise

    async def _process_pdf(self, file_path: str) -> Dict[str, Any]:
        """Каскадная обработка PDF файлов"""
        logger.info(f"Начинаю обработку PDF файла: {file_path}")
        
        # Определение типа PDF
        pdf_type = await self._detect_pdf_type(file_path)
        logger.info(f"Определен тип PDF: {pdf_type}")
        
        # Каскадная обработка по методам
        extraction_methods = [
            ('pdfplumber', self._extract_with_pdfplumber),
            ('tabula', self._extract_with_tabula),
            ('ocr', self._extract_with_ocr),
            ('hybrid', self._extract_hybrid_approach)
        ]
        
        best_result = None
        best_confidence = 0
        
        for method_name, method_func in extraction_methods:
            try:
                logger.info(f"Пробую метод: {method_name}")
                
                result = await method_func(file_path)
                
                if result and self._validate_extraction_quality(result):
                    confidence = result.get('data_quality', {}).get('extraction_confidence', 0)
                    
                    if confidence > best_confidence:
                        best_result = result
                        best_confidence = confidence
                        result['extraction_method'] = method_name
                    
                    # Если достигнуто высокое качество, прекращаем попытки
                    if confidence > 0.8:
                        break
                        
            except Exception as e:
                logger.warning(f"Метод {method_name} не сработал: {e}")
                continue
        
        if not best_result:
            # Fallback - возвращаем базовую структуру
            best_result = {
                'file_type': 'pdf',
                'file_name': os.path.basename(file_path),
                'extraction_method': 'failed',
                'supplier': None,
                'products': [],
                'data_quality': {
                    'extraction_confidence': 0.1,
                    'source_clarity': 'low',
                    'potential_errors': ['Не удалось извлечь данные из PDF']
                }
            }
        
        logger.info(f"Лучший результат: {best_result.get('extraction_method')} с confidence {best_confidence}")
        return best_result

    async def _detect_pdf_type(self, file_path: str) -> str:
        """Определение типа PDF для выбора оптимального метода обработки"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                if len(pdf_reader.pages) == 0:
                    return 'empty'
                
                # Анализ первых страниц
                text_content = ""
                for i in range(min(3, len(pdf_reader.pages))):
                    page_text = pdf_reader.pages[i].extract_text()
                    text_content += page_text
                
                # Определение типа по содержимому
                if len(text_content.strip()) < 50:
                    return 'scanned'  # Сканированный документ
                elif 'price' in text_content.lower() or 'cost' in text_content.lower():
                    return 'text'     # Текстовый PDF с ценами
                elif len(re.findall(r'\d+', text_content)) > 20:
                    return 'table'    # Содержит много цифр, вероятно таблицы
                else:
                    return 'hybrid'   # Смешанный тип
                    
        except Exception as e:
            logger.warning(f"Ошибка определения типа PDF: {e}")
            return 'unknown'

    async def _extract_with_pdfplumber(self, file_path: str) -> Dict[str, Any]:
        """Извлечение данных через pdfplumber"""
        logger.info("Извлечение данных через pdfplumber")
        
        products = []
        supplier_info = None
        total_pages = 0
        
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            
            # Ограничиваем количество обрабатываемых страниц
            max_pages = min(total_pages, PDF_SETTINGS['max_pages'])
            
            for page_num, page in enumerate(pdf.pages[:max_pages]):
                try:
                    # Извлечение текста
                    page_text = page.extract_text()
                    
                    if page_num == 0 and not supplier_info:
                        # Поиск информации о поставщике на первой странице
                        supplier_info = extract_supplier_info(page_text)
                    
                    # Поиск таблиц на странице
                    tables = page.extract_tables()
                    
                    for table in tables:
                        if table and len(table) > 1:
                            # Преобразование таблицы в DataFrame
                            df = pd.DataFrame(table[1:], columns=table[0])
                            page_products = self._extract_products_from_dataframe(df, f"page_{page_num + 1}")
                            products.extend(page_products)
                            
                except Exception as e:
                    logger.warning(f"Ошибка обработки страницы {page_num + 1}: {e}")
                    continue
        
        confidence = 0.8 if products else 0.3
        
        return {
            'file_type': 'pdf',
            'file_name': os.path.basename(file_path),
            'supplier': supplier_info,
            'products': products,
            'pages_processed': max_pages,
            'total_pages': total_pages,
            'data_quality': {
                'extraction_confidence': confidence,
                'source_clarity': 'high' if confidence > 0.7 else 'medium',
                'potential_errors': []
            }
        }

    async def _extract_with_tabula(self, file_path: str) -> Dict[str, Any]:
        """Извлечение таблиц через tabula-py"""
        logger.info("Извлечение данных через tabula-py")
        
        try:
            # Извлечение всех таблиц из PDF
            tables = tabula.read_pdf(
                file_path, 
                pages='all',
                multiple_tables=True,
                pandas_options={'header': 0}
            )
            
            products = []
            
            for i, df in enumerate(tables):
                if not df.empty:
                    # Очистка DataFrame
                    df = self._clean_dataframe(df)
                    table_products = self._extract_products_from_dataframe(df, f"table_{i + 1}")
                    products.extend(table_products)
            
            # Попытка извлечь информацию о поставщике из первой страницы
            supplier_info = None
            try:
                first_page_tables = tabula.read_pdf(file_path, pages=1)
                if first_page_tables:
                    # Поиск поставщика в первой таблице
                    first_table_text = ' '.join(first_page_tables[0].astype(str).values.flatten())
                    supplier_info = extract_supplier_info(first_table_text)
            except:
                pass
            
            confidence = 0.75 if products else 0.2
            
            return {
                'file_type': 'pdf',
                'file_name': os.path.basename(file_path),
                'supplier': supplier_info,
                'products': products,
                'tables_found': len(tables),
                'data_quality': {
                    'extraction_confidence': confidence,
                    'source_clarity': 'medium',
                    'potential_errors': []
                }
            }
            
        except Exception as e:
            logger.warning(f"Ошибка tabula extraction: {e}")
            raise

    async def _extract_with_ocr(self, file_path: str) -> Dict[str, Any]:
        """Извлечение данных через OCR (Tesseract)"""
        logger.info("Извлечение данных через OCR")
        
        try:
            # Конвертация PDF в изображения
            images = convert_from_path(
                file_path,
                dpi=PDF_SETTINGS['dpi'],
                first_page=1,
                last_page=min(PDF_SETTINGS['max_pages'], 20)  # Ограничиваем для OCR
            )
            
            all_text = ""
            products = []
            supplier_info = None
            
            for page_num, image in enumerate(images):
                try:
                    # Предобработка изображения для лучшего OCR
                    processed_image = self._preprocess_image_for_ocr(image)
                    
                    # OCR
                    page_text = pytesseract.image_to_string(
                        processed_image,
                        lang=TESSERACT_CONFIG['lang'],
                        config=TESSERACT_CONFIG['config'],
                        timeout=TESSERACT_CONFIG['timeout']
                    )
                    
                    # Очистка текста от OCR артефактов
                    page_text = self._clean_ocr_text(page_text)
                    all_text += page_text + "\n"
                    
                    # Поиск поставщика на первой странице
                    if page_num == 0:
                        supplier_info = extract_supplier_info(page_text)
                    
                    # Попытка извлечь структурированные данные
                    page_products = self._extract_products_from_text(page_text, f"ocr_page_{page_num + 1}")
                    products.extend(page_products)
                    
                except Exception as e:
                    logger.warning(f"Ошибка OCR страницы {page_num + 1}: {e}")
                    continue
            
            # Оценка качества OCR
            confidence = self._estimate_ocr_confidence(all_text, products)
            
            return {
                'file_type': 'pdf',
                'file_name': os.path.basename(file_path),
                'supplier': supplier_info,
                'products': products,
                'pages_processed': len(images),
                'raw_ocr_text': all_text[:1000],  # Первые 1000 символов для отладки
                'data_quality': {
                    'extraction_confidence': confidence,
                    'source_clarity': 'low' if confidence < 0.6 else 'medium',
                    'potential_errors': self._detect_ocr_errors(all_text)
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка OCR extraction: {e}")
            raise

    async def _extract_hybrid_approach(self, file_path: str) -> Dict[str, Any]:
        """Гибридный подход - комбинирование разных методов"""
        logger.info("Применение гибридного подхода")
        
        try:
            # Сначала пробуем pdfplumber для структурированных данных
            pdfplumber_result = None
            try:
                pdfplumber_result = await self._extract_with_pdfplumber(file_path)
            except:
                pass
            
            # Затем tabula для таблиц
            tabula_result = None
            try:
                tabula_result = await self._extract_with_tabula(file_path)
            except:
                pass
            
            # OCR как fallback
            ocr_result = None
            try:
                ocr_result = await self._extract_with_ocr(file_path)
            except:
                pass
            
            # Объединение результатов
            best_result = self._merge_extraction_results([
                pdfplumber_result,
                tabula_result,
                ocr_result
            ])
            
            if best_result:
                best_result['extraction_method'] = 'hybrid'
                return best_result
            else:
                raise Exception("Все методы извлечения не дали результата")
                
        except Exception as e:
            logger.error(f"Ошибка hybrid extraction: {e}")
            raise

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Очистка DataFrame от пустых строк и столбцов"""
        # Удаление полностью пустых строк и столбцов
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Заполнение NaN пустыми строками для текстовых столбцов
        df = df.fillna('')
        
        # Преобразование в строки для однородности
        df = df.astype(str)
        
        return df

    def _find_table_headers(self, df: pd.DataFrame) -> Optional[int]:
        """Поиск строки с заголовками таблицы"""
        header_keywords = [
            'product', 'название', 'товар', 'item', 'description',
            'price', 'цена', 'cost', 'amount', 'стоимость',
            'unit', 'единица', 'мера', 'quantity', 'количество'
        ]
        
        for i, row in df.iterrows():
            row_text = ' '.join(row.astype(str)).lower()
            
            # Подсчет совпадений с ключевыми словами
            matches = sum(1 for keyword in header_keywords if keyword in row_text)
            
            if matches >= 2:  # Минимум 2 совпадения для признания заголовком
                return i
        
        return None

    def _extract_products_from_dataframe(self, df: pd.DataFrame, source: str) -> List[Dict]:
        """Извлечение товаров из DataFrame"""
        products = []
        
        # Определение столбцов
        product_col = self._find_column_by_keywords(df, ['product', 'название', 'товар', 'item', 'description'])
        price_col = self._find_column_by_keywords(df, ['price', 'цена', 'cost', 'amount', 'стоимость'])
        unit_col = self._find_column_by_keywords(df, ['unit', 'единица', 'мера', 'quantity'])
        
        for idx, row in df.iterrows():
            try:
                # Извлечение названия товара
                product_name = ""
                if product_col is not None:
                    product_name = str(row.iloc[product_col]).strip()
                else:
                    # Ищем в первом столбце
                    product_name = str(row.iloc[0]).strip() if len(row) > 0 else ""
                
                # Пропускаем пустые или слишком короткие названия
                if len(product_name) < QUALITY_THRESHOLDS['MIN_PRODUCT_NAME_LENGTH']:
                    continue
                
                # Извлечение цены
                price = None
                if price_col is not None:
                    price_text = str(row.iloc[price_col])
                    price = self._extract_price_from_text(price_text)
                else:
                    # Ищем цену во всех столбцах
                    for col_val in row:
                        potential_price = self._extract_price_from_text(str(col_val))
                        if potential_price is not None:
                            price = potential_price
                            break
                
                # Извлечение единицы измерения
                unit = ""
                if unit_col is not None:
                    unit = str(row.iloc[unit_col]).strip()
                
                # Создание записи о товаре
                if product_name and price is not None:
                    product = {
                        'original_name': product_name,
                        'price': price,
                        'unit': unit or 'pcs',
                        'source': source,
                        'row_index': idx,
                        'confidence': 0.8  # Базовая уверенность для структурированных данных
                    }
                    
                    products.append(product)
                    
            except Exception as e:
                logger.warning(f"Ошибка обработки строки {idx}: {e}")
                continue
        
        return products

    def _find_column_by_keywords(self, df: pd.DataFrame, keywords: List[str]) -> Optional[int]:
        """Поиск столбца по ключевым словам"""
        if df.empty:
            return None
            
        for col_idx, col_name in enumerate(df.columns):
            col_name_lower = str(col_name).lower()
            for keyword in keywords:
                if keyword in col_name_lower:
                    return col_idx
        
        return None

    def _extract_price_from_text(self, text: str) -> Optional[float]:
        """Извлечение цены из текста"""
        if not text or pd.isna(text):
            return None
        
        # Удаление валютных символов и лишних пробелов
        cleaned_text = re.sub(r'[^\d.,\-]', '', str(text))
        
        # Поиск числовых значений
        price_patterns = [
            r'(\d+[.,]\d{2})',  # 123.45 или 123,45
            r'(\d+[.,]\d{1})',  # 123.4 или 123,4
            r'(\d+)',           # 123
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, cleaned_text)
            if match:
                try:
                    # Замена запятой на точку для float
                    price_str = match.group(1).replace(',', '.')
                    price = float(price_str)
                    
                    # Валидация цены
                    if validate_price(price):
                        return price
                except (ValueError, TypeError):
                    continue
        
        return None

    def _extract_products_from_text(self, text: str, source: str) -> List[Dict]:
        """Извлечение товаров из неструктурированного текста (OCR)"""
        products = []
        
        # Разделение текста на строки
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            
            # Пропускаем короткие строки
            if len(line) < 10:
                continue
            
            # Поиск цены в строке
            price = self._extract_price_from_text(line)
            
            if price is not None:
                # Извлечение названия товара (часть строки до цены)
                price_match = re.search(r'[\d.,]+', line)
                if price_match:
                    product_name = line[:price_match.start()].strip()
                    
                    if len(product_name) >= QUALITY_THRESHOLDS['MIN_PRODUCT_NAME_LENGTH']:
                        # Очистка названия от OCR артефактов
                        product_name = self._clean_product_name(product_name)
                        
                        product = {
                            'original_name': product_name,
                            'price': price,
                            'unit': 'pcs',  # По умолчанию
                            'source': source,
                            'line_number': line_num,
                            'confidence': 0.6  # Низкая уверенность для OCR данных
                        }
                        
                        products.append(product)
        
        return products

    def _clean_product_name(self, name: str) -> str:
        """Очистка названия товара от OCR артефактов"""
        # Удаление лишних пробелов
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Удаление странных символов
        name = re.sub(r'[^\w\s\-.,()]', '', name)
        
        # Исправление типичных OCR ошибок
        ocr_fixes = {
            '0': 'O', '1': 'I', '5': 'S', '6': 'G',
            'rn': 'm', 'vv': 'w', 'nn': 'n'
        }
        
        for wrong, correct in ocr_fixes.items():
            name = name.replace(wrong, correct)
        
        return name

    def _preprocess_image_for_ocr(self, image: Image) -> Image:
        """Предобработка изображения для улучшения качества OCR"""
        # Конвертация в оттенки серого
        if image.mode != 'L':
            image = image.convert('L')
        
        # Увеличение контрастности
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Повышение резкости
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.5)
        
        return image

    def _clean_ocr_text(self, text: str) -> str:
        """Очистка текста от OCR артефактов"""
        # Удаление лишних пробелов и переносов
        text = re.sub(r'\s+', ' ', text)
        
        # Исправление разорванных слов
        text = re.sub(r'(\w)\s+(\w)', r'\1\2', text)
        
        # Удаление строк со слишком большим количеством спецсимволов
        lines = text.split('\n')
        clean_lines = []
        
        for line in lines:
            # Подсчет букв и цифр vs спецсимволов
            alphanumeric = len(re.findall(r'[a-zA-Z0-9а-яА-Я]', line))
            special = len(re.findall(r'[^\w\s]', line))
            
            if alphanumeric > special:
                clean_lines.append(line)
        
        return '\n'.join(clean_lines)

    def _estimate_ocr_confidence(self, text: str, products: List[Dict]) -> float:
        """Оценка качества OCR на основе извлеченных данных"""
        if not text or not products:
            return 0.1
        
        # Факторы для оценки качества
        factors = []
        
        # 1. Наличие читаемых слов
        words = re.findall(r'\b[a-zA-Zа-яА-Я]{3,}\b', text)
        factors.append(min(len(words) / 50, 1.0))  # Нормализация к 1.0
        
        # 2. Количество извлеченных товаров
        factors.append(min(len(products) / 20, 1.0))
        
        # 3. Качество цен (отсутствие аномальных значений)
        valid_prices = sum(1 for p in products if 0.01 <= p['price'] <= 10000)
        if products:
            factors.append(valid_prices / len(products))
        
        # 4. Отсутствие слишком коротких "названий"
        valid_names = sum(1 for p in products if len(p['original_name']) >= 5)
        if products:
            factors.append(valid_names / len(products))
        
        # Среднее арифметическое факторов
        return sum(factors) / len(factors) if factors else 0.1

    def _detect_ocr_errors(self, text: str) -> List[str]:
        """Детекция типичных ошибок OCR"""
        errors = []
        
        # Проверка на слишком много спецсимволов
        special_chars = len(re.findall(r'[^\w\s]', text))
        total_chars = len(text)
        if total_chars > 0 and special_chars / total_chars > 0.3:
            errors.append("Высокий процент спецсимволов - возможны ошибки OCR")
        
        # Проверка на разорванные слова
        broken_words = len(re.findall(r'\b\w{1,2}\b', text))
        if broken_words > 20:
            errors.append("Обнаружены разорванные слова")
        
        # Проверка на нечитаемые последовательности
        unreadable = len(re.findall(r'[^\w\s]{3,}', text))
        if unreadable > 10:
            errors.append("Нечитаемые последовательности символов")
        
        return errors

    def _validate_extraction_quality(self, result: Dict[str, Any]) -> bool:
        """Валидация качества извлеченных данных"""
        if not result:
            return False
        
        # Проверка наличия товаров
        products = result.get('products', [])
        if not products:
            return False
        
        # Проверка качества товаров
        valid_products = 0
        for product in products:
            if (product.get('original_name') and 
                len(product['original_name']) >= QUALITY_THRESHOLDS['MIN_PRODUCT_NAME_LENGTH'] and
                product.get('price') is not None and
                validate_price(product['price'])):
                valid_products += 1
        
        # Минимум 30% товаров должны быть валидными
        return valid_products / len(products) >= 0.3

    def _merge_extraction_results(self, results: List[Optional[Dict]]) -> Optional[Dict]:
        """Объединение результатов разных методов извлечения"""
        valid_results = [r for r in results if r and self._validate_extraction_quality(r)]
        
        if not valid_results:
            return None
        
        # Выбираем результат с наибольшим количеством товаров и уверенностью
        best_result = max(valid_results, key=lambda r: (
            len(r.get('products', [])) * 
            r.get('data_quality', {}).get('extraction_confidence', 0)
        ))
        
        # Дополняем информацией о поставщике из других результатов
        if not best_result.get('supplier'):
            for result in valid_results:
                if result.get('supplier'):
                    best_result['supplier'] = result['supplier']
                    break
        
        return best_result

    async def _extract_supplier_from_excel_metadata(self, file_path: str) -> Optional[Dict]:
        """Извлечение информации о поставщике из метаданных Excel"""
        try:
            workbook = load_workbook(file_path, read_only=True)
            
            # Проверка свойств файла
            props = workbook.properties
            
            supplier_info = {}
            
            if props.creator:
                supplier_info['name'] = props.creator
            
            if props.company:
                supplier_info['company'] = props.company
            
            if props.description:
                supplier_info['description'] = props.description
            
            return supplier_info if supplier_info else None
            
        except Exception as e:
            logger.warning(f"Ошибка извлечения метаданных Excel: {e}")
            return None