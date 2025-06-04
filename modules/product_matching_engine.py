"""
=============================================================================
MONITO PRODUCT MATCHING ENGINE
=============================================================================
Версия: 3.0
Цель: AI-powered система поиска и объединения идентичных товаров
=============================================================================
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from rapidfuzz import fuzz as rfuzz

from models.unified_database import MasterProduct, MatchType
from modules.unified_database_manager import UnifiedDatabaseManager
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ProductMatchCandidate:
    """Кандидат для сопоставления товаров"""
    product: MasterProduct
    similarity_score: float
    match_type: MatchType
    match_details: Dict[str, float]
    confidence_level: str

class ProductMatchingEngine:
    """
    Движок для поиска и сопоставления идентичных товаров
    """
    
    def __init__(self, db_manager: UnifiedDatabaseManager, 
                 similarity_threshold: float = 0.8,
                 exact_match_threshold: float = 0.95,
                 fuzzy_match_threshold: float = 0.8):
        """
        Инициализация движка сопоставления
        
        Args:
            db_manager: Менеджер базы данных
            similarity_threshold: Порог схожести для автоматического сопоставления
            exact_match_threshold: Порог для exact match
            fuzzy_match_threshold: Порог для fuzzy match
        """
        self.db_manager = db_manager
        self.similarity_threshold = similarity_threshold
        self.exact_match_threshold = exact_match_threshold
        self.fuzzy_match_threshold = fuzzy_match_threshold
        
        # Словари для нормализации
        self.brand_aliases = self._load_brand_aliases()
        self.unit_conversions = self._load_unit_conversions()
        self.stop_words = self._load_stop_words()
        
        logger.info(f"Initialized ProductMatchingEngine with thresholds: exact={exact_match_threshold}, fuzzy={fuzzy_match_threshold}")
    
    def _load_brand_aliases(self) -> Dict[str, str]:
        """Загрузка синонимов брендов"""
        return {
            # Coca-Cola variations
            'coca cola': 'coca-cola',
            'coca-cola': 'coca-cola',
            'coke': 'coca-cola',
            'cocacola': 'coca-cola',
            
            # Pepsi variations
            'pepsi cola': 'pepsi',
            'pepsi-cola': 'pepsi',
            
            # Indomie variations
            'indomie': 'indomie',
            'indo mie': 'indomie',
            'indomee': 'indomie',
            
            # Maggi variations
            'maggi': 'maggi',
            'magi': 'maggi',
            
            # Barilla variations
            'barilla': 'barilla',
            'barila': 'barilla',
            
            # ABC variations
            'abc': 'abc',
            'a.b.c': 'abc',
            'a b c': 'abc'
        }
    
    def _load_unit_conversions(self) -> Dict[str, Dict[str, float]]:
        """Загрузка коэффициентов конвертации единиц"""
        return {
            'weight': {
                'g': 1.0,
                'gram': 1.0,
                'gr': 1.0,
                'kg': 1000.0,
                'kilogram': 1000.0,
                'lb': 453.592,
                'pound': 453.592,
                'oz': 28.3495
            },
            'volume': {
                'ml': 1.0,
                'milliliter': 1.0,
                'cc': 1.0,
                'l': 1000.0,
                'liter': 1000.0,
                'litre': 1000.0,
                'fl oz': 29.5735,
                'gallon': 3785.41
            },
            'count': {
                'pcs': 1.0,
                'pieces': 1.0,
                'pc': 1.0,
                'piece': 1.0,
                'unit': 1.0,
                'units': 1.0,
                'box': 1.0,
                'pack': 1.0,
                'packet': 1.0,
                'can': 1.0,
                'bottle': 1.0,
                'jar': 1.0
            }
        }
    
    def _load_stop_words(self) -> List[str]:
        """Загрузка стоп-слов для нормализации названий"""
        return [
            'the', 'and', 'or', 'with', 'without', 'for', 'from', 'to', 'of', 'in',
            'premium', 'original', 'classic', 'special', 'extra', 'super', 'mega',
            'new', 'fresh', 'natural', 'organic', 'pure', 'best', 'quality',
            'pack', 'bottle', 'can', 'jar', 'box', 'bag', 'sachet'
        ]
    
    # =============================================================================
    # CORE MATCHING METHODS
    # =============================================================================
    
    def find_matches(self, new_product: MasterProduct, limit: int = 10) -> List[ProductMatchCandidate]:
        """
        Найти все потенциальные совпадения для нового товара
        
        Args:
            new_product: Новый товар для поиска совпадений
            limit: Максимальное количество кандидатов
            
        Returns:
            Список кандидатов для сопоставления
        """
        logger.info(f"Finding matches for product: {new_product.standard_name}")
        
        # 1. Ищем exact matches
        exact_matches = self._find_exact_matches(new_product)
        if exact_matches:
            logger.info(f"Found {len(exact_matches)} exact matches")
            return exact_matches[:limit]
        
        # 2. Ищем fuzzy matches по категории + бренду
        category_candidates = self._get_category_candidates(new_product)
        
        if not category_candidates:
            logger.info("No candidates found in the same category")
            return []
        
        # 3. Вычисляем similarity для каждого кандидата
        candidates = []
        for candidate in category_candidates:
            similarity_data = self._calculate_detailed_similarity(new_product, candidate)
            
            if similarity_data['overall_similarity'] >= self.fuzzy_match_threshold:
                match_type = MatchType.EXACT if similarity_data['overall_similarity'] >= self.exact_match_threshold else MatchType.FUZZY
                confidence_level = self._determine_confidence_level(similarity_data['overall_similarity'])
                
                candidates.append(ProductMatchCandidate(
                    product=candidate,
                    similarity_score=similarity_data['overall_similarity'],
                    match_type=match_type,
                    match_details=similarity_data,
                    confidence_level=confidence_level
                ))
        
        # Сортируем по убыванию схожести
        candidates.sort(key=lambda x: x.similarity_score, reverse=True)
        
        logger.info(f"Found {len(candidates)} fuzzy matches")
        return candidates[:limit]
    
    def _find_exact_matches(self, product: MasterProduct) -> List[ProductMatchCandidate]:
        """
        Поиск точных совпадений
        
        Args:
            product: Товар для поиска
            
        Returns:
            Список точных совпадений
        """
        # Нормализуем данные продукта
        normalized_name = self._normalize_product_name(product.standard_name)
        self._normalize_brand_name(product.brand) if product.brand else None
        self._normalize_size_unit(product.size, product.unit)
        
        # Поиск кандидатов с тем же нормализованным именем
        candidates = self.db_manager.search_master_products(
            search_term=normalized_name,
            category=product.category
        )
        
        exact_matches = []
        for candidate in candidates:
            if candidate.product_id == product.product_id:
                continue
                
            # Проверяем exact match критерии
            if self._is_exact_match(product, candidate):
                exact_matches.append(ProductMatchCandidate(
                    product=candidate,
                    similarity_score=1.0,
                    match_type=MatchType.EXACT,
                    match_details={
                        'name_similarity': 1.0,
                        'brand_similarity': 1.0,
                        'size_similarity': 1.0,
                        'overall_similarity': 1.0
                    },
                    confidence_level='high'
                ))
        
        return exact_matches
    
    def _is_exact_match(self, product_a: MasterProduct, product_b: MasterProduct) -> bool:
        """
        Проверка на точное совпадение товаров
        
        Args:
            product_a: Первый товар
            product_b: Второй товар
            
        Returns:
            True если товары точно совпадают
        """
        # 1. Категория должна совпадать
        if product_a.category != product_b.category:
            return False
        
        # 2. Нормализованные названия должны совпадать
        name_a = self._normalize_product_name(product_a.standard_name)
        name_b = self._normalize_product_name(product_b.standard_name)
        if name_a != name_b:
            return False
        
        # 3. Бренды должны совпадать (с учетом синонимов)
        brand_a = self._normalize_brand_name(product_a.brand) if product_a.brand else None
        brand_b = self._normalize_brand_name(product_b.brand) if product_b.brand else None
        if brand_a != brand_b:
            return False
        
        # 4. Размеры должны совпадать (с учетом конвертации единиц)
        size_a = self._normalize_size_unit(product_a.size, product_a.unit)
        size_b = self._normalize_size_unit(product_b.size, product_b.unit)
        if not self._sizes_match(size_a, size_b):
            return False
        
        return True
    
    def _get_category_candidates(self, product: MasterProduct) -> List[MasterProduct]:
        """
        Получение кандидатов из той же категории
        
        Args:
            product: Товар для поиска кандидатов
            
        Returns:
            Список кандидатов
        """
        return self.db_manager.search_master_products(
            search_term="",  # Ищем все в категории
            category=product.category,
            limit=100
        )
    
    # =============================================================================
    # SIMILARITY CALCULATION
    # =============================================================================
    
    def _calculate_detailed_similarity(self, product_a: MasterProduct, product_b: MasterProduct) -> Dict[str, float]:
        """
        Детальный расчет схожести между товарами
        
        Args:
            product_a: Первый товар
            product_b: Второй товар
            
        Returns:
            Словарь с детальными оценками схожести
        """
        # 1. Схожесть названий
        name_similarity = self._calculate_name_similarity(product_a.standard_name, product_b.standard_name)
        
        # 2. Схожесть брендов
        brand_similarity = self._calculate_brand_similarity(product_a.brand, product_b.brand)
        
        # 3. Схожесть размеров
        size_similarity = self._calculate_size_similarity(
            product_a.size, product_a.unit,
            product_b.size, product_b.unit
        )
        
        # 4. Взвешенная общая схожесть
        weights = {
            'name': 0.5,
            'brand': 0.3,
            'size': 0.2
        }
        
        overall_similarity = (
            name_similarity * weights['name'] +
            brand_similarity * weights['brand'] +
            size_similarity * weights['size']
        )
        
        return {
            'name_similarity': name_similarity,
            'brand_similarity': brand_similarity,
            'size_similarity': size_similarity,
            'overall_similarity': overall_similarity
        }
    
    def _calculate_name_similarity(self, name_a: str, name_b: str) -> float:
        """
        Расчет схожести названий товаров
        
        Args:
            name_a: Первое название
            name_b: Второе название
            
        Returns:
            Оценка схожести от 0 до 1
        """
        if not name_a or not name_b:
            return 0.0
        
        # Нормализуем названия
        normalized_a = self._normalize_product_name(name_a)
        normalized_b = self._normalize_product_name(name_b)
        
        # Используем несколько методов сравнения
        ratio = rfuzz.ratio(normalized_a, normalized_b) / 100.0
        partial_ratio = rfuzz.partial_ratio(normalized_a, normalized_b) / 100.0
        token_sort_ratio = rfuzz.token_sort_ratio(normalized_a, normalized_b) / 100.0
        token_set_ratio = rfuzz.token_set_ratio(normalized_a, normalized_b) / 100.0
        
        # Берем максимальное значение
        similarity = max(ratio, partial_ratio, token_sort_ratio, token_set_ratio)
        
        return min(similarity, 1.0)
    
    def _calculate_brand_similarity(self, brand_a: str, brand_b: str) -> float:
        """
        Расчет схожести брендов
        
        Args:
            brand_a: Первый бренд
            brand_b: Второй бренд
            
        Returns:
            Оценка схожести от 0 до 1
        """
        if not brand_a and not brand_b:
            return 1.0  # Оба бренда отсутствуют
        
        if not brand_a or not brand_b:
            return 0.5  # Один бренд отсутствует
        
        # Нормализуем бренды
        normalized_a = self._normalize_brand_name(brand_a)
        normalized_b = self._normalize_brand_name(brand_b)
        
        # Точное совпадение после нормализации
        if normalized_a == normalized_b:
            return 1.0
        
        # Fuzzy сравнение
        similarity = rfuzz.ratio(normalized_a, normalized_b) / 100.0
        return min(similarity, 1.0)
    
    def _calculate_size_similarity(self, size_a: float, unit_a: str, size_b: float, unit_b: str) -> float:
        """
        Расчет схожести размеров
        
        Args:
            size_a: Размер первого товара
            unit_a: Единица измерения первого товара
            size_b: Размер второго товара
            unit_b: Единица измерения второго товара
            
        Returns:
            Оценка схожести от 0 до 1
        """
        if not size_a and not size_b:
            return 1.0  # Оба размера отсутствуют
        
        if not size_a or not size_b:
            return 0.5  # Один размер отсутствует
        
        # Нормализуем размеры к одной единице измерения
        normalized_a = self._normalize_size_unit(size_a, unit_a)
        normalized_b = self._normalize_size_unit(size_b, unit_b)
        
        if not normalized_a or not normalized_b:
            return 0.5  # Не удалось нормализовать
        
        # Проверяем точное совпадение
        if abs(normalized_a['value'] - normalized_b['value']) < 0.001:
            return 1.0
        
        # Вычисляем относительную разницу
        max_value = max(normalized_a['value'], normalized_b['value'])
        min_value = min(normalized_a['value'], normalized_b['value'])
        
        if max_value == 0:
            return 1.0
        
        relative_diff = abs(max_value - min_value) / max_value
        
        # Толерантность для размеров (10%)
        if relative_diff <= 0.1:
            return 1.0 - (relative_diff / 0.1) * 0.1  # Плавное снижение
        else:
            return max(0.0, 1.0 - relative_diff)
    
    # =============================================================================
    # NORMALIZATION METHODS
    # =============================================================================
    
    def _normalize_product_name(self, name: str) -> str:
        """
        Нормализация названия товара
        
        Args:
            name: Исходное название
            
        Returns:
            Нормализованное название
        """
        if not name:
            return ""
        
        # Приводим к нижнему регистру
        normalized = name.lower().strip()
        
        # Удаляем специальные символы
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Удаляем множественные пробелы
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Удаляем стоп-слова
        words = normalized.split()
        filtered_words = [word for word in words if word not in self.stop_words]
        
        return ' '.join(filtered_words).strip()
    
    def _normalize_brand_name(self, brand: str) -> str:
        """
        Нормализация названия бренда
        
        Args:
            brand: Исходное название бренда
            
        Returns:
            Нормализованное название бренда
        """
        if not brand:
            return ""
        
        # Приводим к нижнему регистру и удаляем пробелы
        normalized = brand.lower().strip()
        
        # Удаляем специальные символы
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Применяем синонимы брендов
        if normalized in self.brand_aliases:
            return self.brand_aliases[normalized]
        
        return normalized
    
    def _normalize_size_unit(self, size: float, unit: str) -> Optional[Dict[str, Any]]:
        """
        Нормализация размера и единицы измерения
        
        Args:
            size: Размер
            unit: Единица измерения
            
        Returns:
            Словарь с нормализованными данными или None
        """
        if not size or not unit:
            return None
        
        unit_lower = unit.lower().strip()
        
        # Определяем тип единицы измерения
        unit_type = None
        conversion_factor = 1.0
        
        for category, conversions in self.unit_conversions.items():
            if unit_lower in conversions:
                unit_type = category
                conversion_factor = conversions[unit_lower]
                break
        
        if not unit_type:
            return None
        
        return {
            'value': float(size) * conversion_factor,
            'unit_type': unit_type,
            'normalized_unit': 'g' if unit_type == 'weight' else 'ml' if unit_type == 'volume' else 'pcs'
        }
    
    def _sizes_match(self, size_a: Optional[Dict], size_b: Optional[Dict], tolerance: float = 0.05) -> bool:
        """
        Проверка совпадения размеров с учетом толерантности
        
        Args:
            size_a: Первый размер
            size_b: Второй размер
            tolerance: Толерантность (5% по умолчанию)
            
        Returns:
            True если размеры совпадают
        """
        if not size_a and not size_b:
            return True
        
        if not size_a or not size_b:
            return False
        
        if size_a['unit_type'] != size_b['unit_type']:
            return False
        
        # Проверяем с учетом толерантности
        max_value = max(size_a['value'], size_b['value'])
        if max_value == 0:
            return True
        
        relative_diff = abs(size_a['value'] - size_b['value']) / max_value
        return relative_diff <= tolerance
    
    def _determine_confidence_level(self, similarity: float) -> str:
        """
        Определение уровня уверенности в совпадении
        
        Args:
            similarity: Оценка схожести
            
        Returns:
            Уровень уверенности
        """
        if similarity >= 0.95:
            return 'high'
        elif similarity >= 0.85:
            return 'medium'
        elif similarity >= 0.75:
            return 'low'
        else:
            return 'very_low'
    
    # =============================================================================
    # BATCH OPERATIONS
    # =============================================================================
    
    def process_all_products_for_matches(self, batch_size: int = 100) -> Dict[str, int]:
        """
        Обработка всех товаров для поиска совпадений
        
        Args:
            batch_size: Размер пакета для обработки
            
        Returns:
            Статистика обработки
        """
        logger.info("Starting batch processing for product matches")
        
        stats = {
            'products_processed': 0,
            'matches_found': 0,
            'exact_matches': 0,
            'fuzzy_matches': 0,
            'errors': 0
        }
        
        # Получаем все активные товары
        all_products = self.db_manager.search_master_products("", limit=10000)
        
        for i in range(0, len(all_products), batch_size):
            batch = all_products[i:i + batch_size]
            
            for product in batch:
                try:
                    matches = self.find_matches(product, limit=5)
                    
                    for match_candidate in matches:
                        # Создаем запись о совпадении в базе данных
                        self.db_manager.create_product_match(
                            product_a_id=str(product.product_id),
                            product_b_id=str(match_candidate.product.product_id),
                            similarity_score=match_candidate.similarity_score,
                            match_type=match_candidate.match_type,
                            details=match_candidate.match_details
                        )
                        
                        stats['matches_found'] += 1
                        if match_candidate.match_type == MatchType.EXACT:
                            stats['exact_matches'] += 1
                        else:
                            stats['fuzzy_matches'] += 1
                    
                    stats['products_processed'] += 1
                    
                    if stats['products_processed'] % 100 == 0:
                        logger.info(f"Processed {stats['products_processed']} products")
                
                except Exception as e:
                    logger.error(f"Error processing product {product.product_id}: {e}")
                    stats['errors'] += 1
        
        logger.info(f"Batch processing completed: {stats}")
        return stats
    
    def suggest_auto_merges(self, confidence_threshold: float = 0.95) -> List[Dict[str, Any]]:
        """
        Предложение автоматических слияний для высоконадежных совпадений
        
        Args:
            confidence_threshold: Пороговое значение уверенности
            
        Returns:
            Список предложений для слияния
        """
        unreviewed_matches = self.db_manager.get_unreviewed_matches(limit=1000)
        
        auto_merge_suggestions = []
        for match in unreviewed_matches:
            if float(match.similarity_score) >= confidence_threshold:
                suggestion = {
                    'match_id': str(match.match_id),
                    'product_a': match.product_a.to_dict(),
                    'product_b': match.product_b.to_dict(),
                    'similarity_score': float(match.similarity_score),
                    'match_type': match.match_type.value,
                    'suggested_action': 'auto_merge',
                    'confidence_level': 'high'
                }
                auto_merge_suggestions.append(suggestion)
        
        logger.info(f"Generated {len(auto_merge_suggestions)} auto-merge suggestions")
        return auto_merge_suggestions
    
    # =============================================================================
    # SEARCH AND QUERY METHODS
    # =============================================================================
    
    def search_by_name(self, search_term: str, limit: int = 20) -> List[MasterProduct]:
        """
        Поиск товаров по названию
        
        Args:
            search_term: Поисковый термин
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных товаров
        """
        return self.db_manager.search_master_products(search_term, limit=limit)
    
    def get_similar_products(self, product_id: str, limit: int = 10) -> List[ProductMatchCandidate]:
        """
        Получение похожих товаров для конкретного товара
        
        Args:
            product_id: ID товара
            limit: Максимальное количество результатов
            
        Returns:
            Список похожих товаров
        """
        product = self.db_manager.get_master_product_with_prices(product_id)
        if not product:
            return []
        
        return self.find_matches(product, limit=limit) 