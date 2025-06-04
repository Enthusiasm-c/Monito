"""
=============================================================================
MONITO NORMALIZER ADAPTER
=============================================================================
Версия: 3.0
Цель: Адаптер для интеграции существующих нормализаторов с unified системой
=============================================================================
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from modules.unified_database_manager import UnifiedDatabaseManager
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class NormalizationResult:
    """Результат нормализации"""
    original_name: str
    normalized_name: str
    brand: str
    category: str
    size: Optional[float]
    unit: str
    confidence: float
    processing_method: str

class NormalizerAdapter:
    """
    Адаптер для интеграции существующих нормализаторов с unified системой
    """
    
    def __init__(self, db_manager: UnifiedDatabaseManager):
        """
        Инициализация адаптера
        
        Args:
            db_manager: Менеджер unified базы данных
        """
        self.db_manager = db_manager
        
        # Инициализируем legacy нормализаторы
        self._init_legacy_normalizers()
        
        logger.info("Initialized NormalizerAdapter")
    
    def _init_legacy_normalizers(self):
        """Инициализация существующих нормализаторов"""
        try:
            # Пытаемся импортировать существующие нормализаторы
            from normalizer.name_resolver import NameResolver
            
            self.name_resolver = NameResolver()
            self.legacy_normalizers_available = True
            
            logger.info("✅ Legacy normalizers initialized successfully")
            
        except ImportError as e:
            logger.warning(f"⚠️ Legacy normalizers not available: {e}")
            self.name_resolver = None
            self.legacy_normalizers_available = False
    
    # =============================================================================
    # MAIN NORMALIZATION METHODS
    # =============================================================================
    
    def normalize_product_name(self, product_name: str, supplier_name: str = None) -> NormalizationResult:
        """
        Нормализация названия товара с использованием legacy и unified подходов
        
        Args:
            product_name: Исходное название товара
            supplier_name: Имя поставщика (для контекста)
            
        Returns:
            Результат нормализации
        """
        logger.debug(f"Normalizing product: {product_name}")
        
        # Базовая нормализация
        base_result = self._basic_normalization(product_name)
        
        # Если доступны legacy нормализаторы, используем их
        if self.legacy_normalizers_available and self.name_resolver:
            legacy_result = self._use_legacy_normalizer(product_name, supplier_name)
            if legacy_result:
                # Объединяем результаты
                return self._merge_normalization_results(base_result, legacy_result)
        
        # Используем enhanced нормализацию unified системы
        enhanced_result = self._enhanced_normalization(base_result)
        
        return enhanced_result
    
    def _basic_normalization(self, product_name: str) -> NormalizationResult:
        """Базовая нормализация названия"""
        if not product_name:
            return NormalizationResult(
                original_name="",
                normalized_name="",
                brand="",
                category="general",
                size=None,
                unit="pcs",
                confidence=0.0,
                processing_method="basic"
            )
        
        # Очистка названия
        cleaned_name = self._clean_name(product_name)
        
        # Извлечение компонентов
        extracted_info = self._extract_product_components(cleaned_name)
        
        return NormalizationResult(
            original_name=product_name,
            normalized_name=extracted_info['normalized_name'],
            brand=extracted_info['brand'],
            category=extracted_info['category'],
            size=extracted_info['size'],
            unit=extracted_info['unit'],
            confidence=extracted_info['confidence'],
            processing_method="basic"
        )
    
    def _use_legacy_normalizer(self, product_name: str, supplier_name: str = None) -> Optional[NormalizationResult]:
        """Использование legacy нормализатора"""
        try:
            if not self.name_resolver:
                return None
            
            # Используем legacy NameResolver
            resolved_data = self.name_resolver.resolve_product_name(
                product_name, 
                supplier_context=supplier_name
            )
            
            if resolved_data:
                return NormalizationResult(
                    original_name=product_name,
                    normalized_name=resolved_data.get('normalized_name', product_name),
                    brand=resolved_data.get('brand', ''),
                    category=resolved_data.get('category', 'general'),
                    size=resolved_data.get('size'),
                    unit=resolved_data.get('unit', 'pcs'),
                    confidence=resolved_data.get('confidence', 0.8),
                    processing_method="legacy_name_resolver"
                )
                
        except Exception as e:
            logger.warning(f"Legacy normalizer error: {e}")
            
        return None
    
    def _enhanced_normalization(self, base_result: NormalizationResult) -> NormalizationResult:
        """Enhanced нормализация с использованием unified подходов"""
        
        # Дополнительная обработка названия
        enhanced_name = self._advanced_name_processing(base_result.normalized_name)
        
        # Улучшенная категоризация
        enhanced_category = self._advanced_categorization(enhanced_name, base_result.category)
        
        # Улучшенное извлечение бренда
        enhanced_brand = self._advanced_brand_extraction(enhanced_name, base_result.brand)
        
        # Повышение уверенности
        enhanced_confidence = min(base_result.confidence + 0.1, 1.0)
        
        return NormalizationResult(
            original_name=base_result.original_name,
            normalized_name=enhanced_name,
            brand=enhanced_brand,
            category=enhanced_category,
            size=base_result.size,
            unit=base_result.unit,
            confidence=enhanced_confidence,
            processing_method="enhanced_unified"
        )
    
    def _merge_normalization_results(self, base_result: NormalizationResult, 
                                   legacy_result: NormalizationResult) -> NormalizationResult:
        """Объединение результатов базовой и legacy нормализации"""
        
        # Выбираем лучшие элементы из каждого результата
        merged_name = legacy_result.normalized_name if legacy_result.confidence > base_result.confidence else base_result.normalized_name
        merged_brand = legacy_result.brand if legacy_result.brand else base_result.brand
        merged_category = legacy_result.category if legacy_result.category != 'general' else base_result.category
        merged_confidence = max(base_result.confidence, legacy_result.confidence)
        
        return NormalizationResult(
            original_name=base_result.original_name,
            normalized_name=merged_name,
            brand=merged_brand,
            category=merged_category,
            size=legacy_result.size or base_result.size,
            unit=legacy_result.unit or base_result.unit,
            confidence=merged_confidence,
            processing_method="merged_legacy_unified"
        )
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def _clean_name(self, name: str) -> str:
        """Очистка названия товара"""
        import re
        
        if not name:
            return ""
        
        # Приводим к нижнему регистру
        cleaned = name.lower().strip()
        
        # Удаляем лишние символы
        cleaned = re.sub(r'[^\w\s\-\.]', ' ', cleaned)
        
        # Нормализуем пробелы
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def _extract_product_components(self, name: str) -> Dict[str, Any]:
        """Извлечение компонентов товара из названия"""
        import re
        
        # Инициализируем результат
        result = {
            'normalized_name': name,
            'brand': '',
            'category': 'general',
            'size': None,
            'unit': 'pcs',
            'confidence': 0.7
        }
        
        if not name:
            result['confidence'] = 0.0
            return result
        
        # Извлечение размера и единицы
        size_patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l|pcs|pack|box|can|bottle|кг|г|мл|л|шт)',
            r'(\d+(?:[.,]\d+)?)\s*(kilogram|gram|milliliter|liter|piece|pieces)'
        ]
        
        for pattern in size_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                try:
                    size_value = float(match.group(1).replace(',', '.'))
                    unit_value = match.group(2).lower()
                    
                    result['size'] = size_value
                    result['unit'] = self._normalize_unit(unit_value)
                    
                    # Удаляем размер из названия
                    result['normalized_name'] = re.sub(pattern, '', name, flags=re.IGNORECASE).strip()
                    result['normalized_name'] = re.sub(r'\s+', ' ', result['normalized_name'])
                    
                    result['confidence'] += 0.1
                    break
                except ValueError:
                    continue
        
        # Извлечение бренда (обычно в начале или в скобках)
        brand_patterns = [
            r'^([A-Z][a-z]+)\s+',  # Бренд в начале с заглавной буквы
            r'\(([^)]+)\)',        # Бренд в скобках
            r'([A-Z]+)\s+',        # Бренд заглавными буквами
        ]
        
        for pattern in brand_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                potential_brand = match.group(1).strip()
                if len(potential_brand) > 1 and len(potential_brand) < 20:
                    result['brand'] = potential_brand.title()
                    result['confidence'] += 0.05
                    break
        
        # Категоризация по ключевым словам
        result['category'] = self._categorize_by_keywords(result['normalized_name'])
        if result['category'] != 'general':
            result['confidence'] += 0.1
        
        return result
    
    def _advanced_name_processing(self, name: str) -> str:
        """Продвинутая обработка названия"""
        if not name:
            return ""
        
        # Список стоп-слов для удаления
        stop_words = [
            'premium', 'original', 'classic', 'special', 'extra', 'super',
            'new', 'fresh', 'natural', 'organic', 'pure', 'best', 'quality',
            'премиум', 'оригинал', 'классик', 'специальный', 'экстра',
            'новый', 'свежий', 'натуральный', 'органический', 'чистый'
        ]
        
        # Удаляем стоп-слова
        words = name.split()
        filtered_words = [word for word in words if word.lower() not in stop_words]
        
        processed_name = ' '.join(filtered_words).strip()
        
        # Если название стало слишком коротким, возвращаем оригинал
        if len(processed_name) < 3:
            return name
        
        return processed_name
    
    def _advanced_categorization(self, name: str, current_category: str) -> str:
        """Продвинутая категоризация товара"""
        if not name:
            return current_category
        
        name_lower = name.lower()
        
        # Расширенные правила категоризации
        category_rules = {
            'beverages': [
                'cola', 'sprite', 'fanta', 'pepsi', 'drink', 'juice', 'water', 'beer',
                'coffee', 'tea', 'milk', 'soda', 'energy', 'cola', 'напиток', 'сок',
                'пиво', 'кофе', 'чай', 'молоко', 'вода'
            ],
            'canned_food': [
                'canned', 'tin', 'preserve', 'conserve', 'консерв', 'банка',
                'томат', 'sauce', 'соус', 'pasta sauce', 'томатный'
            ],
            'pasta_noodles': [
                'pasta', 'noodle', 'spaghetti', 'macaroni', 'penne', 'fusilli',
                'макарон', 'лапша', 'спагетти', 'паста'
            ],
            'cooking_oil': [
                'oil', 'cooking', 'olive', 'sunflower', 'coconut', 'palm',
                'масло', 'оливковое', 'подсолнечное', 'кокосовое'
            ],
            'spices_seasonings': [
                'spice', 'seasoning', 'salt', 'pepper', 'garlic', 'onion',
                'специи', 'приправа', 'соль', 'перец', 'чеснок', 'лук'
            ],
            'dairy_products': [
                'milk', 'cheese', 'butter', 'yogurt', 'cream', 'dairy',
                'молоко', 'сыр', 'масло', 'йогурт', 'сливки', 'молочный'
            ],
            'snacks': [
                'snack', 'chips', 'cracker', 'biscuit', 'cookie', 'nuts',
                'чипсы', 'печенье', 'крекер', 'орехи', 'снек'
            ],
            'rice_grains': [
                'rice', 'grain', 'wheat', 'barley', 'oats', 'quinoa',
                'рис', 'зерно', 'пшеница', 'ячмень', 'овес', 'крупа'
            ],
            'frozen_food': [
                'frozen', 'ice cream', 'popsicle', 'мороженое', 'замороженный'
            ],
            'household_items': [
                'detergent', 'soap', 'shampoo', 'toothpaste', 'cleaning',
                'моющее', 'мыло', 'шампунь', 'зубная паста', 'чистящее'
            ]
        }
        
        # Ищем наиболее подходящую категорию
        best_category = current_category
        max_matches = 0
        
        for category, keywords in category_rules.items():
            matches = sum(1 for keyword in keywords if keyword in name_lower)
            if matches > max_matches:
                max_matches = matches
                best_category = category
        
        return best_category
    
    def _advanced_brand_extraction(self, name: str, current_brand: str) -> str:
        """Продвинутое извлечение бренда"""
        if current_brand:
            return current_brand
        
        # Известные бренды для поиска
        known_brands = [
            'coca cola', 'pepsi', 'sprite', 'fanta', 'heineken', 'barilla',
            'maggi', 'knorr', 'lipton', 'nestle', 'unilever', 'indomie',
            'abc', 'kecap', 'bango', 'blue band', 'walls', 'aice'
        ]
        
        name_lower = name.lower()
        
        for brand in known_brands:
            if brand in name_lower:
                return brand.title()
        
        return ""
    
    def _categorize_by_keywords(self, name: str) -> str:
        """Категоризация по ключевым словам"""
        if not name:
            return 'general'
        
        name_lower = name.lower()
        
        # Базовая категоризация
        if any(word in name_lower for word in ['cola', 'drink', 'juice', 'water']):
            return 'beverages'
        elif any(word in name_lower for word in ['oil', 'масло']):
            return 'cooking_oil'
        elif any(word in name_lower for word in ['pasta', 'noodle', 'макарон']):
            return 'pasta_noodles'
        elif any(word in name_lower for word in ['rice', 'рис']):
            return 'rice_grains'
        elif any(word in name_lower for word in ['milk', 'молоко']):
            return 'dairy_products'
        
        return 'general'
    
    def _normalize_unit(self, unit: str) -> str:
        """Нормализация единицы измерения"""
        unit_mapping = {
            'кг': 'kg', 'г': 'g', 'мл': 'ml', 'л': 'l',
            'шт': 'pcs', 'килogram': 'kg', 'gram': 'g',
            'milliliter': 'ml', 'liter': 'l', 'piece': 'pcs',
            'pieces': 'pcs', 'bottle': 'bottle', 'can': 'can',
            'pack': 'pack', 'box': 'box'
        }
        
        unit_lower = unit.lower().strip()
        return unit_mapping.get(unit_lower, unit_lower)
    
    # =============================================================================
    # BATCH OPERATIONS
    # =============================================================================
    
    def normalize_product_batch(self, products: List[Dict[str, Any]], 
                              supplier_name: str = None) -> List[NormalizationResult]:
        """
        Пакетная нормализация товаров
        
        Args:
            products: Список товаров для нормализации
            supplier_name: Имя поставщика
            
        Returns:
            Список результатов нормализации
        """
        logger.info(f"Starting batch normalization of {len(products)} products")
        
        results = []
        for product in products:
            try:
                product_name = product.get('name') or product.get('original_name') or product.get('standard_name')
                if product_name:
                    result = self.normalize_product_name(product_name, supplier_name)
                    results.append(result)
                    
            except Exception as e:
                logger.warning(f"Error normalizing product {product}: {e}")
                continue
        
        logger.info(f"Completed batch normalization: {len(results)} successful")
        return results
    
    def update_unified_products_with_normalization(self, limit: int = 1000) -> Dict[str, int]:
        """
        Обновление существующих товаров в unified системе с улучшенной нормализацией
        
        Args:
            limit: Максимальное количество товаров для обработки
            
        Returns:
            Статистика обновления
        """
        logger.info(f"Starting normalization update for up to {limit} products")
        
        stats = {
            'products_processed': 0,
            'products_updated': 0,
            'products_skipped': 0,
            'errors': 0
        }
        
        try:
            # Получаем товары из unified системы
            products = self.db_manager.search_master_products("", limit=limit)
            
            for product in products:
                try:
                    # Нормализуем название
                    normalization_result = self.normalize_product_name(product.standard_name)
                    
                    # Проверяем, нужно ли обновление
                    needs_update = False
                    
                    if normalization_result.normalized_name != product.standard_name:
                        needs_update = True
                    
                    if normalization_result.brand and not product.brand:
                        needs_update = True
                    
                    if normalization_result.category != product.category:
                        needs_update = True
                    
                    if needs_update:
                        # Обновляем товар в базе данных
                        with self.db_manager.get_session() as session:
                            db_product = session.query(
                                self.db_manager.db_manager.MasterProduct
                            ).filter_by(product_id=product.product_id).first()
                            
                            if db_product:
                                db_product.standard_name = normalization_result.normalized_name
                                if normalization_result.brand:
                                    db_product.brand = normalization_result.brand
                                db_product.category = normalization_result.category
                                
                                session.commit()
                                stats['products_updated'] += 1
                    else:
                        stats['products_skipped'] += 1
                    
                    stats['products_processed'] += 1
                    
                    if stats['products_processed'] % 100 == 0:
                        logger.info(f"Processed {stats['products_processed']} products")
                        
                except Exception as e:
                    logger.warning(f"Error processing product {product.product_id}: {e}")
                    stats['errors'] += 1
                    continue
            
            logger.info(f"Normalization update completed: {stats}")
            
        except Exception as e:
            logger.error(f"Error in batch normalization update: {e}")
            stats['error'] = str(e)
        
        return stats 