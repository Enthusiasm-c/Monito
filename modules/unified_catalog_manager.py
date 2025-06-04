"""
=============================================================================
MONITO UNIFIED CATALOG MANAGER
=============================================================================
Версия: 3.0
Цель: Централизованный менеджер каталога с лучшими ценами поставщиков
=============================================================================
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from dataclasses import dataclass
from collections import defaultdict

from modules.unified_database_manager import UnifiedDatabaseManager
from modules.product_matching_engine import ProductMatchingEngine
from modules.price_comparison_engine import PriceComparisonEngine
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class CatalogItem:
    """Элемент unified каталога"""
    product_id: str
    standard_name: str
    brand: str
    category: str
    size: float
    unit: str
    best_price: float
    best_supplier: str
    worst_price: float
    suppliers_count: int
    savings_percentage: float
    price_trend: str
    last_updated: datetime
    confidence_score: float

@dataclass
class CatalogStats:
    """Статистика каталога"""
    total_products: int
    total_suppliers: int
    categories_count: int
    average_savings: float
    max_savings: float
    products_with_multiple_suppliers: int
    last_update: datetime

class UnifiedCatalogManager:
    """
    Менеджер для unified каталога с лучшими ценами
    """
    
    def __init__(self, db_manager: UnifiedDatabaseManager,
                 matching_engine: ProductMatchingEngine,
                 price_engine: PriceComparisonEngine):
        """
        Инициализация менеджера каталога
        
        Args:
            db_manager: Менеджер базы данных
            matching_engine: Движок сопоставления товаров
            price_engine: Движок сравнения цен
        """
        self.db_manager = db_manager
        self.matching_engine = matching_engine
        self.price_engine = price_engine
        
        logger.info("Initialized UnifiedCatalogManager")
    
    # =============================================================================
    # CATALOG GENERATION AND MANAGEMENT
    # =============================================================================
    
    def generate_unified_catalog(self, category: str = None, 
                               min_suppliers: int = 2,
                               include_single_supplier: bool = True) -> List[CatalogItem]:
        """
        Генерация unified каталога с лучшими ценами
        
        Args:
            category: Фильтр по категории
            min_suppliers: Минимальное количество поставщиков
            include_single_supplier: Включать товары с одним поставщиком
            
        Returns:
            Список элементов каталога
        """
        logger.info(f"Generating unified catalog for category: {category}")
        
        # Получаем базовый каталог из БД
        raw_catalog = self.db_manager.get_unified_catalog(category=category, limit=5000)
        
        catalog_items = []
        for item in raw_catalog:
            # Фильтруем по количеству поставщиков
            if not include_single_supplier and item['suppliers_count'] < min_suppliers:
                continue
            
            if item['suppliers_count'] < min_suppliers:
                continue
            
            # Получаем детальный анализ цен
            price_analysis = self.price_engine.analyze_product_prices(item['product_id'])
            
            if not price_analysis:
                continue
            
            # Создаем элемент каталога
            catalog_item = CatalogItem(
                product_id=item['product_id'],
                standard_name=item['standard_name'],
                brand=item['brand'] or 'Unknown',
                category=item['category'],
                size=item['size'] or 0,
                unit=item['unit'] or 'pcs',
                best_price=item['best_price'],
                best_supplier=item['best_supplier'],
                worst_price=item['worst_price'],
                suppliers_count=item['suppliers_count'],
                savings_percentage=item['savings_percentage'],
                price_trend=price_analysis.price_trend,
                last_updated=datetime.utcnow(),
                confidence_score=self.price_engine._calculate_deal_confidence(price_analysis)
            )
            
            catalog_items.append(catalog_item)
        
        # Сортируем по потенциальной экономии
        catalog_items.sort(key=lambda x: x.savings_percentage, reverse=True)
        
        logger.info(f"Generated catalog with {len(catalog_items)} items")
        return catalog_items
    
    def get_catalog_by_category(self, category: str) -> List[CatalogItem]:
        """
        Получение каталога для конкретной категории
        
        Args:
            category: Название категории
            
        Returns:
            Список товаров в категории
        """
        return self.generate_unified_catalog(category=category)
    
    def get_top_deals(self, limit: int = 50, min_savings: float = 5.0) -> List[CatalogItem]:
        """
        Получение топ предложений с максимальной экономией
        
        Args:
            limit: Максимальное количество результатов
            min_savings: Минимальная экономия в процентах
            
        Returns:
            Список лучших предложений
        """
        catalog = self.generate_unified_catalog()
        
        # Фильтруем по минимальной экономии
        top_deals = [item for item in catalog if item.savings_percentage >= min_savings]
        
        # Сортируем по экономии и уверенности
        top_deals.sort(key=lambda x: (x.savings_percentage, x.confidence_score), reverse=True)
        
        return top_deals[:limit]
    
    def search_catalog(self, search_term: str, category: str = None, 
                      limit: int = 50) -> List[CatalogItem]:
        """
        Поиск товаров в каталоге
        
        Args:
            search_term: Поисковый термин
            category: Фильтр по категории
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных товаров
        """
        # Ищем товары в базе данных
        products = self.db_manager.search_master_products(search_term, category, limit)
        
        catalog_items = []
        for product in products:
            # Получаем информацию о ценах
            price_comparison = self.db_manager.get_price_comparison_for_product(str(product.product_id))
            
            if not price_comparison or not price_comparison.get('prices'):
                continue
            
            # Анализируем цены
            price_analysis = self.price_engine.analyze_product_prices(str(product.product_id))
            
            if not price_analysis:
                continue
            
            catalog_item = CatalogItem(
                product_id=str(product.product_id),
                standard_name=product.standard_name,
                brand=product.brand or 'Unknown',
                category=product.category,
                size=float(product.size) if product.size else 0,
                unit=product.unit or 'pcs',
                best_price=price_analysis.best_price['price'],
                best_supplier=price_analysis.best_price['supplier'],
                worst_price=price_analysis.worst_price['price'],
                suppliers_count=price_analysis.suppliers_count,
                savings_percentage=price_analysis.savings_potential,
                price_trend=price_analysis.price_trend,
                last_updated=datetime.utcnow(),
                confidence_score=self.price_engine._calculate_deal_confidence(price_analysis)
            )
            
            catalog_items.append(catalog_item)
        
        # Сортируем по релевантности (экономия + уверенность)
        catalog_items.sort(key=lambda x: (x.savings_percentage, x.confidence_score), reverse=True)
        
        return catalog_items
    
    # =============================================================================
    # CATALOG ANALYTICS
    # =============================================================================
    
    def get_catalog_statistics(self) -> CatalogStats:
        """
        Получение статистики каталога
        
        Returns:
            Статистика каталога
        """
        logger.info("Calculating catalog statistics")
        
        # Получаем полный каталог
        catalog = self.generate_unified_catalog()
        
        if not catalog:
            return CatalogStats(
                total_products=0,
                total_suppliers=0,
                categories_count=0,
                average_savings=0.0,
                max_savings=0.0,
                products_with_multiple_suppliers=0,
                last_update=datetime.utcnow()
            )
        
        # Вычисляем статистики
        total_products = len(catalog)
        
        # Уникальные поставщики
        all_suppliers = set()
        for item in catalog:
            all_suppliers.add(item.best_supplier)
        total_suppliers = len(all_suppliers)
        
        # Уникальные категории
        categories = set(item.category for item in catalog)
        categories_count = len(categories)
        
        # Статистики по экономии
        savings_list = [item.savings_percentage for item in catalog if item.savings_percentage > 0]
        average_savings = sum(savings_list) / len(savings_list) if savings_list else 0
        max_savings = max(savings_list) if savings_list else 0
        
        # Товары с несколькими поставщиками
        products_with_multiple_suppliers = len([item for item in catalog if item.suppliers_count > 1])
        
        return CatalogStats(
            total_products=total_products,
            total_suppliers=total_suppliers,
            categories_count=categories_count,
            average_savings=round(average_savings, 2),
            max_savings=round(max_savings, 2),
            products_with_multiple_suppliers=products_with_multiple_suppliers,
            last_update=datetime.utcnow()
        )
    
    def get_category_analysis(self) -> Dict[str, Dict[str, Any]]:
        """
        Анализ каталога по категориям
        
        Returns:
            Словарь с анализом по категориям
        """
        catalog = self.generate_unified_catalog()
        
        # Группируем по категориям
        category_data = defaultdict(list)
        for item in catalog:
            category_data[item.category].append(item)
        
        category_analysis = {}
        for category, items in category_data.items():
            # Статистики по категории
            total_items = len(items)
            avg_savings = sum(item.savings_percentage for item in items) / total_items
            max_savings = max(item.savings_percentage for item in items)
            avg_suppliers = sum(item.suppliers_count for item in items) / total_items
            
            # Топ товары в категории
            top_items = sorted(items, key=lambda x: x.savings_percentage, reverse=True)[:5]
            
            category_analysis[category] = {
                'total_products': total_items,
                'average_savings': round(avg_savings, 2),
                'max_savings': round(max_savings, 2),
                'average_suppliers_per_product': round(avg_suppliers, 1),
                'top_deals': [
                    {
                        'product_name': item.standard_name,
                        'brand': item.brand,
                        'savings_percentage': item.savings_percentage,
                        'best_supplier': item.best_supplier
                    }
                    for item in top_items
                ]
            }
        
        return category_analysis
    
    def get_supplier_market_share(self) -> Dict[str, Dict[str, Any]]:
        """
        Анализ рыночной доли поставщиков
        
        Returns:
            Словарь с долями поставщиков
        """
        catalog = self.generate_unified_catalog()
        
        # Подсчитываем количество лучших предложений по поставщикам
        supplier_stats = defaultdict(lambda: {
            'best_deals_count': 0,
            'total_products': 0,
            'categories': set(),
            'average_savings': []
        })
        
        for item in catalog:
            supplier_stats[item.best_supplier]['best_deals_count'] += 1
            supplier_stats[item.best_supplier]['total_products'] += 1
            supplier_stats[item.best_supplier]['categories'].add(item.category)
            supplier_stats[item.best_supplier]['average_savings'].append(item.savings_percentage)
        
        # Вычисляем рыночные доли
        total_products = len(catalog)
        market_share = {}
        
        for supplier, stats in supplier_stats.items():
            market_share_percent = (stats['best_deals_count'] / total_products) * 100
            avg_savings = sum(stats['average_savings']) / len(stats['average_savings']) if stats['average_savings'] else 0
            
            market_share[supplier] = {
                'best_deals_count': stats['best_deals_count'],
                'market_share_percent': round(market_share_percent, 2),
                'categories_count': len(stats['categories']),
                'categories': list(stats['categories']),
                'average_savings_provided': round(avg_savings, 2)
            }
        
        # Сортируем по рыночной доле
        sorted_suppliers = sorted(market_share.items(), key=lambda x: x[1]['market_share_percent'], reverse=True)
        
        return dict(sorted_suppliers)
    
    # =============================================================================
    # CATALOG MAINTENANCE
    # =============================================================================
    
    def update_catalog_prices(self) -> Dict[str, int]:
        """
        Обновление цен в каталоге
        
        Returns:
            Статистика обновления
        """
        logger.info("Starting catalog price update")
        
        stats = {
            'products_checked': 0,
            'prices_updated': 0,
            'new_best_deals': 0,
            'errors': 0
        }
        
        # Получаем все активные товары
        all_products = self.db_manager.search_master_products("", limit=10000)
        
        for product in all_products:
            try:
                # Проверяем актуальность цен
                current_prices = self.db_manager.get_current_prices_for_product(str(product.product_id))
                
                if current_prices:
                    # Анализируем изменения цен
                    price_analysis = self.price_engine.analyze_product_prices(str(product.product_id))
                    
                    if price_analysis and price_analysis.savings_potential > 0:
                        stats['new_best_deals'] += 1
                    
                    stats['prices_updated'] += len(current_prices)
                
                stats['products_checked'] += 1
                
                if stats['products_checked'] % 100 == 0:
                    logger.info(f"Checked {stats['products_checked']} products")
            
            except Exception as e:
                logger.error(f"Error updating prices for product {product.product_id}: {e}")
                stats['errors'] += 1
        
        logger.info(f"Catalog update completed: {stats}")
        return stats
    
    def merge_duplicate_products(self, auto_merge_threshold: float = 0.95) -> Dict[str, int]:
        """
        Объединение дублирующихся товаров
        
        Args:
            auto_merge_threshold: Порог для автоматического объединения
            
        Returns:
            Статистика объединения
        """
        logger.info("Starting duplicate products merge")
        
        stats = {
            'matches_found': 0,
            'auto_merged': 0,
            'manual_review_required': 0,
            'errors': 0
        }
        
        # Получаем предложения для автоматического объединения
        auto_merge_suggestions = self.matching_engine.suggest_auto_merges(auto_merge_threshold)
        
        for suggestion in auto_merge_suggestions:
            try:
                if suggestion['confidence_level'] == 'high':
                    # Автоматическое объединение
                    success = self._merge_products(
                        suggestion['product_a']['product_id'],
                        suggestion['product_b']['product_id']
                    )
                    
                    if success:
                        stats['auto_merged'] += 1
                    else:
                        stats['manual_review_required'] += 1
                else:
                    stats['manual_review_required'] += 1
                
                stats['matches_found'] += 1
            
            except Exception as e:
                logger.error(f"Error merging products: {e}")
                stats['errors'] += 1
        
        logger.info(f"Duplicate merge completed: {stats}")
        return stats
    
    def _merge_products(self, product_a_id: str, product_b_id: str) -> bool:
        """
        Объединение двух товаров
        
        Args:
            product_a_id: ID первого товара
            product_b_id: ID второго товара
            
        Returns:
            bool: Успешность операции
        """
        try:
            with self.db_manager.get_session() as session:
                from models.unified_database import MasterProduct, SupplierPrice, ProductStatus
                
                # Получаем товары
                product_a = session.query(MasterProduct).filter_by(product_id=product_a_id).first()
                product_b = session.query(MasterProduct).filter_by(product_id=product_b_id).first()
                
                if not product_a or not product_b:
                    return False
                
                # Переносим все цены от product_b к product_a
                prices_b = session.query(SupplierPrice).filter_by(product_id=product_b_id).all()
                for price in prices_b:
                    price.product_id = product_a_id
                
                # Помечаем product_b как объединенный
                product_b.status = ProductStatus.MERGED
                
                session.commit()
                logger.info(f"Successfully merged products: {product_a_id} <- {product_b_id}")
                return True
        
        except Exception as e:
            logger.error(f"Error merging products {product_a_id} and {product_b_id}: {e}")
            return False
    
    # =============================================================================
    # EXPORT AND REPORTING
    # =============================================================================
    
    def export_catalog_to_dict(self, category: str = None) -> Dict[str, Any]:
        """
        Экспорт каталога в словарь для API
        
        Args:
            category: Фильтр по категории
            
        Returns:
            Словарь с данными каталога
        """
        catalog = self.generate_unified_catalog(category=category)
        stats = self.get_catalog_statistics()
        
        return {
            'metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'category_filter': category,
                'total_items': len(catalog),
                'statistics': {
                    'total_products': stats.total_products,
                    'total_suppliers': stats.total_suppliers,
                    'categories_count': stats.categories_count,
                    'average_savings': stats.average_savings,
                    'max_savings': stats.max_savings
                }
            },
            'catalog': [
                {
                    'product_id': item.product_id,
                    'name': item.standard_name,
                    'brand': item.brand,
                    'category': item.category,
                    'size': item.size,
                    'unit': item.unit,
                    'best_price': item.best_price,
                    'best_supplier': item.best_supplier,
                    'worst_price': item.worst_price,
                    'suppliers_count': item.suppliers_count,
                    'savings_percentage': item.savings_percentage,
                    'price_trend': item.price_trend,
                    'confidence_score': item.confidence_score,
                    'last_updated': item.last_updated.isoformat()
                }
                for item in catalog
            ]
        }
    
    def generate_procurement_report(self, required_products: List[Dict[str, Any]],
                                  budget_limit: float = None) -> Dict[str, Any]:
        """
        Генерация отчета по закупкам
        
        Args:
            required_products: Список требуемых товаров
            budget_limit: Бюджетное ограничение
            
        Returns:
            Отчет по закупкам
        """
        logger.info(f"Generating procurement report for {len(required_products)} products")
        
        # Получаем рекомендации
        recommendations = self.price_engine.generate_procurement_recommendations(
            required_products, budget_limit
        )
        
        # Вычисляем общую стоимость и экономию
        total_cost = sum(rec.recommended_price * req.get('quantity', 1) 
                        for rec, req in zip(recommendations, required_products))
        
        total_savings = sum(rec.potential_savings for rec in recommendations)
        average_confidence = sum(rec.confidence_score for rec in recommendations) / len(recommendations) if recommendations else 0
        
        return {
            'metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'products_requested': len(required_products),
                'recommendations_generated': len(recommendations),
                'budget_limit': budget_limit,
                'total_estimated_cost': round(total_cost, 2),
                'average_savings_percentage': round(total_savings / len(recommendations) if recommendations else 0, 2),
                'average_confidence_score': round(average_confidence, 2)
            },
            'recommendations': [
                {
                    'product_id': rec.product_id,
                    'product_name': rec.product_name,
                    'recommended_supplier': rec.recommended_supplier,
                    'recommended_price': rec.recommended_price,
                    'potential_savings': rec.potential_savings,
                    'confidence_score': rec.confidence_score,
                    'expires_at': rec.expires_at.isoformat(),
                    'reasoning': rec.reasoning,
                    'alternatives': rec.alternative_suppliers
                }
                for rec in recommendations
            ]
        } 