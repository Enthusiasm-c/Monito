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
        self.batch_size = 15  # Уменьшаем до 15 товаров для быстрой обработки
        self.max_tokens = 4000  # Увеличиваем для качественного ответа на 20 товаров
        self.delay_between_requests = 0.2  # Минимальная задержка между запросами
        self.assistant_id = "asst_MNWPJzAGJC7TrZ8LKTDnJLzr"  # ID созданного ассистента
        self.request_timeout = 120  # Увеличиваем timeout до 120 секунд для максимальной стабильности
        
    def split_products_into_batches(self, products: List[Dict], batch_size: int = None) -> List[List[Dict]]:
        """Разделение товаров на пакеты для обработки"""
        if batch_size is None:
            batch_size = self.batch_size
        
        batches = []
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            batches.append(batch)
        
        logger.info(f"📦 Разделено {len(products)} товаров на {len(batches)} пакетов по {batch_size} товаров")
        for i, batch in enumerate(batches):
            logger.debug(f"  Пакет {i+1}: {len(batch)} товаров")
        return batches
    
    def estimate_tokens(self, text: str) -> int:
        """Приблизительная оценка количества токенов"""
        # Примерно 4 символа = 1 токен для английского текста
        # Для русского может быть больше
        return len(text) // 3
    
    def optimize_batch_size(self, products: List[Dict]) -> int:
        """Оптимизация размера пакета для быстрой обработки"""
        if not products:
            return self.batch_size
        
        # Анализируем средний размер названий товаров
        avg_name_length = sum(len(p.get('original_name', '')) for p in products[:10]) / min(10, len(products))
        
        # Приоритет на скорость: меньшие пакеты = быстрее обработка
        if avg_name_length > 50:  # Очень длинные названия
            return 10  # Очень маленькие пакеты для быстроты
        elif avg_name_length > 30:  # Длинные названия
            return 12  # Маленькие пакеты
        elif avg_name_length > 20:  # Средние названия
            return self.batch_size  # 15 товаров (базовый размер)
        else:  # Короткие названия
            return min(self.batch_size + 5, 20)  # До 20 товаров максимум
    
    async def process_products_batch(self, products: List[Dict], supplier_name: str, batch_index: int = 0) -> Optional[Dict]:
        """Обработка одного пакета товаров через ChatGPT"""
        try:
            # Оптимизированная подготовка данных для ChatGPT
            products_list = []
            for i, product in enumerate(products, 1):
                products_list.append(f"{i}. {product['original_name']} | {product['price']} {product.get('unit', 'pcs')}")
            
            products_text = "\n".join(products_list)
            
            # Проверяем размер запроса
            estimated_tokens = self.estimate_tokens(products_text)
            logger.debug(f"📏 Пакет {batch_index + 1}: размер {estimated_tokens} токенов (лимит: {self.max_tokens * 0.7})")
            
            if estimated_tokens > self.max_tokens * 0.7:  # Увеличиваем лимит до 70%
                logger.warning(f"⚠️ Пакет {batch_index + 1} слишком большой ({estimated_tokens} токенов), автоматически разделяем на 2 части")
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
            
            # Оптимизированный промпт для быстрой обработки
            prompt = f"""Быстро стандартизируй {len(products)} товаров в JSON.

ТОВАРЫ:
{products_text}

JSON ОТВЕТ:
{{
  "products": [
    {{
      "original_name": "исходное название",
      "standardized_name": "English Name",
      "brand": "Brand",
      "size": "размер",
      "unit": "единица", 
      "price": цена_числом,
      "currency": "IDR",
      "category": "категория"
    }}
  ]
}}

Категории: Food, Electronics, Clothing, Home, Health, Sports, Books, Auto, General
Единицы: g, kg, ml, l, pcs, pack, box, can, bottle"""

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data_payload = {
                'model': 'gpt-4o-mini',  # Используем mini для скорости
                'messages': [
                    {
                        'role': 'system',
                        'content': 'Быстро стандартизируй товары. Только JSON.'
                    },
                    {
                        'role': 'user', 
                        'content': prompt
                    }
                ],
                'max_tokens': self.max_tokens,
                'temperature': 0,  # Детерминированные ответы
                'response_format': {'type': 'json_object'}
            }
            
            logger.info(f"🚀 Отправка пакета {batch_index + 1} с {len(products)} товарами в ChatGPT (размер: {estimated_tokens} токенов)...")
            
            # Быстрые попытки с короткими таймаутами
            max_retries = 2  # Уменьшаем количество попыток
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        'https://api.openai.com/v1/chat/completions',
                        headers=headers,
                        json=data_payload,
                        timeout=self.request_timeout  # Используем быстрый timeout
                    )
                    break
                except requests.exceptions.Timeout:
                    wait_time = 2 + attempt  # Быстрые повторы: 2с, 3с
                    logger.warning(f"⏰ Быстрый таймаут пакета {batch_index + 1}, попытка {attempt + 1}/{max_retries}. Ожидание {wait_time}с...")
                    if attempt == max_retries - 1:
                        logger.error(f"❌ Пакет {batch_index + 1} отброшен после {max_retries} быстрых попыток")
                        return None
                    time.sleep(wait_time)
                except Exception as e:
                    logger.error(f"❌ Сетевая ошибка пакета {batch_index + 1} (попытка {attempt + 1}/{max_retries}): {type(e).__name__}: {e}")
                    if attempt == max_retries - 1:
                        logger.error(f"❌ Пакет {batch_index + 1} отброшен из-за сетевой ошибки")
                        return None
                    time.sleep(1)  # Быстрое восстановление
            
            logger.debug(f"📡 HTTP ответ пакета {batch_index + 1}: код {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    tokens_used = result.get('usage', {}).get('total_tokens', 0)
                    logger.debug(f"✅ Получен ответ для пакета {batch_index + 1}: {len(content)} символов, {tokens_used} токенов")
                except Exception as e:
                    logger.error(f"❌ ОШИБКА ПАРСИНГА JSON ответа API для пакета {batch_index + 1}: {e}")
                    return None
                
                # Улучшенная очистка ответа
                content = self.clean_chatgpt_response(content)
                
                # Парсинг JSON с улучшенной обработкой
                logger.debug(f"🔍 Парсинг JSON ответа пакета {batch_index + 1}...")
                try:
                    parsed_data = json.loads(content)
                    logger.debug(f"✅ JSON успешно распарсен для пакета {batch_index + 1}")
                    
                    # Валидация и обогащение данных
                    if 'products' in parsed_data:
                        processed_products = []
                        
                        invalid_products = 0
                        for i, product in enumerate(parsed_data['products']):
                            # Базовая валидация
                            if not product.get('standardized_name') and not product.get('name'):
                                invalid_products += 1
                                logger.warning(f"⚠️ Пакет {batch_index + 1}, товар {i+1}: БЕЗ НАЗВАНИЯ - пропускаем. Данные: {product}")
                                continue
                            
                            # Стандартизация полей
                            standardized_product = {
                                'original_name': product.get('original_name', products[i].get('original_name', '') if i < len(products) else ''),
                                'standardized_name': product.get('standardized_name') or product.get('name', ''),
                                'brand': product.get('brand', 'Unknown'),
                                'size': product.get('size', ''),
                                'unit': product.get('unit', 'pcs'),
                                'price': product.get('price', products[i].get('price', 0) if i < len(products) else 0),
                                'currency': product.get('currency', 'IDR'),
                                'category': product.get('category', 'General'),
                                'confidence': 0.95  # Высокая уверенность для обработанных ChatGPT товаров
                            }
                            
                            processed_products.append(standardized_product)
                        
                        parsed_data['products'] = processed_products
                        processed_count = len(processed_products)
                        input_count = len(products)
                        loss_count = input_count - processed_count
                        
                        if invalid_products > 0:
                            logger.warning(f"⚠️ Пакет {batch_index + 1}: {invalid_products} товаров БЕЗ НАЗВАНИЙ отброшено")
                        
                        if loss_count > 0:
                            logger.warning(f"⚠️ Пакет {batch_index + 1}: ПОТЕРЯ {loss_count} товаров ({loss_count/input_count:.1%})")
                        
                        logger.info(f"✅ Пакет {batch_index + 1}: обработано {processed_count}/{input_count} товаров (потери: {loss_count}), токенов: {tokens_used}")
                        
                        return parsed_data
                    else:
                        logger.error(f"❌ КРИТИЧНО: Нет поля 'products' в ответе пакета {batch_index + 1}")
                        logger.error(f"📋 Полученная структура: {list(parsed_data.keys()) if isinstance(parsed_data, dict) else type(parsed_data)}")
                        return None
                    
                except json.JSONDecodeError as e:
                    logger.error(f"❌ КРИТИЧНО: Невалидный JSON в пакете {batch_index + 1}: {e}")
                    logger.error(f"📋 Проблемный ответ (первые 500 символов): {content[:500]}...")
                    logger.error(f"📋 Размер ответа: {len(content)} символов")
                    return None
                    
            else:
                logger.error(f"❌ КРИТИЧНО: Ошибка ChatGPT API для пакета {batch_index + 1}")
                logger.error(f"📡 HTTP код: {response.status_code}")
                logger.error(f"📋 Ответ API: {response.text[:500]}...")
                
                # Специальная обработка известных ошибок
                if response.status_code == 429:
                    logger.error(f"🚫 Rate limiting - слишком много запросов")
                elif response.status_code == 400:
                    logger.error(f"🚫 Неверный запрос - возможно превышен лимит токенов")
                elif response.status_code == 401:
                    logger.error(f"🚫 Ошибка авторизации - проверьте API ключ")
                elif response.status_code >= 500:
                    logger.error(f"🚫 Серверная ошибка OpenAI")
                
                return None
                
        except Exception as e:
            logger.error(f"❌ КРИТИЧНО: Неожиданная ошибка обработки пакета {batch_index + 1}: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"📋 Стек ошибки: {traceback.format_exc()}")
            return None
    
    async def _process_batch_with_timing(self, batch: List[Dict], supplier_name: str, batch_index: int) -> Optional[Dict]:
        """Обработка пакета с измерением времени для параллельной обработки"""
        start_time = time.time()
        logger.info(f"🔄 Параллельная обработка пакета {batch_index + 1}/{batch_index + 1} ({len(batch)} товаров)...")
        
        try:
            result = await self.process_products_batch(batch, supplier_name, batch_index)
            processing_time = time.time() - start_time
            
            if result:
                result['processing_time'] = processing_time
                return result
            else:
                logger.warning(f"⚠️ Пакет {batch_index + 1} вернул None за {processing_time:.1f}с")
                return None
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Ошибка в параллельном пакете {batch_index + 1} за {processing_time:.1f}с: {e}")
            raise e
    
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
            logger.info(f"📊 Оптимальный размер пакета: {optimal_batch_size} товаров")
            
            all_processed_products = []
            successful_batches = 0
            failed_batches = 0
            total_tokens = 0
            failed_batch_details = []
            
            # ПАРАЛЛЕЛЬНАЯ ОБРАБОТКА ПАКЕТОВ для максимальной скорости
            logger.info(f"🚀 Запускаем параллельную обработку {len(batches)} пакетов...")
            
            # Создаем задачи для параллельного выполнения
            batch_tasks = []
            for i, batch in enumerate(batches):
                task = asyncio.create_task(
                    self._process_batch_with_timing(batch, supplier_name, i)
                )
                batch_tasks.append(task)
                
                # Небольшая задержка между запуском задач чтобы не перегрузить API
                if i > 0:
                    await asyncio.sleep(self.delay_between_requests)
            
            # Ждем завершения всех пакетов параллельно
            logger.info(f"⏳ Ожидаем завершения {len(batch_tasks)} параллельных задач...")
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Обрабатываем результаты
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    failed_batches += 1
                    failure_reason = f"{type(result).__name__}: {result}"
                    failed_batch_details.append(f"Пакет {i + 1}: {failure_reason}")
                    logger.error(f"❌ Пакет {i + 1} ПРОВАЛЕН: {failure_reason}")
                elif result and 'products' in result:
                    batch_products = result['products']
                    all_processed_products.extend(batch_products)
                    successful_batches += 1
                    
                    # Учитываем токены
                    total_tokens += self.estimate_tokens(str(result))
                    
                    batch_time = result.get('processing_time', 0)
                    logger.info(f"✅ Пакет {i + 1} УСПЕШНО: {len(batch_products)} товаров за {batch_time:.1f}с")
                else:
                    failed_batches += 1
                    failure_reason = "Нет результата или нет products в ответе"
                    failed_batch_details.append(f"Пакет {i + 1}: {failure_reason}")
                    logger.error(f"❌ Пакет {i + 1} ПРОВАЛЕН: {failure_reason}")
            
            # Детальная статистика потерь
            total_input_products = len(products)
            total_output_products = len(all_processed_products)
            loss_count = total_input_products - total_output_products
            loss_percentage = (loss_count / total_input_products * 100) if total_input_products > 0 else 0
            
            logger.info(f"📊 ИТОГОВАЯ СТАТИСТИКА ПАКЕТНОЙ ОБРАБОТКИ:")
            logger.info(f"   📦 Успешных пакетов: {successful_batches}/{len(batches)} ({successful_batches/len(batches)*100:.1f}%)")
            logger.info(f"   ❌ Провалившихся пакетов: {failed_batches}/{len(batches)} ({failed_batches/len(batches)*100:.1f}%)")
            logger.info(f"   📝 Товаров на входе: {total_input_products}")
            logger.info(f"   ✅ Товаров на выходе: {total_output_products}")
            logger.info(f"   📉 ПОТЕРИ: {loss_count} товаров ({loss_percentage:.1f}%)")
            logger.info(f"   🪙 Общий расход токенов: {total_tokens}")
            
            if failed_batch_details:
                logger.warning(f"🔍 ДЕТАЛИ ПРОВАЛОВ:")
                for detail in failed_batch_details:
                    logger.warning(f"   • {detail}")
            
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