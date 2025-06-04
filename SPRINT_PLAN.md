# 📋 ТЕХНИЧЕСКОЕ ЗАДАНИЕ: РЕФАКТОРИНГ MONITO ДЛЯ UNIFIED PRICE COMPARISON SYSTEM

## 🎯 **ОБЩАЯ ЦЕЛЬ ПРОЕКТА**

Трансформировать существующую систему анализа прайс-листов Monito в **единую систему управления ценами поставщиков острова Бали** с автоматическим объединением идентичных товаров и поиском лучших цен.

---

## 🏗️ **ФАЗА 1: ПРОЕКТИРОВАНИЕ НОВОЙ АРХИТЕКТУРЫ (2 дня)**

### 📊 **Задача 1.1: Проектирование Database Schema**

#### **Цель:** Спроектировать unified database для хранения товаров всех поставщиков

#### **Deliverables:**
```sql
-- 1. Master Products Table
CREATE TABLE master_products (
    product_id UUID PRIMARY KEY,
    standard_name VARCHAR(255) NOT NULL,
    brand VARCHAR(100),
    category VARCHAR(50),
    size DECIMAL(10,3),
    unit VARCHAR(20),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    status ENUM('active', 'discontinued', 'merged')
);

-- 2. Supplier Prices Table  
CREATE TABLE supplier_prices (
    price_id UUID PRIMARY KEY,
    product_id UUID REFERENCES master_products(product_id),
    supplier_name VARCHAR(200) NOT NULL,
    original_name VARCHAR(500),
    price DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'IDR',
    price_date DATE NOT NULL,
    confidence_score DECIMAL(3,2),
    last_seen TIMESTAMP
);

-- 3. Product Matching Table (для AI matching results)
CREATE TABLE product_matches (
    match_id UUID PRIMARY KEY,
    product_a_id UUID REFERENCES master_products(product_id),
    product_b_id UUID REFERENCES master_products(product_id),
    similarity_score DECIMAL(3,2),
    match_type ENUM('exact', 'fuzzy', 'manual'),
    reviewed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP
);

-- 4. Price History Table
CREATE TABLE price_history (
    history_id UUID PRIMARY KEY,
    product_id UUID REFERENCES master_products(product_id),
    supplier_name VARCHAR(200),
    old_price DECIMAL(12,2),
    new_price DECIMAL(12,2),
    change_percentage DECIMAL(5,2),
    change_date TIMESTAMP
);
```

#### **Технические требования:**
- **Database:** PostgreSQL (для complex queries) или SQLite (для простоты)
- **ORM:** SQLAlchemy для Python integration
- **Indexing:** Создать индексы на brand, category, supplier_name, price_date

---

### 🔄 **Задача 1.2: Архитектура Product Matching System**

#### **Цель:** Спроектировать алгоритм объединения идентичных товаров

#### **Алгоритм Matching:**
```python
# Уровни сопоставления (в порядке приоритета):

# Level 1: Exact Match (100% confidence)
def exact_match(product_a, product_b):
    return (
        brand_match(a.brand, b.brand) AND
        normalize_name(a.name) == normalize_name(b.name) AND
        size_match(a.size, b.size) AND
        unit_match(a.unit, b.unit)
    )

# Level 2: Fuzzy Match (80-99% confidence) 
def fuzzy_match(product_a, product_b):
    name_similarity = levenshtein_ratio(a.name, b.name)
    brand_similarity = brand_match_score(a.brand, b.brand)
    size_similarity = size_tolerance_match(a.size, b.size)
    
    combined_score = weighted_average([
        (name_similarity, 0.5),
        (brand_similarity, 0.3), 
        (size_similarity, 0.2)
    ])
    
    return combined_score >= 0.8

# Level 3: Category + Brand Match (60-79% confidence)
def category_brand_match(product_a, product_b):
    return (
        a.category == b.category AND
        brand_match(a.brand, b.brand) AND
        size_tolerance_match(a.size, b.size, tolerance=0.1)
    )
```

#### **Deliverables:**
- **Matching Rules Document** с примерами
- **Confidence Thresholds** для автоматического/ручного review
- **Edge Cases Handling** (разные единицы измерения, вариации брендов)

---

### 💰 **Задача 1.3: Price Comparison Logic**

#### **Цель:** Спроектировать систему сравнения цен с нормализацией

#### **Price Normalization Algorithm:**
```python
def normalize_price_per_unit(price, size, unit):
    """
    Приводим все цены к стандартным единицам для сравнения
    """
    # Конверсия в базовые единицы
    base_conversions = {
        'g': 1,      'kg': 1000,
        'ml': 1,     'l': 1000,
        'pcs': 1,    'box': 1,  # штучные товары остаются как есть
    }
    
    base_size = size * base_conversions.get(unit, 1)
    price_per_base_unit = price / base_size
    
    return {
        'price_per_gram': price_per_base_unit if unit in ['g', 'kg'] else None,
        'price_per_ml': price_per_base_unit if unit in ['ml', 'l'] else None,
        'price_per_piece': price if unit in ['pcs', 'box'] else None,
        'original_price': price
    }

def find_best_supplier(product_id):
    """
    Находим лучшего поставщика по цене
    """
    prices = get_current_prices_for_product(product_id)
    normalized_prices = [normalize_price_per_unit(p.price, p.size, p.unit) for p in prices]
    
    # Сравниваем нормализованные цены
    best_price = min(normalized_prices, key=lambda x: x['price_per_base_unit'])
    
    return {
        'best_supplier': best_price.supplier_name,
        'best_price': best_price.original_price,
        'savings_vs_worst': calculate_savings(best_price, max(normalized_prices)),
        'price_per_unit': best_price.price_per_base_unit
    }
```

---

## 🔧 **ФАЗА 2: INFRASTRUCTURE РЕФАКТОРИНГ (3 дня)**

### 🗄️ **Задача 2.1: Database Migration System**

#### **Цель:** Создать новую database и мигрировать данные из Google Sheets

#### **Шаги реализации:**
```python
# 1. Создать DatabaseManager
class DatabaseManager:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
    
    def create_tables(self):
        # Создание всех таблиц по schema
        Base.metadata.create_all(self.engine)
    
    def migrate_from_sheets(self, sheets_manager):
        # Миграция существующих данных
        pass

# 2. Создать модели SQLAlchemy
class MasterProduct(Base):
    __tablename__ = 'master_products'
    # ... поля из schema

class SupplierPrice(Base):
    __tablename__ = 'supplier_prices'  
    # ... поля из schema
```

#### **Migration Script:**
```python
def migrate_existing_data():
    """
    Переносим данные из Google Sheets в новую database
    """
    # 1. Читаем все существующие листы поставщиков
    sheets_data = read_all_supplier_sheets()
    
    # 2. Для каждого товара создаем запись в master_products
    for supplier, products in sheets_data.items():
        for product in products:
            # Проверяем, есть ли уже такой товар в master_products
            existing = find_matching_product(product)
            
            if existing:
                # Добавляем цену поставщика к существующему товару
                add_supplier_price(existing.product_id, supplier, product)
            else:
                # Создаем новый master product
                new_product = create_master_product(product)
                add_supplier_price(new_product.product_id, supplier, product)
```

#### **Deliverables:**
- **Database setup script**
- **Migration utility** для переноса из Google Sheets  
- **Data validation** скрипты для проверки целостности

---

### 🔌 **Задача 2.2: Database Integration Layer**

#### **Цель:** Интегрировать новую database в существующий pipeline

#### **Новые компоненты:**
```python
# 1. Заменяем GoogleSheetsManagerV2
class UnifiedDatabaseManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def save_processed_products(self, supplier_name, products):
        """
        Сохраняем обработанные товары в unified database
        """
        for product in products:
            # 1. Ищем matching products
            matches = self.find_product_matches(product)
            
            if matches:
                # Обновляем цену существующего товара
                self.update_supplier_price(matches[0].product_id, supplier_name, product)
            else:
                # Создаем новый master product
                master_product = self.create_master_product(product)
                self.add_supplier_price(master_product.product_id, supplier_name, product)
    
    def find_product_matches(self, new_product):
        """
        Используем Product Matching Engine
        """
        return ProductMatchingEngine.find_matches(new_product)
```

#### **Обновление существующего pipeline:**
```python
# Обновляем simple_telegram_bot.py
async def process_file_with_unified_database(file_path, supplier_name):
    # 1-4. Existing processing (parsing, validation, LLM) остается как есть
    parsed_data = parser.parse_file(file_path)
    validated_data = validator.validate_and_cache(parsed_data)
    standardized_data = llm_processor.standardize_products_batch(validated_data)
    
    # 5. NEW: Save to unified database instead of separate sheets
    unified_db_manager.save_processed_products(supplier_name, standardized_data)
    
    # 6. NEW: Generate comparison report
    comparison_report = price_comparison_engine.generate_report(supplier_name)
    
    return comparison_report
```

---

## 🤖 **ФАЗА 3: CORE BUSINESS LOGIC (4 дня)**

### 🔍 **Задача 3.1: Product Matching Engine**

#### **Цель:** Создать AI-powered систему поиска идентичных товаров

#### **Компонент Implementation:**
```python
class ProductMatchingEngine:
    def __init__(self, db_manager, similarity_threshold=0.8):
        self.db = db_manager
        self.threshold = similarity_threshold
        
    def find_matches(self, new_product):
        """
        Находим все потенциальные matches для нового товара
        """
        # 1. Exact matches first
        exact_matches = self._find_exact_matches(new_product)
        if exact_matches:
            return exact_matches
            
        # 2. Fuzzy matching by category + brand
        category_matches = self._find_category_brand_matches(new_product)
        fuzzy_matches = []
        
        for candidate in category_matches:
            similarity = self._calculate_similarity(new_product, candidate)
            if similarity >= self.threshold:
                fuzzy_matches.append({
                    'product': candidate,
                    'similarity': similarity,
                    'match_type': 'fuzzy'
                })
        
        return sorted(fuzzy_matches, key=lambda x: x['similarity'], reverse=True)
    
    def _calculate_similarity(self, product_a, product_b):
        """
        Multi-factor similarity calculation
        """
        # Name similarity (50% weight)
        name_sim = fuzz.ratio(
            self._normalize_name(product_a.name), 
            self._normalize_name(product_b.name)
        ) / 100.0
        
        # Brand similarity (30% weight)
        brand_sim = self._brand_similarity(product_a.brand, product_b.brand)
        
        # Size similarity (20% weight)  
        size_sim = self._size_similarity(product_a.size, product_a.unit, 
                                       product_b.size, product_b.unit)
        
        weighted_similarity = (name_sim * 0.5 + brand_sim * 0.3 + size_sim * 0.2)
        return weighted_similarity
    
    def suggest_merges(self, confidence_threshold=0.9):
        """
        Предлагает автоматические merge для высоконадежных matches
        """
        high_confidence_matches = self.db.query(ProductMatch).filter(
            ProductMatch.similarity_score >= confidence_threshold,
            ProductMatch.reviewed == False
        ).all()
        
        return [
            {
                'product_a': match.product_a,
                'product_b': match.product_b, 
                'confidence': match.similarity_score,
                'suggested_action': 'auto_merge'
            }
            for match in high_confidence_matches
        ]
```

#### **Testing Requirements:**
- **Test cases:** минимум 50 examples товаров с known matches
- **Accuracy target:** >90% для exact matches, >80% для fuzzy matches
- **Performance:** <100ms для поиска matches в базе 10k товаров

---

### 💰 **Задача 3.2: Price Comparison Engine**

#### **Цель:** Создать систему сравнения цен с intelligent recommendations

#### **Компонент Implementation:**
```python
class PriceComparisonEngine:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def get_best_prices_report(self, category=None, supplier=None):
        """
        Генерируем отчет по лучшим ценам
        """
        query = self.db.session.query(MasterProduct).join(SupplierPrice)
        
        if category:
            query = query.filter(MasterProduct.category == category)
        if supplier:
            query = query.filter(SupplierPrice.supplier_name == supplier)
            
        products = query.all()
        report = []
        
        for product in products:
            price_analysis = self._analyze_product_prices(product.product_id)
            report.append({
                'product': product,
                'best_price': price_analysis['best_price'],
                'worst_price': price_analysis['worst_price'],
                'savings_potential': price_analysis['savings'],
                'suppliers_count': price_analysis['suppliers_count'],
                'price_trend': price_analysis['trend']
            })
        
        return sorted(report, key=lambda x: x['savings_potential'], reverse=True)
    
    def _analyze_product_prices(self, product_id):
        """
        Анализируем все цены для конкретного товара
        """
        current_prices = self.db.session.query(SupplierPrice).filter(
            SupplierPrice.product_id == product_id,
            SupplierPrice.price_date >= datetime.now() - timedelta(days=30)
        ).all()
        
        if not current_prices:
            return None
            
        normalized_prices = []
        for price in current_prices:
            normalized = self._normalize_price(price)
            normalized_prices.append({
                'supplier': price.supplier_name,
                'original_price': price.price,
                'normalized_price': normalized,
                'price_date': price.price_date
            })
        
        best = min(normalized_prices, key=lambda x: x['normalized_price'])
        worst = max(normalized_prices, key=lambda x: x['normalized_price'])
        
        return {
            'best_price': best,
            'worst_price': worst,
            'savings': ((worst['normalized_price'] - best['normalized_price']) / worst['normalized_price']) * 100,
            'suppliers_count': len(current_prices),
            'trend': self._calculate_price_trend(product_id)
        }
    
    def generate_procurement_recommendations(self, required_products):
        """
        Генерируем рекомендации по закупкам
        """
        recommendations = []
        
        for required_product in required_products:
            matches = ProductMatchingEngine.find_matches(required_product)
            if matches:
                price_analysis = self._analyze_product_prices(matches[0]['product'].product_id)
                recommendations.append({
                    'required_product': required_product,
                    'matched_product': matches[0]['product'],
                    'recommended_supplier': price_analysis['best_price']['supplier'],
                    'recommended_price': price_analysis['best_price']['original_price'],
                    'potential_savings': price_analysis['savings']
                })
        
        return recommendations
```

---

### 📊 **Задача 3.3: Unified Catalog Manager**

#### **Цель:** Создать unified view всех товаров с лучшими ценами

#### **Компонент Implementation:**
```python
class UnifiedCatalogManager:
    def __init__(self, db_manager, price_engine, matching_engine):
        self.db = db_manager
        self.price_engine = price_engine
        self.matching_engine = matching_engine
    
    def get_unified_catalog(self, filters=None):
        """
        Возвращаем unified catalog с лучшими ценами
        """
        query = self.db.session.query(MasterProduct)
        
        if filters:
            if 'category' in filters:
                query = query.filter(MasterProduct.category.in_(filters['category']))
            if 'brand' in filters:
                query = query.filter(MasterProduct.brand.in_(filters['brand']))
        
        products = query.all()
        catalog = []
        
        for product in products:
            # Получаем лучшую цену для каждого товара
            price_info = self.price_engine._analyze_product_prices(product.product_id)
            
            if price_info:
                catalog.append({
                    'product_id': product.product_id,
                    'standard_name': product.standard_name,
                    'brand': product.brand,
                    'category': product.category,
                    'size': product.size,
                    'unit': product.unit,
                    'best_price': price_info['best_price']['original_price'],
                    'best_supplier': price_info['best_price']['supplier'],
                    'alternative_suppliers': price_info['suppliers_count'] - 1,
                    'last_updated': price_info['best_price']['price_date'],
                    'savings_vs_worst': f"{price_info['savings']:.1f}%"
                })
        
        return catalog
    
    def export_catalog_to_sheets(self, catalog):
        """
        Экспортируем unified catalog в Google Sheets для просмотра
        """
        # Создаем новый лист "Unified Catalog"
        catalog_data = [
            ['Product ID', 'Product Name', 'Brand', 'Category', 'Size', 'Unit', 
             'Best Price (IDR)', 'Best Supplier', 'Alt. Suppliers', 'Last Updated', 'Savings %']
        ]
        
        for item in catalog:
            catalog_data.append([
                item['product_id'],
                item['standard_name'],
                item['brand'], 
                item['category'],
                item['size'],
                item['unit'],
                item['best_price'],
                item['best_supplier'],
                item['alternative_suppliers'],
                item['last_updated'].strftime('%Y-%m-%d'),
                item['savings_vs_worst']
            ])
        
        # Используем существующий GoogleSheetsManagerV2 для экспорта
        sheets_manager = GoogleSheetsManagerV2()
        sheets_manager.create_or_update_sheet("Unified_Catalog", catalog_data)
```

---

## 🤖 **ФАЗА 4: TELEGRAM BOT ENHANCEMENT (2 дня)**

### 📱 **Задача 4.1: Enhanced Bot Commands**

#### **Цель:** Добавить новые команды для работы с unified catalog

#### **Новые команды:**
```python
# Добавляем в simple_telegram_bot.py

@bot.message_handler(commands=['catalog'])
async def handle_catalog_command(message):
    """
    /catalog [category] - показать unified catalog
    """
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    category_filter = args[0] if args else None
    
    catalog = unified_catalog_manager.get_unified_catalog(
        filters={'category': [category_filter]} if category_filter else None
    )
    
    # Показываем top 10 товаров с лучшими ценами
    top_items = sorted(catalog, key=lambda x: float(x['savings_vs_worst'][:-1]), reverse=True)[:10]
    
    response = "🏆 *TOP DEALS IN UNIFIED CATALOG*\n\n"
    for item in top_items:
        response += f"📦 *{item['standard_name']}*\n"
        response += f"💰 Best: {item['best_price']:,} IDR at {item['best_supplier']}\n"
        response += f"💾 Savings: {item['savings_vs_worst']} vs worst supplier\n\n"
    
    await bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['compare'])
async def handle_compare_command(message):
    """
    /compare <product_name> - сравнить цены на товар
    """
    if len(message.text.split()) < 2:
        await bot.reply_to(message, "❌ Usage: /compare <product name>")
        return
    
    product_name = ' '.join(message.text.split()[1:])
    
    # Ищем товар в catalog
    matches = product_matching_engine.search_by_name(product_name)
    
    if not matches:
        await bot.reply_to(message, f"❌ Product '{product_name}' not found in catalog")
        return
    
    best_match = matches[0]
    price_analysis = price_comparison_engine._analyze_product_prices(best_match.product_id)
    
    response = f"📊 *PRICE COMPARISON: {best_match.standard_name}*\n\n"
    
    # Показываем все доступные цены
    current_prices = db.session.query(SupplierPrice).filter(
        SupplierPrice.product_id == best_match.product_id
    ).order_by(SupplierPrice.price).all()
    
    for i, price in enumerate(current_prices):
        icon = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "📍"
        response += f"{icon} {price.supplier_name}: {price.price:,} IDR\n"
    
    savings = price_analysis['savings']
    response += f"\n💡 *Potential savings: {savings:.1f}%*"
    
    await bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['recommend'])
async def handle_recommend_command(message):
    """
    /recommend - получить рекомендации по лучшим deals
    """
    # Находим товары с наибольшими savings potential
    best_deals = price_comparison_engine.get_best_deals(limit=5)
    
    response = "💎 *TOP PROCUREMENT RECOMMENDATIONS*\n\n"
    
    for deal in best_deals:
        response += f"📦 *{deal['product']['standard_name']}*\n"
        response += f"🏪 Buy from: {deal['best_supplier']}\n"
        response += f"💰 Price: {deal['best_price']:,} IDR\n"
        response += f"💾 Save: {deal['savings']:.1f}% vs other suppliers\n\n"
    
    await bot.reply_to(message, response, parse_mode='Markdown')
```

#### **Enhanced file processing:**
```python
async def process_file_with_comparison(file_path, supplier_name, user_id):
    """
    Обновленная обработка файлов с comparison insights
    """
    try:
        # 1-4. Existing processing pipeline
        processing_result = await process_file_with_unified_database(file_path, supplier_name)
        
        # 5. NEW: Generate comparison insights
        new_products_count = len(processing_result['new_products'])
        updated_products_count = len(processing_result['updated_products'])
        
        # 6. NEW: Find competitive advantages  
        competitive_analysis = price_comparison_engine.analyze_supplier_competitiveness(supplier_name)
        
        # 7. Enhanced response with insights
        response = f"✅ *PROCESSING COMPLETE*\n\n"
        response += f"📊 *Results Summary:*\n"
        response += f"🆕 New products: {new_products_count}\n"
        response += f"🔄 Updated products: {updated_products_count}\n\n"
        
        response += f"🏆 *Competitive Analysis for {supplier_name}:*\n"
        response += f"💰 Best prices on: {competitive_analysis['winning_products_count']} products\n"
        response += f"📈 Above market on: {competitive_analysis['above_market_count']} products\n"
        response += f"📊 Average competitiveness: {competitive_analysis['competitiveness_score']:.1f}%\n\n"
        
        if competitive_analysis['top_deals']:
            response += f"🎯 *Top competitive products:*\n"
            for deal in competitive_analysis['top_deals'][:3]:
                response += f"• {deal['product_name']} (beats market by {deal['advantage']:.1f}%)\n"
        
        await bot.send_message(user_id, response, parse_mode='Markdown')
        
    except Exception as e:
        await bot.send_message(user_id, f"❌ Error processing file: {str(e)}")
```

---

## 🧪 **ФАЗА 5: TESTING & VALIDATION (2 дня)**

### 🔍 **Задача 5.1: Integration Testing**

#### **Цель:** Протестировать end-to-end workflow новой системы

#### **Test Scenarios:**
```python
# tests/test_unified_system_integration.py

class TestUnifiedSystemIntegration:
    
    def test_complete_workflow_with_multiple_suppliers(self):
        """
        Тест полного workflow с несколькими поставщиками
        """
        # 1. Загружаем прайс от первого поставщика
        supplier_a_file = "tests/fixtures/supplier_a_pricelist.xlsx"
        result_a = process_file_with_unified_database(supplier_a_file, "PT Supplier A")
        
        # 2. Загружаем прайс от второго поставщика (с пересекающимися товарами)
        supplier_b_file = "tests/fixtures/supplier_b_pricelist.xlsx"
        result_b = process_file_with_unified_database(supplier_b_file, "PT Supplier B")
        
        # 3. Проверяем, что идентичные товары были объединены
        coca_cola_matches = product_matching_engine.search_by_name("COCA COLA 330ml")
        assert len(coca_cola_matches) == 1  # Должен быть только один master product
        
        # 4. Проверяем, что цены от обоих поставщиков сохранены
        prices = db.session.query(SupplierPrice).filter(
            SupplierPrice.product_id == coca_cola_matches[0].product_id
        ).all()
        assert len(prices) == 2  # Цены от двух поставщиков
        
        # 5. Проверяем price comparison
        comparison = price_comparison_engine._analyze_product_prices(coca_cola_matches[0].product_id)
        assert comparison['best_price']['supplier'] in ["PT Supplier A", "PT Supplier B"]
        assert comparison['savings'] > 0  # Должна быть экономия между поставщиками
    
    def test_matching_accuracy(self):
        """
        Тест точности matching алгоритма
        """
        test_cases = [
            # Exact matches
            ("COCA COLA 330ml", "Coca Cola 330 ml", 1.0),
            ("INDOMIE Mi Goreng 85g", "INDOMIE Mie Goreng 85 gram", 0.9),
            
            # Fuzzy matches  
            ("BARILLA Spaghetti No.5", "BARILLA Spaghetti #5", 0.85),
            ("SAPORITO Baked Bean 2.65kg", "SAPORITO Baked Beans 2.65 kg", 0.9),
            
            # Should NOT match
            ("COCA COLA 330ml", "PEPSI 330ml", 0.3),
            ("INDOMIE Mi Goreng", "MAGGI Noodles", 0.2)
        ]
        
        for product_a_name, product_b_name, expected_similarity in test_cases:
            similarity = product_matching_engine._calculate_similarity(
                MockProduct(product_a_name),
                MockProduct(product_b_name)
            )
            
            assert abs(similarity - expected_similarity) < 0.1, \
                f"Similarity for '{product_a_name}' vs '{product_b_name}' should be ~{expected_similarity}, got {similarity}"
    
    def test_price_normalization(self):
        """
        Тест нормализации цен для корректного сравнения
        """
        test_cases = [
            # Одинаковые товары в разных единицах
            ({"price": 5000, "size": 500, "unit": "g"}, {"price": 10000, "size": 1, "unit": "kg"}, True),  # Одинаковая цена за кг
            ({"price": 2500, "size": 250, "unit": "ml"}, {"price": 10000, "size": 1, "unit": "l"}, True),  # Одинаковая цена за литр
            
            # Разные цены
            ({"price": 5000, "size": 500, "unit": "g"}, {"price": 15000, "size": 1, "unit": "kg"}, False), # 10k vs 15k за кг
        ]
        
        for price_a, price_b, should_be_equal in test_cases:
            normalized_a = price_comparison_engine._normalize_price(price_a['price'], price_a['size'], price_a['unit'])
            normalized_b = price_comparison_engine._normalize_price(price_b['price'], price_b['size'], price_b['unit'])
            
            if should_be_equal:
                assert abs(normalized_a - normalized_b) < 0.01, f"Normalized prices should be equal: {normalized_a} vs {normalized_b}"
            else:
                assert abs(normalized_a - normalized_b) > 0.01, f"Normalized prices should be different: {normalized_a} vs {normalized_b}"
```

#### **Performance Testing:**
```python
def test_system_performance():
    """
    Тест производительности unified system
    """
    # Загружаем большой файл (1000+ товаров)
    large_file = "tests/fixtures/large_supplier_pricelist.xlsx"
    
    start_time = time.time()
    result = process_file_with_unified_database(large_file, "Test Supplier")
    processing_time = time.time() - start_time
    
    # Performance targets
    assert processing_time < 60, f"Large file processing should take <60s, took {processing_time}s"
    assert result['products_processed'] > 900, f"Should process >900 products, processed {result['products_processed']}"
    
    # Matching performance
    start_time = time.time()
    matches = product_matching_engine.find_matches(test_product)
    matching_time = time.time() - start_time
    
    assert matching_time < 0.1, f"Product matching should take <100ms, took {matching_time}s"
```

---

### 📊 **Задача 5.2: Business Logic Validation**

#### **Цель:** Проверить корректность бизнес-логики price comparison

#### **Validation Tests:**
```python
def test_competitive_analysis_accuracy():
    """
    Тест точности competitive analysis
    """
    # Создаем тестовые данные: 3 поставщика, 5 товаров
    test_suppliers = ["Supplier A", "Supplier B", "Supplier C"]
    test_products = create_test_products_with_known_prices()
    
    # Загружаем данные в систему
    for supplier in test_suppliers:
        load_test_data(supplier, test_products[supplier])
    
    # Тестируем competitive analysis
    for supplier in test_suppliers:
        analysis = price_comparison_engine.analyze_supplier_competitiveness(supplier)
        
        # Проверяем корректность расчетов
        assert 0 <= analysis['competitiveness_score'] <= 100
        assert analysis['winning_products_count'] >= 0
        assert analysis['above_market_count'] >= 0
        assert len(analysis['top_deals']) <= 5
    
    # Проверяем unified catalog
    catalog = unified_catalog_manager.get_unified_catalog()
    
    # Каждый товар должен иметь лучшую цену от правильного поставщика
    for item in catalog:
        product_prices = db.session.query(SupplierPrice).filter(
            SupplierPrice.product_id == item['product_id']
        ).all()
        
        actual_best = min(product_prices, key=lambda x: x.price)
        assert item['best_supplier'] == actual_best.supplier_name
        assert item['best_price'] == actual_best.price

def test_procurement_recommendations():
    """
    Тест качества procurement recommendations
    """
    # Создаем shopping list
    required_products = [
        {"name": "COCA COLA 330ml", "quantity": 100},
        {"name": "INDOMIE Mi Goreng", "quantity": 50},
        {"name": "BARILLA Spaghetti", "quantity": 20}
    ]
    
    recommendations = price_comparison_engine.generate_procurement_recommendations(required_products)
    
    # Проверяем качество рекомендаций
    assert len(recommendations) == len(required_products)
    
    for rec in recommendations:
        assert rec['potential_savings'] >= 0  # Должна быть экономия или 0
        assert rec['recommended_supplier'] is not None
        assert rec['recommended_price'] > 0
        
        # Проверяем, что рекомендован действительно лучший поставщик
        all_prices = get_all_prices_for_product(rec['matched_product'].product_id)
        best_actual_price = min(all_prices, key=lambda x: x.price)
        assert rec['recommended_supplier'] == best_actual_price.supplier_name
```

---

## 🚀 **ФАЗА 6: DEPLOYMENT & DOCUMENTATION (1 день)**

### 📋 **Задача 6.1: Production Deployment**

#### **Цель:** Подготовить систему к production использованию

#### **Deployment Configuration:**
```python
# config/production.py
import os

class ProductionConfig:
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost/monito_production')
    
    # Redis
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # API Keys
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    # Google Sheets (для экспорта catalog)
    GOOGLE_SHEETS_ID = os.environ.get('GOOGLE_SHEETS_ID')
    
    # Performance settings
    CELERY_WORKER_COUNT = int(os.environ.get('CELERY_WORKER_COUNT', '4'))
    MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', '20'))
    
    # Matching settings
    PRODUCT_SIMILARITY_THRESHOLD = float(os.environ.get('SIMILARITY_THRESHOLD', '0.8'))
    AUTO_MERGE_THRESHOLD = float(os.environ.get('AUTO_MERGE_THRESHOLD', '0.95'))
```

#### **Docker Setup:**
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Создаем пользователя для безопасности
RUN useradd -m monito
USER monito

CMD ["python", "simple_telegram_bot.py"]
```

```yaml
# docker-compose.production.yml
version: '3.8'
services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: monito_production
      POSTGRES_USER: monito
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"

  monito-worker:
    build: .
    command: python worker.py worker
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL=postgresql://monito:${DB_PASSWORD}@postgres:5432/monito_production
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./logs:/app/logs

  monito-bot:
    build: .
    command: python simple_telegram_bot.py
    depends_on:
      - postgres
      - redis
      - monito-worker
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://monito:${DB_PASSWORD}@postgres:5432/monito_production
      - REDIS_URL=redis://redis:6379/0

volumes:
  postgres_data:
```

---

### 📚 **Задача 6.2: Documentation Update**

#### **Цель:** Обновить документацию для новой unified system

#### **Обновить файлы:**

**1. README.md - новый раздел:**
```markdown
## 🎯 Unified Price Comparison System

### What's New in v3.0
- **🔄 Unified Product Database** - All suppliers in one system
- **🤖 Smart Product Matching** - AI-powered duplicate detection  
- **💰 Price Comparison Engine** - Find best deals automatically
- **📊 Competitive Analysis** - Supplier performance insights
- **🎯 Procurement Recommendations** - Optimized buying decisions

### New Bot Commands
- `/catalog` - View unified product catalog
- `/compare <product>` - Compare prices across suppliers
- `/recommend` - Get procurement recommendations
- `/competitive <supplier>` - Analyze supplier competitiveness
```

**2. USAGE.md - новый workflow:**
```markdown
## 🔄 New Unified Workflow

### For Staff Members
1. **Upload supplier price lists** via Telegram bot (same as before)
2. **System automatically matches** identical products across suppliers
3. **View unified catalog** with best prices via `/catalog` command
4. **Get recommendations** for optimal purchasing via `/recommend`
5. **Compare specific products** via `/compare <product name>`

### For Management
1. **Monitor competitive position** of each supplier
2. **Track price trends** across the market
3. **Identify cost-saving opportunities** through best price analysis
4. **Make data-driven procurement decisions** based on comprehensive insights
```

**3. ARCHITECTURE.md - новая диаграмма:**
```mermaid
graph TD
    A[📱 Telegram Bot] --> B[🔄 Existing Pipeline]
    B --> C[📊 Product Matching Engine]
    C --> D[💾 Unified Database]
    D --> E[💰 Price Comparison Engine]
    E --> F[📋 Unified Catalog Manager]
    F --> G[📊 Google Sheets Export]
    F --> H[📱 Telegram Responses]
    
    subgraph "New Components v3.0"
        C
        D
        E
        F
    end
    
    subgraph "Existing Components v2.0"
        B
        G
        H
    end
```

---

## 🎯 **ФИНАЛЬНАЯ ПРОВЕРКА И ПРИЕМКА**

### ✅ **Checklist готовности системы:**

#### **Core Functionality:**
- [ ] Unified database создана и работает
- [ ] Product matching engine находит дубликаты с accuracy >80%
- [ ] Price comparison engine корректно определяет лучшие цены
- [ ] Unified catalog отображает актуальную информацию
- [ ] Telegram bot поддерживает новые команды

#### **Performance Requirements:**
- [ ] Обработка файла 1000+ товаров <60 секунд
- [ ] Product matching <100ms на товар
- [ ] Database queries <1 секунда для catalog
- [ ] Memory usage <2GB для worker процесса

#### **Business Logic Validation:**
- [ ] Идентичные товары от разных поставщиков объединяются
- [ ] Лучшие цены определяются корректно
- [ ] Procurement recommendations дают экономию >5%
- [ ] Competitive analysis отражает реальную ситуацию

#### **Production Readiness:**
- [ ] Docker containers работают стабильно
- [ ] Database migrations выполняются без ошибок
- [ ] Monitoring и logging настроены
- [ ] Error handling покрывает edge cases
- [ ] Documentation обновлена

---

## 🚀 **EXPECTED BUSINESS OUTCOMES**

### 📊 **Measurable Results:**
- **Cost Savings:** 10-25% экономия на закупках через price optimization
- **Time Efficiency:** 80% сокращение времени на сравнение цен
- **Decision Quality:** 95% procurement decisions основаны на data
- **Market Intelligence:** Real-time visibility цен всех поставщиков Бали
- **Supplier Management:** Automated competitive analysis каждого поставщика

### 🎯 **Success Metrics:**
- **System Usage:** >90% staff adoption в течение 2 недель
- **Data Quality:** >95% accuracy автоматического matching товаров  
- **Business Impact:** Measurable cost reduction в первый месяц
- **Operational Efficiency:** 5x faster procurement decision making

---

**🎉 РЕЗУЛЬТАТ: Полностью функциональная unified price comparison система для острова Бали, готовая к production использованию!**