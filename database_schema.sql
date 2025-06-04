-- =============================================================================
-- MONITO UNIFIED PRICE COMPARISON SYSTEM - DATABASE SCHEMA
-- =============================================================================
-- Версия: 3.0
-- Цель: Единая система управления ценами поставщиков острова Бали
-- =============================================================================

-- Создание базы данных
CREATE DATABASE IF NOT EXISTS monito_unified;
USE monito_unified;

-- =============================================================================
-- 1. MASTER PRODUCTS TABLE
-- =============================================================================
-- Основная таблица товаров с уникальными продуктами
CREATE TABLE master_products (
    product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    standard_name VARCHAR(255) NOT NULL,
    brand VARCHAR(100),
    category VARCHAR(50) NOT NULL,
    size DECIMAL(10,3),
    unit VARCHAR(20),
    description TEXT,
    
    -- Метаданные
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('active', 'discontinued', 'merged') DEFAULT 'active',
    
    -- Поля для поиска и группировки
    normalized_name VARCHAR(255) GENERATED ALWAYS AS (
        LOWER(TRIM(REGEXP_REPLACE(standard_name, '[^a-zA-Z0-9\s]', '')))
    ) STORED,
    search_vector TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english', standard_name || ' ' || COALESCE(brand, '') || ' ' || COALESCE(category, ''))
    ) STORED,
    
    -- Индексы
    INDEX idx_brand (brand),
    INDEX idx_category (category),
    INDEX idx_size_unit (size, unit),
    INDEX idx_status (status),
    INDEX idx_normalized_name (normalized_name),
    INDEX idx_search_vector USING GIN (search_vector)
);

-- =============================================================================
-- 2. SUPPLIER PRICES TABLE
-- =============================================================================
-- Цены от разных поставщиков для каждого товара
CREATE TABLE supplier_prices (
    price_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL,
    supplier_name VARCHAR(200) NOT NULL,
    original_name VARCHAR(500) NOT NULL,
    
    -- Ценовая информация
    price DECIMAL(12,2) NOT NULL CHECK (price > 0),
    currency VARCHAR(3) DEFAULT 'IDR',
    price_date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Дополнительная информация
    supplier_product_code VARCHAR(100),
    minimum_order_quantity INTEGER DEFAULT 1,
    availability_status ENUM('in_stock', 'limited', 'out_of_stock', 'unknown') DEFAULT 'unknown',
    
    -- Качество данных
    confidence_score DECIMAL(3,2) CHECK (confidence_score BETWEEN 0 AND 1),
    data_source ENUM('manual', 'excel_upload', 'api', 'web_scraping') DEFAULT 'excel_upload',
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Внешние ключи
    FOREIGN KEY (product_id) REFERENCES master_products(product_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_product_supplier (product_id, supplier_name),
    INDEX idx_supplier (supplier_name),
    INDEX idx_price_date (price_date),
    INDEX idx_price (price),
    INDEX idx_availability (availability_status),
    
    -- Уникальность: один товар от одного поставщика в один день
    UNIQUE KEY unique_supplier_product_date (product_id, supplier_name, price_date)
);

-- =============================================================================
-- 3. PRODUCT MATCHES TABLE
-- =============================================================================
-- Результаты AI matching для объединения дубликатов
CREATE TABLE product_matches (
    match_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_a_id UUID NOT NULL,
    product_b_id UUID NOT NULL,
    
    -- Scoring
    similarity_score DECIMAL(3,2) NOT NULL CHECK (similarity_score BETWEEN 0 AND 1),
    match_type ENUM('exact', 'fuzzy', 'manual', 'rejected') NOT NULL,
    
    -- Детали matching
    name_similarity DECIMAL(3,2),
    brand_similarity DECIMAL(3,2),
    size_similarity DECIMAL(3,2),
    
    -- Workflow управление
    reviewed BOOLEAN DEFAULT FALSE,
    approved BOOLEAN DEFAULT NULL,
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    
    -- Метаданные
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    matching_algorithm_version VARCHAR(10) DEFAULT 'v1.0',
    
    -- Внешние ключи
    FOREIGN KEY (product_a_id) REFERENCES master_products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (product_b_id) REFERENCES master_products(product_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_product_a (product_a_id),
    INDEX idx_product_b (product_b_id),
    INDEX idx_similarity (similarity_score),
    INDEX idx_match_type (match_type),
    INDEX idx_reviewed (reviewed),
    
    -- Предотвращение дублирования matches
    UNIQUE KEY unique_product_pair (
        LEAST(product_a_id, product_b_id), 
        GREATEST(product_a_id, product_b_id)
    )
);

-- =============================================================================
-- 4. PRICE HISTORY TABLE
-- =============================================================================
-- История изменений цен для анализа трендов
CREATE TABLE price_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL,
    supplier_name VARCHAR(200) NOT NULL,
    
    -- Ценовые изменения
    old_price DECIMAL(12,2),
    new_price DECIMAL(12,2) NOT NULL,
    change_amount DECIMAL(12,2) GENERATED ALWAYS AS (new_price - COALESCE(old_price, 0)) STORED,
    change_percentage DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE 
            WHEN old_price IS NULL OR old_price = 0 THEN NULL
            ELSE ((new_price - old_price) / old_price) * 100
        END
    ) STORED,
    
    -- Метаданные изменения
    change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason ENUM('price_update', 'new_supplier', 'correction', 'seasonal', 'promotion') DEFAULT 'price_update',
    notes TEXT,
    
    -- Внешние ключи
    FOREIGN KEY (product_id) REFERENCES master_products(product_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_product_history (product_id, change_date),
    INDEX idx_supplier_history (supplier_name, change_date),
    INDEX idx_change_date (change_date),
    INDEX idx_change_percentage (change_percentage)
);

-- =============================================================================
-- 5. SUPPLIERS TABLE
-- =============================================================================
-- Информация о поставщиках
CREATE TABLE suppliers (
    supplier_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_name VARCHAR(200) NOT NULL UNIQUE,
    
    -- Контактная информация
    contact_person VARCHAR(100),
    phone VARCHAR(50),
    whatsapp VARCHAR(50),
    email VARCHAR(100),
    address TEXT,
    
    -- Бизнес информация
    company_type ENUM('distributor', 'manufacturer', 'retailer', 'wholesaler') DEFAULT 'distributor',
    specialization VARCHAR(200),
    minimum_order_amount DECIMAL(12,2),
    payment_terms VARCHAR(100),
    delivery_areas TEXT,
    
    -- Рейтинг и метрики
    reliability_score DECIMAL(3,2) DEFAULT 0.0 CHECK (reliability_score BETWEEN 0 AND 1),
    price_competitiveness DECIMAL(3,2) DEFAULT 0.0 CHECK (price_competitiveness BETWEEN 0 AND 1),
    total_products INTEGER DEFAULT 0,
    active_products INTEGER DEFAULT 0,
    
    -- Метаданные
    first_seen DATE DEFAULT CURRENT_DATE,
    last_price_update TIMESTAMP,
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
    
    -- Индексы
    INDEX idx_supplier_name (supplier_name),
    INDEX idx_status (status),
    INDEX idx_specialization (specialization),
    INDEX idx_reliability (reliability_score),
    INDEX idx_competitiveness (price_competitiveness)
);

-- =============================================================================
-- 6. CATEGORIES TABLE
-- =============================================================================
-- Справочник категорий товаров
CREATE TABLE categories (
    category_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_name VARCHAR(50) NOT NULL UNIQUE,
    parent_category_id UUID,
    
    -- Описание
    description TEXT,
    keywords TEXT,
    
    -- Метрики
    products_count INTEGER DEFAULT 0,
    avg_price DECIMAL(12,2),
    price_volatility DECIMAL(5,2),
    
    -- Метаданные
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Внешние ключи
    FOREIGN KEY (parent_category_id) REFERENCES categories(category_id),
    
    -- Индексы
    INDEX idx_category_name (category_name),
    INDEX idx_parent_category (parent_category_id)
);

-- =============================================================================
-- 7. PROCUREMENT_RECOMMENDATIONS TABLE
-- =============================================================================
-- История рекомендаций по закупкам
CREATE TABLE procurement_recommendations (
    recommendation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL,
    
    -- Рекомендация
    recommended_supplier VARCHAR(200) NOT NULL,
    recommended_price DECIMAL(12,2) NOT NULL,
    quantity_recommended INTEGER,
    potential_savings DECIMAL(5,2),
    
    -- Альтернативы
    alternative_suppliers JSON,
    market_analysis JSON,
    
    -- Статус
    status ENUM('pending', 'accepted', 'rejected', 'expired') DEFAULT 'pending',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    
    -- Результат
    actual_supplier VARCHAR(200),
    actual_price DECIMAL(12,2),
    actual_savings DECIMAL(5,2),
    executed_at TIMESTAMP,
    
    -- Внешние ключи
    FOREIGN KEY (product_id) REFERENCES master_products(product_id) ON DELETE CASCADE,
    
    -- Индексы
    INDEX idx_product_recommendations (product_id),
    INDEX idx_supplier_recommendations (recommended_supplier),
    INDEX idx_status (status),
    INDEX idx_generated_at (generated_at)
);

-- =============================================================================
-- 8. SYSTEM_METRICS TABLE
-- =============================================================================
-- Метрики работы системы
CREATE TABLE system_metrics (
    metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,5),
    metric_unit VARCHAR(20),
    
    -- Контекст
    entity_type VARCHAR(50), -- 'product', 'supplier', 'category', 'system'
    entity_id VARCHAR(255),
    
    -- Время
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    period_start TIMESTAMP,
    period_end TIMESTAMP,
    
    -- Дополнительные данные
    metadata JSON,
    
    -- Индексы
    INDEX idx_metric_name (metric_name),
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_recorded_at (recorded_at)
);

-- =============================================================================
-- VIEWS FOR BUSINESS LOGIC
-- =============================================================================

-- Unified Catalog View
CREATE VIEW unified_catalog AS
SELECT 
    mp.product_id,
    mp.standard_name,
    mp.brand,
    mp.category,
    mp.size,
    mp.unit,
    
    -- Лучшая цена
    MIN(sp.price) AS best_price,
    MAX(sp.price) AS worst_price,
    COUNT(DISTINCT sp.supplier_name) AS suppliers_count,
    
    -- Лучший поставщик
    (SELECT sp2.supplier_name 
     FROM supplier_prices sp2 
     WHERE sp2.product_id = mp.product_id 
     ORDER BY sp2.price ASC 
     LIMIT 1) AS best_supplier,
    
    -- Потенциальная экономия
    ROUND(((MAX(sp.price) - MIN(sp.price)) / MAX(sp.price)) * 100, 2) AS savings_percentage,
    
    -- Последнее обновление
    MAX(sp.last_seen) AS last_updated
    
FROM master_products mp
LEFT JOIN supplier_prices sp ON mp.product_id = sp.product_id
WHERE mp.status = 'active'
  AND sp.price_date >= CURRENT_DATE - INTERVAL 30 DAY
GROUP BY mp.product_id, mp.standard_name, mp.brand, mp.category, mp.size, mp.unit
HAVING suppliers_count > 0;

-- Price Trends View
CREATE VIEW price_trends AS
SELECT 
    ph.product_id,
    mp.standard_name,
    ph.supplier_name,
    AVG(ph.change_percentage) AS avg_change_percentage,
    COUNT(*) AS changes_count,
    MIN(ph.change_date) AS first_change,
    MAX(ph.change_date) AS last_change,
    
    -- Классификация тренда
    CASE 
        WHEN AVG(ph.change_percentage) > 5 THEN 'increasing'
        WHEN AVG(ph.change_percentage) < -5 THEN 'decreasing'
        ELSE 'stable'
    END AS trend_direction
    
FROM price_history ph
JOIN master_products mp ON ph.product_id = mp.product_id
WHERE ph.change_date >= CURRENT_DATE - INTERVAL 90 DAY
GROUP BY ph.product_id, mp.standard_name, ph.supplier_name;

-- Supplier Performance View
CREATE VIEW supplier_performance AS
SELECT 
    s.supplier_name,
    s.reliability_score,
    s.price_competitiveness,
    COUNT(DISTINCT sp.product_id) AS active_products,
    AVG(sp.price) AS avg_price,
    
    -- Конкурентные позиции
    SUM(CASE WHEN sp.price = (
        SELECT MIN(sp2.price) 
        FROM supplier_prices sp2 
        WHERE sp2.product_id = sp.product_id
          AND sp2.price_date >= CURRENT_DATE - INTERVAL 30 DAY
    ) THEN 1 ELSE 0 END) AS best_price_products,
    
    -- Обновления
    MAX(sp.last_seen) AS last_update,
    s.status
    
FROM suppliers s
LEFT JOIN supplier_prices sp ON s.supplier_name = sp.supplier_name
WHERE sp.price_date >= CURRENT_DATE - INTERVAL 30 DAY
GROUP BY s.supplier_name, s.reliability_score, s.price_competitiveness, s.status;

-- =============================================================================
-- TRIGGERS FOR DATA CONSISTENCY
-- =============================================================================

-- Обновление updated_at для master_products
DELIMITER $$
CREATE TRIGGER tr_master_products_updated_at
    BEFORE UPDATE ON master_products
    FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END$$

-- Обновление счетчиков в suppliers
CREATE TRIGGER tr_supplier_prices_insert
    AFTER INSERT ON supplier_prices
    FOR EACH ROW
BEGIN
    UPDATE suppliers 
    SET total_products = (
        SELECT COUNT(DISTINCT product_id) 
        FROM supplier_prices 
        WHERE supplier_name = NEW.supplier_name
    ),
    last_price_update = CURRENT_TIMESTAMP
    WHERE supplier_name = NEW.supplier_name;
END$$

-- Создание записи в price_history при изменении цены
CREATE TRIGGER tr_price_history_update
    AFTER UPDATE ON supplier_prices
    FOR EACH ROW
BEGIN
    IF OLD.price != NEW.price THEN
        INSERT INTO price_history (
            product_id, supplier_name, old_price, new_price, change_reason
        ) VALUES (
            NEW.product_id, NEW.supplier_name, OLD.price, NEW.price, 'price_update'
        );
    END IF;
END$$

DELIMITER ;

-- =============================================================================
-- SAMPLE DATA INSERTION
-- =============================================================================

-- Вставка основных категорий
INSERT INTO categories (category_name, description) VALUES
('beverages', 'Напитки всех видов'),
('canned_food', 'Консервированные продукты'),
('pasta_noodles', 'Макароны и лапша'),
('cooking_oil', 'Масла для приготовления пищи'),
('spices_seasonings', 'Специи и приправы'),
('dairy_products', 'Молочные продукты'),
('snacks', 'Снеки и закуски'),
('rice_grains', 'Рис и злаки'),
('frozen_food', 'Замороженные продукты'),
('household_items', 'Хозяйственные товары');

-- =============================================================================
-- PERFORMANCE OPTIMIZATIONS
-- =============================================================================

-- Дополнительные индексы для production
CREATE INDEX idx_supplier_prices_composite ON supplier_prices (product_id, price, price_date);
CREATE INDEX idx_master_products_search ON master_products (brand, category, status);
CREATE INDEX idx_price_history_trend ON price_history (product_id, change_date, change_percentage);

-- Partitioning для больших таблиц (опционально)
-- ALTER TABLE price_history PARTITION BY RANGE (YEAR(change_date)) (
--     PARTITION p2023 VALUES LESS THAN (2024),
--     PARTITION p2024 VALUES LESS THAN (2025),
--     PARTITION p2025 VALUES LESS THAN (2026)
-- );

-- =============================================================================
-- SCHEMA VALIDATION
-- =============================================================================

-- Проверка целостности schema
SELECT 
    'Schema created successfully' AS status,
    COUNT(*) AS tables_created
FROM information_schema.tables 
WHERE table_schema = 'monito_unified';

-- =============================================================================
-- END OF SCHEMA
-- ============================================================================= 