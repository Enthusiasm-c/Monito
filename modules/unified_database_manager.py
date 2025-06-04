"""
=============================================================================
MONITO UNIFIED DATABASE MANAGER
=============================================================================
Версия: 3.0
Цель: Менеджер для работы с unified базой данных поставщиков
=============================================================================
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import create_engine, and_, or_, func, desc, asc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from contextlib import contextmanager

from models.unified_database import (
    Base, MasterProduct, SupplierPrice, ProductMatch, PriceHistory,
    Supplier, Category, ProcurementRecommendation, SystemMetric,
    ProductStatus, MatchType, AvailabilityStatus, DataSource,
    ChangeReason, CompanyType, SupplierStatus, RecommendationStatus
)
from utils.logger import get_logger

logger = get_logger(__name__)

class UnifiedDatabaseManager:
    """
    Менеджер для работы с unified database системой сравнения цен
    """
    
    def __init__(self, database_url: str = None):
        """
        Инициализация менеджера базы данных
        
        Args:
            database_url: URL подключения к базе данных
        """
        if not database_url:
            database_url = os.getenv('DATABASE_URL', 'sqlite:///monito_unified.db')
        
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        logger.info(f"Initialized UnifiedDatabaseManager with URL: {database_url}")
    
    def create_tables(self):
        """Создание всех таблиц в базе данных"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
            self._initialize_default_data()
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def _initialize_default_data(self):
        """Инициализация базовых данных"""
        with self.get_session() as session:
            # Создаем основные категории, если их нет
            if session.query(Category).count() == 0:
                default_categories = [
                    {'name': 'beverages', 'description': 'Напитки всех видов'},
                    {'name': 'canned_food', 'description': 'Консервированные продукты'},
                    {'name': 'pasta_noodles', 'description': 'Макароны и лапша'},
                    {'name': 'cooking_oil', 'description': 'Масла для приготовления пищи'},
                    {'name': 'spices_seasonings', 'description': 'Специи и приправы'},
                    {'name': 'dairy_products', 'description': 'Молочные продукты'},
                    {'name': 'snacks', 'description': 'Снеки и закуски'},
                    {'name': 'rice_grains', 'description': 'Рис и злаки'},
                    {'name': 'frozen_food', 'description': 'Замороженные продукты'},
                    {'name': 'household_items', 'description': 'Хозяйственные товары'}
                ]
                
                for cat_data in default_categories:
                    category = Category(
                        category_name=cat_data['name'],
                        description=cat_data['description']
                    )
                    session.add(category)
                
                session.commit()
                logger.info("Default categories initialized")
    
    @contextmanager
    def get_session(self) -> Session:
        """Context manager для работы с сессией"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    # =============================================================================
    # MASTER PRODUCTS OPERATIONS
    # =============================================================================
    
    def create_master_product(self, product_data: Dict[str, Any]) -> MasterProduct:
        """
        Создание нового master product
        
        Args:
            product_data: Данные товара
            
        Returns:
            MasterProduct: Созданный товар
        """
        with self.get_session() as session:
            # Проверяем, что категория существует
            if product_data.get('category'):
                category = session.query(Category).filter_by(
                    category_name=product_data['category']
                ).first()
                if not category:
                    # Создаем новую категорию
                    category = Category(
                        category_name=product_data['category'],
                        description=f"Автоматически созданная категория: {product_data['category']}"
                    )
                    session.add(category)
                    session.flush()
            
            # Создаем master product
            product = MasterProduct(
                standard_name=product_data['standard_name'],
                brand=product_data.get('brand'),
                category=product_data['category'],
                size=Decimal(str(product_data['size'])) if product_data.get('size') else None,
                unit=product_data.get('unit'),
                description=product_data.get('description'),
                status=ProductStatus.ACTIVE
            )
            
            session.add(product)
            session.flush()
            
            logger.info(f"Created master product: {product.standard_name} (ID: {product.product_id})")
            return product
    
    def find_master_product_by_name(self, name: str, brand: str = None) -> Optional[MasterProduct]:
        """
        Поиск master product по имени и бренду
        
        Args:
            name: Название товара
            brand: Бренд товара (опционально)
            
        Returns:
            MasterProduct или None
        """
        with self.get_session() as session:
            query = session.query(MasterProduct).filter(
                MasterProduct.standard_name.ilike(f"%{name}%"),
                MasterProduct.status == ProductStatus.ACTIVE
            )
            
            if brand:
                query = query.filter(MasterProduct.brand.ilike(f"%{brand}%"))
            
            return query.first()
    
    def search_master_products(self, search_term: str, category: str = None, limit: int = 50) -> List[MasterProduct]:
        """
        Поиск master products по различным критериям
        
        Args:
            search_term: Поисковый термин
            category: Категория товара
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных товаров
        """
        with self.get_session() as session:
            query = session.query(MasterProduct).filter(
                MasterProduct.status == ProductStatus.ACTIVE
            )
            
            if search_term:
                search_pattern = f"%{search_term}%"
                query = query.filter(
                    or_(
                        MasterProduct.standard_name.ilike(search_pattern),
                        MasterProduct.brand.ilike(search_pattern),
                        MasterProduct.description.ilike(search_pattern)
                    )
                )
            
            if category:
                query = query.filter(MasterProduct.category == category)
            
            return query.limit(limit).all()
    
    def get_master_product_with_prices(self, product_id: str) -> Optional[MasterProduct]:
        """
        Получение master product с ценами поставщиков
        
        Args:
            product_id: ID товара
            
        Returns:
            MasterProduct с загруженными ценами
        """
        with self.get_session() as session:
            product = session.query(MasterProduct).filter_by(product_id=product_id).first()
            if product:
                # Загружаем связанные цены
                prices = session.query(SupplierPrice).filter_by(product_id=product_id).all()
                product.current_prices = prices
            return product
    
    # =============================================================================
    # SUPPLIER PRICES OPERATIONS
    # =============================================================================
    
    def add_supplier_price(self, price_data: Dict[str, Any]) -> SupplierPrice:
        """
        Добавление цены поставщика
        
        Args:
            price_data: Данные цены
            
        Returns:
            SupplierPrice: Созданная цена
        """
        with self.get_session() as session:
            # Проверяем существование товара
            product = session.query(MasterProduct).filter_by(
                product_id=price_data['product_id']
            ).first()
            
            if not product:
                raise ValueError(f"Product with ID {price_data['product_id']} not found")
            
            # Проверяем, есть ли уже цена от этого поставщика сегодня
            existing_price = session.query(SupplierPrice).filter_by(
                product_id=price_data['product_id'],
                supplier_name=price_data['supplier_name'],
                price_date=price_data.get('price_date', date.today())
            ).first()
            
            if existing_price:
                # Обновляем существующую цену
                old_price = existing_price.price
                existing_price.price = Decimal(str(price_data['price']))
                existing_price.original_name = price_data['original_name']
                existing_price.last_seen = datetime.utcnow()
                
                # Создаем запись в истории цен
                if old_price != existing_price.price:
                    self._create_price_history(
                        product_id=price_data['product_id'],
                        supplier_name=price_data['supplier_name'],
                        old_price=old_price,
                        new_price=existing_price.price,
                        session=session
                    )
                
                logger.info(f"Updated price for {price_data['supplier_name']}: {old_price} -> {existing_price.price}")
                return existing_price
            else:
                # Создаем новую цену
                supplier_price = SupplierPrice(
                    product_id=price_data['product_id'],
                    supplier_name=price_data['supplier_name'],
                    original_name=price_data['original_name'],
                    price=Decimal(str(price_data['price'])),
                    currency=price_data.get('currency', 'IDR'),
                    price_date=price_data.get('price_date', date.today()),
                    supplier_product_code=price_data.get('supplier_product_code'),
                    minimum_order_quantity=price_data.get('minimum_order_quantity', 1),
                    availability_status=AvailabilityStatus.UNKNOWN,
                    confidence_score=Decimal(str(price_data.get('confidence_score', 0.9))),
                    data_source=DataSource.EXCEL_UPLOAD
                )
                
                session.add(supplier_price)
                session.flush()
                
                # Создаем запись в истории цен (первая цена)
                self._create_price_history(
                    product_id=price_data['product_id'],
                    supplier_name=price_data['supplier_name'],
                    old_price=None,
                    new_price=supplier_price.price,
                    change_reason=ChangeReason.NEW_SUPPLIER,
                    session=session
                )
                
                logger.info(f"Added new price for {price_data['supplier_name']}: {supplier_price.price}")
                return supplier_price
    
    def get_current_prices_for_product(self, product_id: str, days_back: int = 30) -> List[SupplierPrice]:
        """
        Получение актуальных цен для товара
        
        Args:
            product_id: ID товара
            days_back: Количество дней назад для поиска актуальных цен
            
        Returns:
            Список актуальных цен
        """
        with self.get_session() as session:
            cutoff_date = date.today() - timedelta(days=days_back)
            
            return session.query(SupplierPrice).filter(
                SupplierPrice.product_id == product_id,
                SupplierPrice.price_date >= cutoff_date
            ).order_by(SupplierPrice.price.asc()).all()
    
    def get_best_price_for_product(self, product_id: str) -> Optional[SupplierPrice]:
        """
        Получение лучшей цены для товара
        
        Args:
            product_id: ID товара
            
        Returns:
            SupplierPrice с лучшей ценой
        """
        prices = self.get_current_prices_for_product(product_id)
        return prices[0] if prices else None
    
    def _create_price_history(self, product_id: str, supplier_name: str, 
                             old_price: Decimal, new_price: Decimal, 
                             change_reason: ChangeReason = ChangeReason.PRICE_UPDATE,
                             session: Session = None):
        """
        Создание записи в истории цен
        
        Args:
            product_id: ID товара
            supplier_name: Имя поставщика
            old_price: Старая цена
            new_price: Новая цена
            change_reason: Причина изменения
            session: Сессия базы данных
        """
        if session is None:
            with self.get_session() as session:
                self._create_price_history(product_id, supplier_name, old_price, new_price, change_reason, session)
                return
        
        history = PriceHistory(
            product_id=product_id,
            supplier_name=supplier_name,
            old_price=old_price,
            new_price=new_price,
            change_reason=change_reason
        )
        
        session.add(history)
    
    # =============================================================================
    # PRODUCT MATCHING OPERATIONS
    # =============================================================================
    
    def create_product_match(self, product_a_id: str, product_b_id: str, 
                           similarity_score: float, match_type: MatchType,
                           details: Dict[str, float] = None) -> ProductMatch:
        """
        Создание записи о совпадении товаров
        
        Args:
            product_a_id: ID первого товара
            product_b_id: ID второго товара
            similarity_score: Оценка схожести
            match_type: Тип совпадения
            details: Детальные оценки схожести
            
        Returns:
            ProductMatch: Созданное совпадение
        """
        with self.get_session() as session:
            # Проверяем, что такого match еще нет
            existing_match = session.query(ProductMatch).filter(
                or_(
                    and_(ProductMatch.product_a_id == product_a_id, ProductMatch.product_b_id == product_b_id),
                    and_(ProductMatch.product_a_id == product_b_id, ProductMatch.product_b_id == product_a_id)
                )
            ).first()
            
            if existing_match:
                logger.warning(f"Product match already exists: {product_a_id} <-> {product_b_id}")
                return existing_match
            
            match = ProductMatch(
                product_a_id=product_a_id,
                product_b_id=product_b_id,
                similarity_score=Decimal(str(similarity_score)),
                match_type=match_type,
                name_similarity=Decimal(str(details.get('name_similarity', 0))) if details else None,
                brand_similarity=Decimal(str(details.get('brand_similarity', 0))) if details else None,
                size_similarity=Decimal(str(details.get('size_similarity', 0))) if details else None
            )
            
            session.add(match)
            session.flush()
            
            logger.info(f"Created product match: {product_a_id} <-> {product_b_id} (score: {similarity_score})")
            return match
    
    def get_product_matches(self, product_id: str, min_similarity: float = 0.8) -> List[ProductMatch]:
        """
        Получение совпадений для товара
        
        Args:
            product_id: ID товара
            min_similarity: Минимальная схожесть
            
        Returns:
            Список совпадений
        """
        with self.get_session() as session:
            return session.query(ProductMatch).filter(
                or_(
                    ProductMatch.product_a_id == product_id,
                    ProductMatch.product_b_id == product_id
                ),
                ProductMatch.similarity_score >= min_similarity,
                ProductMatch.match_type != MatchType.REJECTED
            ).all()
    
    def get_unreviewed_matches(self, limit: int = 100) -> List[ProductMatch]:
        """
        Получение непроверенных совпадений
        
        Args:
            limit: Максимальное количество результатов
            
        Returns:
            Список непроверенных совпадений
        """
        with self.get_session() as session:
            return session.query(ProductMatch).filter(
                ProductMatch.reviewed == False,
                ProductMatch.similarity_score >= 0.7
            ).order_by(ProductMatch.similarity_score.desc()).limit(limit).all()
    
    def approve_product_match(self, match_id: str, reviewer: str) -> bool:
        """
        Одобрение совпадения товаров
        
        Args:
            match_id: ID совпадения
            reviewer: Имя проверяющего
            
        Returns:
            bool: Успешность операции
        """
        with self.get_session() as session:
            match = session.query(ProductMatch).filter_by(match_id=match_id).first()
            if not match:
                return False
            
            match.reviewed = True
            match.approved = True
            match.reviewed_by = reviewer
            match.reviewed_at = datetime.utcnow()
            
            logger.info(f"Approved product match: {match_id} by {reviewer}")
            return True
    
    # =============================================================================
    # SUPPLIER OPERATIONS
    # =============================================================================
    
    def create_or_update_supplier(self, supplier_data: Dict[str, Any]) -> Supplier:
        """
        Создание или обновление поставщика
        
        Args:
            supplier_data: Данные поставщика
            
        Returns:
            Supplier: Созданный или обновленный поставщик
        """
        with self.get_session() as session:
            supplier = session.query(Supplier).filter_by(
                supplier_name=supplier_data['supplier_name']
            ).first()
            
            if supplier:
                # Обновляем существующего поставщика
                for key, value in supplier_data.items():
                    if hasattr(supplier, key) and value is not None:
                        setattr(supplier, key, value)
                supplier.last_price_update = datetime.utcnow()
                logger.info(f"Updated supplier: {supplier.supplier_name}")
            else:
                # Создаем нового поставщика
                supplier = Supplier(**supplier_data)
                session.add(supplier)
                session.flush()
                logger.info(f"Created new supplier: {supplier.supplier_name}")
            
            return supplier
    
    def get_supplier_performance(self, supplier_name: str) -> Dict[str, Any]:
        """
        Получение показателей производительности поставщика
        
        Args:
            supplier_name: Имя поставщика
            
        Returns:
            Словарь с показателями
        """
        with self.get_session() as session:
            supplier = session.query(Supplier).filter_by(supplier_name=supplier_name).first()
            if not supplier:
                return {}
            
            # Количество товаров
            total_products = session.query(SupplierPrice).filter_by(supplier_name=supplier_name).count()
            
            # Количество товаров с лучшими ценами
            best_price_count = 0
            for price in session.query(SupplierPrice).filter_by(supplier_name=supplier_name).all():
                best_price = session.query(func.min(SupplierPrice.price)).filter_by(
                    product_id=price.product_id
                ).scalar()
                if price.price == best_price:
                    best_price_count += 1
            
            competitiveness = (best_price_count / total_products * 100) if total_products > 0 else 0
            
            return {
                'supplier_name': supplier_name,
                'total_products': total_products,
                'best_price_products': best_price_count,
                'price_competitiveness': round(competitiveness, 2),
                'reliability_score': float(supplier.reliability_score) if supplier.reliability_score else 0
            }
    
    # =============================================================================
    # UNIFIED CATALOG OPERATIONS
    # =============================================================================
    
    def get_unified_catalog(self, category: str = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Получение unified catalog с лучшими ценами
        
        Args:
            category: Фильтр по категории
            limit: Максимальное количество товаров
            
        Returns:
            Список товаров с лучшими ценами
        """
        with self.get_session() as session:
            query = session.query(
                MasterProduct.product_id,
                MasterProduct.standard_name,
                MasterProduct.brand,
                MasterProduct.category,
                MasterProduct.size,
                MasterProduct.unit,
                func.min(SupplierPrice.price).label('best_price'),
                func.max(SupplierPrice.price).label('worst_price'),
                func.count(func.distinct(SupplierPrice.supplier_name)).label('suppliers_count')
            ).join(SupplierPrice).filter(
                MasterProduct.status == ProductStatus.ACTIVE,
                SupplierPrice.price_date >= date.today() - timedelta(days=30)
            )
            
            if category:
                query = query.filter(MasterProduct.category == category)
            
            results = query.group_by(
                MasterProduct.product_id,
                MasterProduct.standard_name,
                MasterProduct.brand,
                MasterProduct.category,
                MasterProduct.size,
                MasterProduct.unit
            ).limit(limit).all()
            
            catalog = []
            for result in results:
                # Получаем лучшего поставщика
                best_supplier = session.query(SupplierPrice.supplier_name).filter(
                    SupplierPrice.product_id == result.product_id,
                    SupplierPrice.price == result.best_price
                ).first()
                
                # Вычисляем экономию
                savings_percentage = 0
                if result.worst_price and result.best_price and result.worst_price > result.best_price:
                    savings_percentage = ((result.worst_price - result.best_price) / result.worst_price) * 100
                
                catalog.append({
                    'product_id': str(result.product_id),
                    'standard_name': result.standard_name,
                    'brand': result.brand,
                    'category': result.category,
                    'size': float(result.size) if result.size else None,
                    'unit': result.unit,
                    'best_price': float(result.best_price),
                    'worst_price': float(result.worst_price),
                    'best_supplier': best_supplier.supplier_name if best_supplier else None,
                    'suppliers_count': result.suppliers_count,
                    'savings_percentage': round(savings_percentage, 2)
                })
            
            return sorted(catalog, key=lambda x: x['savings_percentage'], reverse=True)
    
    def get_price_comparison_for_product(self, product_id: str) -> Dict[str, Any]:
        """
        Получение сравнения цен для конкретного товара
        
        Args:
            product_id: ID товара
            
        Returns:
            Словарь с данными сравнения
        """
        with self.get_session() as session:
            product = session.query(MasterProduct).filter_by(product_id=product_id).first()
            if not product:
                return {}
            
            prices = self.get_current_prices_for_product(product_id)
            if not prices:
                return {'product': product.to_dict(), 'prices': []}
            
            best_price = min(prices, key=lambda x: x.price)
            worst_price = max(prices, key=lambda x: x.price)
            
            savings = 0
            if worst_price.price > best_price.price:
                savings = ((worst_price.price - best_price.price) / worst_price.price) * 100
            
            return {
                'product': product.to_dict(),
                'prices': [price.to_dict() for price in prices],
                'best_price': best_price.to_dict(),
                'worst_price': worst_price.to_dict(),
                'potential_savings': round(savings, 2),
                'suppliers_count': len(prices)
            }
    
    # =============================================================================
    # ANALYTICS AND REPORTING
    # =============================================================================
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """
        Получение общей статистики системы
        
        Returns:
            Словарь со статистикой
        """
        with self.get_session() as session:
            stats = {
                'total_products': session.query(MasterProduct).filter_by(status=ProductStatus.ACTIVE).count(),
                'total_suppliers': session.query(Supplier).filter_by(status=SupplierStatus.ACTIVE).count(),
                'total_prices': session.query(SupplierPrice).count(),
                'total_categories': session.query(Category).count(),
                'pending_matches': session.query(ProductMatch).filter_by(reviewed=False).count(),
                'last_price_update': session.query(func.max(SupplierPrice.last_seen)).scalar()
            }
            
            # Добавляем информацию о ценовых трендах
            recent_changes = session.query(PriceHistory).filter(
                PriceHistory.change_date >= datetime.utcnow() - timedelta(days=7)
            ).count()
            
            stats['recent_price_changes'] = recent_changes
            
            return stats
    
    def record_system_metric(self, metric_name: str, metric_value: float, 
                           entity_type: str = None, entity_id: str = None,
                           metadata: Dict[str, Any] = None):
        """
        Запись системной метрики
        
        Args:
            metric_name: Название метрики
            metric_value: Значение метрики
            entity_type: Тип сущности
            entity_id: ID сущности
            metadata: Дополнительные данные
        """
        with self.get_session() as session:
            metric = SystemMetric(
                metric_name=metric_name,
                metric_value=Decimal(str(metric_value)),
                entity_type=entity_type,
                entity_id=entity_id,
                metadata=metadata
            )
            session.add(metric)
            logger.info(f"Recorded metric: {metric_name} = {metric_value}")
    
    # =============================================================================
    # BULK OPERATIONS
    # =============================================================================
    
    def bulk_import_products_and_prices(self, supplier_name: str, products_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Массовый импорт товаров и цен от поставщика
        
        Args:
            supplier_name: Имя поставщика
            products_data: Список данных товаров с ценами
            
        Returns:
            Статистика импорта
        """
        stats = {
            'products_created': 0,
            'products_updated': 0,
            'prices_added': 0,
            'errors': 0
        }
        
        # Создаем или обновляем поставщика
        self.create_or_update_supplier({'supplier_name': supplier_name})
        
        for product_data in products_data:
            try:
                # Ищем существующий товар
                existing_product = self.find_master_product_by_name(
                    product_data.get('standard_name', ''),
                    product_data.get('brand', '')
                )
                
                if existing_product:
                    product_id = existing_product.product_id
                    stats['products_updated'] += 1
                else:
                    # Создаем новый товар
                    new_product = self.create_master_product(product_data)
                    product_id = new_product.product_id
                    stats['products_created'] += 1
                
                # Добавляем цену
                price_data = {
                    'product_id': product_id,
                    'supplier_name': supplier_name,
                    'original_name': product_data.get('original_name', product_data.get('standard_name')),
                    'price': product_data['price'],
                    'confidence_score': product_data.get('confidence_score', 0.9)
                }
                
                self.add_supplier_price(price_data)
                stats['prices_added'] += 1
                
            except Exception as e:
                logger.error(f"Error importing product {product_data.get('standard_name', 'Unknown')}: {e}")
                stats['errors'] += 1
        
        logger.info(f"Bulk import completed for {supplier_name}: {stats}")
        return stats 