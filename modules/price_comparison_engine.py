"""
=============================================================================
MONITO PRICE COMPARISON ENGINE
=============================================================================
Версия: 3.0
Цель: Система сравнения цен с intelligent recommendations
=============================================================================
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
from collections import defaultdict

from models.unified_database import PriceHistory
from modules.unified_database_manager import UnifiedDatabaseManager
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class PriceAnalysis:
    """Анализ цен для товара"""
    product_id: str
    product_name: str
    best_price: Dict[str, Any]
    worst_price: Dict[str, Any]
    average_price: float
    median_price: float
    price_range: float
    savings_potential: float
    suppliers_count: int
    price_trend: str
    competitive_suppliers: List[Dict[str, Any]]
    last_updated: datetime

@dataclass
class SupplierAnalysis:
    """Анализ производительности поставщика"""
    supplier_name: str
    total_products: int
    best_price_products: int
    average_competitiveness: float
    price_volatility: float
    reliability_score: float
    strengths: List[str]
    weaknesses: List[str]
    recommended_categories: List[str]

@dataclass
class ProcurementRecommendation:
    """Рекомендация по закупке"""
    product_id: str
    product_name: str
    recommended_supplier: str
    recommended_price: float
    alternative_suppliers: List[Dict[str, Any]]
    potential_savings: float
    confidence_score: float
    expires_at: datetime
    reasoning: str

class PriceComparisonEngine:
    """
    Движок для сравнения цен и генерации рекомендаций
    """
    
    def __init__(self, db_manager: UnifiedDatabaseManager, 
                 price_tolerance: float = 0.05,
                 trend_analysis_days: int = 30):
        """
        Инициализация движка сравнения цен
        
        Args:
            db_manager: Менеджер базы данных
            price_tolerance: Толерантность для сравнения цен (5%)
            trend_analysis_days: Количество дней для анализа трендов
        """
        self.db_manager = db_manager
        self.price_tolerance = price_tolerance
        self.trend_analysis_days = trend_analysis_days
        
        # Коэффициенты для нормализации цен
        self.unit_base_conversions = {
            'weight': {'base_unit': 'g', 'conversions': {'kg': 1000, 'g': 1, 'lb': 453.592, 'oz': 28.3495}},
            'volume': {'base_unit': 'ml', 'conversions': {'l': 1000, 'ml': 1, 'gallon': 3785.41, 'fl_oz': 29.5735}},
            'count': {'base_unit': 'pcs', 'conversions': {'pcs': 1, 'box': 1, 'pack': 1, 'bottle': 1, 'can': 1}}
        }
        
        logger.info(f"Initialized PriceComparisonEngine with tolerance={price_tolerance}")
    
    # =============================================================================
    # CORE PRICE ANALYSIS METHODS
    # =============================================================================
    
    def analyze_product_prices(self, product_id: str) -> Optional[PriceAnalysis]:
        """
        Полный анализ цен для конкретного товара
        
        Args:
            product_id: ID товара
            
        Returns:
            PriceAnalysis: Детальный анализ цен
        """
        product = self.db_manager.get_master_product_with_prices(product_id)
        if not product:
            logger.warning(f"Product {product_id} not found")
            return None
        
        # Получаем актуальные цены
        current_prices = self.db_manager.get_current_prices_for_product(product_id)
        if not current_prices:
            logger.info(f"No current prices found for product {product_id}")
            return None
        
        # Нормализуем цены для корректного сравнения
        normalized_prices = []
        for price in current_prices:
            normalized = self._normalize_price_per_unit(price.price, product.size, product.unit)
            if normalized:
                normalized_prices.append({
                    'supplier': price.supplier_name,
                    'original_price': float(price.price),
                    'normalized_price': normalized,
                    'price_date': price.price_date,
                    'confidence': float(price.confidence_score) if price.confidence_score else 0.9
                })
        
        if not normalized_prices:
            return None
        
        # Сортируем по нормализованной цене
        normalized_prices.sort(key=lambda x: x['normalized_price'])
        
        # Вычисляем статистики
        prices_only = [p['normalized_price'] for p in normalized_prices]
        best_price = normalized_prices[0]
        worst_price = normalized_prices[-1]
        average_price = sum(prices_only) / len(prices_only)
        median_price = prices_only[len(prices_only) // 2]
        price_range = worst_price['normalized_price'] - best_price['normalized_price']
        
        # Потенциальная экономия
        savings_potential = 0
        if worst_price['normalized_price'] > best_price['normalized_price']:
            savings_potential = ((worst_price['normalized_price'] - best_price['normalized_price']) / 
                               worst_price['normalized_price']) * 100
        
        # Анализ тренда
        price_trend = self._calculate_price_trend(product_id)
        
        # Конкурентные поставщики (топ-3 по цене)
        competitive_suppliers = normalized_prices[:3]
        
        return PriceAnalysis(
            product_id=product_id,
            product_name=product.standard_name,
            best_price={
                'supplier': best_price['supplier'],
                'price': best_price['original_price'],
                'normalized_price': best_price['normalized_price'],
                'date': best_price['price_date']
            },
            worst_price={
                'supplier': worst_price['supplier'],
                'price': worst_price['original_price'],
                'normalized_price': worst_price['normalized_price'],
                'date': worst_price['price_date']
            },
            average_price=average_price,
            median_price=median_price,
            price_range=price_range,
            savings_potential=round(savings_potential, 2),
            suppliers_count=len(normalized_prices),
            price_trend=price_trend,
            competitive_suppliers=competitive_suppliers,
            last_updated=datetime.utcnow()
        )
    
    def get_best_deals_report(self, category: str = None, min_savings: float = 5.0, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Генерация отчета по лучшим предложениям
        
        Args:
            category: Фильтр по категории
            min_savings: Минимальная экономия в процентах
            limit: Максимальное количество результатов
            
        Returns:
            Список лучших предложений
        """
        logger.info(f"Generating best deals report for category: {category}")
        
        catalog = self.db_manager.get_unified_catalog(category=category, limit=1000)
        
        best_deals = []
        for item in catalog:
            if item['savings_percentage'] >= min_savings:
                # Получаем детальный анализ
                analysis = self.analyze_product_prices(item['product_id'])
                if analysis:
                    best_deals.append({
                        'product_id': item['product_id'],
                        'product_name': item['standard_name'],
                        'brand': item['brand'],
                        'category': item['category'],
                        'best_price': item['best_price'],
                        'worst_price': item['worst_price'],
                        'best_supplier': item['best_supplier'],
                        'savings_percentage': item['savings_percentage'],
                        'suppliers_count': item['suppliers_count'],
                        'price_trend': analysis.price_trend,
                        'confidence_score': self._calculate_deal_confidence(analysis)
                    })
        
        # Сортируем по потенциальной экономии
        best_deals.sort(key=lambda x: x['savings_percentage'], reverse=True)
        
        logger.info(f"Found {len(best_deals)} deals with min savings {min_savings}%")
        return best_deals[:limit]
    
    def _normalize_price_per_unit(self, price: Decimal, size: Decimal, unit: str) -> Optional[float]:
        """
        Нормализация цены к базовой единице измерения
        
        Args:
            price: Цена товара
            size: Размер упаковки
            unit: Единица измерения
            
        Returns:
            Нормализованная цена за базовую единицу
        """
        if not price or not size or not unit:
            return None
        
        unit_lower = unit.lower().strip()
        
        # Определяем тип единицы и коэффициент конвертации
        conversion_factor = None
        for unit_type, config in self.unit_base_conversions.items():
            if unit_lower in config['conversions']:
                conversion_factor = config['conversions'][unit_lower]
                break
        
        if conversion_factor is None:
            logger.warning(f"Unknown unit: {unit}")
            return None
        
        # Вычисляем цену за базовую единицу
        base_size = float(size) * conversion_factor
        if base_size == 0:
            return None
        
        price_per_base_unit = float(price) / base_size
        return round(price_per_base_unit, 4)
    
    def _calculate_price_trend(self, product_id: str) -> str:
        """
        Расчет тренда изменения цен
        
        Args:
            product_id: ID товара
            
        Returns:
            Тренд: 'increasing', 'decreasing', 'stable'
        """
        with self.db_manager.get_session() as session:
            # Получаем историю изменений за последний месяц
            cutoff_date = datetime.utcnow() - timedelta(days=self.trend_analysis_days)
            
            history = session.query(PriceHistory).filter(
                PriceHistory.product_id == product_id,
                PriceHistory.change_date >= cutoff_date
            ).order_by(PriceHistory.change_date.asc()).all()
            
            if len(history) < 2:
                return 'stable'
            
            # Вычисляем средний процент изменения
            total_change = 0
            change_count = 0
            
            for record in history:
                if record.change_percentage:
                    total_change += float(record.change_percentage)
                    change_count += 1
            
            if change_count == 0:
                return 'stable'
            
            average_change = total_change / change_count
            
            if average_change > 2:
                return 'increasing'
            elif average_change < -2:
                return 'decreasing'
            else:
                return 'stable'
    
    def _calculate_deal_confidence(self, analysis: PriceAnalysis) -> float:
        """
        Расчет уверенности в качестве предложения
        
        Args:
            analysis: Анализ цен товара
            
        Returns:
            Оценка уверенности от 0 до 1
        """
        confidence_factors = []
        
        # 1. Количество поставщиков (больше = лучше)
        supplier_factor = min(analysis.suppliers_count / 5.0, 1.0)
        confidence_factors.append(supplier_factor * 0.3)
        
        # 2. Размер экономии (больше = лучше, но не слишком подозрительно)
        if analysis.savings_potential <= 50:
            savings_factor = analysis.savings_potential / 50.0
        else:
            savings_factor = max(0.5, 1.0 - (analysis.savings_potential - 50) / 100.0)
        confidence_factors.append(savings_factor * 0.4)
        
        # 3. Стабильность тренда (стабильный или снижающийся = лучше)
        trend_factor = 1.0 if analysis.price_trend in ['stable', 'decreasing'] else 0.7
        confidence_factors.append(trend_factor * 0.3)
        
        return min(sum(confidence_factors), 1.0)
    
    # =============================================================================
    # SUPPLIER ANALYSIS
    # =============================================================================
    
    def analyze_supplier_competitiveness(self, supplier_name: str) -> SupplierAnalysis:
        """
        Анализ конкурентоспособности поставщика
        
        Args:
            supplier_name: Имя поставщика
            
        Returns:
            SupplierAnalysis: Детальный анализ поставщика
        """
        logger.info(f"Analyzing supplier competitiveness: {supplier_name}")
        
        # Получаем базовую информацию о поставщике
        performance = self.db_manager.get_supplier_performance(supplier_name)
        
        if not performance:
            logger.warning(f"No performance data found for supplier: {supplier_name}")
            return SupplierAnalysis(
                supplier_name=supplier_name,
                total_products=0,
                best_price_products=0,
                average_competitiveness=0.0,
                price_volatility=0.0,
                reliability_score=0.0,
                strengths=[],
                weaknesses=[],
                recommended_categories=[]
            )
        
        # Анализируем по категориям
        category_performance = self._analyze_supplier_by_categories(supplier_name)
        
        # Анализируем волатильность цен
        price_volatility = self._calculate_supplier_price_volatility(supplier_name)
        
        # Определяем сильные и слабые стороны
        strengths, weaknesses = self._identify_supplier_strengths_weaknesses(performance, category_performance, price_volatility)
        
        # Рекомендуемые категории
        recommended_categories = self._get_recommended_categories(category_performance)
        
        return SupplierAnalysis(
            supplier_name=supplier_name,
            total_products=performance['total_products'],
            best_price_products=performance['best_price_products'],
            average_competitiveness=performance['price_competitiveness'],
            price_volatility=price_volatility,
            reliability_score=performance['reliability_score'],
            strengths=strengths,
            weaknesses=weaknesses,
            recommended_categories=recommended_categories
        )
    
    def _analyze_supplier_by_categories(self, supplier_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Анализ поставщика по категориям товаров
        
        Args:
            supplier_name: Имя поставщика
            
        Returns:
            Словарь с анализом по категориям
        """
        with self.db_manager.get_session() as session:
            # Получаем все товары поставщика с ценами
            from sqlalchemy import func
            from models.unified_database import MasterProduct, SupplierPrice
            
            results = session.query(
                MasterProduct.category,
                func.count(MasterProduct.product_id).label('products_count'),
                func.avg(SupplierPrice.price).label('avg_price')
            ).join(SupplierPrice).filter(
                SupplierPrice.supplier_name == supplier_name
            ).group_by(MasterProduct.category).all()
            
            category_analysis = {}
            for result in results:
                category = result.category
                
                # Подсчитываем, сколько товаров в этой категории имеют лучшую цену от этого поставщика
                best_price_count = 0
                category_products = session.query(MasterProduct).filter_by(category=category).all()
                
                for product in category_products:
                    best_price = session.query(func.min(SupplierPrice.price)).filter_by(
                        product_id=product.product_id
                    ).scalar()
                    
                    supplier_price = session.query(SupplierPrice.price).filter_by(
                        product_id=product.product_id,
                        supplier_name=supplier_name
                    ).scalar()
                    
                    if supplier_price and best_price and abs(float(supplier_price) - float(best_price)) < 0.01:
                        best_price_count += 1
                
                competitiveness = (best_price_count / result.products_count * 100) if result.products_count > 0 else 0
                
                category_analysis[category] = {
                    'products_count': result.products_count,
                    'best_price_products': best_price_count,
                    'competitiveness': round(competitiveness, 2),
                    'avg_price': float(result.avg_price) if result.avg_price else 0
                }
            
            return category_analysis
    
    def _calculate_supplier_price_volatility(self, supplier_name: str) -> float:
        """
        Расчет волатильности цен поставщика
        
        Args:
            supplier_name: Имя поставщика
            
        Returns:
            Показатель волатильности (стандартное отклонение изменений цен)
        """
        with self.db_manager.get_session() as session:
            # Получаем историю изменений цен за последние 3 месяца
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            price_changes = session.query(PriceHistory.change_percentage).filter(
                PriceHistory.supplier_name == supplier_name,
                PriceHistory.change_date >= cutoff_date,
                PriceHistory.change_percentage.isnot(None)
            ).all()
            
            if len(price_changes) < 2:
                return 0.0
            
            changes = [float(change.change_percentage) for change in price_changes]
            
            # Вычисляем стандартное отклонение
            mean_change = sum(changes) / len(changes)
            variance = sum((change - mean_change) ** 2 for change in changes) / len(changes)
            volatility = variance ** 0.5
            
            return round(volatility, 2)
    
    def _identify_supplier_strengths_weaknesses(self, performance: Dict[str, Any], 
                                              category_performance: Dict[str, Dict[str, Any]], 
                                              price_volatility: float) -> Tuple[List[str], List[str]]:
        """
        Определение сильных и слабых сторон поставщика
        
        Args:
            performance: Общая производительность
            category_performance: Производительность по категориям
            price_volatility: Волатильность цен
            
        Returns:
            Кортеж со списками сильных и слабых сторон
        """
        strengths = []
        weaknesses = []
        
        # Анализируем общую конкурентоспособность
        if performance['price_competitiveness'] >= 70:
            strengths.append("Высокая ценовая конкурентоспособность")
        elif performance['price_competitiveness'] <= 30:
            weaknesses.append("Низкая ценовая конкурентоспособность")
        
        # Анализируем надежность
        if performance['reliability_score'] >= 0.8:
            strengths.append("Высокая надежность")
        elif performance['reliability_score'] <= 0.5:
            weaknesses.append("Низкая надежность")
        
        # Анализируем ассортимент
        if performance['total_products'] >= 100:
            strengths.append("Широкий ассортимент")
        elif performance['total_products'] <= 20:
            weaknesses.append("Ограниченный ассортимент")
        
        # Анализируем стабильность цен
        if price_volatility <= 5:
            strengths.append("Стабильные цены")
        elif price_volatility >= 15:
            weaknesses.append("Высокая волатильность цен")
        
        # Анализируем категории
        strong_categories = [cat for cat, data in category_performance.items() if data['competitiveness'] >= 60]
        if len(strong_categories) >= 3:
            strengths.append(f"Лидирует в {len(strong_categories)} категориях")
        
        weak_categories = [cat for cat, data in category_performance.items() if data['competitiveness'] <= 20]
        if len(weak_categories) >= 2:
            weaknesses.append(f"Слабые позиции в {len(weak_categories)} категориях")
        
        return strengths, weaknesses
    
    def _get_recommended_categories(self, category_performance: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Получение рекомендуемых категорий для закупок у поставщика
        
        Args:
            category_performance: Производительность по категориям
            
        Returns:
            Список рекомендуемых категорий
        """
        # Сортируем категории по конкурентоспособности
        sorted_categories = sorted(
            category_performance.items(),
            key=lambda x: x[1]['competitiveness'],
            reverse=True
        )
        
        # Берем топ категории с конкурентоспособностью >= 50%
        recommended = [cat for cat, data in sorted_categories if data['competitiveness'] >= 50]
        
        return recommended[:5]  # Максимум 5 категорий
    
    # =============================================================================
    # PROCUREMENT RECOMMENDATIONS
    # =============================================================================
    
    def generate_procurement_recommendations(self, required_products: List[Dict[str, Any]], 
                                           budget_limit: float = None) -> List[ProcurementRecommendation]:
        """
        Генерация рекомендаций по закупкам
        
        Args:
            required_products: Список требуемых товаров с количествами
            budget_limit: Бюджетное ограничение
            
        Returns:
            Список рекомендаций по закупкам
        """
        logger.info(f"Generating procurement recommendations for {len(required_products)} products")
        
        recommendations = []
        total_cost = 0
        
        for required_product in required_products:
            # Ищем товар в каталоге
            product_name = required_product.get('name', '')
            quantity = required_product.get('quantity', 1)
            
            # Поиск похожих товаров
            similar_products = self.db_manager.search_master_products(product_name, limit=5)
            
            if not similar_products:
                logger.warning(f"No products found for: {product_name}")
                continue
            
            best_match = similar_products[0]
            analysis = self.analyze_product_prices(str(best_match.product_id))
            
            if not analysis:
                continue
            
            # Проверяем бюджетные ограничения
            recommended_cost = analysis.best_price['price'] * quantity
            if budget_limit and total_cost + recommended_cost > budget_limit:
                # Ищем альтернативы в пределах бюджета
                remaining_budget = budget_limit - total_cost
                max_unit_price = remaining_budget / quantity
                
                # Фильтруем альтернативы по цене
                affordable_suppliers = [
                    supplier for supplier in analysis.competitive_suppliers
                    if supplier['original_price'] <= max_unit_price
                ]
                
                if not affordable_suppliers:
                    logger.warning(f"Product {product_name} exceeds budget limit")
                    continue
                
                best_supplier = affordable_suppliers[0]
                recommended_cost = best_supplier['original_price'] * quantity
            else:
                best_supplier = analysis.competitive_suppliers[0]
            
            # Создаем рекомендацию
            recommendation = ProcurementRecommendation(
                product_id=str(best_match.product_id),
                product_name=best_match.standard_name,
                recommended_supplier=best_supplier['supplier'],
                recommended_price=best_supplier['original_price'],
                alternative_suppliers=analysis.competitive_suppliers[1:4],  # Топ-3 альтернативы
                potential_savings=analysis.savings_potential,
                confidence_score=self._calculate_deal_confidence(analysis),
                expires_at=datetime.utcnow() + timedelta(days=7),  # Рекомендация действует неделю
                reasoning=self._generate_recommendation_reasoning(analysis, best_supplier)
            )
            
            recommendations.append(recommendation)
            total_cost += recommended_cost
        
        logger.info(f"Generated {len(recommendations)} procurement recommendations")
        return recommendations
    
    def _generate_recommendation_reasoning(self, analysis: PriceAnalysis, selected_supplier: Dict[str, Any]) -> str:
        """
        Генерация обоснования рекомендации
        
        Args:
            analysis: Анализ цен товара
            selected_supplier: Выбранный поставщик
            
        Returns:
            Текстовое обоснование
        """
        reasons = []
        
        # Ценовое преимущество
        if analysis.savings_potential > 0:
            reasons.append(f"Экономия {analysis.savings_potential}% по сравнению с худшим предложением")
        
        # Количество альтернатив
        if analysis.suppliers_count > 3:
            reasons.append(f"Широкий выбор: {analysis.suppliers_count} поставщиков")
        
        # Тренд цен
        if analysis.price_trend == 'decreasing':
            reasons.append("Цены снижаются")
        elif analysis.price_trend == 'stable':
            reasons.append("Стабильные цены")
        elif analysis.price_trend == 'increasing':
            reasons.append("Цены растут - рекомендуется закупиться")
        
        return "; ".join(reasons) if reasons else "Лучшее доступное предложение"
    
    # =============================================================================
    # MARKET ANALYSIS
    # =============================================================================
    
    def get_market_overview(self) -> Dict[str, Any]:
        """
        Получение обзора рынка
        
        Returns:
            Словарь с обзором рынка
        """
        logger.info("Generating market overview")
        
        # Общая статистика
        stats = self.db_manager.get_system_statistics()
        
        # Топ категории по экономии
        catalog = self.db_manager.get_unified_catalog(limit=1000)
        
        # Группируем по категориям
        category_savings = defaultdict(list)
        for item in catalog:
            if item['savings_percentage'] > 0:
                category_savings[item['category']].append(item['savings_percentage'])
        
        # Вычисляем среднюю экономию по категориям
        category_analysis = {}
        for category, savings_list in category_savings.items():
            if savings_list:
                category_analysis[category] = {
                    'average_savings': round(sum(savings_list) / len(savings_list), 2),
                    'max_savings': round(max(savings_list), 2),
                    'products_count': len(savings_list)
                }
        
        # Топ категории по экономии
        top_savings_categories = sorted(
            category_analysis.items(),
            key=lambda x: x[1]['average_savings'],
            reverse=True
        )[:5]
        
        # Топ предложения
        top_deals = self.get_best_deals_report(limit=10)
        
        return {
            'statistics': stats,
            'top_savings_categories': [
                {
                    'category': cat,
                    'average_savings': data['average_savings'],
                    'max_savings': data['max_savings'],
                    'products_count': data['products_count']
                }
                for cat, data in top_savings_categories
            ],
            'top_deals': top_deals,
            'market_trends': self._analyze_market_trends(),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _analyze_market_trends(self) -> Dict[str, Any]:
        """
        Анализ рыночных трендов
        
        Returns:
            Словарь с трендами
        """
        with self.db_manager.get_session() as session:
            # Анализируем изменения цен за последний месяц
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            from sqlalchemy import func
            
            trends = session.query(
                func.count(PriceHistory.history_id).label('total_changes'),
                func.avg(PriceHistory.change_percentage).label('avg_change'),
                func.sum(func.case([(PriceHistory.change_percentage > 0, 1)], else_=0)).label('price_increases'),
                func.sum(func.case([(PriceHistory.change_percentage < 0, 1)], else_=0)).label('price_decreases')
            ).filter(PriceHistory.change_date >= cutoff_date).first()
            
            if not trends or trends.total_changes == 0:
                return {
                    'overall_trend': 'stable',
                    'price_changes_count': 0,
                    'average_change': 0,
                    'volatility': 'low'
                }
            
            # Определяем общий тренд
            overall_trend = 'stable'
            if trends.avg_change > 2:
                overall_trend = 'increasing'
            elif trends.avg_change < -2:
                overall_trend = 'decreasing'
            
            # Определяем волатильность
            volatility = 'low'
            if trends.total_changes > 100:
                volatility = 'high'
            elif trends.total_changes > 50:
                volatility = 'medium'
            
            return {
                'overall_trend': overall_trend,
                'price_changes_count': trends.total_changes,
                'average_change': round(float(trends.avg_change), 2) if trends.avg_change else 0,
                'price_increases': trends.price_increases,
                'price_decreases': trends.price_decreases,
                'volatility': volatility
            } 