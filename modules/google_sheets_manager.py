import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import gspread
from google.auth.exceptions import GoogleAuthError

logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    """Менеджер для работы с Google Sheets"""
    
    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv()  # Загружаем переменные окружения
        
        self.client = None
        self.sheet = None
        self.credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'google_credentials.json')
        self.sheet_id = os.getenv('GOOGLE_SHEET_ID')
        self._initialize()
    
    def _initialize(self):
        """Инициализация подключения к Google Sheets"""
        try:
            if not os.path.exists(self.credentials_file):
                logger.warning(f"Файл учетных данных Google не найден: {self.credentials_file}")
                return False
            
            if not self.sheet_id:
                logger.warning("GOOGLE_SHEET_ID не установлен в переменных окружения")
                return False
            
            # Подключение к Google Sheets API
            self.client = gspread.service_account(filename=self.credentials_file)
            
            # Открытие таблицы
            self.sheet = self.client.open_by_key(self.sheet_id)
            
            logger.info(f"✅ Подключение к Google Sheets установлено: {self.sheet.title}")
            return True
            
        except FileNotFoundError:
            logger.error(f"❌ Файл учетных данных не найден: {self.credentials_file}")
            return False
        except GoogleAuthError as e:
            logger.error(f"❌ Ошибка аутентификации Google: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Google Sheets: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Проверка подключения"""
        return self.client is not None and self.sheet is not None
    
    def get_or_create_worksheet(self, title: str) -> Optional[gspread.Worksheet]:
        """Получение или создание листа"""
        try:
            if not self.is_connected():
                logger.error("Нет подключения к Google Sheets")
                return None
            
            try:
                # Попытка найти существующий лист
                worksheet = self.sheet.worksheet(title)
                logger.info(f"Найден существующий лист: {title}")
                return worksheet
            except gspread.WorksheetNotFound:
                # Создание нового листа
                worksheet = self.sheet.add_worksheet(title=title, rows=1000, cols=20)
                logger.info(f"Создан новый лист: {title}")
                return worksheet
                
        except Exception as e:
            logger.error(f"Ошибка получения/создания листа {title}: {e}")
            return None
    
    def create_master_table(self) -> bool:
        """Создание основной таблицы с заголовками"""
        try:
            worksheet = self.get_or_create_worksheet("Master Table")
            if not worksheet:
                return False
            
            # Заголовки основной таблицы
            headers = [
                'Product Name (EN)',
                'Brand',
                'Size',
                'Unit',
                'Currency',
                'Category', 
                'First Added',
                'Last Updated'
            ]
            
            # Проверяем, есть ли уже заголовки
            if worksheet.row_count == 0 or not worksheet.get('A1'):
                worksheet.update('A1:H1', [headers])
                
                # Форматирование заголовков
                worksheet.format('A1:H1', {
                    'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 1.0},
                    'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
                })
                
                logger.info("✅ Основная таблица создана с заголовками")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания основной таблицы: {e}")
            return False
    
    def add_supplier_columns(self, supplier_name: str) -> bool:
        """Добавление столбцов для нового поставщика"""
        try:
            worksheet = self.get_or_create_worksheet("Master Table")
            if not worksheet:
                return False
            
            # Получаем заголовки
            headers = worksheet.row_values(1)
            
            # Проверяем, есть ли уже столбцы для этого поставщика
            price_col_name = f"{supplier_name}_Price"
            date_col_name = f"{supplier_name}_Updated"
            
            if price_col_name not in headers:
                # Добавляем новые столбцы в конец
                next_col = len(headers) + 1
                
                new_headers = [price_col_name, date_col_name]
                range_name = f"{gspread.utils.rowcol_to_a1(1, next_col)}:{gspread.utils.rowcol_to_a1(1, next_col + 1)}"
                
                worksheet.update(range_name, [new_headers])
                
                # Форматирование новых заголовков
                worksheet.format(range_name, {
                    'backgroundColor': {'red': 0.9, 'green': 0.6, 'blue': 0.2},
                    'textFormat': {'bold': True}
                })
                
                logger.info(f"✅ Добавлены столбцы для поставщика: {supplier_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления столбцов поставщика {supplier_name}: {e}")
            return False
    
    def _validate_product_data(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация данных товара"""
        errors = []
        
        # Проверка названия
        name = product.get('standardized_name', '').strip()
        if not name or len(name) < 2:
            errors.append("Отсутствует или слишком короткое название товара")
        
        # Проверка цены
        price = product.get('price', 0)
        try:
            price = float(price)
            if price <= 0:
                errors.append("Цена должна быть больше нуля")
            elif price > 1000000:
                errors.append("Цена слишком велика (>1,000,000)")
        except (ValueError, TypeError):
            errors.append("Цена должна быть числом")
            price = 0
        
        # Проверка единицы измерения
        unit = product.get('unit', '').strip()
        valid_units = ['pcs', 'kg', 'l', 'm', 'box', 'pack', 'set', 'pair']
        if not unit:
            unit = 'pcs'  # По умолчанию
        elif unit not in valid_units:
            # Попробуем стандартизировать
            unit_mapping = {
                'шт': 'pcs', 'штук': 'pcs', 'piece': 'pcs',
                'кг': 'kg', 'килограмм': 'kg',
                'л': 'l', 'литр': 'l', 'liter': 'l',
                'м': 'm', 'метр': 'm', 'meter': 'm',
                'коробка': 'box', 'упаковка': 'pack', 'пара': 'pair'
            }
            unit = unit_mapping.get(unit.lower(), 'pcs')
        
        # Проверка категории
        category = product.get('category', '').strip()
        if not category:
            category = 'general'
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'cleaned_data': {
                'standardized_name': name,
                'brand': product.get('brand', 'unknown'),
                'size': product.get('size', 'unknown'),
                'price': price,
                'unit': unit,
                'currency': product.get('currency', 'USD'),
                'category': category,
                'confidence': product.get('confidence', 0.8),
                'original_name': product.get('original_name', name)
            }
        }

    def update_master_table(self, standardized_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновление основной таблицы данными"""
        try:
            logger.info(f"💾 Начинаем сохранение в Google Sheets...")
            
            if not self.is_connected():
                logger.error(f"❌ Нет подключения к Google Sheets")
                return {'error': 'Нет подключения к Google Sheets'}
            
            # Создаем основную таблицу если не существует
            if not self.create_master_table():
                logger.error(f"❌ Не удалось создать основную таблицу")
                return {'error': 'Не удалось создать основную таблицу'}
            
            worksheet = self.get_or_create_worksheet("Master Table")
            supplier = standardized_data.get('supplier', {})
            products = standardized_data.get('products', [])
            
            logger.info(f"📊 Получено товаров для сохранения: {len(products)}")
            
            if not products:
                logger.error(f"❌ Нет товаров для добавления")
                return {'error': 'Нет товаров для добавления'}
            
            # Валидация товаров
            logger.info(f"🔍 Начинаем валидацию {len(products)} товаров...")
            validated_products = []
            validation_errors = []
            detailed_errors = []
            
            for i, product in enumerate(products):
                validation = self._validate_product_data(product)
                if validation['valid']:
                    validated_products.append(validation['cleaned_data'])
                    logger.debug(f"✅ Товар {i+1} валиден: {product.get('standardized_name', product.get('original_name', 'N/A'))}")
                else:
                    error_details = f"Товар {i+1} ({product.get('standardized_name', product.get('original_name', 'N/A'))}): {', '.join(validation['errors'])}"
                    validation_errors.append(error_details)
                    detailed_errors.append({
                        'index': i+1,
                        'name': product.get('standardized_name', product.get('original_name', 'N/A')),
                        'errors': validation['errors'],
                        'raw_data': product
                    })
                    logger.warning(f"⚠️ {error_details}")
            
            loss_count = len(products) - len(validated_products)
            loss_percentage = (loss_count / len(products) * 100) if len(products) > 0 else 0
            
            logger.info(f"📊 РЕЗУЛЬТАТ ВАЛИДАЦИИ:")
            logger.info(f"   ✅ Валидных товаров: {len(validated_products)}/{len(products)} ({len(validated_products)/len(products)*100:.1f}%)")
            logger.info(f"   ❌ Невалидных товаров: {loss_count}/{len(products)} ({loss_percentage:.1f}%)")
            
            if detailed_errors:
                logger.warning(f"🔍 ДЕТАЛИ ВАЛИДАЦИОННЫХ ОШИБОК:")
                for error in detailed_errors[:5]:  # Показываем первые 5 ошибок
                    logger.warning(f"   • {error['name']}: {', '.join(error['errors'])}")
                if len(detailed_errors) > 5:
                    logger.warning(f"   ... и еще {len(detailed_errors) - 5} ошибок")
            
            if not validated_products:
                logger.error(f"❌ КРИТИЧНО: Все товары содержат ошибки валидации")
                return {'error': f'Все товары содержат ошибки: {"; ".join(validation_errors)}'}
            
            if validation_errors:
                logger.warning(f"⚠️ Товары с ошибками будут пропущены: {len(validation_errors)} из {len(products)}")
            
            # Заменяем products на валидированные данные
            products = validated_products
            
            # Подготовка имени поставщика
            supplier_name = self._clean_supplier_name(supplier.get('name', 'Unknown Supplier'))
            
            # Добавляем столбцы для поставщика
            if not self.add_supplier_columns(supplier_name):
                return {'error': 'Не удалось добавить столбцы поставщика'}
            
            # Получаем текущие данные
            all_data = worksheet.get_all_records()
            headers = worksheet.row_values(1)
            
            # Поиск индексов столбцов
            try:
                price_col_idx = headers.index(f"{supplier_name}_Price") + 1
                date_col_idx = headers.index(f"{supplier_name}_Updated") + 1
            except ValueError:
                return {'error': 'Не удалось найти столбцы поставщика'}
            
            stats = {
                'new_products': 0,
                'updated_prices': 0,
                'processed_products': 0
            }
            
            current_date = datetime.now().strftime('%Y-%m-%d')
            updates = []
            
            # Обработка каждого товара
            for product in products:
                try:
                    product_name = product.get('standardized_name', '')
                    price = product.get('price', 0)
                    unit = product.get('unit', 'pcs')
                    category = product.get('category', 'general')
                    
                    if not product_name or price <= 0:
                        continue
                    
                    # Поиск существующего товара
                    existing_row = None
                    for idx, row_data in enumerate(all_data):
                        if row_data.get('Product Name (EN)', '').lower() == product_name.lower():
                            existing_row = idx + 2  # +2 потому что enumerate с 0, а строки с 1, плюс заголовок
                            break
                    
                    if existing_row:
                        # Обновление существующего товара
                        updates.append({
                            'range': gspread.utils.rowcol_to_a1(existing_row, price_col_idx),
                            'values': [[price]]
                        })
                        updates.append({
                            'range': gspread.utils.rowcol_to_a1(existing_row, date_col_idx),
                            'values': [[current_date]]
                        })
                        updates.append({
                            'range': gspread.utils.rowcol_to_a1(existing_row, 8),  # Last Updated column (теперь H)
                            'values': [[current_date]]
                        })
                        stats['updated_prices'] += 1
                    else:
                        # Добавление нового товара
                        new_row = len(all_data) + 2  # +2 для заголовка и индексации с 1
                        
                        # Подготовка строки с данными
                        row_data = [''] * len(headers)
                        if len(row_data) > 0: row_data[0] = product_name  # Product Name (EN)
                        if len(row_data) > 1: row_data[1] = product.get('brand', 'unknown')  # Brand
                        if len(row_data) > 2: row_data[2] = product.get('size', 'unknown')  # Size
                        if len(row_data) > 3: row_data[3] = unit  # Unit
                        if len(row_data) > 4: row_data[4] = product.get('currency', 'USD')  # Currency
                        if len(row_data) > 5: row_data[5] = category  # Category
                        if len(row_data) > 6: row_data[6] = current_date  # First Added
                        if len(row_data) > 7: row_data[7] = current_date  # Last Updated
                        if price_col_idx <= len(row_data): row_data[price_col_idx - 1] = price  # Supplier Price
                        if date_col_idx <= len(row_data): row_data[date_col_idx - 1] = current_date  # Supplier Updated
                        
                        updates.append({
                            'range': f"A{new_row}:{gspread.utils.rowcol_to_a1(new_row, len(headers))}",
                            'values': [row_data]
                        })
                        stats['new_products'] += 1
                    
                    stats['processed_products'] += 1
                    
                except Exception as e:
                    logger.warning(f"Ошибка обработки товара {product.get('standardized_name', 'unknown')}: {e}")
                    continue
            
            # Выполнение всех обновлений одним batch запросом
            if updates:
                worksheet.batch_update(updates)
                logger.info(f"✅ Обновлено {len(updates)} ячеек в Google Sheets")
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка обновления основной таблицы: {e}")
            return {'error': str(e)}
    
    def create_supplier_summary(self, supplier_name: str, products: List[Dict]) -> bool:
        """Создание отдельного листа с данными поставщика"""
        try:
            clean_name = self._clean_supplier_name(supplier_name)
            worksheet_title = f"Supplier_{clean_name}"
            
            worksheet = self.get_or_create_worksheet(worksheet_title)
            if not worksheet:
                return False
            
            # Очистка листа
            worksheet.clear()
            
            # Заголовки
            headers = [
                'Original Name',
                'Standardized Name',
                'Brand',
                'Size',
                'Price',
                'Currency',
                'Unit',
                'Category',
                'Confidence',
                'Added Date'
            ]
            
            # Данные
            data = [headers]
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
                data.append(row)
            
            # Обновление листа
            worksheet.update(f'A1:{gspread.utils.rowcol_to_a1(len(data), len(headers))}', data)
            
            # Форматирование заголовков
            worksheet.format('A1:J1', {
                'backgroundColor': {'red': 0.2, 'green': 0.8, 'blue': 0.2},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            
            logger.info(f"✅ Создан лист поставщика: {worksheet_title}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания листа поставщика {supplier_name}: {e}")
            return False
    
    def get_sheet_url(self) -> Optional[str]:
        """Получение URL таблицы"""
        if self.sheet:
            return f"https://docs.google.com/spreadsheets/d/{self.sheet.id}"
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики таблицы"""
        try:
            if not self.is_connected():
                return {'error': 'Нет подключения к Google Sheets'}
            
            worksheet = self.get_or_create_worksheet("Master Table")
            if not worksheet:
                return {'error': 'Основная таблица не найдена'}
            
            # Получение данных
            all_data = worksheet.get_all_records()
            headers = worksheet.row_values(1)
            
            # Подсчет поставщиков (столбцы заканчивающиеся на _Price)
            suppliers = [h.replace('_Price', '') for h in headers if h.endswith('_Price')]
            
            # Подсчет категорий
            categories = set()
            for row in all_data:
                if row.get('Category'):
                    categories.add(row['Category'])
            
            return {
                'total_products': len(all_data),
                'total_suppliers': len(suppliers),
                'categories': list(categories),
                'suppliers': suppliers,
                'sheet_url': self.get_sheet_url(),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {'error': str(e)}
    
    def _clean_supplier_name(self, name: str) -> str:
        """Очистка имени поставщика для использования в названиях столбцов и листов"""
        import re
        # Удаление недопустимых символов
        clean_name = re.sub(r'[^\w\s\-]', '', str(name))
        # Замена пробелов на подчеркивания
        clean_name = re.sub(r'\s+', '_', clean_name)
        # Ограничение длины
        clean_name = clean_name[:30]
        return clean_name.strip('_') or 'Unknown_Supplier'
    
    def test_connection(self) -> Dict[str, Any]:
        """Тест подключения к Google Sheets"""
        try:
            if not self.is_connected():
                return {
                    'status': 'error',
                    'message': 'Нет подключения к Google Sheets',
                    'suggestions': [
                        'Проверьте файл google_credentials.json',
                        'Убедитесь что GOOGLE_SHEET_ID установлен в .env',
                        'Проверьте права доступа к таблице'
                    ]
                }
            
            # Попытка прочитать информацию о таблице
            sheet_info = {
                'title': self.sheet.title,
                'id': self.sheet.id,
                'url': self.get_sheet_url(),
                'worksheets': [ws.title for ws in self.sheet.worksheets()]
            }
            
            return {
                'status': 'success',
                'message': 'Подключение к Google Sheets активно',
                'sheet_info': sheet_info
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Ошибка тестирования подключения: {e}',
                'suggestions': [
                    'Проверьте интернет соединение',
                    'Убедитесь что Service Account имеет доступ к таблице',
                    'Проверьте правильность GOOGLE_SHEET_ID'
                ]
            }