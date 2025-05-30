import os
import json
import logging
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from fuzzywuzzy import fuzz

from config import (
    MASTER_TABLE_PATH, 
    QUALITY_THRESHOLDS, 
    BACKUP_CONFIG,
    PROCESSING_METRICS
)
from modules.utils import calculate_similarity, backup_file

logger = logging.getLogger(__name__)

class DataManager:
    """Менеджер для управления основной таблицей и данными"""
    
    def __init__(self):
        self.master_table_path = MASTER_TABLE_PATH
        self.stats_file = "data/processing_stats.json"
        self._ensure_data_directory()
        
    def _ensure_data_directory(self):
        """Создание директории для данных если не существует"""
        os.makedirs(os.path.dirname(self.master_table_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)

    async def update_master_table(self, standardized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обновление основной таблицы новыми данными
        Возвращает статистику изменений
        """
        try:
            logger.info("Начинаю обновление основной таблицы")
            
            # Загрузка существующей таблицы или создание новой
            master_df = self._load_or_create_master_table()
            
            # Извлечение данных поставщика и товаров
            supplier = standardized_data.get('supplier', {})
            products = standardized_data.get('products', [])
            
            if not products:
                logger.warning("Нет товаров для добавления в таблицу")
                return {'new_products': 0, 'updated_prices': 0, 'new_supplier': False}
            
            # Подготовка имени поставщика
            supplier_name = self._prepare_supplier_name(supplier)
            
            # Проверка на новый поставщик
            is_new_supplier = self._is_new_supplier(master_df, supplier_name)
            
            if is_new_supplier:
                logger.info(f"Добавление нового поставщика: {supplier_name}")
                master_df = self._add_new_supplier_columns(master_df, supplier_name)
            
            # Обработка товаров
            stats = {
                'new_products': 0,
                'updated_prices': 0,
                'new_supplier': is_new_supplier,
                'total_products': len(products),
                'processed_products': 0
            }
            
            for product in products:
                try:
                    result = self._process_product(master_df, product, supplier_name)
                    
                    if result['action'] == 'new_product':
                        stats['new_products'] += 1
                    elif result['action'] == 'updated_price':
                        stats['updated_prices'] += 1
                    
                    stats['processed_products'] += 1
                    
                except Exception as e:
                    logger.warning(f"Ошибка обработки товара {product.get('standardized_name', 'unknown')}: {e}")
                    continue
            
            # Сохранение обновленной таблицы
            self._save_master_table(master_df)
            
            # Обновление статистики
            await self._update_processing_stats(stats, standardized_data)
            
            # Создание бэкапа если включено
            if BACKUP_CONFIG.get('enabled', False):
                await self._create_backup()
            
            logger.info(f"Таблица обновлена: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка обновления основной таблицы: {e}")
            raise

    def _load_or_create_master_table(self) -> pd.DataFrame:
        """Загрузка существующей таблицы или создание новой"""
        try:
            if os.path.exists(self.master_table_path):
                logger.info("Загружаю существующую основную таблицу")
                df = pd.read_excel(self.master_table_path, index_col=0)
                
                # Валидация структуры таблицы
                if not self._validate_master_table_structure(df):
                    logger.warning("Структура таблицы нарушена, создаю новую")
                    return self._create_empty_master_table()
                
                return df
            else:
                logger.info("Создаю новую основную таблицу")
                return self._create_empty_master_table()
                
        except Exception as e:
            logger.error(f"Ошибка загрузки таблицы: {e}, создаю новую")
            return self._create_empty_master_table()

    def _create_empty_master_table(self) -> pd.DataFrame:
        """Создание пустой основной таблицы с базовой структурой"""
        columns = [
            'Product Name (EN)',
            'Unit',
            'Category',
            'First Added',
            'Last Updated'
        ]
        
        df = pd.DataFrame(columns=columns)
        df.index.name = 'Product ID'
        
        return df

    def _validate_master_table_structure(self, df: pd.DataFrame) -> bool:
        """Валидация структуры основной таблицы"""
        required_columns = ['Product Name (EN)', 'Unit']
        
        for col in required_columns:
            if col not in df.columns:
                return False
        
        return True

    def _prepare_supplier_name(self, supplier: Dict[str, Any]) -> str:
        """Подготовка имени поставщика для использования в качестве столбца"""
        name = supplier.get('name', 'Unknown Supplier')
        
        # Очистка имени от недопустимых символов для названий столбцов
        clean_name = ''.join(c for c in name if c.isalnum() or c in ' -_')
        
        # Ограничение длины
        if len(clean_name) > 30:
            clean_name = clean_name[:30]
        
        # Удаление пробелов в начале и конце
        clean_name = clean_name.strip()
        
        return clean_name or 'Unknown Supplier'

    def _is_new_supplier(self, df: pd.DataFrame, supplier_name: str) -> bool:
        """Проверка, является ли поставщик новым"""
        # Ищем столбцы поставщика (заканчивающиеся на _Price или _Updated)
        supplier_columns = [col for col in df.columns if col.startswith(supplier_name)]
        return len(supplier_columns) == 0

    def _add_new_supplier_columns(self, df: pd.DataFrame, supplier_name: str) -> pd.DataFrame:
        """Добавление столбцов для нового поставщика"""
        price_column = f"{supplier_name}_Price"
        updated_column = f"{supplier_name}_Updated"
        
        # Добавляем столбцы в конец таблицы
        df[price_column] = None
        df[updated_column] = None
        
        return df

    def _process_product(self, df: pd.DataFrame, product: Dict[str, Any], supplier_name: str) -> Dict[str, str]:
        """Обработка одного товара - добавление или обновление"""
        
        standardized_name = product.get('standardized_name', '')
        price = product.get('price', 0)
        unit = product.get('unit', 'pcs')
        category = product.get('category', 'general')
        
        # Поиск существующего товара
        existing_row_idx = self._find_matching_product(df, standardized_name)
        
        price_column = f"{supplier_name}_Price"
        updated_column = f"{supplier_name}_Updated"
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        if existing_row_idx is not None:
            # Обновление существующего товара
            df.loc[existing_row_idx, price_column] = price
            df.loc[existing_row_idx, updated_column] = current_date
            df.loc[existing_row_idx, 'Last Updated'] = current_date
            
            return {'action': 'updated_price', 'row_idx': existing_row_idx}
        
        else:
            # Добавление нового товара
            new_row_idx = len(df)
            
            # Создание новой строки
            new_row = {
                'Product Name (EN)': standardized_name,
                'Unit': unit,
                'Category': category,
                'First Added': current_date,
                'Last Updated': current_date,
                price_column: price,
                updated_column: current_date
            }
            
            # Заполнение остальных столбцов поставщиков пустыми значениями
            for col in df.columns:
                if col not in new_row:
                    new_row[col] = None
            
            # Добавление строки в DataFrame
            df.loc[new_row_idx] = new_row
            
            return {'action': 'new_product', 'row_idx': new_row_idx}

    def _find_matching_product(self, df: pd.DataFrame, product_name: str) -> Optional[int]:
        """Поиск соответствующего товара в таблице"""
        if df.empty or 'Product Name (EN)' not in df.columns:
            return None
        
        # 1. Точное совпадение
        exact_matches = df[df['Product Name (EN)'] == product_name]
        if not exact_matches.empty:
            return exact_matches.index[0]
        
        # 2. Поиск по similarity
        best_match_idx = None
        best_similarity = 0
        
        for idx, existing_name in df['Product Name (EN)'].items():
            if pd.isna(existing_name):
                continue
                
            similarity = calculate_similarity(product_name, str(existing_name))
            
            if similarity > QUALITY_THRESHOLDS['SIMILARITY_THRESHOLD'] and similarity > best_similarity:
                best_similarity = similarity
                best_match_idx = idx
        
        return best_match_idx

    def _save_master_table(self, df: pd.DataFrame):
        """Сохранение основной таблицы"""
        try:
            # Создание резервной копии перед сохранением
            if os.path.exists(self.master_table_path):
                backup_path = f"{self.master_table_path}.backup"
                shutil.copy2(self.master_table_path, backup_path)
            
            # Сохранение таблицы
            df.to_excel(self.master_table_path, index=True)
            logger.info(f"Основная таблица сохранена: {self.master_table_path}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения таблицы: {e}")
            raise

    async def _update_processing_stats(self, operation_stats: Dict[str, Any], data: Dict[str, Any]):
        """Обновление статистики обработки"""
        try:
            # Загрузка текущей статистики
            stats = self.get_processing_stats()
            
            # Обновление счетчиков
            stats['files_processed'] = stats.get('files_processed', 0) + 1
            stats['products_added'] = stats.get('products_added', 0) + operation_stats.get('new_products', 0)
            
            if operation_stats.get('new_supplier', False):
                stats['suppliers_added'] = stats.get('suppliers_added', 0) + 1
            
            # Обновление успешности обработки
            total_files = stats['files_processed']
            successful_files = stats.get('successful_files', 0) + (1 if operation_stats.get('processed_products', 0) > 0 else 0)
            stats['successful_files'] = successful_files
            stats['success_rate'] = (successful_files / total_files * 100) if total_files > 0 else 0
            
            # Статистика по типам файлов
            file_type = data.get('file_type', 'unknown')
            if file_type == 'excel':
                excel_success = stats.get('excel_successful', 0) + 1
                excel_total = stats.get('excel_total', 0) + 1
                stats['excel_successful'] = excel_success
                stats['excel_total'] = excel_total
                stats['excel_success_rate'] = (excel_success / excel_total * 100) if excel_total > 0 else 0
            elif file_type == 'pdf':
                pdf_success = stats.get('pdf_successful', 0) + 1
                pdf_total = stats.get('pdf_total', 0) + 1
                stats['pdf_successful'] = pdf_success
                stats['pdf_total'] = pdf_total
                stats['pdf_success_rate'] = (pdf_success / pdf_total * 100) if pdf_total > 0 else 0
            
            # OCR accuracy для PDF
            if file_type == 'pdf':
                extraction_confidence = data.get('data_quality', {}).get('extraction_confidence', 0)
                current_ocr_accuracy = stats.get('ocr_accuracy', 0)
                pdf_count = stats.get('pdf_total', 1)
                
                # Скользящее среднее OCR accuracy
                stats['ocr_accuracy'] = ((current_ocr_accuracy * (pdf_count - 1)) + extraction_confidence) / pdf_count
            
            # Время последнего обновления
            stats['last_update'] = datetime.now().isoformat()
            
            # Сохранение статистики
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            logger.info("Статистика обработки обновлена")
            
        except Exception as e:
            logger.error(f"Ошибка обновления статистики: {e}")

    def get_processing_stats(self) -> Dict[str, Any]:
        """Получение статистики обработки"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Возвращаем базовую статистику
                return {
                    'files_processed': 0,
                    'success_rate': 0.0,
                    'avg_processing_time': 0.0,
                    'pdf_success_rate': 0.0,
                    'excel_success_rate': 0.0,
                    'ocr_accuracy': 0.0,
                    'products_added': 0,
                    'suppliers_added': 0,
                    'last_update': 'Никогда'
                }
        except Exception as e:
            logger.error(f"Ошибка загрузки статистики: {e}")
            return {}

    async def _create_backup(self):
        """Создание резервной копии основной таблицы"""
        try:
            if not os.path.exists(self.master_table_path):
                return
            
            # Создание директории для бэкапов
            backup_dir = BACKUP_CONFIG.get('backup_location', 'backups/')
            os.makedirs(backup_dir, exist_ok=True)
            
            # Имя файла бэкапа с временной меткой
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"master_table_backup_{timestamp}.xlsx"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Копирование файла
            shutil.copy2(self.master_table_path, backup_path)
            
            # Сжатие если требуется
            if BACKUP_CONFIG.get('compress', False):
                backup_file(backup_path)
            
            logger.info(f"Создан бэкап: {backup_path}")
            
            # Очистка старых бэкапов
            await self._cleanup_old_backups(backup_dir)
            
        except Exception as e:
            logger.error(f"Ошибка создания бэкапа: {e}")

    async def _cleanup_old_backups(self, backup_dir: str):
        """Очистка старых файлов бэкапа"""
        try:
            retention_days = BACKUP_CONFIG.get('retention_days', 30)
            cutoff_date = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
            
            for filename in os.listdir(backup_dir):
                if filename.startswith('master_table_backup_'):
                    file_path = os.path.join(backup_dir, filename)
                    file_time = os.path.getmtime(file_path)
                    
                    if file_time < cutoff_date:
                        os.remove(file_path)
                        logger.info(f"Удален старый бэкап: {filename}")
                        
        except Exception as e:
            logger.error(f"Ошибка очистки бэкапов: {e}")

    def get_suppliers_list(self) -> List[str]:
        """Получение списка всех поставщиков"""
        try:
            df = self._load_or_create_master_table()
            
            # Извлечение имен поставщиков из названий столбцов
            suppliers = []
            for col in df.columns:
                if col.endswith('_Price'):
                    supplier_name = col.replace('_Price', '')
                    suppliers.append(supplier_name)
            
            return sorted(suppliers)
            
        except Exception as e:
            logger.error(f"Ошибка получения списка поставщиков: {e}")
            return []

    def get_products_by_supplier(self, supplier_name: str) -> List[Dict[str, Any]]:
        """Получение товаров конкретного поставщика"""
        try:
            df = self._load_or_create_master_table()
            
            price_column = f"{supplier_name}_Price"
            updated_column = f"{supplier_name}_Updated"
            
            if price_column not in df.columns:
                return []
            
            # Фильтрация товаров с ценами от данного поставщика
            supplier_products = df[df[price_column].notna()]
            
            products = []
            for idx, row in supplier_products.iterrows():
                product = {
                    'product_name': row.get('Product Name (EN)', ''),
                    'unit': row.get('Unit', 'pcs'),
                    'category': row.get('Category', 'general'),
                    'price': row.get(price_column),
                    'last_updated': row.get(updated_column, '')
                }
                products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"Ошибка получения товаров поставщика {supplier_name}: {e}")
            return []

    def search_products(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Поиск товаров по названию"""
        try:
            df = self._load_or_create_master_table()
            
            if df.empty or 'Product Name (EN)' not in df.columns:
                return []
            
            # Поиск по подстроке (case-insensitive)
            query_lower = query.lower()
            matching_products = df[
                df['Product Name (EN)'].str.lower().str.contains(query_lower, na=False)
            ]
            
            # Если мало результатов, используем fuzzy search
            if len(matching_products) < limit:
                fuzzy_matches = []
                
                for idx, row in df.iterrows():
                    product_name = row.get('Product Name (EN)', '')
                    if pd.isna(product_name):
                        continue
                    
                    similarity = fuzz.partial_ratio(query_lower, product_name.lower())
                    if similarity > 60:  # Порог для fuzzy match
                        fuzzy_matches.append((idx, similarity))
                
                # Сортировка по similarity
                fuzzy_matches.sort(key=lambda x: x[1], reverse=True)
                
                # Добавление лучших fuzzy matches
                for idx, _ in fuzzy_matches[:limit - len(matching_products)]:
                    if idx not in matching_products.index:
                        matching_products = pd.concat([matching_products, df.iloc[[idx]]])
            
            # Конвертация в список словарей
            results = []
            for idx, row in matching_products.head(limit).iterrows():
                product = {
                    'product_name': row.get('Product Name (EN)', ''),
                    'unit': row.get('Unit', 'pcs'),
                    'category': row.get('Category', 'general'),
                    'suppliers': {}
                }
                
                # Добавление цен от всех поставщиков
                for col in df.columns:
                    if col.endswith('_Price') and pd.notna(row[col]):
                        supplier_name = col.replace('_Price', '')
                        updated_col = f"{supplier_name}_Updated"
                        
                        product['suppliers'][supplier_name] = {
                            'price': row[col],
                            'last_updated': row.get(updated_col, '')
                        }
                
                results.append(product)
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка поиска товаров: {e}")
            return []

    def get_table_summary(self) -> Dict[str, Any]:
        """Получение сводной информации о таблице"""
        try:
            df = self._load_or_create_master_table()
            
            if df.empty:
                return {
                    'total_products': 0,
                    'total_suppliers': 0,
                    'categories': [],
                    'last_updated': None
                }
            
            # Подсчет поставщиков
            supplier_columns = [col for col in df.columns if col.endswith('_Price')]
            total_suppliers = len(supplier_columns)
            
            # Подсчет категорий
            categories = []
            if 'Category' in df.columns:
                categories = df['Category'].dropna().unique().tolist()
            
            # Последняя дата обновления
            last_updated = None
            if 'Last Updated' in df.columns:
                last_updated_series = pd.to_datetime(df['Last Updated'], errors='coerce')
                if not last_updated_series.isna().all():
                    last_updated = last_updated_series.max().strftime('%Y-%m-%d')
            
            return {
                'total_products': len(df),
                'total_suppliers': total_suppliers,
                'categories': categories,
                'last_updated': last_updated,
                'suppliers': [col.replace('_Price', '') for col in supplier_columns]
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения сводки таблицы: {e}")
            return {}

    def export_table(self, format_type: str = 'xlsx', supplier_filter: Optional[str] = None) -> str:
        """Экспорт таблицы в различных форматах"""
        try:
            df = self._load_or_create_master_table()
            
            if df.empty:
                raise ValueError("Таблица пуста")
            
            # Фильтрация по поставщику если указан
            if supplier_filter:
                price_col = f"{supplier_filter}_Price"
                if price_col in df.columns:
                    df = df[df[price_col].notna()]
            
            # Создание имени файла
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"price_list_export_{timestamp}"
            
            if supplier_filter:
                filename += f"_{supplier_filter}"
            
            # Экспорт в зависимости от формата
            if format_type.lower() == 'xlsx':
                export_path = f"data/{filename}.xlsx"
                df.to_excel(export_path, index=True)
            elif format_type.lower() == 'csv':
                export_path = f"data/{filename}.csv"
                df.to_csv(export_path, index=True, encoding='utf-8')
            else:
                raise ValueError(f"Неподдерживаемый формат: {format_type}")
            
            logger.info(f"Таблица экспортирована: {export_path}")
            return export_path
            
        except Exception as e:
            logger.error(f"Ошибка экспорта таблицы: {e}")
            raise