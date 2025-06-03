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
    
    def create_unified_price_comparison(self) -> Dict[str, Any]:
        """Создает сводный прайс-лист со сравнением цен от всех поставщиков"""
        try:
            logger.info("🔄 Создание сводного прайс-листа со всеми поставщиками...")
            
            if not self.is_connected():
                return {'error': 'Нет подключения к Google Sheets'}
            
            # Получаем данные из Master Table
            master_worksheet = self.get_or_create_worksheet("Master Table")
            if not master_worksheet:
                return {'error': 'Основная таблица не найдена'}
            
            # Получаем все данные и заголовки
            all_data = master_worksheet.get_all_records()
            headers = master_worksheet.row_values(1)
            
            logger.info(f"📊 Найдено {len(all_data)} товаров в основной таблице")
            
            # Находим столбцы поставщиков (заканчивающиеся на _Price)
            supplier_columns = {}
            for i, header in enumerate(headers):
                if header.endswith('_Price'):
                    supplier_name = header.replace('_Price', '')
                    supplier_columns[supplier_name] = i
            
            logger.info(f"🏪 Найдено поставщиков: {len(supplier_columns)} - {list(supplier_columns.keys())}")
            
            if not supplier_columns:
                return {'error': 'Не найдено данных поставщиков'}
            
            # Создаем или очищаем лист сравнения цен
            comparison_worksheet = self.get_or_create_worksheet("Price Comparison")
            comparison_worksheet.clear()
            
            # Создаем заголовки для сводной таблицы
            comparison_headers = [
                'Product Name',
                'Category', 
                'Unit',
                'Best Price',
                'Best Supplier',
                'Price Difference %'
            ]
            
            # Добавляем столбцы для каждого поставщика
            for supplier in sorted(supplier_columns.keys()):
                comparison_headers.extend([f'{supplier}_Price', f'{supplier}_Updated'])
            
            comparison_headers.extend(['Average Price', 'Suppliers Count', 'Last Updated'])
            
            # Подготавливаем данные для сводной таблицы
            comparison_data = [comparison_headers]
            stats = {
                'total_products': len(all_data),
                'products_with_prices': 0,
                'suppliers_count': len(supplier_columns),
                'average_price_difference': 0
            }
            
            price_differences = []
            
            for product_row in all_data:
                product_name = product_row.get('Product Name (EN)', '')
                category = product_row.get('Category', 'general')
                unit = product_row.get('Unit', 'pcs')
                
                if not product_name:
                    continue
                
                # Собираем цены от всех поставщиков
                supplier_prices = {}
                supplier_dates = {}
                
                for supplier, col_index in supplier_columns.items():
                    price_value = product_row.get(f'{supplier}_Price', '')
                    date_value = product_row.get(f'{supplier}_Updated', '')
                    
                    if price_value and str(price_value).replace('.', '').replace(',', '').isdigit():
                        try:
                            price = float(str(price_value).replace(',', ''))
                            if price > 0:
                                supplier_prices[supplier] = price
                                supplier_dates[supplier] = date_value
                        except ValueError:
                            continue
                
                if not supplier_prices:
                    continue
                
                stats['products_with_prices'] += 1
                
                # Находим лучшую (минимальную) цену
                best_price = min(supplier_prices.values())
                best_supplier = min(supplier_prices.keys(), key=lambda k: supplier_prices[k])
                
                # Вычисляем среднюю цену и разброс
                average_price = sum(supplier_prices.values()) / len(supplier_prices)
                max_price = max(supplier_prices.values())
                price_difference_pct = ((max_price - best_price) / best_price * 100) if best_price > 0 else 0
                price_differences.append(price_difference_pct)
                
                # Формируем строку данных
                row_data = [
                    product_name,
                    category,
                    unit,
                    f"{best_price:,.0f}",
                    best_supplier,
                    f"{price_difference_pct:.1f}%"
                ]
                
                # Добавляем цены от каждого поставщика
                for supplier in sorted(supplier_columns.keys()):
                    if supplier in supplier_prices:
                        row_data.extend([
                            f"{supplier_prices[supplier]:,.0f}",
                            supplier_dates.get(supplier, '')
                        ])
                    else:
                        row_data.extend(['', ''])
                
                # Добавляем итоговую информацию
                row_data.extend([
                    f"{average_price:,.0f}",
                    str(len(supplier_prices)),
                    max(supplier_dates.values()) if supplier_dates else ''
                ])
                
                comparison_data.append(row_data)
            
            # Сортируем по категориям, затем по названию
            comparison_data[1:] = sorted(comparison_data[1:], key=lambda x: (x[1], x[0]))
            
            # Записываем данные в лист
            range_end = gspread.utils.rowcol_to_a1(len(comparison_data), len(comparison_headers))
            comparison_worksheet.update(f'A1:{range_end}', comparison_data)
            
            # Форматируем заголовки
            comparison_worksheet.format('A1:' + gspread.utils.rowcol_to_a1(1, len(comparison_headers)), {
                'backgroundColor': {'red': 0.1, 'green': 0.4, 'blue': 0.8},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            
            # Выделяем колонки лучших цен
            if len(comparison_data) > 1:
                best_price_range = f'D2:D{len(comparison_data)}'
                comparison_worksheet.format(best_price_range, {
                    'backgroundColor': {'red': 0.9, 'green': 1.0, 'blue': 0.9},
                    'textFormat': {'bold': True}
                })
            
            # Вычисляем итоговую статистику
            if price_differences:
                stats['average_price_difference'] = sum(price_differences) / len(price_differences)
            
            logger.info("✅ Сводный прайс-лист создан успешно")
            logger.info(f"   📦 Товаров с ценами: {stats['products_with_prices']}")
            logger.info(f"   🏪 Поставщиков: {stats['suppliers_count']}")
            logger.info(f"   📊 Средний разброс цен: {stats['average_price_difference']:.1f}%")
            
            return {
                'success': True,
                'worksheet_name': 'Price Comparison',
                'stats': stats,
                'sheet_url': self.get_sheet_url()
            }
            
        except Exception as e:
            logger.error(f"Ошибка создания сводного прайс-листа: {e}")
            return {'error': str(e)}
    
    def get_price_comparison_summary(self) -> Dict[str, Any]:
        """Возвращает краткую сводку по сравнению цен"""
        try:
            if not self.is_connected():
                return {'error': 'Нет подключения к Google Sheets'}
            
            # Получаем данные из листа сравнения
            try:
                comparison_worksheet = self.sheet.worksheet("Price Comparison")
                data = comparison_worksheet.get_all_records()
            except gspread.WorksheetNotFound:
                return {'error': 'Лист сравнения цен не найден. Создайте его сначала.'}
            
            if not data:
                return {'error': 'Нет данных в листе сравнения цен'}
            
            # Анализируем данные
            categories = {}
            total_savings = 0
            suppliers = set()
            
            for row in data:
                category = row.get('Category', 'general')
                if category not in categories:
                    categories[category] = {'count': 0, 'best_deals': []}
                
                categories[category]['count'] += 1
                
                # Находим поставщиков для этого товара
                for key in row.keys():
                    if key.endswith('_Price') and row[key]:
                        supplier = key.replace('_Price', '')
                        suppliers.add(supplier)
            
            return {
                'total_products': len(data),
                'categories': len(categories),
                'categories_breakdown': categories,
                'suppliers_count': len(suppliers),
                'suppliers': list(suppliers),
                'sheet_url': self.get_sheet_url()
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения сводки: {e}")
            return {'error': str(e)}