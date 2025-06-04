"""
=============================================================================
MONITO LEGACY API WRAPPER
=============================================================================
Версия: 3.0
Цель: Обертка для legacy API с переадресацией на unified систему
=============================================================================
"""

import logging
import warnings
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from modules.unified_database_manager import UnifiedDatabaseManager
from modules.adapters.legacy_integration_adapter import LegacyIntegrationAdapter
from modules.compatibility.format_converter import FormatConverter
from utils.logger import get_logger

logger = get_logger(__name__)

class LegacyAPIWrapper:
    """
    Обертка для legacy API, перенаправляющая вызовы в unified систему
    """
    
    def __init__(self, integration_adapter: LegacyIntegrationAdapter):
        """
        Инициализация wrapper'a
        
        Args:
            integration_adapter: Адаптер интеграции с unified системой
        """
        self.integration_adapter = integration_adapter
        self.format_converter = FormatConverter()
        
        # Счетчики использования legacy методов
        self.legacy_calls_count = {}
        
        logger.info("LegacyAPIWrapper initialized")
    
    # =============================================================================
    # LEGACY PARSER API COMPATIBILITY
    # =============================================================================
    
    def extract_products_from_excel(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Legacy метод: извлечение товаров из Excel
        
        DEPRECATED: Используйте integration_adapter.integrate_single_file()
        """
        self._log_legacy_call('extract_products_from_excel')
        
        warnings.warn(
            "extract_products_from_excel is deprecated. Use integration_adapter.integrate_single_file()",
            DeprecationWarning,
            stacklevel=2
        )
        
        try:
            # Переадресуем на unified систему
            unified_result = self.integration_adapter.integrate_single_file(file_path)
            
            # Конвертируем в legacy формат
            legacy_result = self.format_converter.unified_to_legacy_parser_result(unified_result)
            
            return legacy_result
            
        except Exception as e:
            logger.error(f"Legacy Excel extraction failed: {e}")
            return {
                'error': str(e),
                'products': [],
                'extraction_stats': {'extracted_products': 0}
            }
    
    def extract_products_from_pdf(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Legacy метод: извлечение товаров из PDF
        
        DEPRECATED: Используйте integration_adapter.integrate_single_file()
        """
        self._log_legacy_call('extract_products_from_pdf')
        
        warnings.warn(
            "extract_products_from_pdf is deprecated. Use integration_adapter.integrate_single_file()",
            DeprecationWarning,
            stacklevel=2
        )
        
        try:
            # Переадресуем на unified систему
            unified_result = self.integration_adapter.integrate_single_file(file_path)
            
            # Конвертируем в legacy формат
            legacy_result = self.format_converter.unified_to_legacy_parser_result(unified_result)
            
            return legacy_result
            
        except Exception as e:
            logger.error(f"Legacy PDF extraction failed: {e}")
            return {
                'error': str(e),
                'products': [],
                'extraction_stats': {'extracted_products': 0}
            }
    
    def process_price_list(self, file_path: str, supplier_name: str = None) -> Dict[str, Any]:
        """
        Legacy метод: обработка прайс-листа
        
        DEPRECATED: Используйте integration_adapter.integrate_single_file()
        """
        self._log_legacy_call('process_price_list')
        
        warnings.warn(
            "process_price_list is deprecated. Use integration_adapter.integrate_single_file()",
            DeprecationWarning,
            stacklevel=2
        )
        
        try:
            # Переадресуем на unified систему
            unified_result = self.integration_adapter.integrate_single_file(file_path, supplier_name)
            
            # Конвертируем в legacy формат
            legacy_result = self.format_converter.unified_to_legacy_processing_result(unified_result)
            
            return legacy_result
            
        except Exception as e:
            logger.error(f"Legacy price list processing failed: {e}")
            return {
                'error': str(e),
                'processed_products': 0,
                'supplier': supplier_name or 'unknown'
            }
    
    # =============================================================================
    # LEGACY NORMALIZER API COMPATIBILITY
    # =============================================================================
    
    def normalize_product_name(self, product_name: str, context: str = None) -> Dict[str, Any]:
        """
        Legacy метод: нормализация названия товара
        
        DEPRECATED: Используйте normalizer_adapter.normalize_product_name()
        """
        self._log_legacy_call('normalize_product_name')
        
        warnings.warn(
            "normalize_product_name is deprecated. Use normalizer_adapter.normalize_product_name()",
            DeprecationWarning,
            stacklevel=2
        )
        
        try:
            # Переадресуем на unified систему
            normalization_result = self.integration_adapter.normalizer_adapter.normalize_product_name(
                product_name, context
            )
            
            # Конвертируем в legacy формат
            legacy_result = self.format_converter.normalization_to_legacy_format(normalization_result)
            
            return legacy_result
            
        except Exception as e:
            logger.error(f"Legacy normalization failed: {e}")
            return {
                'error': str(e),
                'original_name': product_name,
                'normalized_name': product_name,
                'confidence': 0.0
            }
    
    def resolve_product_data(self, product_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Legacy метод: разрешение данных товара
        
        DEPRECATED: Используйте unified систему
        """
        self._log_legacy_call('resolve_product_data')
        
        warnings.warn(
            "resolve_product_data is deprecated. Use unified system directly",
            DeprecationWarning,
            stacklevel=2
        )
        
        try:
            # Извлекаем название товара
            product_name = product_info.get('name') or product_info.get('product_name') or ''
            
            if not product_name:
                return {
                    'error': 'No product name provided',
                    'resolved_data': {}
                }
            
            # Нормализуем через unified систему
            normalization_result = self.integration_adapter.normalizer_adapter.normalize_product_name(product_name)
            
            # Ищем в unified каталоге
            catalog_products = self.integration_adapter.db_manager.search_master_products(product_name, limit=5)
            
            # Формируем legacy ответ
            legacy_result = {
                'original_data': product_info,
                'resolved_data': {
                    'normalized_name': normalization_result.normalized_name,
                    'brand': normalization_result.brand,
                    'category': normalization_result.category,
                    'confidence': normalization_result.confidence
                },
                'catalog_matches': len(catalog_products),
                'suggestions': [
                    {
                        'name': product.standard_name,
                        'brand': product.brand,
                        'category': product.category
                    }
                    for product in catalog_products[:3]
                ]
            }
            
            return legacy_result
            
        except Exception as e:
            logger.error(f"Legacy product resolution failed: {e}")
            return {
                'error': str(e),
                'original_data': product_info,
                'resolved_data': {}
            }
    
    # =============================================================================
    # LEGACY DATABASE API COMPATIBILITY
    # =============================================================================
    
    def get_products_by_supplier(self, supplier_name: str) -> List[Dict[str, Any]]:
        """
        Legacy метод: получение товаров по поставщику
        
        DEPRECATED: Используйте unified database queries
        """
        self._log_legacy_call('get_products_by_supplier')
        
        warnings.warn(
            "get_products_by_supplier is deprecated. Use unified database queries",
            DeprecationWarning,
            stacklevel=2
        )
        
        try:
            # Получаем товары через unified систему
            all_products = self.integration_adapter.db_manager.search_master_products("", limit=1000)
            
            # Фильтруем по поставщику
            supplier_products = []
            for product in all_products:
                prices = self.integration_adapter.db_manager.get_current_prices_for_product(str(product.product_id))
                
                for price in prices:
                    if price.supplier_name == supplier_name:
                        # Конвертируем в legacy формат
                        legacy_product = self.format_converter.unified_product_to_legacy_format(product, price)
                        supplier_products.append(legacy_product)
                        break
            
            return supplier_products
            
        except Exception as e:
            logger.error(f"Legacy supplier products query failed: {e}")
            return []
    
    def search_products(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Legacy метод: поиск товаров
        
        DEPRECATED: Используйте unified catalog search
        """
        self._log_legacy_call('search_products')
        
        warnings.warn(
            "search_products is deprecated. Use unified catalog search",
            DeprecationWarning,
            stacklevel=2
        )
        
        try:
            # Поиск через unified систему
            unified_products = self.integration_adapter.db_manager.search_master_products(query, limit=limit)
            
            # Конвертируем в legacy формат
            legacy_products = []
            for product in unified_products:
                prices = self.integration_adapter.db_manager.get_current_prices_for_product(str(product.product_id))
                best_price = min(prices, key=lambda p: p.price) if prices else None
                
                legacy_product = self.format_converter.unified_product_to_legacy_format(product, best_price)
                legacy_products.append(legacy_product)
            
            return legacy_products
            
        except Exception as e:
            logger.error(f"Legacy product search failed: {e}")
            return []
    
    def get_product_prices(self, product_name: str) -> List[Dict[str, Any]]:
        """
        Legacy метод: получение цен товара
        
        DEPRECATED: Используйте unified price queries
        """
        self._log_legacy_call('get_product_prices')
        
        warnings.warn(
            "get_product_prices is deprecated. Use unified price queries",
            DeprecationWarning,
            stacklevel=2
        )
        
        try:
            # Ищем товар в unified системе
            products = self.integration_adapter.db_manager.search_master_products(product_name, limit=1)
            
            if not products:
                return []
            
            product = products[0]
            prices = self.integration_adapter.db_manager.get_current_prices_for_product(str(product.product_id))
            
            # Конвертируем в legacy формат
            legacy_prices = []
            for price in prices:
                legacy_price = {
                    'product_name': product.standard_name,
                    'supplier': price.supplier_name,
                    'price': price.price,
                    'unit': price.unit,
                    'last_updated': price.last_updated.isoformat() if price.last_updated else None,
                    'currency': 'IDR'  # По умолчанию для Бали
                }
                legacy_prices.append(legacy_price)
            
            return legacy_prices
            
        except Exception as e:
            logger.error(f"Legacy price query failed: {e}")
            return []
    
    # =============================================================================
    # LEGACY REPORTING API COMPATIBILITY
    # =============================================================================
    
    def generate_price_comparison_report(self, product_list: List[str]) -> Dict[str, Any]:
        """
        Legacy метод: генерация отчета сравнения цен
        
        DEPRECATED: Используйте unified reporting system
        """
        self._log_legacy_call('generate_price_comparison_report')
        
        warnings.warn(
            "generate_price_comparison_report is deprecated. Use unified reporting system",
            DeprecationWarning,
            stacklevel=2
        )
        
        try:
            # Формируем требуемые товары для unified системы
            required_products = [{'name': name, 'quantity': 1} for name in product_list]
            
            # Генерируем отчет через unified систему
            unified_report = self.integration_adapter.get_procurement_recommendations_report(required_products)
            
            # Конвертируем в legacy формат
            legacy_report = self.format_converter.unified_report_to_legacy_format(unified_report)
            
            return legacy_report
            
        except Exception as e:
            logger.error(f"Legacy report generation failed: {e}")
            return {
                'error': str(e),
                'products_analyzed': 0,
                'report_data': {}
            }
    
    def get_supplier_statistics(self, supplier_name: str = None) -> Dict[str, Any]:
        """
        Legacy метод: получение статистики поставщиков
        
        DEPRECATED: Используйте unified analytics
        """
        self._log_legacy_call('get_supplier_statistics')
        
        warnings.warn(
            "get_supplier_statistics is deprecated. Use unified analytics",
            DeprecationWarning,
            stacklevel=2
        )
        
        try:
            if supplier_name:
                # Статистика конкретного поставщика
                performance = self.integration_adapter.db_manager.get_supplier_performance(supplier_name)
                
                legacy_stats = {
                    'supplier_name': supplier_name,
                    'total_products': performance.get('total_products', 0),
                    'competitive_products': performance.get('best_price_products', 0),
                    'average_competitiveness': performance.get('price_competitiveness', 0),
                    'reliability_score': performance.get('reliability_score', 0)
                }
            else:
                # Общая статистика всех поставщиков
                system_stats = self.integration_adapter.db_manager.get_system_statistics()
                
                legacy_stats = {
                    'total_suppliers': system_stats['total_suppliers'],
                    'total_products': system_stats['total_products'],
                    'total_prices': system_stats['total_prices'],
                    'categories_count': system_stats['categories_count']
                }
            
            return legacy_stats
            
        except Exception as e:
            logger.error(f"Legacy statistics query failed: {e}")
            return {'error': str(e)}
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def _log_legacy_call(self, method_name: str):
        """Логирование вызовов legacy методов"""
        self.legacy_calls_count[method_name] = self.legacy_calls_count.get(method_name, 0) + 1
        
        logger.warning(f"Legacy API call: {method_name} (call #{self.legacy_calls_count[method_name]})")
    
    def get_legacy_usage_stats(self) -> Dict[str, Any]:
        """
        Получение статистики использования legacy API
        
        Returns:
            Статистика вызовов legacy методов
        """
        total_calls = sum(self.legacy_calls_count.values())
        
        stats = {
            'total_legacy_calls': total_calls,
            'methods_used': len(self.legacy_calls_count),
            'call_breakdown': dict(self.legacy_calls_count),
            'most_used_method': max(self.legacy_calls_count, key=self.legacy_calls_count.get) if self.legacy_calls_count else None,
            'migration_urgency': self._calculate_migration_urgency()
        }
        
        return stats
    
    def _calculate_migration_urgency(self) -> str:
        """Расчет срочности миграции на основе использования legacy API"""
        total_calls = sum(self.legacy_calls_count.values())
        
        if total_calls == 0:
            return 'none'
        elif total_calls < 10:
            return 'low'
        elif total_calls < 50:
            return 'medium'
        else:
            return 'high'
    
    def generate_migration_guide(self) -> Dict[str, Any]:
        """
        Генерация руководства по миграции на основе использования legacy API
        
        Returns:
            Руководство по замене legacy методов
        """
        migration_guide = {
            'legacy_methods_used': list(self.legacy_calls_count.keys()),
            'replacement_suggestions': {},
            'migration_steps': [],
            'estimated_effort': 'low'
        }
        
        # Предложения по замене
        replacements = {
            'extract_products_from_excel': 'integration_adapter.integrate_single_file()',
            'extract_products_from_pdf': 'integration_adapter.integrate_single_file()',
            'process_price_list': 'integration_adapter.integrate_single_file()',
            'normalize_product_name': 'normalizer_adapter.normalize_product_name()',
            'resolve_product_data': 'Direct unified system queries',
            'get_products_by_supplier': 'db_manager.search_master_products() + filtering',
            'search_products': 'db_manager.search_master_products()',
            'get_product_prices': 'db_manager.get_current_prices_for_product()',
            'generate_price_comparison_report': 'get_procurement_recommendations_report()',
            'get_supplier_statistics': 'db_manager.get_system_statistics()'
        }
        
        for method in self.legacy_calls_count:
            if method in replacements:
                migration_guide['replacement_suggestions'][method] = replacements[method]
        
        # Шаги миграции
        if self.legacy_calls_count:
            migration_guide['migration_steps'] = [
                '1. Identify all legacy API usage in your codebase',
                '2. Replace legacy calls with unified system equivalents',
                '3. Update data format handling using FormatConverter',
                '4. Test thoroughly with unified system',
                '5. Remove LegacyAPIWrapper dependency'
            ]
            
            # Оценка усилий
            total_methods = len(self.legacy_calls_count)
            if total_methods <= 2:
                migration_guide['estimated_effort'] = 'low'
            elif total_methods <= 5:
                migration_guide['estimated_effort'] = 'medium'
            else:
                migration_guide['estimated_effort'] = 'high'
        
        return migration_guide 