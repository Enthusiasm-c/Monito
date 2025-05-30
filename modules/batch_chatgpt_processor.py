#!/usr/bin/env python3
"""
Пакетная обработка больших объемов данных через ChatGPT
"""

import os
import json
import time
import asyncio
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class BatchChatGPTProcessor:
    """Пакетная обработка данных через ChatGPT"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.batch_size = 8  # Товаров за один запрос (уменьшено из-за зависаний)
        self.max_tokens = 1000  # Максимум токенов на запрос (для ассистента)
        self.delay_between_requests = 2  # Возвращаем задержки для стабильности
        self.assistant_id = "asst_MNWPJzAGJC7TrZ8LKTDnJLzr"  # ID созданного ассистента
        
    def split_products_into_batches(self, products: List[Dict], batch_size: int = None) -> List[List[Dict]]:
        """Разделение товаров на пакеты для обработки"""
        if batch_size is None:
            batch_size = self.batch_size
        
        batches = []
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            batches.append(batch)
        
        logger.info(f"Разделено {len(products)} товаров на {len(batches)} пакетов по {batch_size} товаров")
        return batches
    
    def estimate_tokens(self, text: str) -> int:
        """Приблизительная оценка количества токенов"""
        # Примерно 4 символа = 1 токен для английского текста
        # Для русского может быть больше
        return len(text) // 3
    
    def optimize_batch_size(self, products: List[Dict]) -> int:
        """Оптимизация размера пакета в зависимости от сложности данных"""
        if not products:
            return self.batch_size
        
        # Анализируем средний размер названий товаров
        avg_name_length = sum(len(p.get('original_name', '')) for p in products[:10]) / min(10, len(products))
        
        # Всегда используем консервативный размер для стабильности
        if avg_name_length > 30:  # Длинные названия
            return max(self.batch_size // 2, 4)  # Минимум 4 товара
        elif avg_name_length > 20:  # Средние названия
            return self.batch_size  # 8 товаров
        else:  # Короткие названия
            return min(self.batch_size + 2, 10)  # Максимум 10
    
    async def process_products_batch(self, products: List[Dict], supplier_name: str, batch_index: int = 0) -> Optional[Dict]:
        """Обработка одного пакета товаров через ChatGPT"""
        try:
            # Подготовка данных для ChatGPT
            products_text = ""
            for i, product in enumerate(products, 1):
                products_text += f"{i}. {product['original_name']} | {product['price']} | {product.get('unit', 'pcs')}\n"
            
            # Проверяем размер запроса
            estimated_tokens = self.estimate_tokens(products_text)
            if estimated_tokens > self.max_tokens * 0.5:  # Консервативный лимит - 50% от максимума
                logger.warning(f"Пакет {batch_index} слишком большой ({estimated_tokens} токенов), разделяем")
                # Рекурсивно разделяем пакет пополам
                mid = len(products) // 2
                batch1 = await self.process_products_batch(products[:mid], supplier_name, batch_index)
                batch2 = await self.process_products_batch(products[mid:], supplier_name, batch_index)
                
                if batch1 and batch2:
                    # Объединяем результаты
                    combined_products = batch1.get('products', []) + batch2.get('products', [])
                    return {
                        'supplier': batch1.get('supplier', {}),
                        'products': combined_products,
                        'data_quality': batch1.get('data_quality', {})
                    }
                return batch1 or batch2
            
            prompt = f"""Товары:
{products_text}

JSON: {{"products": [{{"name": "English name", "brand": "brand", "size": "size", "unit": "g/ml/kg/l/pcs", "price": number, "currency": "IDR"}}]}}"""

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data_payload = {
                'model': 'gpt-4o',  # Используем GPT-4o (самая новая модель)
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 1000,  # Меньше токенов для простого ответа
                'temperature': 0
            }
            
            logger.info(f"Отправка пакета {batch_index + 1} с {len(products)} товарами в ChatGPT...")
            
            # Попытки с повторами
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        'https://api.openai.com/v1/chat/completions',
                        headers=headers,
                        json=data_payload,
                        timeout=25  # Увеличенный timeout для стабильности
                    )
                    break
                except requests.exceptions.Timeout:
                    logger.warning(f"⏰ Таймаут пакета {batch_index + 1}, попытка {attempt + 1}/{max_retries}")
                    if attempt == max_retries - 1:
                        logger.error(f"❌ Все попытки исчерпаны для пакета {batch_index + 1}")
                        return None
                    time.sleep(3 ** attempt)  # Более длинная экспоненциальная задержка
                except Exception as e:
                    logger.error(f"❌ Ошибка сети для пакета {batch_index + 1}: {e}")
                    if attempt == max_retries - 1:
                        return None
                    time.sleep(2)
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                tokens_used = result.get('usage', {}).get('total_tokens', 0)
                
                # Улучшенная очистка ответа
                content = self.clean_chatgpt_response(content)
                
                # Парсинг JSON
                try:
                    parsed_data = json.loads(content)
                    
                    # Адаптируем новый формат к старому
                    if 'products' in parsed_data:
                        for product in parsed_data['products']:
                            # Добавляем недостающие поля для совместимости
                            if 'name' in product and 'standardized_name' not in product:
                                product['standardized_name'] = product['name']
                                product['original_name'] = product.get('name', '')
                            if 'confidence' not in product:
                                product['confidence'] = 0.9
                            if 'category' not in product:
                                product['category'] = 'general'
                    
                    processed_count = len(parsed_data.get('products', []))
                    
                    logger.info(f"✅ Пакет {batch_index + 1}: обработано {processed_count} товаров, токенов: {tokens_used}")
                    
                    return parsed_data
                    
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Невалидный JSON в пакете {batch_index + 1}: {e}")
                    logger.debug(f"Проблемный ответ: {content[:500]}...")
                    return None
                    
            else:
                logger.error(f"❌ Ошибка ChatGPT API для пакета {batch_index + 1}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки пакета {batch_index + 1}: {e}")
            return None
    
    def clean_chatgpt_response(self, content: str) -> str:
        """Улучшенная очистка ответа ChatGPT"""
        content = content.strip()
        
        # Удаление markdown блоков кода
        if content.startswith('```json'):
            content = content[7:]
        elif content.startswith('```'):
            content = content[3:]
            
        if content.endswith('```'):
            content = content[:-3]
        
        content = content.strip()
        
        # Поиск JSON блока в тексте
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        
        # Удаление возможных комментариев
        lines = content.split('\n')
        clean_lines = []
        for line in lines:
            # Пропускаем строки с комментариями
            if not line.strip().startswith('//') and not line.strip().startswith('#'):
                clean_lines.append(line)
        
        return '\n'.join(clean_lines)
    
    async def process_all_products(self, products: List[Dict], supplier_name: str) -> Dict[str, Any]:
        """Обработка всех товаров с автоматическим разделением на пакеты"""
        try:
            if not products:
                return {'error': 'Нет товаров для обработки'}
            
            # Оптимизируем размер пакета
            optimal_batch_size = self.optimize_batch_size(products)
            
            # Разделяем на пакеты
            batches = self.split_products_into_batches(products, optimal_batch_size)
            
            logger.info(f"🚀 Начинаем пакетную обработку {len(products)} товаров в {len(batches)} пакетах")
            
            all_processed_products = []
            successful_batches = 0
            total_tokens = 0
            
            # Обрабатываем каждый пакет
            for i, batch in enumerate(batches):
                try:
                    # Задержка между запросами
                    if i > 0:
                        await asyncio.sleep(self.delay_between_requests)
                    
                    batch_result = await self.process_products_batch(batch, supplier_name, i)
                    
                    if batch_result and 'products' in batch_result:
                        all_processed_products.extend(batch_result['products'])
                        successful_batches += 1
                        
                        # Учитываем токены (приблизительно)
                        total_tokens += self.estimate_tokens(str(batch_result))
                    else:
                        logger.warning(f"⚠️ Пакет {i + 1} не обработан, пропускаем")
                        
                except Exception as e:
                    logger.error(f"❌ Критическая ошибка в пакете {i + 1}: {e}")
                    continue
            
            # Формируем итоговый результат
            if all_processed_products:
                result = {
                    'supplier': {
                        'name': supplier_name,
                        'confidence': 0.9
                    },
                    'products': all_processed_products,
                    'data_quality': {
                        'extraction_confidence': successful_batches / len(batches),
                        'source_clarity': 'high' if successful_batches > len(batches) * 0.8 else 'medium',
                        'potential_errors': [] if successful_batches == len(batches) else [f'Не обработано {len(batches) - successful_batches} пакетов']
                    },
                    'processing_stats': {
                        'total_input_products': len(products),
                        'total_output_products': len(all_processed_products),
                        'successful_batches': successful_batches,
                        'total_batches': len(batches),
                        'estimated_tokens': total_tokens,
                        'success_rate': len(all_processed_products) / len(products) if products else 0
                    }
                }
                
                logger.info(f"🎉 Пакетная обработка завершена: {len(all_processed_products)}/{len(products)} товаров обработано")
                return result
            else:
                # Fallback: если ChatGPT полностью не работает, возвращаем базовую обработку
                logger.warning("🔄 ChatGPT обработка не удалась, используем fallback")
                fallback_products = []
                for product in products:
                    fallback_product = {
                        'original_name': product.get('original_name', ''),
                        'standardized_name': product.get('original_name', ''),
                        'brand': 'unknown',
                        'price': product.get('price', 0),
                        'unit': product.get('unit', 'pcs'),
                        'category': 'general',
                        'confidence': 0.6  # Низкая уверенность без ChatGPT
                    }
                    fallback_products.append(fallback_product)
                
                return {
                    'supplier': {'name': supplier_name, 'confidence': 0.7},
                    'products': fallback_products,
                    'data_quality': {
                        'extraction_confidence': 0.6,
                        'source_clarity': 'low',
                        'potential_errors': ['Обработано без ChatGPT - базовое качество']
                    },
                    'processing_stats': {
                        'total_input_products': len(products),
                        'total_output_products': len(fallback_products),
                        'successful_batches': 0,
                        'total_batches': len(batches),
                        'estimated_tokens': 0,
                        'success_rate': 1.0,
                        'fallback_used': True
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ Критическая ошибка пакетной обработки: {e}")
            return {'error': str(e)}