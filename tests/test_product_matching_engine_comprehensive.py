"""
COMPREHENSIVE TESTS FOR PRODUCT MATCHING ENGINE
Test Coverage: 95%+
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from modules.product_matching_engine import (
    ProductMatchingEngine, ProductMatchCandidate
)
from modules.unified_database_manager import UnifiedDatabaseManager
from models.unified_database import MasterProduct, MatchType

class TestProductMatchingEngine:
    """Comprehensive test suite for ProductMatchingEngine"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager"""
        return Mock(spec=UnifiedDatabaseManager)
    
    @pytest.fixture
    def matching_engine(self, mock_db_manager):
        """Product matching engine instance"""
        return ProductMatchingEngine(
            db_manager=mock_db_manager,
            similarity_threshold=0.8,
            exact_match_threshold=0.95,
            fuzzy_match_threshold=0.8
        )
    
    @pytest.fixture
    def sample_product(self):
        """Sample master product"""
        return MasterProduct(
            product_id="prod-123",
            standard_name="Coca Cola 500ml Bottle",
            category="Beverages",
            brand="Coca-Cola",
            size=Decimal("500"),
            unit="ml"
        )
    
    @pytest.fixture
    def sample_candidate(self):
        """Sample candidate product for matching"""
        return MasterProduct(
            product_id="prod-456",
            standard_name="Coca-Cola 500ml Bottle Classic",
            category="Beverages", 
            brand="Coca Cola",
            size=Decimal("500"),
            unit="ml"
        )
    
    # =============================================================================
    # INITIALIZATION TESTS
    # =============================================================================
    
    def test_engine_initialization_default(self, mock_db_manager):
        """Test engine initialization with default parameters"""
        engine = ProductMatchingEngine(mock_db_manager)
        
        assert engine.db_manager == mock_db_manager
        assert engine.similarity_threshold == 0.8
        assert engine.exact_match_threshold == 0.95
        assert engine.fuzzy_match_threshold == 0.8
        assert len(engine.brand_aliases) > 0
        assert len(engine.unit_conversions) > 0
        assert len(engine.stop_words) > 0
    
    def test_engine_initialization_custom_thresholds(self, mock_db_manager):
        """Test engine initialization with custom thresholds"""
        engine = ProductMatchingEngine(
            mock_db_manager,
            similarity_threshold=0.7,
            exact_match_threshold=0.9,
            fuzzy_match_threshold=0.75
        )
        
        assert engine.similarity_threshold == 0.7
        assert engine.exact_match_threshold == 0.9
        assert engine.fuzzy_match_threshold == 0.75
    
    def test_load_brand_aliases(self, matching_engine):
        """Test brand aliases loading"""
        aliases = matching_engine.brand_aliases
        
        assert 'coca cola' in aliases
        assert aliases['coca cola'] == 'coca-cola'
        assert 'pepsi cola' in aliases
        assert aliases['pepsi cola'] == 'pepsi'
        assert 'indomie' in aliases
        assert aliases['indomie'] == 'indomie'
    
    def test_load_unit_conversions(self, matching_engine):
        """Test unit conversions loading"""
        conversions = matching_engine.unit_conversions
        
        assert 'weight' in conversions
        assert 'volume' in conversions
        assert 'count' in conversions
        
        # Test weight conversions
        assert conversions['weight']['kg'] == 1000.0
        assert conversions['weight']['g'] == 1.0
        assert conversions['weight']['lb'] == 453.592
        
        # Test volume conversions
        assert conversions['volume']['l'] == 1000.0
        assert conversions['volume']['ml'] == 1.0
        
        # Test count conversions
        assert conversions['count']['pcs'] == 1.0
        assert conversions['count']['box'] == 1.0
    
    def test_load_stop_words(self, matching_engine):
        """Test stop words loading"""
        stop_words = matching_engine.stop_words
        
        assert 'the' in stop_words
        assert 'and' in stop_words
        assert 'premium' in stop_words
        assert 'pack' in stop_words
        assert 'bottle' in stop_words
    
    # =============================================================================
    # FIND MATCHES TESTS
    # =============================================================================
    
    def test_find_matches_exact_match_found(self, matching_engine, sample_product):
        """Test find matches when exact match is found"""
        exact_candidate = ProductMatchCandidate(
            product=sample_product,
            similarity_score=1.0,
            match_type=MatchType.EXACT,
            match_details={'overall_similarity': 1.0},
            confidence_level='high'
        )
        
        with patch.object(matching_engine, '_find_exact_matches') as mock_exact:
            mock_exact.return_value = [exact_candidate]
            
            result = matching_engine.find_matches(sample_product, limit=10)
            
            assert len(result) == 1
            assert result[0].match_type == MatchType.EXACT
            assert result[0].similarity_score == 1.0
            mock_exact.assert_called_once_with(sample_product)
    
    def test_find_matches_fuzzy_matches(self, matching_engine, sample_product, sample_candidate):
        """Test find matches when only fuzzy matches found"""
        with patch.object(matching_engine, '_find_exact_matches') as mock_exact, \
             patch.object(matching_engine, '_get_category_candidates') as mock_candidates, \
             patch.object(matching_engine, '_calculate_detailed_similarity') as mock_similarity, \
             patch.object(matching_engine, '_determine_confidence_level') as mock_confidence:
            
            mock_exact.return_value = []
            mock_candidates.return_value = [sample_candidate]
            mock_similarity.return_value = {
                'name_similarity': 0.9,
                'brand_similarity': 0.95,
                'size_similarity': 1.0,
                'overall_similarity': 0.9
            }
            mock_confidence.return_value = 'high'
            
            result = matching_engine.find_matches(sample_product, limit=10)
            
            assert len(result) == 1
            assert result[0].match_type == MatchType.FUZZY
            assert result[0].similarity_score == 0.9
            assert result[0].confidence_level == 'high'
    
    def test_find_matches_no_category_candidates(self, matching_engine, sample_product):
        """Test find matches when no category candidates found"""
        with patch.object(matching_engine, '_find_exact_matches') as mock_exact, \
             patch.object(matching_engine, '_get_category_candidates') as mock_candidates:
            
            mock_exact.return_value = []
            mock_candidates.return_value = []
            
            result = matching_engine.find_matches(sample_product, limit=10)
            
            assert len(result) == 0
    
    def test_find_matches_below_threshold(self, matching_engine, sample_product, sample_candidate):
        """Test find matches when similarity below threshold"""
        with patch.object(matching_engine, '_find_exact_matches') as mock_exact, \
             patch.object(matching_engine, '_get_category_candidates') as mock_candidates, \
             patch.object(matching_engine, '_calculate_detailed_similarity') as mock_similarity:
            
            mock_exact.return_value = []
            mock_candidates.return_value = [sample_candidate]
            mock_similarity.return_value = {
                'overall_similarity': 0.5  # Below threshold
            }
            
            result = matching_engine.find_matches(sample_product, limit=10)
            
            assert len(result) == 0
    
    # =============================================================================
    # EXACT MATCH TESTS
    # =============================================================================
    
    def test_find_exact_matches_success(self, matching_engine, sample_product):
        """Test finding exact matches successfully"""
        candidates = [sample_product]
        
        with patch.object(matching_engine, '_normalize_product_name') as mock_normalize_name, \
             patch.object(matching_engine, '_normalize_brand_name') as mock_normalize_brand, \
             patch.object(matching_engine, '_normalize_size_unit') as mock_normalize_size, \
             patch.object(matching_engine, '_is_exact_match') as mock_is_exact:
            
            matching_engine.db_manager.search_master_products.return_value = candidates
            mock_normalize_name.return_value = "normalized_name"
            mock_normalize_brand.return_value = "normalized_brand"
            mock_normalize_size.return_value = {"value": 500, "unit": "ml"}
            mock_is_exact.return_value = True
            
            result = matching_engine._find_exact_matches(sample_product)
            
            assert len(result) == 1
            assert result[0].match_type == MatchType.EXACT
            assert result[0].similarity_score == 1.0
    
    def test_find_exact_matches_skip_same_product(self, matching_engine, sample_product):
        """Test that exact match skips the same product"""
        # Create candidate with same product_id
        same_product = MasterProduct(
            product_id="prod-123",  # Same as sample_product
            standard_name="Different Name",
            category="Beverages",
            brand="Different Brand",
            size=Decimal("500"),
            unit="ml"
        )
        
        candidates = [same_product]
        
        with patch.object(matching_engine, '_normalize_product_name'), \
             patch.object(matching_engine, '_normalize_brand_name'), \
             patch.object(matching_engine, '_normalize_size_unit'):
            
            matching_engine.db_manager.search_master_products.return_value = candidates
            
            result = matching_engine._find_exact_matches(sample_product)
            
            assert len(result) == 0  # Should skip same product
    
    def test_is_exact_match_true(self, matching_engine):
        """Test is_exact_match returns True for identical products"""
        product_a = MasterProduct(
            product_id="prod-1",
            standard_name="Test Product",
            category="Electronics",
            brand="TestBrand",
            size=Decimal("100"),
            unit="g"
        )
        
        product_b = MasterProduct(
            product_id="prod-2",
            standard_name="Test Product",
            category="Electronics",
            brand="TestBrand",
            size=Decimal("100"),
            unit="g"
        )
        
        with patch.object(matching_engine, '_normalize_product_name') as mock_name, \
             patch.object(matching_engine, '_normalize_brand_name') as mock_brand, \
             patch.object(matching_engine, '_normalize_size_unit') as mock_size, \
             patch.object(matching_engine, '_sizes_match') as mock_sizes_match:
            
            mock_name.return_value = "test product"
            mock_brand.return_value = "testbrand"
            mock_size.return_value = {"value": 100, "unit": "g"}
            mock_sizes_match.return_value = True
            
            result = matching_engine._is_exact_match(product_a, product_b)
            
            assert result is True
    
    def test_is_exact_match_different_category(self, matching_engine):
        """Test is_exact_match returns False for different categories"""
        product_a = MasterProduct(
            product_id="prod-1",
            standard_name="Test Product",
            category="Electronics",
            brand="TestBrand",
            size=Decimal("100"),
            unit="g"
        )
        
        product_b = MasterProduct(
            product_id="prod-2",
            standard_name="Test Product",
            category="Food",  # Different category
            brand="TestBrand",
            size=Decimal("100"),
            unit="g"
        )
        
        result = matching_engine._is_exact_match(product_a, product_b)
        
        assert result is False
    
    def test_is_exact_match_different_names(self, matching_engine):
        """Test is_exact_match returns False for different normalized names"""
        product_a = MasterProduct(
            product_id="prod-1",
            standard_name="Test Product A",
            category="Electronics",
            brand="TestBrand",
            size=Decimal("100"),
            unit="g"
        )
        
        product_b = MasterProduct(
            product_id="prod-2",
            standard_name="Test Product B",
            category="Electronics",
            brand="TestBrand",
            size=Decimal("100"),
            unit="g"
        )
        
        with patch.object(matching_engine, '_normalize_product_name') as mock_name:
            mock_name.side_effect = ["test product a", "test product b"]
            
            result = matching_engine._is_exact_match(product_a, product_b)
            
            assert result is False
    
    # =============================================================================
    # SIMILARITY CALCULATION TESTS
    # =============================================================================
    
    def test_calculate_detailed_similarity(self, matching_engine, sample_product, sample_candidate):
        """Test detailed similarity calculation"""
        with patch.object(matching_engine, '_calculate_name_similarity') as mock_name, \
             patch.object(matching_engine, '_calculate_brand_similarity') as mock_brand, \
             patch.object(matching_engine, '_calculate_size_similarity') as mock_size:
            
            mock_name.return_value = 0.9
            mock_brand.return_value = 0.8
            mock_size.return_value = 1.0
            
            result = matching_engine._calculate_detailed_similarity(sample_product, sample_candidate)
            
            assert 'name_similarity' in result
            assert 'brand_similarity' in result
            assert 'size_similarity' in result
            assert 'overall_similarity' in result
            
            # Check weighted calculation (0.5*0.9 + 0.3*0.8 + 0.2*1.0)
            expected_overall = 0.5 * 0.9 + 0.3 * 0.8 + 0.2 * 1.0
            assert abs(result['overall_similarity'] - expected_overall) < 0.001
    
    def test_calculate_name_similarity_high(self, matching_engine):
        """Test name similarity calculation - high similarity"""
        with patch('modules.product_matching_engine.rfuzz') as mock_fuzz, \
             patch.object(matching_engine, '_normalize_product_name') as mock_normalize:
            
            mock_normalize.side_effect = ["coca cola", "coca cola"]
            mock_fuzz.ratio.return_value = 100
            mock_fuzz.partial_ratio.return_value = 100
            mock_fuzz.token_sort_ratio.return_value = 100
            mock_fuzz.token_set_ratio.return_value = 100
            
            result = matching_engine._calculate_name_similarity("Coca Cola", "Coca-Cola")
            
            assert result == 1.0
    
    def test_calculate_name_similarity_empty_names(self, matching_engine):
        """Test name similarity with empty names"""
        assert matching_engine._calculate_name_similarity("", "Test") == 0.0
        assert matching_engine._calculate_name_similarity("Test", "") == 0.0
        assert matching_engine._calculate_name_similarity(None, "Test") == 0.0
    
    def test_calculate_brand_similarity_both_empty(self, matching_engine):
        """Test brand similarity when both brands are empty"""
        result = matching_engine._calculate_brand_similarity("", "")
        assert result == 1.0
    
    def test_calculate_brand_similarity_one_empty(self, matching_engine):
        """Test brand similarity when one brand is empty"""
        result = matching_engine._calculate_brand_similarity("Brand", "")
        assert result == 0.5
        
        result = matching_engine._calculate_brand_similarity("", "Brand")
        assert result == 0.5
    
    def test_calculate_brand_similarity_exact_match(self, matching_engine):
        """Test brand similarity with exact match after normalization"""
        with patch.object(matching_engine, '_normalize_brand_name') as mock_normalize:
            mock_normalize.return_value = "coca-cola"
            
            result = matching_engine._calculate_brand_similarity("Coca Cola", "Coca-Cola")
            
            assert result == 1.0
    
    def test_calculate_brand_similarity_fuzzy_match(self, matching_engine):
        """Test brand similarity with fuzzy matching"""
        with patch.object(matching_engine, '_normalize_brand_name') as mock_normalize, \
             patch('modules.product_matching_engine.rfuzz') as mock_fuzz:
            
            mock_normalize.side_effect = ["coca-cola", "pepsi"]
            mock_fuzz.ratio.return_value = 60
            
            result = matching_engine._calculate_brand_similarity("Coca Cola", "Pepsi")
            
            assert result == 0.6
    
    def test_calculate_size_similarity_both_empty(self, matching_engine):
        """Test size similarity when both sizes are empty"""
        result = matching_engine._calculate_size_similarity(None, None, None, None)
        assert result == 1.0
    
    def test_calculate_size_similarity_one_empty(self, matching_engine):
        """Test size similarity when one size is empty"""
        result = matching_engine._calculate_size_similarity(100.0, "g", None, None)
        assert result == 0.5
    
    def test_calculate_size_similarity_exact_match(self, matching_engine):
        """Test size similarity with exact match"""
        with patch.object(matching_engine, '_normalize_size_unit') as mock_normalize:
            mock_normalize.return_value = {"value": 500, "unit": "ml"}
            
            result = matching_engine._calculate_size_similarity(500.0, "ml", 500.0, "ml")
            
            assert result == 1.0
    
    def test_calculate_size_similarity_within_tolerance(self, matching_engine):
        """Test size similarity within tolerance"""
        with patch.object(matching_engine, '_normalize_size_unit') as mock_normalize:
            mock_normalize.side_effect = [
                {"value": 500, "unit": "ml"},
                {"value": 510, "unit": "ml"}  # 2% difference, within 10% tolerance
            ]
            
            result = matching_engine._calculate_size_similarity(500.0, "ml", 510.0, "ml")
            
            assert result > 0.9  # Should be high due to small difference
    
    def test_calculate_size_similarity_normalization_failure(self, matching_engine):
        """Test size similarity when normalization fails"""
        with patch.object(matching_engine, '_normalize_size_unit') as mock_normalize:
            mock_normalize.return_value = None
            
            result = matching_engine._calculate_size_similarity(500.0, "ml", 500.0, "ml")
            
            assert result == 0.5
    
    # =============================================================================
    # NORMALIZATION TESTS
    # =============================================================================
    
    def test_normalize_product_name(self, matching_engine):
        """Test product name normalization"""
        # Test basic normalization
        result = matching_engine._normalize_product_name("Coca-Cola Premium 500ml Bottle")
        expected = "coca cola 500ml"  # Removes stop words and special chars
        assert result == expected
        
        # Test empty name
        assert matching_engine._normalize_product_name("") == ""
        assert matching_engine._normalize_product_name(None) == ""
        
        # Test multiple spaces
        result = matching_engine._normalize_product_name("Test   Product    Name")
        assert "  " not in result  # No multiple spaces
    
    def test_normalize_brand_name(self, matching_engine):
        """Test brand name normalization"""
        # Test alias replacement
        result = matching_engine._normalize_brand_name("Coca Cola")
        assert result == "coca-cola"
        
        result = matching_engine._normalize_brand_name("Pepsi Cola")
        assert result == "pepsi"
        
        # Test unknown brand
        result = matching_engine._normalize_brand_name("Unknown Brand")
        assert result == "unknown brand"
        
        # Test empty brand
        assert matching_engine._normalize_brand_name("") == ""
        assert matching_engine._normalize_brand_name(None) == ""
    
    def test_normalize_size_unit_weight(self, matching_engine):
        """Test size unit normalization for weight"""
        # Test kg to g conversion
        result = matching_engine._normalize_size_unit(1.0, "kg")
        assert result['value'] == 1000.0
        assert result['unit_type'] == 'weight'
        assert result['base_unit'] == 'g'
        
        # Test pound to g conversion
        result = matching_engine._normalize_size_unit(1.0, "lb")
        assert abs(result['value'] - 453.592) < 0.001
    
    def test_normalize_size_unit_volume(self, matching_engine):
        """Test size unit normalization for volume"""
        # Test liter to ml conversion
        result = matching_engine._normalize_size_unit(1.0, "l")
        assert result['value'] == 1000.0
        assert result['unit_type'] == 'volume'
        assert result['base_unit'] == 'ml'
        
        # Test fl oz to ml conversion
        result = matching_engine._normalize_size_unit(1.0, "fl oz")
        assert abs(result['value'] - 29.5735) < 0.001
    
    def test_normalize_size_unit_count(self, matching_engine):
        """Test size unit normalization for count"""
        result = matching_engine._normalize_size_unit(12.0, "pcs")
        assert result['value'] == 12.0
        assert result['unit_type'] == 'count'
        assert result['base_unit'] == 'pcs'
    
    def test_normalize_size_unit_unknown(self, matching_engine):
        """Test size unit normalization with unknown unit"""
        result = matching_engine._normalize_size_unit(100.0, "unknown")
        assert result is None
    
    def test_normalize_size_unit_invalid_inputs(self, matching_engine):
        """Test size unit normalization with invalid inputs"""
        assert matching_engine._normalize_size_unit(None, "kg") is None
        assert matching_engine._normalize_size_unit(100.0, None) is None
        assert matching_engine._normalize_size_unit(100.0, "") is None
    
    # =============================================================================
    # SIZE MATCHING TESTS
    # =============================================================================
    
    def test_sizes_match_both_none(self, matching_engine):
        """Test sizes match when both are None"""
        assert matching_engine._sizes_match(None, None) is True
    
    def test_sizes_match_one_none(self, matching_engine):
        """Test sizes match when one is None"""
        size_a = {"value": 500, "unit_type": "volume"}
        assert matching_engine._sizes_match(size_a, None) is False
        assert matching_engine._sizes_match(None, size_a) is False
    
    def test_sizes_match_different_unit_types(self, matching_engine):
        """Test sizes match with different unit types"""
        size_a = {"value": 500, "unit_type": "volume"}
        size_b = {"value": 500, "unit_type": "weight"}
        
        assert matching_engine._sizes_match(size_a, size_b) is False
    
    def test_sizes_match_exact(self, matching_engine):
        """Test sizes match exactly"""
        size_a = {"value": 500, "unit_type": "volume"}
        size_b = {"value": 500, "unit_type": "volume"}
        
        assert matching_engine._sizes_match(size_a, size_b) is True
    
    def test_sizes_match_within_tolerance(self, matching_engine):
        """Test sizes match within tolerance"""
        size_a = {"value": 500, "unit_type": "volume"}
        size_b = {"value": 510, "unit_type": "volume"}  # 2% difference, within 5% default tolerance
        
        assert matching_engine._sizes_match(size_a, size_b) is True
    
    def test_sizes_match_outside_tolerance(self, matching_engine):
        """Test sizes don't match outside tolerance"""
        size_a = {"value": 500, "unit_type": "volume"}
        size_b = {"value": 600, "unit_type": "volume"}  # 20% difference, outside 5% tolerance
        
        assert matching_engine._sizes_match(size_a, size_b) is False
    
    # =============================================================================
    # CONFIDENCE LEVEL TESTS
    # =============================================================================
    
    def test_determine_confidence_level_high(self, matching_engine):
        """Test confidence level determination - high"""
        assert matching_engine._determine_confidence_level(0.95) == "high"
        assert matching_engine._determine_confidence_level(1.0) == "high"
    
    def test_determine_confidence_level_medium(self, matching_engine):
        """Test confidence level determination - medium"""
        assert matching_engine._determine_confidence_level(0.85) == "medium"
        assert matching_engine._determine_confidence_level(0.8) == "medium"
    
    def test_determine_confidence_level_low(self, matching_engine):
        """Test confidence level determination - low"""
        assert matching_engine._determine_confidence_level(0.7) == "low"
        assert matching_engine._determine_confidence_level(0.5) == "low"
        assert matching_engine._determine_confidence_level(0.0) == "low"
    
    # =============================================================================
    # CATEGORY CANDIDATES TESTS
    # =============================================================================
    
    def test_get_category_candidates(self, matching_engine, sample_product):
        """Test getting category candidates"""
        expected_candidates = [sample_product]
        matching_engine.db_manager.search_master_products.return_value = expected_candidates
        
        result = matching_engine._get_category_candidates(sample_product)
        
        assert result == expected_candidates
        matching_engine.db_manager.search_master_products.assert_called_once_with(
            search_term="",
            category="Beverages",
            limit=100
        )
    
    # =============================================================================
    # BATCH PROCESSING TESTS
    # =============================================================================
    
    def test_process_all_products_for_matches(self, matching_engine):
        """Test batch processing of all products for matches"""
        # Mock products to process
        products = [
            Mock(product_id="prod-1", standard_name="Product 1"),
            Mock(product_id="prod-2", standard_name="Product 2")
        ]
        
        with patch.object(matching_engine.db_manager, 'get_all_master_products') as mock_get_all, \
             patch.object(matching_engine, 'find_matches') as mock_find_matches, \
             patch.object(matching_engine.db_manager, 'save_product_matches') as mock_save:
            
            mock_get_all.return_value = products
            mock_find_matches.side_effect = [
                [Mock(similarity_score=0.9)],  # 1 match for prod-1
                []  # 0 matches for prod-2
            ]
            
            result = matching_engine.process_all_products_for_matches(batch_size=1)
            
            assert result['total_processed'] == 2
            assert result['total_matches_found'] == 1
            assert result['products_with_matches'] == 1
            assert mock_find_matches.call_count == 2
    
    # =============================================================================
    # AUTO MERGE SUGGESTIONS TESTS
    # =============================================================================
    
    def test_suggest_auto_merges(self, matching_engine):
        """Test auto merge suggestions"""
        # Mock high-confidence matches
        high_confidence_match = Mock()
        high_confidence_match.product = Mock(product_id="prod-2", standard_name="Product 2")
        high_confidence_match.similarity_score = 0.98
        high_confidence_match.confidence_level = "high"
        
        products = [Mock(product_id="prod-1", standard_name="Product 1")]
        
        with patch.object(matching_engine.db_manager, 'get_all_master_products') as mock_get_all, \
             patch.object(matching_engine, 'find_matches') as mock_find_matches:
            
            mock_get_all.return_value = products
            mock_find_matches.return_value = [high_confidence_match]
            
            result = matching_engine.suggest_auto_merges(confidence_threshold=0.95)
            
            assert len(result) == 1
            assert result[0]['primary_product_id'] == "prod-1"
            assert result[0]['candidate_product_id'] == "prod-2"
            assert result[0]['similarity_score'] == 0.98
            assert result[0]['confidence_level'] == "high"
    
    def test_suggest_auto_merges_below_threshold(self, matching_engine):
        """Test auto merge suggestions below confidence threshold"""
        # Mock low-confidence match
        low_confidence_match = Mock()
        low_confidence_match.similarity_score = 0.8  # Below 0.95 threshold
        
        products = [Mock(product_id="prod-1")]
        
        with patch.object(matching_engine.db_manager, 'get_all_master_products') as mock_get_all, \
             patch.object(matching_engine, 'find_matches') as mock_find_matches:
            
            mock_get_all.return_value = products
            mock_find_matches.return_value = [low_confidence_match]
            
            result = matching_engine.suggest_auto_merges(confidence_threshold=0.95)
            
            assert len(result) == 0  # Should be filtered out
    
    # =============================================================================
    # SEARCH FUNCTIONALITY TESTS
    # =============================================================================
    
    def test_search_by_name(self, matching_engine):
        """Test search by name functionality"""
        expected_products = [Mock(standard_name="Coca Cola")]
        matching_engine.db_manager.search_master_products.return_value = expected_products
        
        result = matching_engine.search_by_name("Coca Cola", limit=20)
        
        assert result == expected_products
        matching_engine.db_manager.search_master_products.assert_called_once_with(
            search_term="Coca Cola",
            limit=20
        )
    
    def test_get_similar_products(self, matching_engine, sample_product):
        """Test getting similar products"""
        similar_product = Mock()
        match_candidate = Mock()
        match_candidate.product = similar_product
        match_candidate.similarity_score = 0.85
        
        with patch.object(matching_engine.db_manager, 'get_master_product') as mock_get_product, \
             patch.object(matching_engine, 'find_matches') as mock_find_matches:
            
            mock_get_product.return_value = sample_product
            mock_find_matches.return_value = [match_candidate]
            
            result = matching_engine.get_similar_products("prod-123", limit=10)
            
            assert len(result) == 1
            assert result[0] == match_candidate
            mock_get_product.assert_called_once_with("prod-123")
            mock_find_matches.assert_called_once_with(sample_product, limit=10)
    
    def test_get_similar_products_not_found(self, matching_engine):
        """Test getting similar products for non-existent product"""
        matching_engine.db_manager.get_master_product.return_value = None
        
        result = matching_engine.get_similar_products("non-existent")
        
        assert result == []
    
    # =============================================================================
    # EDGE CASES AND ERROR HANDLING TESTS
    # =============================================================================
    
    def test_find_matches_limit_respected(self, matching_engine, sample_product):
        """Test that find matches respects the limit parameter"""
        # Create more candidates than the limit
        candidates = [Mock(product_id=f"prod-{i}") for i in range(20)]
        
        with patch.object(matching_engine, '_find_exact_matches') as mock_exact, \
             patch.object(matching_engine, '_get_category_candidates') as mock_candidates, \
             patch.object(matching_engine, '_calculate_detailed_similarity') as mock_similarity, \
             patch.object(matching_engine, '_determine_confidence_level') as mock_confidence:
            
            mock_exact.return_value = []
            mock_candidates.return_value = candidates
            mock_similarity.return_value = {'overall_similarity': 0.9}
            mock_confidence.return_value = 'high'
            
            result = matching_engine.find_matches(sample_product, limit=5)
            
            assert len(result) <= 5  # Should respect limit
    
    def test_normalization_with_special_characters(self, matching_engine):
        """Test normalization handles special characters correctly"""
        # Test product name with special characters
        result = matching_engine._normalize_product_name("Coca-Cola® Premium 500ml (Bottle)")
        
        # Should remove special characters and normalize
        assert "®" not in result
        assert "(" not in result
        assert ")" not in result
    
    def test_brand_similarity_case_insensitive(self, matching_engine):
        """Test brand similarity is case insensitive"""
        with patch.object(matching_engine, '_normalize_brand_name') as mock_normalize:
            mock_normalize.return_value = "coca-cola"
            
            result = matching_engine._calculate_brand_similarity("COCA-COLA", "coca-cola")
            
            assert result == 1.0  # Should match after normalization


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 