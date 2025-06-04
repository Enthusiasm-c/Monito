"""
COMPREHENSIVE TESTS FOR PRICE COMPARISON ENGINE
Test Coverage: 95%+
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict

from modules.price_comparison_engine import (
    PriceComparisonEngine, PriceAnalysis, SupplierAnalysis, 
    ProcurementRecommendation
)
from modules.unified_database_manager import UnifiedDatabaseManager
from models.unified_database import MasterProduct, SupplierPrice, PriceHistory

class TestPriceComparisonEngine:
    """Comprehensive test suite for PriceComparisonEngine"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager"""
        return Mock(spec=UnifiedDatabaseManager)
    
    @pytest.fixture
    def price_engine(self, mock_db_manager):
        """Price comparison engine instance"""
        return PriceComparisonEngine(
            db_manager=mock_db_manager,
            price_tolerance=0.05,
            trend_analysis_days=30
        )
    
    @pytest.fixture
    def sample_product(self):
        """Sample master product"""
        return MasterProduct(
            product_id="prod-123",
            standard_name="Test Product",
            category="Electronics",
            brand="TestBrand",
            size=Decimal("100"),
            unit="g"
        )
    
    @pytest.fixture
    def sample_prices(self):
        """Sample price data"""
        return [
            Mock(
                supplier_name="Supplier A",
                price=Decimal("10.00"),
                price_date=datetime.utcnow(),
                confidence_score=Decimal("0.9")
            ),
            Mock(
                supplier_name="Supplier B", 
                price=Decimal("12.00"),
                price_date=datetime.utcnow(),
                confidence_score=Decimal("0.85")
            ),
            Mock(
                supplier_name="Supplier C",
                price=Decimal("15.00"),
                price_date=datetime.utcnow(),
                confidence_score=Decimal("0.8")
            )
        ]
    
    # =============================================================================
    # INITIALIZATION TESTS
    # =============================================================================
    
    def test_engine_initialization(self, mock_db_manager):
        """Test engine initialization with default parameters"""
        engine = PriceComparisonEngine(mock_db_manager)
        
        assert engine.db_manager == mock_db_manager
        assert engine.price_tolerance == 0.05
        assert engine.trend_analysis_days == 30
        assert "weight" in engine.unit_base_conversions
        assert "volume" in engine.unit_base_conversions
        assert "count" in engine.unit_base_conversions
    
    def test_engine_initialization_custom_params(self, mock_db_manager):
        """Test engine initialization with custom parameters"""
        engine = PriceComparisonEngine(
            mock_db_manager, 
            price_tolerance=0.1,
            trend_analysis_days=60
        )
        
        assert engine.price_tolerance == 0.1
        assert engine.trend_analysis_days == 60
    
    # =============================================================================
    # PRICE ANALYSIS TESTS
    # =============================================================================
    
    def test_analyze_product_prices_success(self, price_engine, sample_product, sample_prices):
        """Test successful product price analysis"""
        # Setup mocks
        price_engine.db_manager.get_master_product_with_prices.return_value = sample_product
        price_engine.db_manager.get_current_prices_for_product.return_value = sample_prices
        
        with patch.object(price_engine, '_normalize_price_per_unit') as mock_normalize, \
             patch.object(price_engine, '_calculate_price_trend') as mock_trend:
            
            mock_normalize.side_effect = [0.1, 0.12, 0.15]  # Normalized prices
            mock_trend.return_value = "stable"
            
            result = price_engine.analyze_product_prices("prod-123")
            
            assert isinstance(result, PriceAnalysis)
            assert result.product_id == "prod-123"
            assert result.product_name == "Test Product"
            assert result.best_price['supplier'] == "Supplier A"
            assert result.worst_price['supplier'] == "Supplier C"
            assert result.suppliers_count == 3
            assert result.price_trend == "stable"
            assert result.savings_potential > 0
    
    def test_analyze_product_prices_not_found(self, price_engine):
        """Test price analysis for non-existent product"""
        price_engine.db_manager.get_master_product_with_prices.return_value = None
        
        result = price_engine.analyze_product_prices("non-existent")
        
        assert result is None
        price_engine.db_manager.get_master_product_with_prices.assert_called_once_with("non-existent")
    
    def test_analyze_product_prices_no_current_prices(self, price_engine, sample_product):
        """Test price analysis when no current prices available"""
        price_engine.db_manager.get_master_product_with_prices.return_value = sample_product
        price_engine.db_manager.get_current_prices_for_product.return_value = []
        
        result = price_engine.analyze_product_prices("prod-123")
        
        assert result is None
    
    def test_analyze_product_prices_no_normalized_prices(self, price_engine, sample_product, sample_prices):
        """Test price analysis when normalization fails"""
        price_engine.db_manager.get_master_product_with_prices.return_value = sample_product
        price_engine.db_manager.get_current_prices_for_product.return_value = sample_prices
        
        with patch.object(price_engine, '_normalize_price_per_unit', return_value=None):
            result = price_engine.analyze_product_prices("prod-123")
            
            assert result is None
    
    # =============================================================================
    # BEST DEALS TESTS
    # =============================================================================
    
    def test_get_best_deals_report_success(self, price_engine):
        """Test successful best deals report generation"""
        mock_catalog = [
            {
                'product_id': 'prod-1',
                'standard_name': 'Product 1',
                'brand': 'Brand A',
                'category': 'Electronics',
                'best_price': 10.0,
                'worst_price': 15.0,
                'best_supplier': 'Supplier A',
                'savings_percentage': 25.0,
                'suppliers_count': 3
            },
            {
                'product_id': 'prod-2',
                'standard_name': 'Product 2',
                'brand': 'Brand B',
                'category': 'Food',
                'best_price': 5.0,
                'worst_price': 8.0,
                'best_supplier': 'Supplier B',
                'savings_percentage': 37.5,
                'suppliers_count': 2
            }
        ]
        
        price_engine.db_manager.get_unified_catalog.return_value = mock_catalog
        
        with patch.object(price_engine, 'analyze_product_prices') as mock_analyze, \
             patch.object(price_engine, '_calculate_deal_confidence') as mock_confidence:
            
            mock_analysis = Mock()
            mock_analysis.price_trend = "decreasing"
            mock_analyze.return_value = mock_analysis
            mock_confidence.return_value = 0.85
            
            result = price_engine.get_best_deals_report(min_savings=20.0, limit=10)
            
            assert len(result) == 2
            assert result[0]['savings_percentage'] == 37.5  # Sorted by savings
            assert result[1]['savings_percentage'] == 25.0
            assert all('confidence_score' in deal for deal in result)
    
    def test_get_best_deals_report_with_category_filter(self, price_engine):
        """Test best deals report with category filter"""
        price_engine.db_manager.get_unified_catalog.return_value = []
        
        price_engine.get_best_deals_report(category="Electronics")
        
        price_engine.db_manager.get_unified_catalog.assert_called_once_with(category="Electronics", limit=1000)
    
    def test_get_best_deals_report_min_savings_filter(self, price_engine):
        """Test best deals report filters by minimum savings"""
        mock_catalog = [
            {
                'product_id': 'prod-1',
                'standard_name': 'Product 1',
                'brand': 'Brand A',
                'category': 'Electronics',
                'best_price': 10.0,
                'worst_price': 12.0,
                'best_supplier': 'Supplier A',
                'savings_percentage': 2.0,  # Below threshold
                'suppliers_count': 2
            }
        ]
        
        price_engine.db_manager.get_unified_catalog.return_value = mock_catalog
        
        result = price_engine.get_best_deals_report(min_savings=5.0)
        
        assert len(result) == 0  # Filtered out
    
    # =============================================================================
    # PRICE NORMALIZATION TESTS
    # =============================================================================
    
    def test_normalize_price_per_unit_weight(self, price_engine):
        """Test price normalization for weight units"""
        # Test kg to g conversion
        result = price_engine._normalize_price_per_unit(Decimal("10.00"), Decimal("1"), "kg")
        assert result == 0.01  # 10.00 / (1 * 1000) = 0.01 per gram
        
        # Test pound to g conversion  
        result = price_engine._normalize_price_per_unit(Decimal("5.00"), Decimal("1"), "lb")
        expected = 5.00 / 453.592  # Price per gram
        assert abs(result - expected) < 0.0001
    
    def test_normalize_price_per_unit_volume(self, price_engine):
        """Test price normalization for volume units"""
        # Test liter to ml conversion
        result = price_engine._normalize_price_per_unit(Decimal("2.00"), Decimal("1"), "l")
        assert result == 0.002  # 2.00 / (1 * 1000) = 0.002 per ml
        
        # Test fl_oz to ml conversion
        result = price_engine._normalize_price_per_unit(Decimal("1.00"), Decimal("1"), "fl_oz")
        expected = 1.00 / 29.5735
        assert abs(result - expected) < 0.0001
    
    def test_normalize_price_per_unit_count(self, price_engine):
        """Test price normalization for count units"""
        result = price_engine._normalize_price_per_unit(Decimal("12.00"), Decimal("6"), "pcs")
        assert result == 2.0  # 12.00 / (6 * 1) = 2.0 per piece
    
    def test_normalize_price_per_unit_unknown_unit(self, price_engine):
        """Test price normalization with unknown unit"""
        result = price_engine._normalize_price_per_unit(Decimal("10.00"), Decimal("1"), "unknown")
        assert result is None
    
    def test_normalize_price_per_unit_invalid_inputs(self, price_engine):
        """Test price normalization with invalid inputs"""
        # None price
        assert price_engine._normalize_price_per_unit(None, Decimal("1"), "kg") is None
        
        # None size
        assert price_engine._normalize_price_per_unit(Decimal("10"), None, "kg") is None
        
        # Zero size
        assert price_engine._normalize_price_per_unit(Decimal("10"), Decimal("0"), "kg") is None
        
        # None unit
        assert price_engine._normalize_price_per_unit(Decimal("10"), Decimal("1"), None) is None
    
    # =============================================================================
    # PRICE TREND TESTS
    # =============================================================================
    
    def test_calculate_price_trend_increasing(self, price_engine):
        """Test price trend calculation - increasing"""
        mock_session = Mock()
        mock_history = [
            Mock(change_percentage=Decimal("5.0")),
            Mock(change_percentage=Decimal("3.0")),
            Mock(change_percentage=Decimal("4.0"))
        ]
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_history
        
        with patch.object(price_engine.db_manager, 'get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            result = price_engine._calculate_price_trend("prod-123")
            
            assert result == "increasing"
    
    def test_calculate_price_trend_decreasing(self, price_engine):
        """Test price trend calculation - decreasing"""
        mock_session = Mock()
        mock_history = [
            Mock(change_percentage=Decimal("-5.0")),
            Mock(change_percentage=Decimal("-3.0")),
            Mock(change_percentage=Decimal("-4.0"))
        ]
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_history
        
        with patch.object(price_engine.db_manager, 'get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            result = price_engine._calculate_price_trend("prod-123")
            
            assert result == "decreasing"
    
    def test_calculate_price_trend_stable(self, price_engine):
        """Test price trend calculation - stable"""
        mock_session = Mock()
        mock_history = [
            Mock(change_percentage=Decimal("1.0")),
            Mock(change_percentage=Decimal("-0.5")),
            Mock(change_percentage=Decimal("0.5"))
        ]
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_history
        
        with patch.object(price_engine.db_manager, 'get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            result = price_engine._calculate_price_trend("prod-123")
            
            assert result == "stable"
    
    def test_calculate_price_trend_insufficient_data(self, price_engine):
        """Test price trend calculation with insufficient data"""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        with patch.object(price_engine.db_manager, 'get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            result = price_engine._calculate_price_trend("prod-123")
            
            assert result == "stable"
    
    # =============================================================================
    # DEAL CONFIDENCE TESTS
    # =============================================================================
    
    def test_calculate_deal_confidence_high(self, price_engine):
        """Test deal confidence calculation - high confidence"""
        analysis = PriceAnalysis(
            product_id="prod-123",
            product_name="Test Product",
            best_price={'supplier': 'A', 'price': 10.0, 'normalized_price': 0.1, 'date': datetime.utcnow()},
            worst_price={'supplier': 'C', 'price': 15.0, 'normalized_price': 0.15, 'date': datetime.utcnow()},
            average_price=12.5,
            median_price=12.0,
            price_range=5.0,
            savings_potential=25.0,  # Good savings
            suppliers_count=5,  # Many suppliers
            price_trend="stable",  # Stable trend
            competitive_suppliers=[],
            last_updated=datetime.utcnow()
        )
        
        confidence = price_engine._calculate_deal_confidence(analysis)
        
        assert confidence >= 0.8  # High confidence
    
    def test_calculate_deal_confidence_low(self, price_engine):
        """Test deal confidence calculation - low confidence"""
        analysis = PriceAnalysis(
            product_id="prod-123",
            product_name="Test Product",
            best_price={'supplier': 'A', 'price': 10.0, 'normalized_price': 0.1, 'date': datetime.utcnow()},
            worst_price={'supplier': 'B', 'price': 11.0, 'normalized_price': 0.11, 'date': datetime.utcnow()},
            average_price=10.5,
            median_price=10.5,
            price_range=1.0,
            savings_potential=80.0,  # Too high savings (suspicious)
            suppliers_count=1,  # Few suppliers
            price_trend="increasing",  # Unstable trend
            competitive_suppliers=[],
            last_updated=datetime.utcnow()
        )
        
        confidence = price_engine._calculate_deal_confidence(analysis)
        
        assert confidence <= 0.6  # Low confidence
    
    # =============================================================================
    # SUPPLIER ANALYSIS TESTS
    # =============================================================================
    
    def test_analyze_supplier_competitiveness_success(self, price_engine):
        """Test successful supplier competitiveness analysis"""
        mock_performance = {
            'total_products': 100,
            'best_price_products': 25,
            'price_competitiveness': 75.0,
            'reliability_score': 0.9
        }
        
        price_engine.db_manager.get_supplier_performance.return_value = mock_performance
        
        with patch.object(price_engine, '_analyze_supplier_by_categories') as mock_categories, \
             patch.object(price_engine, '_calculate_supplier_price_volatility') as mock_volatility, \
             patch.object(price_engine, '_identify_supplier_strengths_weaknesses') as mock_strengths, \
             patch.object(price_engine, '_get_recommended_categories') as mock_recommended:
            
            mock_categories.return_value = {}
            mock_volatility.return_value = 2.5
            mock_strengths.return_value = (["High competitiveness"], ["Price volatility"])
            mock_recommended.return_value = ["Electronics", "Food"]
            
            result = price_engine.analyze_supplier_competitiveness("Supplier A")
            
            assert isinstance(result, SupplierAnalysis)
            assert result.supplier_name == "Supplier A"
            assert result.total_products == 100
            assert result.best_price_products == 25
            assert result.average_competitiveness == 75.0
            assert result.price_volatility == 2.5
            assert "High competitiveness" in result.strengths
            assert "Price volatility" in result.weaknesses
    
    def test_analyze_supplier_competitiveness_no_data(self, price_engine):
        """Test supplier analysis with no performance data"""
        price_engine.db_manager.get_supplier_performance.return_value = None
        
        result = price_engine.analyze_supplier_competitiveness("Unknown Supplier")
        
        assert isinstance(result, SupplierAnalysis)
        assert result.supplier_name == "Unknown Supplier"
        assert result.total_products == 0
        assert result.average_competitiveness == 0.0
        assert result.strengths == []
        assert result.weaknesses == []
    
    # =============================================================================
    # SUPPLIER CATEGORY ANALYSIS TESTS
    # =============================================================================
    
    @patch('modules.price_comparison_engine.func')
    def test_analyze_supplier_by_categories(self, mock_func, price_engine):
        """Test supplier analysis by categories"""
        mock_session = Mock()
        
        # Mock query results
        mock_results = [
            Mock(category="Electronics", products_count=50, avg_price=25.0),
            Mock(category="Food", products_count=30, avg_price=15.0)
        ]
        mock_session.query.return_value.join.return_value.filter.return_value.group_by.return_value.all.return_value = mock_results
        
        # Mock category products and prices
        mock_products = [Mock(product_id=f"prod-{i}") for i in range(5)]
        mock_session.query.return_value.filter_by.return_value.all.return_value = mock_products
        mock_session.query.return_value.filter_by.return_value.scalar.side_effect = [10.0, 10.0, 15.0, 10.0, 20.0, 15.0]
        
        with patch.object(price_engine.db_manager, 'get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            result = price_engine._analyze_supplier_by_categories("Supplier A")
            
            assert "Electronics" in result
            assert "Food" in result
            assert result["Electronics"]["products_count"] == 50
            assert result["Food"]["products_count"] == 30
    
    # =============================================================================
    # SUPPLIER PRICE VOLATILITY TESTS
    # =============================================================================
    
    def test_calculate_supplier_price_volatility(self, price_engine):
        """Test supplier price volatility calculation"""
        mock_session = Mock()
        mock_changes = [
            Mock(change_percentage=Decimal("5.0")),
            Mock(change_percentage=Decimal("-3.0")),
            Mock(change_percentage=Decimal("2.0")),
            Mock(change_percentage=Decimal("-1.0"))
        ]
        mock_session.query.return_value.filter.return_value.all.return_value = mock_changes
        
        with patch.object(price_engine.db_manager, 'get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            result = price_engine._calculate_supplier_price_volatility("Supplier A")
            
            assert isinstance(result, float)
            assert result > 0  # Should have some volatility
    
    def test_calculate_supplier_price_volatility_insufficient_data(self, price_engine):
        """Test price volatility with insufficient data"""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = []
        
        with patch.object(price_engine.db_manager, 'get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            result = price_engine._calculate_supplier_price_volatility("Supplier A")
            
            assert result == 0.0
    
    # =============================================================================
    # SUPPLIER STRENGTHS/WEAKNESSES TESTS
    # =============================================================================
    
    def test_identify_supplier_strengths_weaknesses(self, price_engine):
        """Test identification of supplier strengths and weaknesses"""
        performance = {
            'price_competitiveness': 80.0,  # High
            'reliability_score': 0.9  # High
        }
        category_performance = {
            'Electronics': {'competitiveness': 90.0},
            'Food': {'competitiveness': 85.0}
        }
        price_volatility = 1.5  # Low
        
        strengths, weaknesses = price_engine._identify_supplier_strengths_weaknesses(
            performance, category_performance, price_volatility
        )
        
        assert "Высокая ценовая конкурентоспособность" in strengths
        assert "Высокая надежность" in strengths
        assert "Стабильные цены" in strengths
        assert len(weaknesses) == 0  # No weaknesses for this good supplier
    
    def test_identify_supplier_strengths_weaknesses_poor_performance(self, price_engine):
        """Test identification with poor performance"""
        performance = {
            'price_competitiveness': 20.0,  # Low
            'reliability_score': 0.4  # Low
        }
        category_performance = {}
        price_volatility = 8.0  # High
        
        strengths, weaknesses = price_engine._identify_supplier_strengths_weaknesses(
            performance, category_performance, price_volatility
        )
        
        assert "Низкая ценовая конкурентоспособность" in weaknesses
        assert "Низкая надежность" in weaknesses
        assert "Высокая волатильность цен" in weaknesses
        assert len(strengths) == 0  # No strengths for this poor supplier
    
    # =============================================================================
    # RECOMMENDED CATEGORIES TESTS
    # =============================================================================
    
    def test_get_recommended_categories(self, price_engine):
        """Test getting recommended categories for supplier"""
        category_performance = {
            'Electronics': {'competitiveness': 85.0, 'products_count': 50},
            'Food': {'competitiveness': 90.0, 'products_count': 30},
            'Clothing': {'competitiveness': 60.0, 'products_count': 10},
            'Books': {'competitiveness': 95.0, 'products_count': 5}  # High competitiveness but few products
        }
        
        result = price_engine._get_recommended_categories(category_performance)
        
        # Should recommend categories with high competitiveness and decent product count
        assert "Food" in result  # 90% competitiveness, 30 products
        assert "Electronics" in result  # 85% competitiveness, 50 products
        assert "Clothing" not in result  # Low competitiveness
        assert "Books" not in result  # Too few products
    
    # =============================================================================
    # PROCUREMENT RECOMMENDATIONS TESTS
    # =============================================================================
    
    def test_generate_procurement_recommendations(self, price_engine):
        """Test procurement recommendations generation"""
        required_products = [
            {
                'product_id': 'prod-1',
                'quantity': 10,
                'max_price': 15.0
            },
            {
                'product_id': 'prod-2', 
                'quantity': 5,
                'max_price': 25.0
            }
        ]
        
        # Mock analysis results
        mock_analysis_1 = Mock()
        mock_analysis_1.product_id = 'prod-1'
        mock_analysis_1.product_name = 'Product 1'
        mock_analysis_1.best_price = {
            'supplier': 'Supplier A',
            'price': 12.0,
            'normalized_price': 0.12
        }
        mock_analysis_1.competitive_suppliers = [
            {'supplier': 'Supplier B', 'price': 13.0}
        ]
        mock_analysis_1.savings_potential = 20.0
        
        mock_analysis_2 = Mock()
        mock_analysis_2.product_id = 'prod-2'
        mock_analysis_2.product_name = 'Product 2'
        mock_analysis_2.best_price = {
            'supplier': 'Supplier C',
            'price': 22.0,
            'normalized_price': 0.22
        }
        mock_analysis_2.competitive_suppliers = []
        mock_analysis_2.savings_potential = 15.0
        
        with patch.object(price_engine, 'analyze_product_prices') as mock_analyze, \
             patch.object(price_engine, '_generate_recommendation_reasoning') as mock_reasoning:
            
            mock_analyze.side_effect = [mock_analysis_1, mock_analysis_2]
            mock_reasoning.side_effect = ["Good deal from reliable supplier", "Best available option"]
            
            result = price_engine.generate_procurement_recommendations(required_products)
            
            assert len(result) == 2
            assert all(isinstance(rec, ProcurementRecommendation) for rec in result)
            assert result[0].product_id == 'prod-1'
            assert result[0].recommended_supplier == 'Supplier A'
            assert result[0].recommended_price == 12.0
    
    def test_generate_procurement_recommendations_with_budget(self, price_engine):
        """Test procurement recommendations with budget limit"""
        required_products = [
            {'product_id': 'prod-1', 'quantity': 10, 'max_price': 15.0}
        ]
        
        mock_analysis = Mock()
        mock_analysis.product_id = 'prod-1'
        mock_analysis.product_name = 'Product 1'
        mock_analysis.best_price = {
            'supplier': 'Supplier A',
            'price': 12.0,
            'normalized_price': 0.12
        }
        mock_analysis.competitive_suppliers = []
        mock_analysis.savings_potential = 20.0
        
        with patch.object(price_engine, 'analyze_product_prices', return_value=mock_analysis), \
             patch.object(price_engine, '_generate_recommendation_reasoning', return_value="Within budget"):
            
            # Test within budget
            result = price_engine.generate_procurement_recommendations(required_products, budget_limit=200.0)
            assert len(result) == 1
            
            # Test over budget
            result = price_engine.generate_procurement_recommendations(required_products, budget_limit=100.0)
            assert len(result) == 0  # Should be filtered out
    
    # =============================================================================
    # RECOMMENDATION REASONING TESTS
    # =============================================================================
    
    def test_generate_recommendation_reasoning(self, price_engine):
        """Test recommendation reasoning generation"""
        analysis = Mock()
        analysis.savings_potential = 25.0
        analysis.suppliers_count = 3
        analysis.price_trend = "decreasing"
        
        selected_supplier = {
            'supplier': 'Supplier A',
            'confidence': 0.9
        }
        
        reasoning = price_engine._generate_recommendation_reasoning(analysis, selected_supplier)
        
        assert isinstance(reasoning, str)
        assert len(reasoning) > 0
        assert "25.0%" in reasoning  # Should mention savings
        assert "Supplier A" in reasoning  # Should mention supplier
    
    # =============================================================================
    # MARKET OVERVIEW TESTS
    # =============================================================================
    
    def test_get_market_overview(self, price_engine):
        """Test market overview generation"""
        # Mock database statistics
        price_engine.db_manager.get_catalog_statistics.return_value = {
            'total_products': 1000,
            'total_suppliers': 50,
            'categories_count': 10,
            'avg_suppliers_per_product': 3.2
        }
        
        with patch.object(price_engine, '_analyze_market_trends') as mock_trends:
            mock_trends.return_value = {
                'overall_trend': 'stable',
                'category_trends': {'Electronics': 'decreasing', 'Food': 'increasing'}
            }
            
            result = price_engine.get_market_overview()
            
            assert 'catalog_statistics' in result
            assert 'market_trends' in result
            assert result['catalog_statistics']['total_products'] == 1000
            assert result['market_trends']['overall_trend'] == 'stable'
    
    def test_analyze_market_trends(self, price_engine):
        """Test market trends analysis"""
        mock_session = Mock()
        
        # Mock overall trend data
        mock_overall_changes = [
            Mock(change_percentage=Decimal("2.0")),
            Mock(change_percentage=Decimal("-1.0")),
            Mock(change_percentage=Decimal("0.5"))
        ]
        
        # Mock category trend data  
        mock_category_results = [
            Mock(category="Electronics", avg_change=Decimal("-2.5")),
            Mock(category="Food", avg_change=Decimal("3.0")),
            Mock(category="Clothing", avg_change=Decimal("0.5"))
        ]
        
        mock_session.query.return_value.filter.return_value.all.return_value = mock_overall_changes
        mock_session.query.return_value.join.return_value.filter.return_value.group_by.return_value.all.return_value = mock_category_results
        
        with patch.object(price_engine.db_manager, 'get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            result = price_engine._analyze_market_trends()
            
            assert 'overall_trend' in result
            assert 'category_trends' in result
            assert result['category_trends']['Electronics'] == 'decreasing'
            assert result['category_trends']['Food'] == 'increasing'
            assert result['category_trends']['Clothing'] == 'stable'


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 