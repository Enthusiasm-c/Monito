#!/usr/bin/env python3
"""
Базовый класс для всех парсеров с общими функциями
Устраняет дублирование кода между модулями
"""

import re
import pandas as pd
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class BaseParser:
    """Базовый класс для всех парсеров с общими функциями анализа"""
    
    def __init__(self):
        # Паттерны для поиска товаров и цен
        self.product_patterns = [
            r'[а-яёa-z]{3,}.*\d+.*[а-яёa-z]',  # Текст с числами и буквами
            r'[а-яёa-z]{5,}',  # Просто текст длиннее 5 символов
            r'.*[а-яёa-z]{3,}.*[а-яёa-z]{3,}',  # Несколько слов
        ]
        
        self.price_patterns = [
            r'^\d{3,}\.?\d*$',  # Числа от 100
            r'^\d{1,3}[\s,]\d{3}.*$',  # Числа с разделителями
        ]
        
        self.common_units = [
            'kg', 'g', 'ml', 'l', 'pcs', 'pack', 'box', 'can', 'btl', 
            'ikat', 'gln', 'gram', 'liter', 'piece', 'кг', 'г', 'мл', 'л', 'шт'
        ]
    
    def _looks_like_product(self, value: str) -> bool:
        """Проверка, похоже ли значение на название товара"""
        if len(value) < 3 or len(value) > 200:
            return False
        
        # Пропускаем числа и служебные слова
        if (value.replace('.', '').replace(',', '').isdigit() or
            value.lower() in ['unit', 'price', 'no', 'description', 'total', 'sum', 'nan', 'none']):
            return False
        
        # Должно содержать буквы
        if not any(c.isalpha() for c in value):
            return False
        
        # Проверяем паттерны товаров
        for pattern in self.product_patterns:
            if re.search(pattern, value.lower()):
                return True
        
        return False
    
    def _looks_like_price(self, value: str) -> bool:
        """Проверка, похоже ли значение на цену"""
        try:
            # Очищаем от символов и пробуем преобразовать
            clean_value = re.sub(r'[^\d.]', '', str(value))
            if not clean_value:
                return False
            
            num_value = float(clean_value)
            
            # Разумный диапазон цен
            return 10 <= num_value <= 50000000
            
        except:
            return False
    
    def _looks_like_unit(self, value: str) -> bool:
        """Проверка, похоже ли значение на единицу измерения"""
        value_lower = str(value).lower().strip()
        return value_lower in self.common_units
    
    def _clean_price(self, value) -> float:
        """Очистка и извлечение цены - унифицированная версия"""
        if pd.isna(value):
            return 0
        
        try:
            # Если уже число
            if isinstance(value, (int, float)):
                price = float(value)
                return price if 10 <= price <= 50000000 else 0
            
            # Убираем все кроме цифр и точки
            clean_value = re.sub(r'[^\d.]', '', str(value))
            if not clean_value:
                return 0
            
            price = float(clean_value)
            return price if 10 <= price <= 50000000 else 0
            
        except:
            return 0
    
    def _clean_product_name(self, value) -> Optional[str]:
        """Очистка названия товара"""
        if pd.isna(value):
            return None
        
        name = str(value).strip()
        
        if not self._looks_like_product(name):
            return None
        
        return name 