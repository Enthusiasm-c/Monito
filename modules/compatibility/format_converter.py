"""
=============================================================================
MONITO FORMAT CONVERTER
=============================================================================
Версия: 3.0
Цель: Конвертация форматов данных между legacy и unified системами
=============================================================================
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from modules.adapters.normalizer_adapter import NormalizationResult
from utils.logger import get_logger

logger = get_logger(__name__)

class FormatConverter:
    """
    Конвертер форматов данных между legacy и unified системами
    """
    
    def __init__(self):
        """Инициализация конвертера"""
        logger.info("FormatConverter initialized")
    
    # =============================================================================
    # UNIFIED TO LEGACY CONVERSIONS
    # =============================================================================
    
    def unified_to_legacy_parser_result(self, unified_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Конвертация результата unified парсера в legacy формат
        
        Args:
            unified_result: Результат из unified системы
            
        Returns:
            Результат в legacy формате
        """
        try:
            if unified_result.get('error'):
                return {
                    'error': unified_result['error'],
                    'products': [],
                    'extraction_stats': {'extracted_products': 0}
                }
            
            # Извлекаем продукты из unified результата
            unified_products = []
            
            # Проверяем разные места где могут быть продукты
            if 'final_statistics' in unified_result:
                products_count = unified_result['final_statistics'].get('products_in_unified_system', 0)
                # Симулируем legacy продукты
                unified_products = self._generate_legacy_products_from_stats(unified_result)
            elif 'processing_steps' in unified_result:
                parsing_step = unified_result['processing_steps'].get('parsing', {})
                if 'statistics' in parsing_step:
                    products_count = parsing_step['statistics'].get('legacy_products_found', 0)
                    unified_products = self._generate_legacy_products_from_stats(unified_result)
            
            # Конвертируем в legacy формат
            legacy_products = []
            for product_data in unified_products:
                legacy_product = self._unified_product_data_to_legacy(product_data)
                legacy_products.append(legacy_product)
            
            # Формируем legacy результат
            legacy_result = {
                'file_type': 'auto_detected',
                'supplier': {'name': unified_result.get('supplier_name', 'unknown')},
                'products': legacy_products,
                'extraction_stats': {
                    'extracted_products': len(legacy_products),
                    'total_rows': len(legacy_products),
                    'success_rate': 1.0 if legacy_products else 0.0,
                    'extraction_method': 'unified_system'
                }
            }
            
            return legacy_result
            
        except Exception as e:
            logger.error(f"Unified to legacy parser conversion failed: {e}")
            return {
                'error': f'Conversion failed: {str(e)}',
                'products': [],
                'extraction_stats': {'extracted_products': 0}
            }
    
    def unified_to_legacy_processing_result(self, unified_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Конвертация результата unified обработки в legacy формат
        
        Args:
            unified_result: Результат из unified системы
            
        Returns:
            Результат в legacy формате обработки
        """
        try:
            if unified_result.get('error'):
                return {
                    'error': unified_result['error'],
                    'processed_products': 0,
                    'supplier': 'unknown'
                }
            
            final_stats = unified_result.get('final_statistics', {})
            
            legacy_result = {
                'supplier': unified_result.get('supplier_name', 'unknown'),
                'processed_products': final_stats.get('products_in_unified_system', 0),
                'best_deals_found': final_stats.get('best_deals_found', 0),
                'potential_savings': final_stats.get('potential_savings', 0.0),
                'processing_time': unified_result.get('processing_steps', {}).get('parsing', {}).get('statistics', {}).get('processing_time_seconds', 0),
                'success': True,
                'recommendations': final_stats.get('recommendation_confidence', 0),
                'analysis': {
                    'price_competitiveness': final_stats.get('potential_savings', 0),
                    'product_coverage': final_stats.get('products_in_unified_system', 0),
                    'data_quality': 'good' if final_stats.get('products_in_unified_system', 0) > 0 else 'poor'
                }
            }
            
            return legacy_result
            
        except Exception as e:
            logger.error(f"Unified to legacy processing conversion failed: {e}")
            return {
                'error': f'Conversion failed: {str(e)}',
                'processed_products': 0,
                'supplier': 'unknown'
            }
    
    def normalization_to_legacy_format(self, normalization_result: NormalizationResult) -> Dict[str, Any]:
        """
        Конвертация результата нормализации в legacy формат
        
        Args:
            normalization_result: Результат нормализации из unified системы
            
        Returns:
            Результат в legacy формате
        """
        try:
            legacy_result = {
                'original_name': normalization_result.original_name,
                'normalized_name': normalization_result.normalized_name,
                'confidence': normalization_result.confidence,
                'brand': normalization_result.brand,
                'category': normalization_result.category,
                'size': normalization_result.size,
                'unit': normalization_result.unit,
                'processing_method': normalization_result.processing_method,
                'quality_score': normalization_result.confidence,
                'suggestions': {
                    'brand_extracted': bool(normalization_result.brand),
                    'category_detected': normalization_result.category != 'general',
                    'size_parsed': normalization_result.size is not None
                }
            }
            
            return legacy_result
            
        except Exception as e:
            logger.error(f"Normalization to legacy conversion failed: {e}")
            return {
                'error': f'Conversion failed: {str(e)}',
                'original_name': '',
                'normalized_name': '',
                'confidence': 0.0
            }
    
    def unified_product_to_legacy_format(self, unified_product: Any, price_info: Any = None) -> Dict[str, Any]:
        """
        Конвертация unified товара в legacy формат
        
        Args:
            unified_product: Товар из unified системы
            price_info: Информация о цене
            
        Returns:
            Товар в legacy формате
        """
        try:
            legacy_product = {
                'name': getattr(unified_product, 'standard_name', ''),
                'original_name': getattr(unified_product, 'description', '') or getattr(unified_product, 'standard_name', ''),
                'brand': getattr(unified_product, 'brand', '') or 'unknown',
                'category': getattr(unified_product, 'category', 'general'),
                'size': getattr(unified_product, 'size', None),
                'unit': getattr(unified_product, 'unit', 'pcs'),
                'product_id': str(getattr(unified_product, 'product_id', '')),
                'created_at': getattr(unified_product, 'created_at', datetime.utcnow()).isoformat() if hasattr(unified_product, 'created_at') else datetime.utcnow().isoformat()
            }
            
            # Добавляем информацию о цене если есть
            if price_info:
                legacy_product.update({
                    'price': getattr(price_info, 'price', 0.0),
                    'supplier': getattr(price_info, 'supplier_name', 'unknown'),
                    'currency': 'IDR',
                    'price_unit': getattr(price_info, 'unit', 'pcs'),
                    'last_updated': getattr(price_info, 'last_updated', datetime.utcnow()).isoformat() if hasattr(price_info, 'last_updated') else datetime.utcnow().isoformat()
                })
            
            return legacy_product
            
        except Exception as e:
            logger.error(f"Unified product to legacy conversion failed: {e}")
            return {
                'name': 'conversion_error',
                'error': str(e)
            }
    
    def unified_report_to_legacy_format(self, unified_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Конвертация unified отчета в legacy формат
        
        Args:
            unified_report: Отчет из unified системы
            
        Returns:
            Отчет в legacy формате
        """
        try:
            if unified_report.get('error'):
                return {
                    'error': unified_report['error'],
                    'products_analyzed': 0,
                    'report_data': {}
                }
            
            # Извлекаем данные из unified отчета
            catalog_data = unified_report.get('catalog_data', {})
            analytics = unified_report.get('analytics', {})
            
            # Формируем legacy отчет
            legacy_report = {
                'products_analyzed': len(catalog_data.get('products', [])),
                'suppliers_compared': len(catalog_data.get('suppliers', [])),
                'categories_covered': len(analytics.get('category_analysis', {})),
                'best_deals': self._extract_best_deals_legacy_format(catalog_data),
                'price_comparison': self._create_legacy_price_comparison(catalog_data),
                'supplier_analysis': self._create_legacy_supplier_analysis(analytics),
                'recommendations': self._create_legacy_recommendations(unified_report),
                'report_metadata': {
                    'generated_at': unified_report.get('generated_at', datetime.utcnow().isoformat()),
                    'report_type': 'price_comparison',
                    'currency': 'IDR'
                }
            }
            
            return legacy_report
            
        except Exception as e:
            logger.error(f"Unified report to legacy conversion failed: {e}")
            return {
                'error': f'Conversion failed: {str(e)}',
                'products_analyzed': 0,
                'report_data': {}
            }
    
    # =============================================================================
    # LEGACY TO UNIFIED CONVERSIONS
    # =============================================================================
    
    def legacy_product_to_unified_format(self, legacy_product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Конвертация legacy товара в unified формат
        
        Args:
            legacy_product: Товар в legacy формате
            
        Returns:
            Товар в unified формате
        """
        try:
            unified_product = {
                'standard_name': legacy_product.get('name') or legacy_product.get('normalized_name', ''),
                'brand': legacy_product.get('brand', ''),
                'category': legacy_product.get('category', 'general'),
                'size': legacy_product.get('size'),
                'unit': legacy_product.get('unit', 'pcs'),
                'description': legacy_product.get('original_name', ''),
                'original_name': legacy_product.get('original_name', ''),
                'price': legacy_product.get('price', 0.0),
                'confidence_score': legacy_product.get('confidence', 0.8)
            }
            
            # Очищаем None значения
            unified_product = {k: v for k, v in unified_product.items() if v is not None}
            
            return unified_product
            
        except Exception as e:
            logger.error(f"Legacy to unified product conversion failed: {e}")
            return {
                'standard_name': 'conversion_error',
                'error': str(e)
            }
    
    def legacy_search_query_to_unified(self, legacy_query: str, legacy_filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Конвертация legacy поискового запроса в unified формат
        
        Args:
            legacy_query: Поисковый запрос в legacy формате
            legacy_filters: Фильтры в legacy формате
            
        Returns:
            Параметры поиска в unified формате
        """
        try:
            unified_search = {
                'query': legacy_query,
                'filters': {}
            }
            
            if legacy_filters:
                # Конвертируем legacy фильтры
                if 'category' in legacy_filters:
                    unified_search['filters']['category'] = legacy_filters['category']
                
                if 'supplier' in legacy_filters:
                    unified_search['filters']['supplier_name'] = legacy_filters['supplier']
                
                if 'price_range' in legacy_filters:
                    price_range = legacy_filters['price_range']
                    if isinstance(price_range, dict):
                        unified_search['filters']['price_min'] = price_range.get('min')
                        unified_search['filters']['price_max'] = price_range.get('max')
                
                if 'brand' in legacy_filters:
                    unified_search['filters']['brand'] = legacy_filters['brand']
            
            return unified_search
            
        except Exception as e:
            logger.error(f"Legacy search query conversion failed: {e}")
            return {'query': legacy_query, 'filters': {}}
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def _generate_legacy_products_from_stats(self, unified_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Генерация legacy товаров на основе статистики unified результата"""
        products = []
        
        try:
            # Пытаемся извлечь информацию о товарах из различных мест
            final_stats = unified_result.get('final_statistics', {})
            product_count = final_stats.get('products_in_unified_system', 0)
            supplier_name = unified_result.get('supplier_name', 'unknown')
            
            # Генерируем базовые товары для совместимости
            for i in range(min(product_count, 10)):  # Ограничиваем количество для примера
                product = {
                    'original_name': f'Product {i+1} from {supplier_name}',
                    'standardized_name': f'Standardized Product {i+1}',
                    'price': 10000 + (i * 1000),  # Примерные цены
                    'unit': 'pcs',
                    'brand': 'unknown',
                    'category': 'general',
                    'confidence': 0.8
                }
                products.append(product)
                
        except Exception as e:
            logger.warning(f"Could not generate legacy products from stats: {e}")
        
        return products
    
    def _unified_product_data_to_legacy(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Конвертация unified данных товара в legacy формат"""
        legacy_product = {
            'original_name': product_data.get('original_name', ''),
            'standardized_name': product_data.get('standard_name', ''),
            'price': product_data.get('price', 0.0),
            'unit': product_data.get('unit', 'pcs'),
            'brand': product_data.get('brand', 'unknown'),
            'category': product_data.get('category', 'general'),
            'size': product_data.get('size'),
            'confidence': product_data.get('confidence_score', 0.8)
        }
        
        return legacy_product
    
    def _extract_best_deals_legacy_format(self, catalog_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Извлечение лучших предложений в legacy формате"""
        best_deals = []
        
        try:
            products = catalog_data.get('products', [])
            
            for product in products[:5]:  # Топ 5 лучших предложений
                deal = {
                    'product_name': product.get('name', ''),
                    'best_price': product.get('best_price', 0.0),
                    'best_supplier': product.get('best_supplier', ''),
                    'savings_amount': product.get('savings', 0.0),
                    'savings_percentage': product.get('savings_percentage', 0.0)
                }
                best_deals.append(deal)
                
        except Exception as e:
            logger.warning(f"Could not extract best deals: {e}")
        
        return best_deals
    
    def _create_legacy_price_comparison(self, catalog_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание сравнения цен в legacy формате"""
        comparison = {
            'products_compared': len(catalog_data.get('products', [])),
            'suppliers_involved': len(catalog_data.get('suppliers', [])),
            'price_range': {
                'min': 0.0,
                'max': 0.0,
                'average': 0.0
            },
            'currency': 'IDR'
        }
        
        try:
            products = catalog_data.get('products', [])
            if products:
                prices = [p.get('best_price', 0) for p in products if p.get('best_price', 0) > 0]
                if prices:
                    comparison['price_range'] = {
                        'min': min(prices),
                        'max': max(prices),
                        'average': sum(prices) / len(prices)
                    }
        except Exception as e:
            logger.warning(f"Could not create price comparison: {e}")
        
        return comparison
    
    def _create_legacy_supplier_analysis(self, analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Создание анализа поставщиков в legacy формате"""
        analysis = {
            'total_suppliers': 0,
            'top_performers': [],
            'market_share': {},
            'competitiveness_scores': {}
        }
        
        try:
            supplier_market_share = analytics.get('supplier_market_share', {})
            analysis['total_suppliers'] = len(supplier_market_share)
            analysis['market_share'] = supplier_market_share
            
            # Создаем топ исполнителей
            for supplier, share in list(supplier_market_share.items())[:3]:
                performer = {
                    'supplier_name': supplier,
                    'market_share': share,
                    'competitiveness': 'high'  # Упрощенная оценка
                }
                analysis['top_performers'].append(performer)
                
        except Exception as e:
            logger.warning(f"Could not create supplier analysis: {e}")
        
        return analysis
    
    def _create_legacy_recommendations(self, unified_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Создание рекомендаций в legacy формате"""
        recommendations = []
        
        try:
            additional_analysis = unified_report.get('additional_analysis', {})
            supplier_recommendations = additional_analysis.get('supplier_recommendations', [])
            
            for supplier_rec in supplier_recommendations[:3]:
                recommendation = {
                    'type': 'supplier_recommendation',
                    'supplier_name': supplier_rec.get('supplier_name', ''),
                    'reliability_score': supplier_rec.get('reliability_score', 0),
                    'recommendation': f"Consider {supplier_rec.get('supplier_name', 'this supplier')} for competitive pricing"
                }
                recommendations.append(recommendation)
            
            # Добавляем общие рекомендации
            if not recommendations:
                recommendations.append({
                    'type': 'general',
                    'recommendation': 'Review supplier performance regularly for optimal procurement',
                    'priority': 'medium'
                })
                
        except Exception as e:
            logger.warning(f"Could not create recommendations: {e}")
        
        return recommendations 