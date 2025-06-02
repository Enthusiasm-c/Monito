#!/usr/bin/env python3
"""
Google Sheets Manager V2 - Оптимизированная версия для MON-005
Основные улучшения:
- batchUpdate API вместо множественных обновлений
- Минимальное количество API вызовов  
- Batch операции для всех данных сразу
- 10x ускорение записи данных
"""

import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

@dataclass
class SheetsStats:
    """Статистика работы с таблицей"""
    new_products: int = 0
    updated_prices: int = 0
    total_rows_written: int = 0
    api_calls_made: int = 0
    processing_time_ms: int = 0

class GoogleSheetsManagerV2:
    """
    Оптимизированный менеджер Google Sheets с batch API
    MON-005: Переход с append_row на spreadsheets.values.batchUpdate
    
    Ожидаемые улучшения:
    - Время записи: 30-60 сек → 3-5 сек (10x быстрее)
    - API вызовы: N товаров → 2-3 вызова максимум
    - Пропускная способность: 5x увеличение
    """
    
    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv()
        
        self.service = None
        self.sheet_id = os.getenv('GOOGLE_SHEET_ID')
        self.credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'google_credentials.json')
        self.stats = SheetsStats()
        self._initialize()
    
    def _initialize(self) -> bool:
        """Инициализация Google Sheets API v4"""
        try:
            if not os.path.exists(self.credentials_file):
                logger.error(f"❌ Файл учетных данных не найден: {self.credentials_file}")
                return False
            
            if not self.sheet_id:
                logger.error("❌ GOOGLE_SHEET_ID не установлен в переменных окружения")
                return False
            
            # Создание credentials
            credentials = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            # Инициализация Google Sheets API v4
            self.service = build('sheets', 'v4', credentials=credentials)
            
            # Тест подключения
            sheet_info = self.service.spreadsheets().get(
                spreadsheetId=self.sheet_id
            ).execute()
            
            logger.info(f"✅ Google Sheets API v4 инициализирован: {sheet_info.get('properties', {}).get('title', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Google Sheets API: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Проверка подключения"""
        return self.service is not None
    
    def _get_sheet_data(self, sheet_name: str, range_name: str = None) -> List[List[str]]:
        """Быстрое чтение данных из листа"""
        try:
            if not range_name:
                range_name = f"{sheet_name}!A:Z"  # Читаем до столбца Z
            
            start_time = time.time()
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=range_name,
                valueRenderOption='UNFORMATTED_VALUE'
            ).execute()
            
            self.stats.api_calls_made += 1
            self.stats.processing_time_ms += int((time.time() - start_time) * 1000)
            
            return result.get('values', [])
            
        except HttpError as e:
            if e.resp.status == 400 and 'not found' in str(e):
                logger.info(f"📋 Лист '{sheet_name}' не существует, будет создан")
                return []
            logger.error(f"❌ Ошибка чтения данных из {sheet_name}: {e}")
            return []
    
    def _create_sheet_if_not_exists(self, sheet_name: str) -> bool:
        """Создание листа если не существует"""
        try:
            # Проверяем существование листа
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=self.sheet_id
            ).execute()
            
            existing_sheets = [sheet['properties']['title'] 
                             for sheet in sheet_metadata.get('sheets', [])]
            
            if sheet_name in existing_sheets:
                logger.debug(f"📋 Лист '{sheet_name}' уже существует")
                return True
            
            # Создаем новый лист
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name,
                            'gridProperties': {
                                'rowCount': 1000,
                                'columnCount': 26
                            }
                        }
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.sheet_id,
                body=request_body
            ).execute()
            
            self.stats.api_calls_made += 1
            logger.info(f"✅ Создан новый лист: {sheet_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания листа {sheet_name}: {e}")
            return False
    
    def _prepare_master_table_headers(self) -> List[str]:
        """Подготовка заголовков основной таблицы"""
        return [
            'Product Name (EN)',
            'Brand', 
            'Size',
            'Unit',
            'Currency',
            'Category',
            'First Added',
            'Last Updated'
        ]
    
    def _add_supplier_columns_to_headers(self, headers: List[str], supplier_name: str) -> List[str]:
        """Добавление столбцов поставщика к заголовкам"""
        price_col = f"{supplier_name}_Price"
        date_col = f"{supplier_name}_Updated"
        
        if price_col not in headers:
            headers.extend([price_col, date_col])
            logger.info(f"➕ Добавлены столбцы для поставщика: {supplier_name}")
        
        return headers
    
    def _clean_supplier_name(self, name: str) -> str:
        """Очистка имени поставщика"""
        import re
        clean_name = re.sub(r'[^\w\s\-]', '', str(name))
        clean_name = re.sub(r'\s+', '_', clean_name)
        return clean_name[:30].strip('_') or 'Unknown_Supplier'
    
    def _build_product_matrix(self, 
                            existing_data: List[List[str]], 
                            headers: List[str],
                            products: List[Dict[str, Any]], 
                            supplier_name: str) -> Tuple[List[List[str]], SheetsStats]:
        """
        Построение матрицы данных для batch обновления
        Самая важная функция для производительности!
        """
        start_time = time.time()
        stats = SheetsStats()
        
        # Индексы важных столбцов
        try:
            product_name_idx = headers.index('Product Name (EN)')
            price_col_idx = headers.index(f"{supplier_name}_Price")
            date_col_idx = headers.index(f"{supplier_name}_Updated")
            last_updated_idx = headers.index('Last Updated')
        except ValueError as e:
            logger.error(f"❌ Не найден обязательный столбец: {e}")
            return existing_data, stats
        
        # Создаем словарь существующих товаров для быстрого поиска
        existing_products = {}
        for row_idx, row in enumerate(existing_data[1:], start=1):  # Пропускаем заголовки
            if len(row) > product_name_idx and row[product_name_idx]:
                product_key = row[product_name_idx].lower().strip()
                existing_products[product_key] = row_idx
        
        # Подготавливаем матрицу данных
        data_matrix = [row[:] for row in existing_data]  # Копируем существующие данные
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Обрабатываем каждый товар
        for product in products:
            product_name = product.get('standardized_name', '').strip()
            price = product.get('price', 0)
            
            if not product_name or price <= 0:
                continue
            
            product_key = product_name.lower()
            
            if product_key in existing_products:
                # Обновляем существующий товар
                row_idx = existing_products[product_key]
                
                # Убеждаемся что строка достаточно длинная
                while len(data_matrix[row_idx]) <= max(price_col_idx, date_col_idx, last_updated_idx):
                    data_matrix[row_idx].append('')
                
                data_matrix[row_idx][price_col_idx] = price
                data_matrix[row_idx][date_col_idx] = current_date
                data_matrix[row_idx][last_updated_idx] = current_date
                
                stats.updated_prices += 1
            else:
                # Добавляем новый товар
                new_row = [''] * len(headers)
                new_row[product_name_idx] = product_name
                new_row[1] = product.get('brand', 'unknown')  # Brand
                new_row[2] = product.get('size', 'unknown')   # Size
                new_row[3] = product.get('unit', 'pcs')       # Unit
                new_row[4] = product.get('currency', 'USD')   # Currency
                new_row[5] = product.get('category', 'general') # Category
                new_row[6] = current_date                     # First Added
                new_row[7] = current_date                     # Last Updated
                new_row[price_col_idx] = price
                new_row[date_col_idx] = current_date
                
                data_matrix.append(new_row)
                stats.new_products += 1
        
        stats.processing_time_ms = int((time.time() - start_time) * 1000)
        stats.total_rows_written = len(data_matrix)
        
        logger.info(f"📊 Матрица подготовлена за {stats.processing_time_ms}ms: "
                   f"{stats.new_products} новых, {stats.updated_prices} обновлений")
        
        return data_matrix, stats
    
    def update_master_table_batch(self, standardized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        ⚡ ОСНОВНАЯ ФУНКЦИЯ MON-005: Batch обновление основной таблицы
        
        Заменяет медленный update_master_table на быстрый batch API
        Ожидаемое ускорение: 10x (30-60 сек → 3-5 сек)
        """
        start_time = time.time()
        
        try:
            logger.info(f"🚀 MON-005: Начинаем BATCH сохранение в Google Sheets...")
            
            if not self.is_connected():
                return {'error': 'Нет подключения к Google Sheets API'}
            
            supplier = standardized_data.get('supplier', {})
            products = standardized_data.get('products', [])
            supplier_name = self._clean_supplier_name(supplier.get('name', 'Unknown_Supplier'))
            
            if not products:
                return {'error': 'Нет товаров для добавления'}
            
            logger.info(f"📦 Получено товаров: {len(products)}")
            logger.info(f"🏪 Поставщик: {supplier_name}")
            
            # Шаг 1: Создаем лист если не существует
            sheet_name = "Master Table"
            if not self._create_sheet_if_not_exists(sheet_name):
                return {'error': f'Не удалось создать лист {sheet_name}'}
            
            # Шаг 2: Читаем существующие данные (1 API вызов)
            logger.info(f"📖 Читаем существующие данные...")
            existing_data = self._get_sheet_data(sheet_name)
            
            # Шаг 3: Подготавливаем заголовки
            if not existing_data:
                # Первый запуск - создаем заголовки
                headers = self._prepare_master_table_headers()
                existing_data = [headers]
                logger.info(f"📋 Создаем новые заголовки: {len(headers)} столбцов")
            else:
                headers = existing_data[0][:]  # Копируем заголовки
            
            # Добавляем столбцы поставщика если нужно
            original_header_count = len(headers)
            headers = self._add_supplier_columns_to_headers(headers, supplier_name)
            headers_changed = len(headers) != original_header_count
            
            # Шаг 4: Строим матрицу данных (в памяти)
            logger.info(f"🔧 Подготавливаем матрицу данных...")
            data_matrix, batch_stats = self._build_product_matrix(
                existing_data, headers, products, supplier_name
            )
            
            # Обновляем общую статистику
            self.stats.new_products += batch_stats.new_products
            self.stats.updated_prices += batch_stats.updated_prices
            
            # Шаг 5: Отправляем ВСЕ данные одним batch запросом
            logger.info(f"⚡ Отправляем BATCH обновление: {len(data_matrix)} строк...")
            
            # Определяем диапазон для записи
            end_column = chr(ord('A') + len(headers) - 1)  # A, B, C... до нужного столбца
            range_name = f"{sheet_name}!A1:{end_column}{len(data_matrix)}"
            
            batch_update_request = {
                'valueInputOption': 'RAW',
                'data': [{
                    'range': range_name,
                    'values': data_matrix
                }]
            }
            
            batch_start = time.time()
            self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.sheet_id,
                body=batch_update_request
            ).execute()
            
            batch_time = time.time() - batch_start
            self.stats.api_calls_made += 1
            
            # Шаг 6: Форматирование заголовков (опционально)
            if headers_changed:
                self._format_headers(sheet_name, headers)
            
            # Создаем лист поставщика
            self._create_supplier_sheet_batch(supplier_name, products)
            
            total_time = time.time() - start_time
            
            result = {
                'status': 'success',
                'new_products': batch_stats.new_products,
                'updated_prices': batch_stats.updated_prices,
                'processed_products': batch_stats.new_products + batch_stats.updated_prices,
                'total_rows': len(data_matrix),
                'processing_time_sec': round(total_time, 2),
                'batch_write_time_sec': round(batch_time, 2),
                'api_calls_made': self.stats.api_calls_made,
                'supplier': supplier_name,
                'sheet_url': f"https://docs.google.com/spreadsheets/d/{self.sheet_id}"
            }
            
            logger.info(f"✅ MON-005 COMPLETED: {batch_stats.new_products} новых, "
                       f"{batch_stats.updated_prices} обновлений за {total_time:.1f}с "
                       f"({self.stats.api_calls_made} API вызовов)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка batch обновления: {e}")
            return {'error': str(e)}
    
    def _format_headers(self, sheet_name: str, headers: List[str]) -> None:
        """Форматирование заголовков таблицы"""
        try:
            # Получаем sheet ID
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=self.sheet_id
            ).execute()
            
            sheet_id = None
            for sheet in sheet_metadata.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                return
            
            # Форматируем заголовки
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': len(headers)
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 1.0},
                            'textFormat': {
                                'bold': True,
                                'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            }]
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.sheet_id,
                body={'requests': requests}
            ).execute()
            
            self.stats.api_calls_made += 1
            logger.debug(f"✨ Заголовки отформатированы для {sheet_name}")
            
        except Exception as e:
            logger.warning(f"⚠️ Не удалось отформатировать заголовки: {e}")
    
    def _create_supplier_sheet_batch(self, supplier_name: str, products: List[Dict]) -> bool:
        """Создание листа поставщика с batch API"""
        try:
            sheet_name = f"Supplier_{supplier_name}"
            
            if not self._create_sheet_if_not_exists(sheet_name):
                return False
            
            # Подготовка данных
            headers = [
                'Original Name', 'Standardized Name', 'Brand', 'Size', 
                'Price', 'Currency', 'Unit', 'Category', 'Confidence', 'Added Date'
            ]
            
            data_matrix = [headers]
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for product in products:
                row = [
                    product.get('original_name', ''),
                    product.get('standardized_name', ''),
                    product.get('brand', 'unknown'),
                    product.get('size', 'unknown'),
                    product.get('price', 0),
                    product.get('currency', 'USD'),
                    product.get('unit', 'pcs'),
                    product.get('category', 'general'),
                    product.get('confidence', 0),
                    current_date
                ]
                data_matrix.append(row)
            
            # Batch запись
            range_name = f"{sheet_name}!A1:J{len(data_matrix)}"
            
            self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.sheet_id,
                body={
                    'valueInputOption': 'RAW',
                    'data': [{
                        'range': range_name,
                        'values': data_matrix
                    }]
                }
            ).execute()
            
            self.stats.api_calls_made += 1
            logger.info(f"✅ Создан лист поставщика: {sheet_name} ({len(products)} товаров)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания листа поставщика: {e}")
            return False
    
    def create_stats_sheet(self, processing_stats: Dict[str, Any]) -> bool:
        """
        MON-005.2: Создание листа со статистикой
        Добавляет Sheet «Stats» с метриками обработки
        """
        try:
            sheet_name = "Stats"
            
            if not self._create_sheet_if_not_exists(sheet_name):
                return False
            
            # Подготовка статистики
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            headers = [
                'Timestamp', 'Supplier', 'Total Rows', 'New Products', 'Updated Products',
                'Processing Time (sec)', 'Parse Time (sec)', 'API Calls', 'Tokens Used'
            ]
            
            stats_row = [
                current_time,
                processing_stats.get('supplier', 'Unknown'),
                processing_stats.get('total_rows', 0),
                processing_stats.get('new_products', 0), 
                processing_stats.get('updated_prices', 0),
                processing_stats.get('processing_time_sec', 0),
                processing_stats.get('parse_time_sec', 0),
                processing_stats.get('api_calls_made', 0),
                processing_stats.get('tokens_used', 0)
            ]
            
            # Читаем существующие данные
            existing_data = self._get_sheet_data(sheet_name)
            
            if not existing_data:
                # Первый запуск - создаем заголовки
                data_matrix = [headers, stats_row]
            else:
                # Добавляем новую строку
                data_matrix = existing_data[:]
                data_matrix.append(stats_row)
            
            # Batch обновление
            range_name = f"{sheet_name}!A1:I{len(data_matrix)}"
            
            self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.sheet_id,
                body={
                    'valueInputOption': 'RAW',
                    'data': [{
                        'range': range_name,
                        'values': data_matrix
                    }]
                }
            ).execute()
            
            self.stats.api_calls_made += 1
            logger.info(f"📊 Статистика записана в лист Stats")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания листа статистики: {e}")
            return False
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Отчет о производительности MON-005"""
        return {
            'api_calls_made': self.stats.api_calls_made,
            'processing_time_ms': self.stats.processing_time_ms,
            'new_products': self.stats.new_products,
            'updated_prices': self.stats.updated_prices,
            'total_rows_written': self.stats.total_rows_written,
            'avg_time_per_row_ms': (
                self.stats.processing_time_ms / max(self.stats.total_rows_written, 1)
            )
        }


# Backward compatibility wrapper
class GoogleSheetsManager(GoogleSheetsManagerV2):
    """
    Обратная совместимость со старым API
    Перенаправляет старые вызовы на новые batch методы
    """
    
    def update_master_table(self, standardized_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compatibility wrapper для старого API"""
        logger.info("🔄 Перенаправляем на оптимизированный batch API...")
        return self.update_master_table_batch(standardized_data) 