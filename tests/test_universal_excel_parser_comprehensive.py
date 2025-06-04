"""
COMPREHENSIVE TESTS FOR UNIVERSAL EXCEL PARSER
Test Coverage: 95%+
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
import io
from typing import Dict, Any, List

from modules.universal_excel_parser import UniversalExcelParser

class TestUniversalExcelParser:
    """Comprehensive test suite for UniversalExcelParser"""
    
    @pytest.fixture
    def parser(self):
        """Universal Excel parser instance"""
        return UniversalExcelParser()
    
    @pytest.fixture
    def sample_excel_data(self):
        """Sample Excel data as DataFrame"""
        return pd.DataFrame({
            'Product Name': ['Coca Cola 500ml', 'Pepsi 500ml', 'Water 1L'],
            'Price': [15000, 14000, 5000],
            'Unit': ['bottle', 'bottle', 'bottle'],
            'Brand': ['Coca-Cola', 'Pepsi', 'Aqua']
        })
    
    @pytest.fixture
    def mixed_format_data(self):
        """Mixed format Excel data"""
        return pd.DataFrame({
            'Col1': ['Product', 'Coca Cola 500ml', 'Pepsi 500ml', None],
            'Col2': ['Price (IDR)', '15,000', '14000', None],
            'Col3': ['Brand', 'Coca-Cola', 'Pepsi', None],
            'Col4': [None, 'bottle', 'bottle', None]
        })
    
    @pytest.fixture
    def supplier_contact_data(self):
        """Data with supplier contact information"""
        return pd.DataFrame({
            'A': ['PT. Fresh Market', 'Manager: John Doe', 'Phone: 0812345678', 'Product', 'Coca Cola'],
            'B': ['Bali Supplier Co.', 'Email: info@bali.com', 'Address: Denpasar', 'Price', '15000'],
            'C': [None, None, None, 'Unit', 'bottle']
        })
    
    # =============================================================================
    # INITIALIZATION TESTS
    # =============================================================================
    
    def test_parser_initialization(self, parser):
        """Test parser initialization"""
        assert parser.analysis_strategy == 'adaptive'
        assert parser.confidence_threshold == 0.7
        assert parser.max_header_scan_rows == 10
        assert len(parser.product_keywords) > 0
        assert len(parser.price_keywords) > 0
        assert len(parser.unit_keywords) > 0
    
    def test_parser_initialization_custom_params(self):
        """Test parser initialization with custom parameters"""
        parser = UniversalExcelParser(
            analysis_strategy='heuristic',
            confidence_threshold=0.8,
            max_header_scan_rows=15
        )
        
        assert parser.analysis_strategy == 'heuristic'
        assert parser.confidence_threshold == 0.8
        assert parser.max_header_scan_rows == 15
    
    # =============================================================================
    # FILE PROCESSING TESTS
    # =============================================================================
    
    @patch('pandas.read_excel')
    def test_process_file_success(self, mock_read_excel, parser, sample_excel_data):
        """Test successful file processing"""
        mock_read_excel.return_value = {'Sheet1': sample_excel_data}
        
        with patch.object(parser, '_analyze_sheet_structure') as mock_analyze, \
             patch.object(parser, '_extract_products_and_prices') as mock_extract, \
             patch.object(parser, '_extract_supplier_info') as mock_supplier:
            
            mock_analyze.return_value = {
                'structure_type': 'tabular',
                'headers': {'product': 0, 'price': 1},
                'data_start_row': 1,
                'confidence': 0.9
            }
            
            mock_extract.return_value = [
                {'name': 'Coca Cola 500ml', 'price': 15000, 'unit': 'bottle'}
            ]
            
            mock_supplier.return_value = {
                'name': 'Test Supplier',
                'contact': '123456789'
            }
            
            result = parser.process_file('test.xlsx')
            
            assert result['success'] is True
            assert len(result['sheets']) == 1
            assert result['sheets'][0]['products']
            assert 'supplier_info' in result['sheets'][0]
    
    @patch('pandas.read_excel')
    def test_process_file_read_error(self, mock_read_excel, parser):
        """Test file processing with read error"""
        mock_read_excel.side_effect = Exception("File not found")
        
        result = parser.process_file('nonexistent.xlsx')
        
        assert result['success'] is False
        assert 'error' in result
        assert 'File not found' in result['error']
    
    @patch('pandas.read_excel')
    def test_process_file_empty_sheets(self, mock_read_excel, parser):
        """Test file processing with empty sheets"""
        mock_read_excel.return_value = {}
        
        result = parser.process_file('empty.xlsx')
        
        assert result['success'] is False
        assert 'No sheets found' in result['error']
    
    @patch('pandas.read_excel')
    def test_process_file_multiple_sheets(self, mock_read_excel, parser, sample_excel_data):
        """Test file processing with multiple sheets"""
        mock_read_excel.return_value = {
            'Sheet1': sample_excel_data,
            'Sheet2': sample_excel_data.copy()
        }
        
        with patch.object(parser, '_analyze_sheet_structure') as mock_analyze, \
             patch.object(parser, '_extract_products_and_prices') as mock_extract, \
             patch.object(parser, '_extract_supplier_info') as mock_supplier:
            
            mock_analyze.return_value = {
                'structure_type': 'tabular',
                'headers': {'product': 0, 'price': 1},
                'data_start_row': 1,
                'confidence': 0.9
            }
            
            mock_extract.return_value = [
                {'name': 'Coca Cola 500ml', 'price': 15000}
            ]
            
            mock_supplier.return_value = {}
            
            result = parser.process_file('multi_sheet.xlsx')
            
            assert result['success'] is True
            assert len(result['sheets']) == 2
    
    # =============================================================================
    # SHEET STRUCTURE ANALYSIS TESTS
    # =============================================================================
    
    def test_analyze_sheet_structure_tabular(self, parser, sample_excel_data):
        """Test sheet structure analysis for tabular format"""
        result = parser._analyze_sheet_structure(sample_excel_data)
        
        assert result['structure_type'] == 'tabular'
        assert 'product' in result['headers']
        assert 'price' in result['headers']
        assert result['data_start_row'] >= 0
        assert result['confidence'] > 0
    
    def test_analyze_sheet_structure_mixed(self, parser, mixed_format_data):
        """Test sheet structure analysis for mixed format"""
        result = parser._analyze_sheet_structure(mixed_format_data)
        
        assert result['structure_type'] in ['mixed', 'sparse']
        assert isinstance(result['headers'], dict)
        assert result['confidence'] >= 0
    
    def test_analyze_sheet_structure_empty(self, parser):
        """Test sheet structure analysis with empty data"""
        empty_data = pd.DataFrame()
        
        result = parser._analyze_sheet_structure(empty_data)
        
        assert result['structure_type'] == 'unknown'
        assert result['confidence'] == 0
    
    def test_detect_headers_keyword_match(self, parser, sample_excel_data):
        """Test header detection with keyword matching"""
        headers = parser._detect_headers(sample_excel_data)
        
        assert 'product' in headers
        assert 'price' in headers
        assert headers['product'] == 0  # Column index
        assert headers['price'] == 1
    
    def test_detect_headers_fuzzy_match(self, parser):
        """Test header detection with fuzzy matching"""
        data = pd.DataFrame({
            'Nama Produk': ['Item 1'],  # Should match 'product' 
            'Harga (Rp)': [10000],     # Should match 'price'
            'Satuan': ['pcs']          # Should match 'unit'
        })
        
        headers = parser._detect_headers(data)
        
        assert 'product' in headers
        assert 'price' in headers
        assert 'unit' in headers
    
    def test_detect_headers_no_match(self, parser):
        """Test header detection with no matches"""
        data = pd.DataFrame({
            'Random Column 1': ['Value'],
            'Random Column 2': ['Value']
        })
        
        headers = parser._detect_headers(data)
        
        # Should return empty dict when no headers match
        assert len(headers) == 0
    
    # =============================================================================
    # DATA EXTRACTION TESTS
    # =============================================================================
    
    def test_extract_products_and_prices_tabular(self, parser, sample_excel_data):
        """Test extraction from tabular format"""
        structure = {
            'structure_type': 'tabular',
            'headers': {'product': 0, 'price': 1, 'unit': 2, 'brand': 3},
            'data_start_row': 1
        }
        
        result = parser._extract_products_and_prices(sample_excel_data, structure)
        
        assert len(result) == 3
        assert result[0]['name'] == 'Coca Cola 500ml'
        assert result[0]['price'] == 15000
        assert result[0]['unit'] == 'bottle'
        assert result[0]['brand'] == 'Coca-Cola'
    
    def test_extract_products_and_prices_mixed(self, parser):
        """Test extraction from mixed format"""
        data = pd.DataFrame({
            'A': ['Product:', 'Coca Cola', 'Price:', '15000'],
            'B': ['Brand:', 'Coca-Cola', 'Unit:', 'bottle']
        })
        
        structure = {
            'structure_type': 'mixed',
            'headers': {},
            'data_start_row': 0
        }
        
        with patch.object(parser, '_extract_from_mixed_format') as mock_extract:
            mock_extract.return_value = [
                {'name': 'Coca Cola', 'price': 15000, 'brand': 'Coca-Cola', 'unit': 'bottle'}
            ]
            
            result = parser._extract_products_and_prices(data, structure)
            
            assert len(result) == 1
            assert result[0]['name'] == 'Coca Cola'
    
    def test_extract_from_mixed_format_product_price_pairs(self, parser):
        """Test extraction from mixed format with product-price pairs"""
        data = pd.DataFrame({
            'A': ['Coca Cola 500ml', 'Pepsi 500ml', 'Water 1L'],
            'B': [15000, 14000, 5000],
            'C': ['bottle', 'bottle', 'bottle']
        })
        
        result = parser._extract_from_mixed_format(data)
        
        assert len(result) >= 1
        # Should find products and prices
        product_names = [item['name'] for item in result if 'name' in item]
        assert any('Coca Cola' in name for name in product_names)
    
    def test_extract_from_mixed_format_sparse_data(self, parser):
        """Test extraction from sparse mixed format"""
        data = pd.DataFrame({
            'A': ['Product', 'Coca Cola', None, 'Price', '15000'],
            'B': ['Brand', 'Coca-Cola', None, 'Unit', 'bottle']
        })
        
        result = parser._extract_from_mixed_format(data)
        
        # Should extract meaningful data even from sparse format
        assert len(result) > 0
    
    # =============================================================================
    # PRICE DETECTION TESTS
    # =============================================================================
    
    def test_is_price_value_numeric(self, parser):
        """Test price detection with numeric values"""
        assert parser._is_price_value(15000) is True
        assert parser._is_price_value(15000.5) is True
        assert parser._is_price_value(0) is False  # Zero price invalid
        assert parser._is_price_value(-100) is False  # Negative price invalid
    
    def test_is_price_value_string_formats(self, parser):
        """Test price detection with various string formats"""
        assert parser._is_price_value('15000') is True
        assert parser._is_price_value('15,000') is True
        assert parser._is_price_value('15.000') is True
        assert parser._is_price_value('Rp 15000') is True
        assert parser._is_price_value('IDR 15,000') is True
        assert parser._is_price_value('$ 15.50') is True
    
    def test_is_price_value_invalid(self, parser):
        """Test price detection with invalid values"""
        assert parser._is_price_value('abc') is False
        assert parser._is_price_value('') is False
        assert parser._is_price_value(None) is False
        assert parser._is_price_value('Product Name') is False
    
    def test_parse_price_numeric(self, parser):
        """Test price parsing with numeric values"""
        assert parser._parse_price(15000) == 15000
        assert parser._parse_price(15000.5) == 15000.5
    
    def test_parse_price_string_formats(self, parser):
        """Test price parsing with string formats"""
        assert parser._parse_price('15000') == 15000
        assert parser._parse_price('15,000') == 15000
        assert parser._parse_price('15.000') == 15000
        assert parser._parse_price('Rp 15000') == 15000
        assert parser._parse_price('IDR 15,000') == 15000
        assert parser._parse_price('$ 15.50') == 15.50
    
    def test_parse_price_invalid(self, parser):
        """Test price parsing with invalid values"""
        assert parser._parse_price('abc') is None
        assert parser._parse_price('') is None
        assert parser._parse_price(None) is None
    
    # =============================================================================
    # PRODUCT NAME DETECTION TESTS
    # =============================================================================
    
    def test_is_product_name_valid(self, parser):
        """Test product name detection with valid names"""
        assert parser._is_product_name('Coca Cola 500ml') is True
        assert parser._is_product_name('Pepsi Zero Sugar') is True
        assert parser._is_product_name('Mineral Water 1L') is True
        assert parser._is_product_name('Indomie Ayam Bawang') is True
    
    def test_is_product_name_invalid(self, parser):
        """Test product name detection with invalid names"""
        assert parser._is_product_name('') is False
        assert parser._is_product_name(None) is False
        assert parser._is_product_name('123') is False  # Only numbers
        assert parser._is_product_name('a') is False   # Too short
        assert parser._is_product_name('Price') is False  # Keyword
    
    def test_is_product_name_edge_cases(self, parser):
        """Test product name detection edge cases"""
        assert parser._is_product_name('Product Name') is False  # Header-like
        assert parser._is_product_name('15000') is False  # Price-like
        assert parser._is_product_name('kg') is False  # Unit-like
        assert parser._is_product_name('Total') is False  # Summary keyword
    
    # =============================================================================
    # SUPPLIER INFO EXTRACTION TESTS
    # =============================================================================
    
    def test_extract_supplier_info_contact_data(self, parser, supplier_contact_data):
        """Test supplier info extraction with contact data"""
        result = parser._extract_supplier_info(supplier_contact_data)
        
        assert 'name' in result
        assert 'contact' in result or 'phone' in result
        assert 'email' in result or 'address' in result
    
    def test_extract_supplier_info_no_data(self, parser, sample_excel_data):
        """Test supplier info extraction with no supplier data"""
        result = parser._extract_supplier_info(sample_excel_data)
        
        # Should return empty dict or minimal info
        assert isinstance(result, dict)
    
    def test_detect_contact_patterns_phone(self, parser):
        """Test contact pattern detection for phone numbers"""
        assert parser._detect_contact_patterns('0812345678') == 'phone'
        assert parser._detect_contact_patterns('+62 812 345 678') == 'phone'
        assert parser._detect_contact_patterns('(021) 123-4567') == 'phone'
    
    def test_detect_contact_patterns_email(self, parser):
        """Test contact pattern detection for email"""
        assert parser._detect_contact_patterns('info@company.com') == 'email'
        assert parser._detect_contact_patterns('john.doe@gmail.com') == 'email'
    
    def test_detect_contact_patterns_address(self, parser):
        """Test contact pattern detection for addresses"""
        assert parser._detect_contact_patterns('Jl. Sunset Road No. 123') == 'address'
        assert parser._detect_contact_patterns('Denpasar, Bali') == 'address'
    
    def test_detect_contact_patterns_unknown(self, parser):
        """Test contact pattern detection for unknown patterns"""
        assert parser._detect_contact_patterns('Random text') == 'unknown'
        assert parser._detect_contact_patterns('123') == 'unknown'
    
    # =============================================================================
    # HEADER SIMILARITY TESTS
    # =============================================================================
    
    def test_calculate_header_similarity_exact_match(self, parser):
        """Test header similarity with exact matches"""
        assert parser._calculate_header_similarity('product', 'product') == 1.0
        assert parser._calculate_header_similarity('price', 'price') == 1.0
    
    def test_calculate_header_similarity_case_insensitive(self, parser):
        """Test header similarity is case insensitive"""
        assert parser._calculate_header_similarity('Product', 'product') == 1.0
        assert parser._calculate_header_similarity('PRICE', 'price') == 1.0
    
    def test_calculate_header_similarity_fuzzy_match(self, parser):
        """Test header similarity with fuzzy matching"""
        # These should have high similarity
        similarity = parser._calculate_header_similarity('Nama Produk', 'product')
        assert similarity > 0.5  # Should match reasonably well
        
        similarity = parser._calculate_header_similarity('Harga', 'price')
        assert similarity > 0.5
    
    def test_calculate_header_similarity_no_match(self, parser):
        """Test header similarity with no match"""
        similarity = parser._calculate_header_similarity('Random Column', 'product')
        assert similarity < 0.5  # Should have low similarity
    
    # =============================================================================
    # CONFIDENCE CALCULATION TESTS
    # =============================================================================
    
    def test_calculate_confidence_high(self, parser):
        """Test confidence calculation with high confidence indicators"""
        structure = {
            'headers': {'product': 0, 'price': 1, 'unit': 2, 'brand': 3},
            'data_start_row': 1
        }
        
        data = pd.DataFrame({
            'Product Name': ['Coca Cola', 'Pepsi'],
            'Price': [15000, 14000],
            'Unit': ['bottle', 'bottle'],
            'Brand': ['Coca-Cola', 'Pepsi']
        })
        
        confidence = parser._calculate_confidence(structure, data)
        
        assert confidence > 0.8  # Should have high confidence
    
    def test_calculate_confidence_low(self, parser):
        """Test confidence calculation with low confidence indicators"""
        structure = {
            'headers': {},  # No headers found
            'data_start_row': 0
        }
        
        data = pd.DataFrame({
            'Col1': ['Random', 'Data'],
            'Col2': ['More', 'Random']
        })
        
        confidence = parser._calculate_confidence(structure, data)
        
        assert confidence < 0.5  # Should have low confidence
    
    # =============================================================================
    # VALIDATION TESTS
    # =============================================================================
    
    def test_validate_extracted_data_valid(self, parser):
        """Test validation with valid extracted data"""
        data = [
            {'name': 'Coca Cola 500ml', 'price': 15000, 'unit': 'bottle'},
            {'name': 'Pepsi 500ml', 'price': 14000, 'unit': 'bottle'}
        ]
        
        result = parser._validate_extracted_data(data)
        
        assert result['is_valid'] is True
        assert result['error_count'] == 0
        assert len(result['clean_data']) == 2
    
    def test_validate_extracted_data_invalid(self, parser):
        """Test validation with invalid data"""
        data = [
            {'name': '', 'price': 15000},  # Empty name
            {'name': 'Valid Product', 'price': -100},  # Invalid price
            {'name': 'Another Product', 'price': 'invalid'}  # Non-numeric price
        ]
        
        result = parser._validate_extracted_data(data)
        
        assert result['is_valid'] is False
        assert result['error_count'] > 0
        assert len(result['clean_data']) < len(data)  # Some items filtered
    
    def test_validate_extracted_data_empty(self, parser):
        """Test validation with empty data"""
        result = parser._validate_extracted_data([])
        
        assert result['is_valid'] is False
        assert result['error_count'] == 0
        assert len(result['clean_data']) == 0
    
    # =============================================================================
    # DATA CLEANING TESTS
    # =============================================================================
    
    def test_clean_product_name(self, parser):
        """Test product name cleaning"""
        assert parser._clean_product_name('  Coca Cola 500ml  ') == 'Coca Cola 500ml'
        assert parser._clean_product_name('Coca-Cola® 500ml') == 'Coca-Cola 500ml'
        assert parser._clean_product_name('') == ''
    
    def test_clean_price_value(self, parser):
        """Test price value cleaning"""
        assert parser._clean_price_value('Rp 15,000') == 15000
        assert parser._clean_price_value('IDR 15.000') == 15000
        assert parser._clean_price_value('$ 15.50') == 15.50
        assert parser._clean_price_value('invalid') is None
    
    def test_clean_unit_value(self, parser):
        """Test unit value cleaning"""
        assert parser._clean_unit_value('  pcs  ') == 'pcs'
        assert parser._clean_unit_value('Bottle') == 'bottle'
        assert parser._clean_unit_value('KG') == 'kg'
        assert parser._clean_unit_value('') == ''
    
    # =============================================================================
    # ADAPTIVE STRATEGY TESTS
    # =============================================================================
    
    def test_adaptive_strategy_tabular_data(self, parser, sample_excel_data):
        """Test adaptive strategy with clear tabular data"""
        parser.analysis_strategy = 'adaptive'
        
        result = parser._analyze_sheet_structure(sample_excel_data)
        
        assert result['structure_type'] == 'tabular'
        assert result['confidence'] > 0.8
    
    def test_adaptive_strategy_mixed_data(self, parser, mixed_format_data):
        """Test adaptive strategy with mixed format data"""
        parser.analysis_strategy = 'adaptive'
        
        result = parser._analyze_sheet_structure(mixed_format_data)
        
        assert result['structure_type'] in ['mixed', 'sparse']
        assert result['confidence'] > 0
    
    # =============================================================================
    # HEURISTIC STRATEGY TESTS
    # =============================================================================
    
    def test_heuristic_strategy(self, parser, sample_excel_data):
        """Test heuristic analysis strategy"""
        parser.analysis_strategy = 'heuristic'
        
        with patch.object(parser, '_heuristic_analysis') as mock_heuristic:
            mock_heuristic.return_value = {
                'structure_type': 'tabular',
                'headers': {'product': 0, 'price': 1},
                'confidence': 0.9
            }
            
            result = parser._analyze_sheet_structure(sample_excel_data)
            
            assert result['structure_type'] == 'tabular'
            mock_heuristic.assert_called_once()
    
    def test_heuristic_analysis(self, parser, sample_excel_data):
        """Test heuristic analysis implementation"""
        result = parser._heuristic_analysis(sample_excel_data)
        
        assert 'structure_type' in result
        assert 'headers' in result
        assert 'confidence' in result
        assert isinstance(result['headers'], dict)
    
    # =============================================================================
    # ERROR HANDLING TESTS
    # =============================================================================
    
    def test_process_corrupted_data(self, parser):
        """Test processing corrupted or malformed data"""
        corrupted_data = pd.DataFrame({
            'Col1': [None, float('inf'), 'Text'],
            'Col2': [float('nan'), 'More text', None]
        })
        
        # Should not crash and return some result
        result = parser._analyze_sheet_structure(corrupted_data)
        assert isinstance(result, dict)
        assert 'structure_type' in result
    
    def test_process_very_large_data(self, parser):
        """Test processing very large datasets"""
        # Create large dataset
        large_data = pd.DataFrame({
            'Product': [f'Product {i}' for i in range(1000)],
            'Price': [10000 + i for i in range(1000)]
        })
        
        # Should handle large data efficiently
        result = parser._analyze_sheet_structure(large_data)
        assert result['structure_type'] == 'tabular'
    
    def test_process_unicode_data(self, parser):
        """Test processing data with unicode characters"""
        unicode_data = pd.DataFrame({
            'Produk': ['Coca Cola 500ml', 'Teh Botol Sosro', 'Kopi Kapal Api'],
            'Harga': [15000, 5000, 8000],
            'Merek': ['Coca-Cola', 'Sosro', 'Kapal Api']
        })
        
        result = parser._analyze_sheet_structure(unicode_data)
        assert result['structure_type'] == 'tabular'
        assert 'product' in result['headers']  # Should match Indonesian headers
    
    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================
    
    def test_end_to_end_processing(self, parser):
        """Test complete end-to-end processing"""
        # Create comprehensive test data
        test_data = pd.DataFrame({
            'Product Name': [
                'Coca Cola 500ml Bottle',
                'Pepsi Cola 500ml Bottle', 
                'Aqua 600ml Bottle',
                'Indomie Ayam Bawang 85g'
            ],
            'Price (IDR)': [
                '15,000',
                '14000',
                'Rp 3,500',
                '2500'
            ],
            'Unit': ['bottle', 'bottle', 'bottle', 'pack'],
            'Brand': ['Coca-Cola', 'Pepsi', 'Aqua', 'Indomie'],
            'Category': ['Beverages', 'Beverages', 'Beverages', 'Food']
        })
        
        # Analyze structure
        structure = parser._analyze_sheet_structure(test_data)
        
        # Extract products
        products = parser._extract_products_and_prices(test_data, structure)
        
        # Validate
        validation = parser._validate_extracted_data(products)
        
        assert structure['structure_type'] == 'tabular'
        assert len(products) == 4
        assert validation['is_valid'] is True
        assert all('name' in product for product in products)
        assert all('price' in product for product in products)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 