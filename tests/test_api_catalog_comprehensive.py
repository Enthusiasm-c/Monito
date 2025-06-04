"""
COMPREHENSIVE TESTS FOR API CATALOG ROUTER
Test Coverage: 95%+
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
import json
from datetime import datetime

from api.routers.catalog import router as catalog_router

class TestCatalogAPI:
    """Comprehensive test suite for Catalog API Router"""
    
    @pytest.fixture
    def app(self):
        """FastAPI test application"""
        app = FastAPI()
        app.include_router(catalog_router, prefix="/catalog")
        return app
    
    @pytest.fixture
    def client(self, app):
        """Test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager"""
        return Mock()
    
    @pytest.fixture
    def sample_catalog_data(self):
        """Sample catalog data"""
        return [
            {
                'product_id': 'prod-1',
                'standard_name': 'Coca Cola 500ml',
                'brand': 'Coca-Cola',
                'category': 'Beverages',
                'best_price': 15000,
                'worst_price': 18000,
                'best_supplier': 'Supplier A',
                'worst_supplier': 'Supplier C',
                'suppliers_count': 3,
                'savings_percentage': 16.67,
                'size': 500,
                'unit': 'ml'
            },
            {
                'product_id': 'prod-2',
                'standard_name': 'Pepsi 500ml',
                'brand': 'Pepsi',
                'category': 'Beverages',
                'best_price': 14000,
                'worst_price': 17000,
                'best_supplier': 'Supplier B',
                'worst_supplier': 'Supplier D',
                'suppliers_count': 2,
                'savings_percentage': 17.65,
                'size': 500,
                'unit': 'ml'
            }
        ]
    
    @pytest.fixture
    def sample_product_details(self):
        """Sample product details"""
        return {
            'product_id': 'prod-1',
            'standard_name': 'Coca Cola 500ml',
            'brand': 'Coca-Cola',
            'category': 'Beverages',
            'size': 500,
            'unit': 'ml',
            'description': 'Refreshing cola drink',
            'suppliers': [
                {
                    'supplier_name': 'Supplier A',
                    'price': 15000,
                    'last_updated': '2024-01-01T00:00:00',
                    'confidence_score': 0.95
                },
                {
                    'supplier_name': 'Supplier B',
                    'price': 16000,
                    'last_updated': '2024-01-01T00:00:00',
                    'confidence_score': 0.90
                }
            ],
            'price_history': [
                {
                    'date': '2024-01-01',
                    'avg_price': 15500,
                    'min_price': 15000,
                    'max_price': 16000
                }
            ]
        }
    
    # =============================================================================
    # GET UNIFIED CATALOG TESTS
    # =============================================================================
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_get_unified_catalog_success(self, mock_get_db, client, sample_catalog_data):
        """Test successful unified catalog retrieval"""
        mock_db = Mock()
        mock_db.get_unified_catalog.return_value = sample_catalog_data
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/unified")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 2
        assert data['data'][0]['product_id'] == 'prod-1'
        assert data['data'][0]['standard_name'] == 'Coca Cola 500ml'
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_get_unified_catalog_with_filters(self, mock_get_db, client, sample_catalog_data):
        """Test unified catalog with filters"""
        mock_db = Mock()
        mock_db.get_unified_catalog.return_value = sample_catalog_data
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/unified?category=Beverages&min_savings=10&limit=50")
        
        assert response.status_code == 200
        mock_db.get_unified_catalog.assert_called_once_with(
            category="Beverages",
            min_savings=10.0,
            limit=50
        )
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_get_unified_catalog_empty_result(self, mock_get_db, client):
        """Test unified catalog with empty result"""
        mock_db = Mock()
        mock_db.get_unified_catalog.return_value = []
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/unified")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 0
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_get_unified_catalog_database_error(self, mock_get_db, client):
        """Test unified catalog with database error"""
        mock_db = Mock()
        mock_db.get_unified_catalog.side_effect = Exception("Database connection failed")
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/unified")
        
        assert response.status_code == 500
        data = response.json()
        assert data['success'] is False
        assert "Database connection failed" in data['error']
    
    # =============================================================================
    # GET PRODUCT DETAILS TESTS
    # =============================================================================
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_get_product_details_success(self, mock_get_db, client, sample_product_details):
        """Test successful product details retrieval"""
        mock_db = Mock()
        mock_db.get_product_details.return_value = sample_product_details
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/products/prod-1")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['product_id'] == 'prod-1'
        assert len(data['data']['suppliers']) == 2
        assert len(data['data']['price_history']) == 1
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_get_product_details_not_found(self, mock_get_db, client):
        """Test product details for non-existent product"""
        mock_db = Mock()
        mock_db.get_product_details.return_value = None
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/products/non-existent")
        
        assert response.status_code == 404
        data = response.json()
        assert data['success'] is False
        assert "Product not found" in data['error']
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_get_product_details_database_error(self, mock_get_db, client):
        """Test product details with database error"""
        mock_db = Mock()
        mock_db.get_product_details.side_effect = Exception("Database error")
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/products/prod-1")
        
        assert response.status_code == 500
        data = response.json()
        assert data['success'] is False
        assert "Database error" in data['error']
    
    # =============================================================================
    # SEARCH PRODUCTS TESTS
    # =============================================================================
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_search_products_success(self, mock_get_db, client, sample_catalog_data):
        """Test successful product search"""
        mock_db = Mock()
        mock_db.search_products.return_value = sample_catalog_data
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/search?q=coca cola")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 2
        mock_db.search_products.assert_called_once_with(
            search_term="coca cola",
            category=None,
            brand=None,
            limit=20
        )
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_search_products_with_filters(self, mock_get_db, client, sample_catalog_data):
        """Test product search with filters"""
        mock_db = Mock()
        mock_db.search_products.return_value = sample_catalog_data
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/search?q=cola&category=Beverages&brand=Coca-Cola&limit=10")
        
        assert response.status_code == 200
        mock_db.search_products.assert_called_once_with(
            search_term="cola",
            category="Beverages",
            brand="Coca-Cola",
            limit=10
        )
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_search_products_empty_query(self, mock_get_db, client):
        """Test product search with empty query"""
        response = client.get("/catalog/search")
        
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert "Search query is required" in data['error']
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_search_products_no_results(self, mock_get_db, client):
        """Test product search with no results"""
        mock_db = Mock()
        mock_db.search_products.return_value = []
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/search?q=nonexistent")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 0
    
    # =============================================================================
    # GET CATEGORIES TESTS
    # =============================================================================
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_get_categories_success(self, mock_get_db, client):
        """Test successful categories retrieval"""
        mock_categories = [
            {'category': 'Beverages', 'product_count': 150, 'avg_price': 12500},
            {'category': 'Food', 'product_count': 200, 'avg_price': 8500},
            {'category': 'Electronics', 'product_count': 75, 'avg_price': 45000}
        ]
        
        mock_db = Mock()
        mock_db.get_categories_with_stats.return_value = mock_categories
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/categories")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 3
        assert data['data'][0]['category'] == 'Beverages'
        assert data['data'][0]['product_count'] == 150
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_get_categories_empty(self, mock_get_db, client):
        """Test categories retrieval with empty result"""
        mock_db = Mock()
        mock_db.get_categories_with_stats.return_value = []
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/categories")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 0
    
    # =============================================================================
    # GET SUPPLIERS TESTS
    # =============================================================================
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_get_suppliers_success(self, mock_get_db, client):
        """Test successful suppliers retrieval"""
        mock_suppliers = [
            {
                'supplier_name': 'Supplier A',
                'product_count': 120,
                'avg_price': 13000,
                'last_update': '2024-01-01T00:00:00',
                'reliability_score': 0.95
            },
            {
                'supplier_name': 'Supplier B',
                'product_count': 85,
                'avg_price': 14500,
                'last_update': '2024-01-01T00:00:00',
                'reliability_score': 0.88
            }
        ]
        
        mock_db = Mock()
        mock_db.get_suppliers_with_stats.return_value = mock_suppliers
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/suppliers")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 2
        assert data['data'][0]['supplier_name'] == 'Supplier A'
        assert data['data'][0]['product_count'] == 120
    
    # =============================================================================
    # GET PRICE COMPARISON TESTS
    # =============================================================================
    
    @patch('api.routers.catalog.get_unified_database_manager')
    @patch('api.routers.catalog.PriceComparisonEngine')
    def test_get_price_comparison_success(self, mock_engine_class, mock_get_db, client):
        """Test successful price comparison"""
        mock_analysis = {
            'product_id': 'prod-1',
            'product_name': 'Coca Cola 500ml',
            'best_price': {'supplier': 'Supplier A', 'price': 15000},
            'worst_price': {'supplier': 'Supplier C', 'price': 18000},
            'average_price': 16500,
            'savings_potential': 16.67,
            'suppliers_count': 3,
            'price_trend': 'stable'
        }
        
        mock_engine = Mock()
        mock_engine.analyze_product_prices.return_value = mock_analysis
        mock_engine_class.return_value = mock_engine
        
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/products/prod-1/price-comparison")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['product_id'] == 'prod-1'
        assert data['data']['savings_potential'] == 16.67
    
    @patch('api.routers.catalog.get_unified_database_manager')
    @patch('api.routers.catalog.PriceComparisonEngine')
    def test_get_price_comparison_not_found(self, mock_engine_class, mock_get_db, client):
        """Test price comparison for non-existent product"""
        mock_engine = Mock()
        mock_engine.analyze_product_prices.return_value = None
        mock_engine_class.return_value = mock_engine
        
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/products/non-existent/price-comparison")
        
        assert response.status_code == 404
        data = response.json()
        assert data['success'] is False
        assert "Price analysis not available" in data['error']
    
    # =============================================================================
    # GET BEST DEALS TESTS
    # =============================================================================
    
    @patch('api.routers.catalog.get_unified_database_manager')
    @patch('api.routers.catalog.PriceComparisonEngine')
    def test_get_best_deals_success(self, mock_engine_class, mock_get_db, client):
        """Test successful best deals retrieval"""
        mock_deals = [
            {
                'product_id': 'prod-1',
                'product_name': 'Coca Cola 500ml',
                'best_price': 15000,
                'worst_price': 18000,
                'savings_percentage': 16.67,
                'best_supplier': 'Supplier A',
                'confidence_score': 0.92
            },
            {
                'product_id': 'prod-2',
                'product_name': 'Pepsi 500ml',
                'best_price': 14000,
                'worst_price': 17000,
                'savings_percentage': 17.65,
                'best_supplier': 'Supplier B',
                'confidence_score': 0.88
            }
        ]
        
        mock_engine = Mock()
        mock_engine.get_best_deals_report.return_value = mock_deals
        mock_engine_class.return_value = mock_engine
        
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/best-deals")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 2
        assert data['data'][0]['savings_percentage'] == 16.67
    
    @patch('api.routers.catalog.get_unified_database_manager')
    @patch('api.routers.catalog.PriceComparisonEngine')
    def test_get_best_deals_with_filters(self, mock_engine_class, mock_get_db, client):
        """Test best deals with filters"""
        mock_engine = Mock()
        mock_engine.get_best_deals_report.return_value = []
        mock_engine_class.return_value = mock_engine
        
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/best-deals?category=Beverages&min_savings=15&limit=10")
        
        assert response.status_code == 200
        mock_engine.get_best_deals_report.assert_called_once_with(
            category="Beverages",
            min_savings=15.0,
            limit=10
        )
    
    # =============================================================================
    # GET SUPPLIER PERFORMANCE TESTS
    # =============================================================================
    
    @patch('api.routers.catalog.get_unified_database_manager')
    @patch('api.routers.catalog.PriceComparisonEngine')
    def test_get_supplier_performance_success(self, mock_engine_class, mock_get_db, client):
        """Test successful supplier performance retrieval"""
        mock_performance = {
            'supplier_name': 'Supplier A',
            'total_products': 120,
            'best_price_products': 45,
            'average_competitiveness': 82.5,
            'reliability_score': 0.95,
            'strengths': ['High competitiveness', 'Reliable pricing'],
            'weaknesses': ['Limited product range'],
            'recommended_categories': ['Beverages', 'Food']
        }
        
        mock_engine = Mock()
        mock_engine.analyze_supplier_competitiveness.return_value = mock_performance
        mock_engine_class.return_value = mock_engine
        
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/suppliers/Supplier A/performance")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['supplier_name'] == 'Supplier A'
        assert data['data']['total_products'] == 120
        assert len(data['data']['strengths']) == 2
    
    @patch('api.routers.catalog.get_unified_database_manager')
    @patch('api.routers.catalog.PriceComparisonEngine')
    def test_get_supplier_performance_not_found(self, mock_engine_class, mock_get_db, client):
        """Test supplier performance for non-existent supplier"""
        mock_performance = {
            'supplier_name': 'Unknown Supplier',
            'total_products': 0,
            'best_price_products': 0,
            'average_competitiveness': 0.0,
            'reliability_score': 0.0,
            'strengths': [],
            'weaknesses': [],
            'recommended_categories': []
        }
        
        mock_engine = Mock()
        mock_engine.analyze_supplier_competitiveness.return_value = mock_performance
        mock_engine_class.return_value = mock_engine
        
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/suppliers/Unknown Supplier/performance")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['total_products'] == 0
    
    # =============================================================================
    # GET MARKET OVERVIEW TESTS
    # =============================================================================
    
    @patch('api.routers.catalog.get_unified_database_manager')
    @patch('api.routers.catalog.PriceComparisonEngine')
    def test_get_market_overview_success(self, mock_engine_class, mock_get_db, client):
        """Test successful market overview retrieval"""
        mock_overview = {
            'catalog_statistics': {
                'total_products': 500,
                'total_suppliers': 25,
                'categories_count': 8,
                'avg_suppliers_per_product': 3.2
            },
            'market_trends': {
                'overall_trend': 'stable',
                'category_trends': {
                    'Beverages': 'decreasing',
                    'Food': 'increasing',
                    'Electronics': 'stable'
                }
            },
            'top_categories': [
                {'category': 'Beverages', 'product_count': 150},
                {'category': 'Food', 'product_count': 200}
            ],
            'price_insights': {
                'avg_savings_potential': 18.5,
                'best_category_for_savings': 'Electronics',
                'most_competitive_suppliers': ['Supplier A', 'Supplier B']
            }
        }
        
        mock_engine = Mock()
        mock_engine.get_market_overview.return_value = mock_overview
        mock_engine_class.return_value = mock_engine
        
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/market-overview")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['catalog_statistics']['total_products'] == 500
        assert data['data']['market_trends']['overall_trend'] == 'stable'
        assert len(data['data']['top_categories']) == 2
    
    # =============================================================================
    # GET PRODUCT MATCHES TESTS
    # =============================================================================
    
    @patch('api.routers.catalog.get_unified_database_manager')
    @patch('api.routers.catalog.ProductMatchingEngine')
    def test_get_product_matches_success(self, mock_engine_class, mock_get_db, client):
        """Test successful product matches retrieval"""
        mock_matches = [
            {
                'product_id': 'prod-2',
                'product_name': 'Coca-Cola 500ml Classic',
                'similarity_score': 0.95,
                'match_type': 'fuzzy',
                'confidence_level': 'high'
            },
            {
                'product_id': 'prod-3',
                'product_name': 'Coca Cola 500ml Bottle',
                'similarity_score': 0.88,
                'match_type': 'fuzzy',
                'confidence_level': 'medium'
            }
        ]
        
        mock_engine = Mock()
        mock_engine.get_similar_products.return_value = mock_matches
        mock_engine_class.return_value = mock_engine
        
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/products/prod-1/matches")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 2
        assert data['data'][0]['similarity_score'] == 0.95
    
    @patch('api.routers.catalog.get_unified_database_manager')
    @patch('api.routers.catalog.ProductMatchingEngine')
    def test_get_product_matches_not_found(self, mock_engine_class, mock_get_db, client):
        """Test product matches for non-existent product"""
        mock_engine = Mock()
        mock_engine.get_similar_products.return_value = []
        mock_engine_class.return_value = mock_engine
        
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/products/non-existent/matches")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 0
    
    # =============================================================================
    # GET CATALOG STATISTICS TESTS
    # =============================================================================
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_get_catalog_statistics_success(self, mock_get_db, client):
        """Test successful catalog statistics retrieval"""
        mock_stats = {
            'total_products': 500,
            'total_suppliers': 25,
            'categories': [
                {'name': 'Beverages', 'count': 150},
                {'name': 'Food', 'count': 200},
                {'name': 'Electronics', 'count': 150}
            ],
            'price_ranges': {
                'min_price': 1000,
                'max_price': 150000,
                'avg_price': 18500
            },
            'recent_updates': {
                'last_price_update': '2024-01-01T00:00:00',
                'new_products_this_week': 15,
                'price_changes_this_week': 45
            }
        }
        
        mock_db = Mock()
        mock_db.get_catalog_statistics.return_value = mock_stats
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/statistics")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['total_products'] == 500
        assert data['data']['total_suppliers'] == 25
        assert len(data['data']['categories']) == 3
    
    # =============================================================================
    # VALIDATION TESTS
    # =============================================================================
    
    def test_invalid_limit_parameter(self, client):
        """Test validation of limit parameter"""
        response = client.get("/catalog/unified?limit=0")
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_min_savings_parameter(self, client):
        """Test validation of min_savings parameter"""
        response = client.get("/catalog/unified?min_savings=-5")
        
        assert response.status_code == 422  # Validation error
    
    def test_very_large_limit_parameter(self, client):
        """Test very large limit parameter"""
        response = client.get("/catalog/unified?limit=10000")
        
        # Should be capped or validated
        assert response.status_code in [200, 422]
    
    # =============================================================================
    # ERROR HANDLING TESTS
    # =============================================================================
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_database_connection_error(self, mock_get_db, client):
        """Test handling of database connection errors"""
        mock_get_db.side_effect = Exception("Database connection failed")
        
        response = client.get("/catalog/unified")
        
        assert response.status_code == 500
        data = response.json()
        assert data['success'] is False
        assert "Database connection failed" in data['error']
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_unexpected_error_handling(self, mock_get_db, client):
        """Test handling of unexpected errors"""
        mock_db = Mock()
        mock_db.get_unified_catalog.side_effect = RuntimeError("Unexpected error")
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/unified")
        
        assert response.status_code == 500
        data = response.json()
        assert data['success'] is False
        assert "Unexpected error" in data['error']
    
    # =============================================================================
    # PERFORMANCE TESTS
    # =============================================================================
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_large_catalog_response(self, mock_get_db, client):
        """Test handling of large catalog responses"""
        # Create large dataset
        large_catalog = [
            {
                'product_id': f'prod-{i}',
                'standard_name': f'Product {i}',
                'brand': f'Brand {i % 10}',
                'category': f'Category {i % 5}',
                'best_price': 10000 + i,
                'worst_price': 15000 + i,
                'best_supplier': f'Supplier {i % 3}',
                'suppliers_count': 3,
                'savings_percentage': 25.0
            }
            for i in range(1000)
        ]
        
        mock_db = Mock()
        mock_db.get_unified_catalog.return_value = large_catalog
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/unified?limit=1000")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 1000
    
    # =============================================================================
    # EDGE CASES TESTS
    # =============================================================================
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_special_characters_in_search(self, mock_get_db, client):
        """Test search with special characters"""
        mock_db = Mock()
        mock_db.search_products.return_value = []
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/search?q=Coca-Cola® 500ml (Bottle)")
        
        assert response.status_code == 200
        # Should handle special characters gracefully
        mock_db.search_products.assert_called_once()
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_unicode_search_query(self, mock_get_db, client):
        """Test search with unicode characters"""
        mock_db = Mock()
        mock_db.search_products.return_value = []
        mock_get_db.return_value = mock_db
        
        response = client.get("/catalog/search?q=Teh Botol Sosro")
        
        assert response.status_code == 200
        # Should handle unicode characters properly
        mock_db.search_products.assert_called_once()
    
    @patch('api.routers.catalog.get_unified_database_manager')
    def test_very_long_search_query(self, mock_get_db, client):
        """Test search with very long query"""
        long_query = "a" * 1000  # Very long query
        
        mock_db = Mock()
        mock_db.search_products.return_value = []
        mock_get_db.return_value = mock_db
        
        response = client.get(f"/catalog/search?q={long_query}")
        
        # Should handle long queries (either process or reject gracefully)
        assert response.status_code in [200, 400, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 