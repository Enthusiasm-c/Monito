#!/usr/bin/env python3
"""
Адаптер данных для преобразования результатов InteligentPreProcessor 
в формат, подходящий для GoogleSheetsManager
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DataAdapter:
    """Адаптер для преобразования данных между модулями"""
    
    def __init__(self):
        self.unit_mapping = {
            'kg': 'kg',
            'kilogram': 'kg',
            'kilo': 'kg',
            'l': 'l',
            'liter': 'l',
            'litre': 'l',
            'pcs': 'pcs',
            'piece': 'pcs',
            'pack': 'pack',
            'bottle': 'bottle',
            'can': 'can',
            'box': 'box'
        }
        
        self.category_mapping = {
            # Овощи
            'tomato': 'vegetables',
            'potato': 'vegetables',
            'onion': 'vegetables',
            'carrot': 'vegetables',
            'cabbage': 'vegetables',
            'lettuce': 'vegetables',
            'spinach': 'vegetables',
            'capsicum': 'vegetables',
            'pepper': 'vegetables',
            'chili': 'spices',
            'cucumber': 'vegetables',
            'eggplant': 'vegetables',
            'mushroom': 'vegetables',
            'celery': 'vegetables',
            'corn': 'vegetables',
            
            # Зелень и специи
            'basil': 'herbs',
            'parsley': 'herbs',
            'mint': 'herbs',
            'oregano': 'herbs',
            'ginger': 'spices',
            'garlic': 'spices',
            'galangal': 'spices',
            'lemongrass': 'herbs',
            'lime': 'herbs',
            'lemon': 'fruits',
            
            # Фрукты
            'mango': 'fruits',
            'banana': 'fruits',
            'apple': 'fruits',
            'orange': 'fruits',
            'pear': 'fruits',
            'grape': 'fruits',
            
            # Молочные продукты
            'cheese': 'dairy',
            'milk': 'dairy',
            'yogurt': 'dairy',
            'butter': 'dairy',
            
            # Мясо
            'chicken': 'meat',
            'beef': 'meat',
            'pork': 'meat',
            'fish': 'seafood',
            
            # Зерновые и бобовые
            'rice': 'grains',
            'wheat': 'grains',
            'bean': 'legumes',
            'lentil': 'legumes',
            
            # Напитки
            'juice': 'beverages',
            'water': 'beverages',
            'tea': 'beverages',
            'coffee': 'beverages'
        }
    
    def convert_intelligent_to_sheets_format(self, intelligent_result: Dict[str, Any], 
                                           supplier_name: str = "AI_Extracted") -> Dict[str, Any]:
        """
        Преобразует результат InteligentPreProcessor в формат для GoogleSheetsManager
        """
        
        logger.info(f"🔄 Преобразование данных для Google Sheets...")
        logger.info(f"📊 Входные данные: {len(intelligent_result.get('total_products', []))} товаров, {len(intelligent_result.get('total_prices', []))} цен")
        
        try:
            # Получаем списки товаров и цен
            raw_products = intelligent_result.get('total_products', [])
            raw_prices = intelligent_result.get('total_prices', [])
            linked_pairs = intelligent_result.get('product_price_pairs', [])
            
            # Создаем словарь цен по позициям
            price_by_position = {}
            for price in raw_prices:
                row = price.get('row')
                if row:
                    price_by_position[row] = price
            
            converted_products = []
            
            # Если есть готовые связанные пары - используем их
            if linked_pairs:
                logger.info(f"🔗 Используем {len(linked_pairs)} связанных пар товар-цена")
                
                for pair in linked_pairs:
                    product = pair.get('product', {})
                    price_info = pair.get('price', {})
                    
                    converted_product = self._create_product_from_pair(product, price_info, supplier_name)
                    if converted_product:
                        converted_products.append(converted_product)
            
            else:
                # Связываем товары с ценами по строкам
                logger.info(f"🔄 Связываем товары с ценами по строкам...")
                
                for product in raw_products:
                    row = product.get('row')
                    price_info = price_by_position.get(row)
                    
                    converted_product = self._create_product_from_components(product, price_info, supplier_name)
                    if converted_product:
                        converted_products.append(converted_product)
            
            # Убираем дубликаты по названию
            unique_products = self._deduplicate_products(converted_products)
            
            # Создаем финальную структуру
            result = {
                'supplier': {
                    'name': supplier_name,
                    'type': 'ai_extracted',
                    'contact': 'auto_generated',
                    'extracted_at': datetime.now().isoformat()
                },
                'products': unique_products,
                'data_quality': {
                    'extraction_confidence': intelligent_result.get('recovery_stats', {}).get('data_completeness', 0) / 100,
                    'source_clarity': 'intelligent_preprocessor',
                    'potential_errors': []
                },
                'processing_stats': {
                    'original_products': len(raw_products),
                    'original_prices': len(raw_prices),
                    'linked_pairs': len(linked_pairs),
                    'final_products': len(unique_products),
                    'success_rate': (len(unique_products) / max(len(raw_products), 1)) * 100
                }
            }
            
            logger.info(f"✅ Преобразование завершено:")
            logger.info(f"   📦 Исходных товаров: {len(raw_products)}")
            logger.info(f"   💰 Исходных цен: {len(raw_prices)}")
            logger.info(f"   🔗 Связанных пар: {len(linked_pairs)}")
            logger.info(f"   ✅ Финальных товаров: {len(unique_products)}")
            logger.info(f"   📊 Успешность: {result['processing_stats']['success_rate']:.1f}%")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка преобразования данных: {e}")
            return {
                'error': f'Ошибка преобразования данных: {e}',
                'supplier': {'name': supplier_name},
                'products': []
            }
    
    def _create_product_from_pair(self, product_info: Dict, price_info: Dict, supplier_name: str) -> Dict[str, Any]:
        """Создает товар из связанной пары"""
        
        try:
            product_name = product_info.get('name', '').strip()
            price_value = price_info.get('value', 0)
            
            if not product_name or price_value <= 0:
                return None
            
            # Определяем единицу измерения и категорию
            unit = self._extract_unit_from_name(product_name)
            category = self._determine_category(product_name)
            
            return {
                'original_name': product_name,
                'standardized_name': self._standardize_name(product_name),
                'price': float(price_value),
                'unit': unit,
                'currency': 'IDR',  # По умолчанию для индонезийских прайсов
                'category': category,
                'brand': 'unknown',
                'size': 'unknown',
                'confidence': min(product_info.get('confidence', 0.8), price_info.get('confidence', 0.8)),
                'source_position': f"R{product_info.get('row', 0)}C{product_info.get('column', 0)}",
                'supplier': supplier_name
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка создания товара из пары: {e}")
            return None
    
    def _create_product_from_components(self, product_info: Dict, price_info: Dict, supplier_name: str) -> Dict[str, Any]:
        """Создает товар из отдельных компонентов"""
        
        try:
            product_name = product_info.get('name', '').strip()
            
            if not product_name:
                return None
            
            # Цена может быть None если не найдена в той же строке
            price_value = price_info.get('value', 0) if price_info else 0
            
            # Определяем единицу измерения и категорию
            unit = self._extract_unit_from_name(product_name)
            category = self._determine_category(product_name)
            
            return {
                'original_name': product_name,
                'standardized_name': self._standardize_name(product_name),
                'price': float(price_value) if price_value > 0 else 0,
                'unit': unit,
                'currency': 'IDR',
                'category': category,
                'brand': 'unknown',
                'size': 'unknown',
                'confidence': product_info.get('confidence', 0.8),
                'source_position': f"R{product_info.get('row', 0)}C{product_info.get('column', 0)}",
                'supplier': supplier_name
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка создания товара из компонентов: {e}")
            return None
    
    def _extract_unit_from_name(self, name: str) -> str:
        """Извлекает единицу измерения из названия товара"""
        
        name_lower = name.lower()
        
        # Ищем явные указания единиц
        for unit_key, unit_value in self.unit_mapping.items():
            if unit_key in name_lower:
                return unit_value
        
        # Определяем по типу товара
        if any(veg in name_lower for veg in ['vegetable', 'овощ', 'зелень']):
            return 'kg'
        elif any(fruit in name_lower for fruit in ['fruit', 'фрукт']):
            return 'kg'
        elif any(liquid in name_lower for liquid in ['juice', 'milk', 'oil', 'sauce']):
            return 'l'
        elif any(grain in name_lower for grain in ['rice', 'flour', 'sugar']):
            return 'kg'
        
        return 'pcs'  # По умолчанию
    
    def _determine_category(self, name: str) -> str:
        """Определяет категорию товара по названию"""
        
        name_lower = name.lower()
        
        # Проверяем ключевые слова
        for keyword, category in self.category_mapping.items():
            if keyword in name_lower:
                return category
        
        # Определяем по общим словам
        if any(word in name_lower for word in ['fresh', 'organic', 'green', 'leaf']):
            return 'vegetables'
        elif any(word in name_lower for word in ['seed', 'powder', 'dried']):
            return 'spices'
        elif any(word in name_lower for word in ['sauce', 'paste', 'vinegar']):
            return 'condiments'
        
        return 'general'
    
    def _standardize_name(self, name: str) -> str:
        """Стандартизирует название товара"""
        
        # Убираем лишние пробелы и приводим к стандартному виду
        standardized = ' '.join(name.split())
        
        # Приводим к правильному регистру (каждое слово с большой буквы)
        standardized = standardized.title()
        
        # Исправляем некоторые общие ошибки
        replacements = {
            'Buttom': 'Button',
            'Stringbeen': 'String Bean',
            'Pokcoy': 'Bok Choy',
            'Lolobionda': 'Lollo Bionda',
            'Lolorosso': 'Lollo Rosso'
        }
        
        for old, new in replacements.items():
            standardized = standardized.replace(old, new)
        
        return standardized
    
    def _deduplicate_products(self, products: List[Dict]) -> List[Dict]:
        """Убирает дубликаты товаров"""
        
        unique_products = {}
        
        for product in products:
            name = product.get('standardized_name', '').lower()
            
            if name not in unique_products:
                unique_products[name] = product
            else:
                # Если дубликат, берем тот что с более высокой confidence
                existing = unique_products[name]
                if product.get('confidence', 0) > existing.get('confidence', 0):
                    unique_products[name] = product
        
        return list(unique_products.values()) 