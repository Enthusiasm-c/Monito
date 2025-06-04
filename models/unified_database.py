"""
=============================================================================
MONITO UNIFIED PRICE COMPARISON SYSTEM - SQLAlchemy Models
=============================================================================
Версия: 3.0
Цель: SQLAlchemy модели для единой системы управления ценами поставщиков
=============================================================================
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Decimal as SQLDecimal, DateTime, Date, 
    Boolean, Text, JSON, ForeignKey, Index, UniqueConstraint,
    CheckConstraint, func, text
)
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
import uuid

Base = declarative_base()

# =============================================================================
# ENUMS
# =============================================================================

class ProductStatus(ENUM):
    ACTIVE = "active"
    DISCONTINUED = "discontinued"
    MERGED = "merged"

class MatchType(ENUM):
    EXACT = "exact"
    FUZZY = "fuzzy"
    MANUAL = "manual"
    REJECTED = "rejected"

class AvailabilityStatus(ENUM):
    IN_STOCK = "in_stock"
    LIMITED = "limited"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"

class DataSource(ENUM):
    MANUAL = "manual"
    EXCEL_UPLOAD = "excel_upload"
    API = "api"
    WEB_SCRAPING = "web_scraping"

class ChangeReason(ENUM):
    PRICE_UPDATE = "price_update"
    NEW_SUPPLIER = "new_supplier"
    CORRECTION = "correction"
    SEASONAL = "seasonal"
    PROMOTION = "promotion"

class CompanyType(ENUM):
    DISTRIBUTOR = "distributor"
    MANUFACTURER = "manufacturer"
    RETAILER = "retailer"
    WHOLESALER = "wholesaler"

class SupplierStatus(ENUM):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class RecommendationStatus(ENUM):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"

# =============================================================================
# 1. MASTER PRODUCTS MODEL
# =============================================================================

class MasterProduct(Base):
    __tablename__ = 'master_products'
    
    # Primary Key
    product_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Core product information
    standard_name = Column(String(255), nullable=False, index=True)
    brand = Column(String(100), index=True)
    category = Column(String(50), nullable=False, index=True)
    size = Column(SQLDecimal(10, 3))
    unit = Column(String(20))
    description = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(ENUM(ProductStatus), default=ProductStatus.ACTIVE, index=True)
    
    # Relationships
    supplier_prices = relationship("SupplierPrice", back_populates="product", cascade="all, delete-orphan")
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")
    matches_a = relationship("ProductMatch", foreign_keys="ProductMatch.product_a_id", cascade="all, delete-orphan")
    matches_b = relationship("ProductMatch", foreign_keys="ProductMatch.product_b_id", cascade="all, delete-orphan")
    recommendations = relationship("ProcurementRecommendation", back_populates="product", cascade="all, delete-orphan")
    
    # Hybrid properties
    @hybrid_property
    def normalized_name(self):
        """Нормализованное имя для поиска"""
        import re
        if self.standard_name:
            return re.sub(r'[^a-zA-Z0-9\s]', '', self.standard_name.lower().strip())
        return ""
    
    @hybrid_property
    def display_name(self):
        """Полное отображаемое имя"""
        parts = [self.standard_name]
        if self.brand:
            parts.append(f"({self.brand})")
        if self.size and self.unit:
            parts.append(f"{self.size}{self.unit}")
        return " ".join(parts)
    
    # Validations
    @validates('category')
    def validate_category(self, key, category):
        if not category or len(category.strip()) == 0:
            raise ValueError("Category cannot be empty")
        return category.lower().strip()
    
    @validates('unit')
    def validate_unit(self, key, unit):
        valid_units = ['g', 'kg', 'ml', 'l', 'pcs', 'box', 'pack', 'can', 'bottle']
        if unit and unit.lower() not in valid_units:
            raise ValueError(f"Unit must be one of: {valid_units}")
        return unit.lower() if unit else None
    
    def __repr__(self):
        return f"<MasterProduct(id={self.product_id}, name='{self.standard_name}', brand='{self.brand}')>"
    
    def to_dict(self):
        return {
            'product_id': str(self.product_id),
            'standard_name': self.standard_name,
            'brand': self.brand,
            'category': self.category,
            'size': float(self.size) if self.size else None,
            'unit': self.unit,
            'description': self.description,
            'status': self.status.value if self.status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# =============================================================================
# 2. SUPPLIER PRICES MODEL
# =============================================================================

class SupplierPrice(Base):
    __tablename__ = 'supplier_prices'
    
    # Primary Key
    price_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    product_id = Column(UUID(as_uuid=True), ForeignKey('master_products.product_id'), nullable=False, index=True)
    
    # Supplier information
    supplier_name = Column(String(200), nullable=False, index=True)
    original_name = Column(String(500), nullable=False)
    
    # Price information
    price = Column(SQLDecimal(12, 2), nullable=False, index=True)
    currency = Column(String(3), default='IDR')
    price_date = Column(Date, nullable=False, default=date.today, index=True)
    
    # Additional information
    supplier_product_code = Column(String(100))
    minimum_order_quantity = Column(Integer, default=1)
    availability_status = Column(ENUM(AvailabilityStatus), default=AvailabilityStatus.UNKNOWN, index=True)
    
    # Data quality
    confidence_score = Column(SQLDecimal(3, 2))
    data_source = Column(ENUM(DataSource), default=DataSource.EXCEL_UPLOAD)
    last_seen = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("MasterProduct", back_populates="supplier_prices")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('price > 0', name='positive_price'),
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name='valid_confidence'),
        UniqueConstraint('product_id', 'supplier_name', 'price_date', name='unique_supplier_product_date'),
        Index('idx_product_supplier', 'product_id', 'supplier_name'),
        Index('idx_price_date_supplier', 'price_date', 'supplier_name'),
    )
    
    # Validations
    @validates('price')
    def validate_price(self, key, price):
        if price <= 0:
            raise ValueError("Price must be positive")
        return price
    
    @validates('confidence_score')
    def validate_confidence_score(self, key, score):
        if score is not None and (score < 0 or score > 1):
            raise ValueError("Confidence score must be between 0 and 1")
        return score
    
    @validates('supplier_name')
    def validate_supplier_name(self, key, name):
        if not name or len(name.strip()) == 0:
            raise ValueError("Supplier name cannot be empty")
        return name.strip()
    
    def __repr__(self):
        return f"<SupplierPrice(supplier='{self.supplier_name}', price={self.price}, date={self.price_date})>"
    
    def to_dict(self):
        return {
            'price_id': str(self.price_id),
            'product_id': str(self.product_id),
            'supplier_name': self.supplier_name,
            'original_name': self.original_name,
            'price': float(self.price),
            'currency': self.currency,
            'price_date': self.price_date.isoformat() if self.price_date else None,
            'supplier_product_code': self.supplier_product_code,
            'minimum_order_quantity': self.minimum_order_quantity,
            'availability_status': self.availability_status.value if self.availability_status else None,
            'confidence_score': float(self.confidence_score) if self.confidence_score else None,
            'data_source': self.data_source.value if self.data_source else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None
        }

# =============================================================================
# 3. PRODUCT MATCHES MODEL
# =============================================================================

class ProductMatch(Base):
    __tablename__ = 'product_matches'
    
    # Primary Key
    match_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    product_a_id = Column(UUID(as_uuid=True), ForeignKey('master_products.product_id'), nullable=False)
    product_b_id = Column(UUID(as_uuid=True), ForeignKey('master_products.product_id'), nullable=False)
    
    # Scoring
    similarity_score = Column(SQLDecimal(3, 2), nullable=False, index=True)
    match_type = Column(ENUM(MatchType), nullable=False, index=True)
    
    # Detailed similarities
    name_similarity = Column(SQLDecimal(3, 2))
    brand_similarity = Column(SQLDecimal(3, 2))
    size_similarity = Column(SQLDecimal(3, 2))
    
    # Workflow management
    reviewed = Column(Boolean, default=False, index=True)
    approved = Column(Boolean)
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    matching_algorithm_version = Column(String(10), default='v1.0')
    
    # Relationships
    product_a = relationship("MasterProduct", foreign_keys=[product_a_id])
    product_b = relationship("MasterProduct", foreign_keys=[product_b_id])
    
    # Constraints
    __table_args__ = (
        CheckConstraint('similarity_score >= 0 AND similarity_score <= 1', name='valid_similarity'),
        CheckConstraint('product_a_id != product_b_id', name='different_products'),
        # Prevent duplicate matches (order independent)
        UniqueConstraint(
            func.least(product_a_id, product_b_id),
            func.greatest(product_a_id, product_b_id),
            name='unique_product_pair'
        ),
    )
    
    @validates('similarity_score')
    def validate_similarity_score(self, key, score):
        if score < 0 or score > 1:
            raise ValueError("Similarity score must be between 0 and 1")
        return score
    
    def __repr__(self):
        return f"<ProductMatch(similarity={self.similarity_score}, type={self.match_type})>"
    
    def to_dict(self):
        return {
            'match_id': str(self.match_id),
            'product_a_id': str(self.product_a_id),
            'product_b_id': str(self.product_b_id),
            'similarity_score': float(self.similarity_score),
            'match_type': self.match_type.value,
            'name_similarity': float(self.name_similarity) if self.name_similarity else None,
            'brand_similarity': float(self.brand_similarity) if self.brand_similarity else None,
            'size_similarity': float(self.size_similarity) if self.size_similarity else None,
            'reviewed': self.reviewed,
            'approved': self.approved,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# =============================================================================
# 4. PRICE HISTORY MODEL
# =============================================================================

class PriceHistory(Base):
    __tablename__ = 'price_history'
    
    # Primary Key
    history_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Key
    product_id = Column(UUID(as_uuid=True), ForeignKey('master_products.product_id'), nullable=False, index=True)
    supplier_name = Column(String(200), nullable=False, index=True)
    
    # Price changes
    old_price = Column(SQLDecimal(12, 2))
    new_price = Column(SQLDecimal(12, 2), nullable=False)
    
    # Metadata
    change_date = Column(DateTime, default=datetime.utcnow, index=True)
    change_reason = Column(ENUM(ChangeReason), default=ChangeReason.PRICE_UPDATE)
    notes = Column(Text)
    
    # Relationships
    product = relationship("MasterProduct", back_populates="price_history")
    
    # Hybrid properties
    @hybrid_property
    def change_amount(self):
        if self.old_price:
            return self.new_price - self.old_price
        return self.new_price
    
    @hybrid_property
    def change_percentage(self):
        if self.old_price and self.old_price > 0:
            return ((self.new_price - self.old_price) / self.old_price) * 100
        return None
    
    def __repr__(self):
        return f"<PriceHistory(supplier='{self.supplier_name}', old={self.old_price}, new={self.new_price})>"
    
    def to_dict(self):
        return {
            'history_id': str(self.history_id),
            'product_id': str(self.product_id),
            'supplier_name': self.supplier_name,
            'old_price': float(self.old_price) if self.old_price else None,
            'new_price': float(self.new_price),
            'change_amount': float(self.change_amount) if self.change_amount else None,
            'change_percentage': float(self.change_percentage) if self.change_percentage else None,
            'change_date': self.change_date.isoformat() if self.change_date else None,
            'change_reason': self.change_reason.value if self.change_reason else None,
            'notes': self.notes
        }

# =============================================================================
# 5. SUPPLIERS MODEL
# =============================================================================

class Supplier(Base):
    __tablename__ = 'suppliers'
    
    # Primary Key
    supplier_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_name = Column(String(200), nullable=False, unique=True, index=True)
    
    # Contact information
    contact_person = Column(String(100))
    phone = Column(String(50))
    whatsapp = Column(String(50))
    email = Column(String(100))
    address = Column(Text)
    
    # Business information
    company_type = Column(ENUM(CompanyType), default=CompanyType.DISTRIBUTOR)
    specialization = Column(String(200), index=True)
    minimum_order_amount = Column(SQLDecimal(12, 2))
    payment_terms = Column(String(100))
    delivery_areas = Column(Text)
    
    # Rating and metrics
    reliability_score = Column(SQLDecimal(3, 2), default=0.0, index=True)
    price_competitiveness = Column(SQLDecimal(3, 2), default=0.0, index=True)
    total_products = Column(Integer, default=0)
    active_products = Column(Integer, default=0)
    
    # Metadata
    first_seen = Column(Date, default=date.today)
    last_price_update = Column(DateTime)
    status = Column(ENUM(SupplierStatus), default=SupplierStatus.ACTIVE, index=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('reliability_score >= 0 AND reliability_score <= 1', name='valid_reliability'),
        CheckConstraint('price_competitiveness >= 0 AND price_competitiveness <= 1', name='valid_competitiveness'),
    )
    
    @validates('reliability_score', 'price_competitiveness')
    def validate_scores(self, key, score):
        if score is not None and (score < 0 or score > 1):
            raise ValueError(f"{key} must be between 0 and 1")
        return score
    
    def __repr__(self):
        return f"<Supplier(name='{self.supplier_name}', type={self.company_type})>"
    
    def to_dict(self):
        return {
            'supplier_id': str(self.supplier_id),
            'supplier_name': self.supplier_name,
            'contact_person': self.contact_person,
            'phone': self.phone,
            'whatsapp': self.whatsapp,
            'email': self.email,
            'address': self.address,
            'company_type': self.company_type.value if self.company_type else None,
            'specialization': self.specialization,
            'minimum_order_amount': float(self.minimum_order_amount) if self.minimum_order_amount else None,
            'payment_terms': self.payment_terms,
            'delivery_areas': self.delivery_areas,
            'reliability_score': float(self.reliability_score) if self.reliability_score else None,
            'price_competitiveness': float(self.price_competitiveness) if self.price_competitiveness else None,
            'total_products': self.total_products,
            'active_products': self.active_products,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_price_update': self.last_price_update.isoformat() if self.last_price_update else None,
            'status': self.status.value if self.status else None
        }

# =============================================================================
# 6. CATEGORIES MODEL
# =============================================================================

class Category(Base):
    __tablename__ = 'categories'
    
    # Primary Key
    category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_name = Column(String(50), nullable=False, unique=True, index=True)
    parent_category_id = Column(UUID(as_uuid=True), ForeignKey('categories.category_id'))
    
    # Description
    description = Column(Text)
    keywords = Column(Text)
    
    # Metrics
    products_count = Column(Integer, default=0)
    avg_price = Column(SQLDecimal(12, 2))
    price_volatility = Column(SQLDecimal(5, 2))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent_category = relationship("Category", remote_side=[category_id])
    subcategories = relationship("Category")
    
    def __repr__(self):
        return f"<Category(name='{self.category_name}', products={self.products_count})>"
    
    def to_dict(self):
        return {
            'category_id': str(self.category_id),
            'category_name': self.category_name,
            'parent_category_id': str(self.parent_category_id) if self.parent_category_id else None,
            'description': self.description,
            'keywords': self.keywords,
            'products_count': self.products_count,
            'avg_price': float(self.avg_price) if self.avg_price else None,
            'price_volatility': float(self.price_volatility) if self.price_volatility else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# =============================================================================
# 7. PROCUREMENT RECOMMENDATIONS MODEL
# =============================================================================

class ProcurementRecommendation(Base):
    __tablename__ = 'procurement_recommendations'
    
    # Primary Key
    recommendation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Key
    product_id = Column(UUID(as_uuid=True), ForeignKey('master_products.product_id'), nullable=False, index=True)
    
    # Recommendation
    recommended_supplier = Column(String(200), nullable=False, index=True)
    recommended_price = Column(SQLDecimal(12, 2), nullable=False)
    quantity_recommended = Column(Integer)
    potential_savings = Column(SQLDecimal(5, 2))
    
    # Alternatives
    alternative_suppliers = Column(JSON)
    market_analysis = Column(JSON)
    
    # Status
    status = Column(ENUM(RecommendationStatus), default=RecommendationStatus.PENDING, index=True)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime)
    
    # Result
    actual_supplier = Column(String(200))
    actual_price = Column(SQLDecimal(12, 2))
    actual_savings = Column(SQLDecimal(5, 2))
    executed_at = Column(DateTime)
    
    # Relationships
    product = relationship("MasterProduct", back_populates="recommendations")
    
    def __repr__(self):
        return f"<ProcurementRecommendation(supplier='{self.recommended_supplier}', savings={self.potential_savings}%)>"
    
    def to_dict(self):
        return {
            'recommendation_id': str(self.recommendation_id),
            'product_id': str(self.product_id),
            'recommended_supplier': self.recommended_supplier,
            'recommended_price': float(self.recommended_price),
            'quantity_recommended': self.quantity_recommended,
            'potential_savings': float(self.potential_savings) if self.potential_savings else None,
            'alternative_suppliers': self.alternative_suppliers,
            'market_analysis': self.market_analysis,
            'status': self.status.value,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'actual_supplier': self.actual_supplier,
            'actual_price': float(self.actual_price) if self.actual_price else None,
            'actual_savings': float(self.actual_savings) if self.actual_savings else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None
        }

# =============================================================================
# 8. SYSTEM METRICS MODEL
# =============================================================================

class SystemMetric(Base):
    __tablename__ = 'system_metrics'
    
    # Primary Key
    metric_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(SQLDecimal(15, 5))
    metric_unit = Column(String(20))
    
    # Context
    entity_type = Column(String(50), index=True)  # 'product', 'supplier', 'category', 'system'
    entity_id = Column(String(255), index=True)
    
    # Time
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    
    # Additional data
    metadata = Column(JSON)
    
    def __repr__(self):
        return f"<SystemMetric(name='{self.metric_name}', value={self.metric_value})>"
    
    def to_dict(self):
        return {
            'metric_id': str(self.metric_id),
            'metric_name': self.metric_name,
            'metric_value': float(self.metric_value) if self.metric_value else None,
            'metric_unit': self.metric_unit,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'metadata': self.metadata
        }

# =============================================================================
# DATABASE UTILITY FUNCTIONS
# =============================================================================

def create_all_tables(engine):
    """Создать все таблицы в базе данных"""
    Base.metadata.create_all(engine)

def get_table_info():
    """Получить информацию о всех таблицах"""
    tables = []
    for table_name, table in Base.metadata.tables.items():
        columns = [col.name for col in table.columns]
        tables.append({
            'table_name': table_name,
            'columns': columns,
            'column_count': len(columns)
        })
    return tables

# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_product_data(data: Dict[str, Any]) -> bool:
    """Валидация данных товара"""
    required_fields = ['standard_name', 'category']
    for field in required_fields:
        if field not in data or not data[field]:
            return False
    return True

def validate_price_data(data: Dict[str, Any]) -> bool:
    """Валидация данных цены"""
    required_fields = ['product_id', 'supplier_name', 'price']
    for field in required_fields:
        if field not in data or not data[field]:
            return False
    
    if data['price'] <= 0:
        return False
    
    return True 