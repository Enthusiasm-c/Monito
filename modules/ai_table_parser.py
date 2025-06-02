#!/usr/bin/env python3
"""
AI-powered парсер таблиц через ChatGPT
Автоматически понимает структуру таблиц без ручной настройки
"""

import pandas as pd
import requests
import json
import logging
import os
import time
from typing import Dict, List, Any, Optional, Tuple
from .base_parser import BaseParser

logger = logging.getLogger(__name__)

class AITableParser(BaseParser):
    """AI-powered парсер таблиц через ChatGPT"""
    
    def __init__(self, openai_api_key: str):
        # Инициализируем базовый класс для использования общих функций
        super().__init__()
        
        self.api_key = openai_api_key
        self.max_rows_for_analysis = 100  # Уменьшаем для быстрой обработки и избежания таймаутов
        self.max_tokens = 8000  # Уменьшаем лимит токенов для более быстрых ответов
        
    def analyze_table_structure(self, df: pd.DataFrame, context: str = "") -> Optional[Dict]:
        """
        Анализ структуры таблицы через ChatGPT
        Возвращает информацию о столбцах и извлеченных товарах
        """
        try:
            if df.empty:
                return None
            
            # Готовим образец таблицы для анализа
            table_sample = self._prepare_table_sample(df)
            
            # Формируем промпт для ChatGPT
            prompt = self._create_analysis_prompt(table_sample, context)
            
            # Отправляем запрос к ChatGPT
            response = self._query_chatgpt(prompt)
            
            if response:
                return self._parse_chatgpt_response(response, df)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка AI анализа таблицы: {e}")
            return None
    
    def _prepare_table_sample(self, df: pd.DataFrame) -> str:
        """Подготовка образца таблицы для отправки в ChatGPT"""
        # Умное сэмплирование: берем начало, середину и конец таблицы
        if len(df) <= self.max_rows_for_analysis:
            # Если таблица маленькая - берем всю
            sample_df = df.copy()
            logger.info(f"📊 Анализируем всю таблицу: {len(df)} строк")
        else:
            # Для больших таблиц берем: начало (40%), середину (40%), конец (20%)
            total_rows = self.max_rows_for_analysis
            start_rows = int(total_rows * 0.4)  # 200 строк
            middle_rows = int(total_rows * 0.4)  # 200 строк  
            end_rows = total_rows - start_rows - middle_rows  # 100 строк
            
            # Начало таблицы
            start_df = df.head(start_rows)
            
            # Середина таблицы
            middle_start = len(df) // 2 - middle_rows // 2
            middle_end = middle_start + middle_rows
            middle_df = df.iloc[middle_start:middle_end]
            
            # Конец таблицы
            end_df = df.tail(end_rows)
            
            logger.info(f"📊 Умное сэмплирование из {len(df)} строк:")
            logger.info(f"   📍 Начало: строки 0-{start_rows-1} ({start_rows} строк)")
            logger.info(f"   📍 Середина: строки {middle_start}-{middle_end-1} ({middle_rows} строк)")
            logger.info(f"   📍 Конец: последние {end_rows} строк")
            logger.info(f"   📊 Итого для анализа: {total_rows} строк")
            
            # Объединяем с разделителями
            sample_df = pd.concat([start_df, middle_df, end_df], ignore_index=True)
        
        # Конвертируем в текстовый формат
        table_text = ""
        
        # Добавляем заголовки столбцов с реальными названиями
        headers = [str(col) if pd.notna(col) and str(col).strip() else f"Col{i}" for i, col in enumerate(df.columns)]
        table_text += "COLUMNS: " + " | ".join(headers) + "\\n\\n"
        
        # Добавляем строки данных
        for idx, row in sample_df.iterrows():
            row_data = []
            for col in df.columns:
                value = str(row[col]).strip() if pd.notna(row[col]) else ""
                # Ограничиваем длину ячейки
                if len(value) > 50:
                    value = value[:47] + "..."
                row_data.append(value)
            
            table_text += f"Row{idx}: " + " | ".join(row_data) + "\\n"
        
        return table_text
    
    def _create_analysis_prompt(self, table_sample: str, context: str) -> str:
        """Создание промпта для анализа структуры таблицы"""
        
        prompt = f"""Извлеки ВСЕ товары из прайс-листа. Строки и столбцы нумеруются с нуля.

### BEGIN_TABLE
{table_sample}
### END_TABLE

КОНТЕКСТ: {context if context else "Прайс-лист товаров"}

АЛГОРИТМ ИЗВЛЕЧЕНИЯ:
1. ЗАГОЛОВКИ: Найди строку с заголовками столбцов. Ищи синонимы:
   - Товары: "Item", "Product", "Name", "Description", "Nama Barang", "Artikel"
   - Цены: "Price", "Harga", "Cost", "Amount", "Total", "Sum"
   - Единицы: "Unit", "UOM", "Qty", "Quantity", "Satuan", "Kemasan"
   - Размеры: "Size", "Volume", "Weight", "Ukuran", "Berat"

2. ФИЛЬТРАЦИЯ: Извлекай только строки где:
   - Есть название товара (не пустое)
   - Цена = ЧИСЛО (игнорируй "–", "N/A", пустые, текст)
   - Не служебная информация (контакты, итоги, категории без цен)

3. ОПРЕДЕЛЕНИЕ ПОЛЕЙ:
   - unit: значения часто повторяются (kg, pc, pkt, bottle, can, ml, l, g)
   - brand: первое слово ЗАГЛАВНЫМИ или Capitalized (но не unit)
   - size: числа + единицы измерения (200g, 1kg, 500ml)

ОГРАНИЧЕНИЯ:
- Максимум 500 товаров в ответе
- Не вставляй переносы строк внутри JSON строк
- Никаких комментариев в JSON

ПРИМЕР ВАЛИДНОГО JSON:
{{
  "table_analysis": {{
    "header_row": 10,
    "product_column": 1,
    "price_column": 3,
    "unit_column": 2,
    "brand_column": null,
    "size_column": null,
    "data_start_row": 12
  }},
  "extracted_products": [
    {{
      "row_index": 12,
      "product_name": "Basil Green Fresh",
      "brand": null,
      "price": 95000,
      "unit": "Kg",
      "size": null,
      "currency": "IDR",
      "source_supplier": null,
      "confidence": 0.95
    }}
  ]
}}

FALLBACK: Если не можешь найти заголовки, попробуй определить столбцы по содержимому и верни результат.

ФОРМАТ ОТВЕТА - только валидный JSON без markdown:"""
        
        return prompt
    
    def _query_chatgpt(self, prompt: str) -> Optional[Dict]:
        """Запрос к ChatGPT API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'gpt-4o',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'Ты эксперт по анализу прайс-листов и извлечению товарных данных из таблиц любой структуры. Твоя задача - найти ВСЕ товары с ценами и вернуть строго валидный JSON без комментариев и markdown. Игнорируй строки без числовых цен.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': self.max_tokens,
                'temperature': 0,
                'response_format': {'type': 'json_object'}
            }
            
            logger.info("🤖 Отправляем таблицу на анализ в ChatGPT...")
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                tokens_used = result.get('usage', {}).get('total_tokens', 0)
                
                logger.info(f"✅ ChatGPT проанализировал таблицу, токенов: {tokens_used}")
                
                # Парсим JSON ответ
                try:
                    parsed_response = json.loads(content)
                    return parsed_response
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Невалидный JSON от ChatGPT: {e}")
                    logger.debug(f"Ответ: {content}")
                    return None
            else:
                logger.error(f"❌ Ошибка ChatGPT API: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка запроса к ChatGPT: {e}")
            return None
    
    def _parse_chatgpt_response(self, response: Dict, original_df: pd.DataFrame) -> Dict:
        """Парсинг ответа ChatGPT и формирование результата"""
        try:
            analysis = response.get('table_analysis', {})
            extracted_products = response.get('extracted_products', [])
            
            # Валидируем и обогащаем данные
            validated_products = []
            
            for product in extracted_products:
                # Базовая валидация
                if not product.get('product_name') or not product.get('price'):
                    continue
                
                # Стандартизируем формат
                validated_product = {
                    'original_name': product.get('product_name', ''),
                    'standardized_name': product.get('product_name', ''),
                    'brand': product.get('brand', ''),
                    'size': product.get('size', ''),
                    'price': self._clean_price(product.get('price', 0)),
                    'unit': product.get('unit', 'pcs'),
                    'currency': product.get('currency', 'IDR'),
                    'category': 'General',
                    'confidence': product.get('confidence', 0.9),
                    'row_index': product.get('row_index', 0),
                    'source_supplier': product.get('source_supplier', ''),
                    'extraction_method': 'ai_analysis'
                }
                
                # Фильтруем по минимальным требованиям
                if (validated_product['price'] > 0 and 
                    len(validated_product['original_name']) > 2):
                    validated_products.append(validated_product)
            
            result = {
                'analysis': analysis,
                'products': validated_products,
                'ai_extraction_stats': {
                    'total_found': len(extracted_products),
                    'validated_products': len(validated_products),
                    'confidence': sum(p['confidence'] for p in validated_products) / len(validated_products) if validated_products else 0,
                    'extraction_method': 'ai_powered'
                }
            }
            
            logger.info(f"🎯 AI извлечение: {len(validated_products)} товаров из {len(original_df)} строк")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга ответа ChatGPT: {e}")
            return None
    
    def extract_products_with_ai(self, df: pd.DataFrame, context: str = "") -> Dict[str, Any]:
        """
        Основная функция извлечения товаров с помощью AI
        """
        if not self.api_key:
            return {'error': 'OpenAI API key не установлен'}
        
        # Анализируем структуру через AI
        ai_result = self.analyze_table_structure(df, context)
        
        if ai_result and ai_result.get('products'):
            return {
                'file_type': 'ai_parsed',
                'supplier': {'name': 'AI_Extracted', 'confidence': 0.9},
                'products': ai_result['products'],
                'extraction_stats': ai_result.get('ai_extraction_stats', {}),
                'table_analysis': ai_result.get('analysis', {})
            }
        else:
            return {'error': 'AI не смог проанализировать таблицу'}
    
    def is_available(self) -> bool:
        """Проверка доступности AI парсера"""
        return bool(self.api_key)