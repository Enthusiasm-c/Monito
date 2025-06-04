"""
=============================================================================
MONITO PARSER ADAPTER
=============================================================================
Версия: 3.0
Цель: Адаптер для интеграции существующих парсеров с unified системой
=============================================================================
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from modules.unified_database_manager import UnifiedDatabaseManager
from modules.product_matching_engine import ProductMatchingEngine
from utils.logger import get_logger

logger = get_logger(__name__)

class ParserAdapter:
    """
    Адаптер для интеграции существующих парсеров с unified системой
    """
    
    def __init__(self, db_manager: UnifiedDatabaseManager, 
                 matching_engine: ProductMatchingEngine):
        """
        Инициализация адаптера
        
        Args:
            db_manager: Менеджер unified базы данных
            matching_engine: Движок сопоставления товаров
        """
        self.db_manager = db_manager
        self.matching_engine = matching_engine
        
        # Инициализируем legacy парсеры
        self._init_legacy_parsers()
        
        logger.info("Initialized ParserAdapter")
    
    def _init_legacy_parsers(self):
        """Инициализация существующих парсеров"""
        try:
            # Импортируем существующие парсеры
            from modules.universal_excel_parser_v2 import UniversalExcelParserV2
            from modules.pdf_parser import PDFParser
            
            self.excel_parser = UniversalExcelParserV2()
            self.pdf_parser = PDFParser()
            
            logger.info("✅ Legacy parsers initialized successfully")
            
        except ImportError as e:
            logger.error(f"❌ Failed to import legacy parsers: {e}")
            self.excel_parser = None
            self.pdf_parser = None
    
    # =============================================================================
    # MAIN ADAPTATION METHODS
    # =============================================================================
    
    def process_file_to_unified_system(self, file_path: str, supplier_name: str = None,
                                     auto_match_duplicates: bool = True) -> Dict[str, Any]:
        """
        Обработка файла через legacy парсеры и интеграция в unified систему
        
        Args:
            file_path: Путь к файлу
            supplier_name: Имя поставщика (если не указано, берется из имени файла)
            auto_match_duplicates: Автоматически искать дубликаты
            
        Returns:
            Результат обработки и интеграции
        """
        logger.info(f"Processing file to unified system: {file_path}")
        
        start_time = datetime.utcnow()
        result = {
            'file_path': file_path,
            'supplier_name': supplier_name or Path(file_path).stem,
            'processing_start': start_time.isoformat(),
            'legacy_parsing': {},
            'unified_integration': {},
            'matching_results': {},
            'statistics': {}
        }
        
        try:
            # 1. Парсинг через legacy системы
            logger.info("📄 Step 1: Legacy parsing")
            legacy_result = self._parse_with_legacy_parsers(file_path)
            
            if legacy_result.get('error'):
                result['error'] = legacy_result['error']
                return result
            
            result['legacy_parsing'] = legacy_result
            
            # 2. Конвертация в unified формат
            logger.info("🔄 Step 2: Converting to unified format")
            unified_products = self._convert_to_unified_format(
                legacy_result['products'],
                result['supplier_name']
            )
            
            result['unified_integration']['converted_products'] = len(unified_products)
            
            # 3. Интеграция в unified database
            logger.info("💾 Step 3: Integration into unified database")
            integration_stats = self._integrate_into_unified_db(
                unified_products,
                result['supplier_name']
            )
            
            result['unified_integration'].update(integration_stats)
            
            # 4. Поиск и обработка дубликатов
            if auto_match_duplicates:
                logger.info("🔍 Step 4: Matching duplicates")
                matching_stats = self._process_duplicate_matching(unified_products)
                result['matching_results'] = matching_stats
            
            # 5. Финальная статистика
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            result['statistics'] = {
                'processing_time_seconds': processing_time,
                'legacy_products_found': len(legacy_result.get('products', [])),
                'unified_products_created': result['unified_integration'].get('products_created', 0),
                'unified_products_updated': result['unified_integration'].get('products_updated', 0),
                'prices_added': result['unified_integration'].get('prices_added', 0),
                'potential_duplicates_found': result['matching_results'].get('matches_found', 0),
                'processing_end': end_time.isoformat()
            }
            
            logger.info(f"✅ File processing completed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing file: {e}")
            result['error'] = f"Processing failed: {str(e)}"
            return result
    
    def _parse_with_legacy_parsers(self, file_path: str) -> Dict[str, Any]:
        """Парсинг файла через существующие парсеры"""
        file_ext = Path(file_path).suffix.lower()
        
        try:
            if file_ext in ['.xlsx', '.xls']:
                if self.excel_parser:
                    logger.debug("Using UniversalExcelParserV2")
                    return self.excel_parser.extract_products_universal(file_path)
                else:
                    return {'error': 'Excel parser not available'}
                    
            elif file_ext == '.pdf':
                if self.pdf_parser:
                    logger.debug("Using PDFParser")
                    return self.pdf_parser.extract_products_from_pdf(file_path)
                else:
                    return {'error': 'PDF parser not available'}
            else:
                return {'error': f'Unsupported file format: {file_ext}'}
                
        except Exception as e:
            logger.error(f"Legacy parsing error: {e}")
            return {'error': f'Legacy parsing failed: {str(e)}'}
    
    def _convert_to_unified_format(self, legacy_products: List[Dict], 
                                 supplier_name: str) -> List[Dict[str, Any]]:
        """
        Конвертация legacy формата товаров в unified формат
        
        Args:
            legacy_products: Товары в legacy формате
            supplier_name: Имя поставщика
            
        Returns:
            Товары в unified формате
        """
        unified_products = []
        
        for legacy_product in legacy_products:
            try:
                # Извлекаем данные из legacy формата
                original_name = legacy_product.get('original_name', '')
                standardized_name = legacy_product.get('standardized_name', original_name)
                price = legacy_product.get('price', 0)
                unit = legacy_product.get('unit', 'pcs')
                brand = legacy_product.get('brand', '')
                category = legacy_product.get('category', 'general')
                size = legacy_product.get('size', '')
                confidence = legacy_product.get('confidence', 0.8)
                
                # Очистка и нормализация данных
                cleaned_name = self._clean_product_name(standardized_name or original_name)
                if not cleaned_name:
                    continue
                
                cleaned_price = self._clean_price(price)
                if cleaned_price <= 0:
                    continue
                
                # Извлечение размера из названия если не указан
                size_info = self._extract_size_from_name(cleaned_name)
                if size_info and not size:
                    size = size_info['size']
                    unit = size_info['unit']
                    cleaned_name = size_info['cleaned_name']
                
                # Категоризация если не указана
                if not category or category == 'general':
                    category = self._categorize_product(cleaned_name)
                
                # Создаем unified product
                unified_product = {
                    'standard_name': cleaned_name,
                    'brand': self._clean_brand_name(brand),
                    'category': category,
                    'size': self._parse_size(size) if size else None,
                    'unit': self._normalize_unit(unit),
                    'description': original_name,  # Сохраняем оригинальное название
                    'supplier_name': supplier_name,
                    'original_name': original_name,
                    'price': cleaned_price,
                    'confidence_score': confidence
                }
                
                unified_products.append(unified_product)
                
            except Exception as e:
                logger.warning(f"Error converting product {legacy_product}: {e}")
                continue
        
        logger.info(f"Converted {len(unified_products)} products to unified format")
        return unified_products
    
    def _integrate_into_unified_db(self, unified_products: List[Dict], 
                                 supplier_name: str) -> Dict[str, int]:
        """
        Интеграция товаров в unified database
        
        Args:
            unified_products: Товары в unified формате
            supplier_name: Имя поставщика
            
        Returns:
            Статистика интеграции
        """
        logger.info(f"Integrating {len(unified_products)} products into unified DB")
        
        # Используем bulk import из database manager
        import_stats = self.db_manager.bulk_import_products_and_prices(
            supplier_name, unified_products
        )
        
        logger.info(f"Integration completed: {import_stats}")
        return import_stats
    
    def _process_duplicate_matching(self, unified_products: List[Dict]) -> Dict[str, int]:
        """
        Поиск и обработка потенциальных дубликатов
        
        Args:
            unified_products: Товары в unified формате
            
        Returns:
            Статистика сопоставления
        """
        matching_stats = {
            'matches_found': 0,
            'exact_matches': 0,
            'fuzzy_matches': 0,
            'products_processed': 0
        }
        
        try:
            # Получаем все master products из базы
            all_products = self.db_manager.search_master_products("", limit=10000)
            
            # Ищем совпадения для новых товаров
            for product_data in unified_products:
                try:
                    # Создаем временный MasterProduct для поиска
                    from models.unified_database import MasterProduct
                    temp_product = MasterProduct(
                        standard_name=product_data['standard_name'],
                        brand=product_data.get('brand'),
                        category=product_data['category'],
                        size=product_data.get('size'),
                        unit=product_data.get('unit')
                    )
                    
                    # Ищем совпадения
                    matches = self.matching_engine.find_matches(temp_product, limit=5)
                    
                    if matches:
                        matching_stats['matches_found'] += len(matches)
                        
                        for match in matches:
                            if match.match_type.value == 'exact':
                                matching_stats['exact_matches'] += 1
                            else:
                                matching_stats['fuzzy_matches'] += 1
                    
                    matching_stats['products_processed'] += 1
                    
                except Exception as e:
                    logger.warning(f"Error matching product {product_data.get('standard_name')}: {e}")
                    continue
            
            logger.info(f"Duplicate matching completed: {matching_stats}")
            
        except Exception as e:
            logger.error(f"Error in duplicate matching: {e}")
            matching_stats['error'] = str(e)
        
        return matching_stats
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def _clean_product_name(self, name: str) -> str:
        """Очистка названия товара"""
        if not name:
            return ""
        
        # Удаляем лишние пробелы и символы
        cleaned = str(name).strip()
        cleaned = ' '.join(cleaned.split())  # Нормализуем пробелы
        
        # Удаляем очевидно некорректные значения
        if len(cleaned) < 2 or cleaned.lower() in ['nan', 'none', 'null', '']:
            return ""
        
        return cleaned
    
    def _clean_price(self, price: Any) -> float:
        """Очистка и нормализация цены"""
        if not price:
            return 0.0
        
        try:
            # Если уже число
            if isinstance(price, (int, float)):
                return float(price)
            
            # Очищаем строку
            price_str = str(price).strip()
            
            # Удаляем валютные символы и буквы
            import re
            price_str = re.sub(r'[^\d.,\-]', '', price_str)
            
            # Заменяем запятую на точку
            price_str = price_str.replace(',', '.')
            
            if not price_str:
                return 0.0
            
            return float(price_str)
            
        except (ValueError, TypeError):
            return 0.0
    
    def _extract_size_from_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Извлечение размера из названия товара"""
        if not name:
            return None
        
        import re
        
        # Паттерны для размеров
        size_patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l|pcs|pack|box|can|bottle)(?:\s|$)',
            r'(\d+(?:[.,]\d+)?)\s*(кг|г|мл|л|шт|упак|коробка|банка|бутылка)(?:\s|$)',
        ]
        
        for pattern in size_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                size_value = match.group(1).replace(',', '.')
                unit = match.group(2).lower()
                
                # Очищаем название от размера
                cleaned_name = re.sub(pattern, '', name, flags=re.IGNORECASE).strip()
                cleaned_name = re.sub(r'\s+', ' ', cleaned_name)  # Нормализуем пробелы
                
                return {
                    'size': float(size_value),
                    'unit': self._normalize_unit(unit),
                    'cleaned_name': cleaned_name
                }
        
        return None
    
    def _categorize_product(self, name: str) -> str:
        """Простая категоризация товара по названию"""
        if not name:
            return 'general'
        
        name_lower = name.lower()
        
        # Категории напитков
        if any(word in name_lower for word in ['cola', 'sprite', 'fanta', 'pepsi', 'drink', 'juice', 'water', 'beer']):
            return 'beverages'
        
        # Категории консервов
        if any(word in name_lower for word in ['canned', 'tin', 'preserve', 'консерв', 'банка']):
            return 'canned_food'
        
        # Категории макарон
        if any(word in name_lower for word in ['pasta', 'noodle', 'spaghetti', 'macaroni', 'макарон', 'лапша']):
            return 'pasta_noodles'
        
        # Категории масел
        if any(word in name_lower for word in ['oil', 'cooking', 'olive', 'sunflower', 'масло']):
            return 'cooking_oil'
        
        # Категории специй
        if any(word in name_lower for word in ['spice', 'seasoning', 'salt', 'pepper', 'специи', 'приправа']):
            return 'spices_seasonings'
        
        # Категории снеков
        if any(word in name_lower for word in ['snack', 'chips', 'cracker', 'biscuit', 'чипсы', 'печенье']):
            return 'snacks'
        
        return 'general'
    
    def _clean_brand_name(self, brand: str) -> str:
        """Очистка названия бренда"""
        if not brand or str(brand).lower() in ['unknown', 'nan', 'none', 'null']:
            return ""
        
        return str(brand).strip()
    
    def _parse_size(self, size: Any) -> Optional[float]:
        """Парсинг размера"""
        if not size:
            return None
        
        try:
            if isinstance(size, (int, float)):
                return float(size)
            
            # Извлекаем числовое значение из строки
            import re
            size_str = str(size).strip()
            match = re.search(r'(\d+(?:[.,]\d+)?)', size_str)
            
            if match:
                return float(match.group(1).replace(',', '.'))
            
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _normalize_unit(self, unit: str) -> str:
        """Нормализация единицы измерения"""
        if not unit:
            return 'pcs'
        
        unit_mapping = {
            'кг': 'kg', 'г': 'g', 'мл': 'ml', 'л': 'l',
            'шт': 'pcs', 'упак': 'pack', 'коробка': 'box',
            'банка': 'can', 'бутылка': 'bottle',
            'kilogram': 'kg', 'gram': 'g', 'milliliter': 'ml',
            'liter': 'l', 'piece': 'pcs', 'pieces': 'pcs'
        }
        
        unit_lower = str(unit).lower().strip()
        return unit_mapping.get(unit_lower, unit_lower)
    
    # =============================================================================
    # BATCH PROCESSING
    # =============================================================================
    
    def process_multiple_files(self, file_paths: List[str], 
                             auto_match_duplicates: bool = True) -> Dict[str, Any]:
        """
        Пакетная обработка нескольких файлов
        
        Args:
            file_paths: Список путей к файлам
            auto_match_duplicates: Автоматически искать дубликаты
            
        Returns:
            Сводная статистика обработки
        """
        logger.info(f"Starting batch processing of {len(file_paths)} files")
        
        batch_stats = {
            'files_processed': 0,
            'files_successful': 0,
            'files_failed': 0,
            'total_products_found': 0,
            'total_products_integrated': 0,
            'total_duplicates_found': 0,
            'file_results': [],
            'errors': []
        }
        
        for file_path in file_paths:
            try:
                logger.info(f"Processing file: {file_path}")
                
                result = self.process_file_to_unified_system(
                    file_path, 
                    auto_match_duplicates=auto_match_duplicates
                )
                
                batch_stats['files_processed'] += 1
                
                if result.get('error'):
                    batch_stats['files_failed'] += 1
                    batch_stats['errors'].append({
                        'file': file_path,
                        'error': result['error']
                    })
                else:
                    batch_stats['files_successful'] += 1
                    batch_stats['total_products_found'] += result['statistics'].get('legacy_products_found', 0)
                    batch_stats['total_products_integrated'] += result['statistics'].get('unified_products_created', 0)
                    batch_stats['total_duplicates_found'] += result['statistics'].get('potential_duplicates_found', 0)
                
                batch_stats['file_results'].append({
                    'file': file_path,
                    'success': not result.get('error'),
                    'statistics': result.get('statistics', {})
                })
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                batch_stats['files_failed'] += 1
                batch_stats['errors'].append({
                    'file': file_path,
                    'error': str(e)
                })
        
        logger.info(f"Batch processing completed: {batch_stats['files_successful']}/{batch_stats['files_processed']} successful")
        return batch_stats 