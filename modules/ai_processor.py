import json
import time
import logging
import asyncio
from typing import Dict, List, Optional, Any
from openai import AsyncOpenAI

from config import GPT_CONFIG, OPENAI_API_KEY, QUALITY_THRESHOLDS
from modules.utils import validate_price, clean_text

logger = logging.getLogger(__name__)

class AIProcessor:
    """Процессор для стандартизации данных через GPT-4"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = GPT_CONFIG['MODEL']
        
    async def process_data(self, extracted_data: Dict[str, Any], file_type: str = 'unknown') -> Optional[Dict[str, Any]]:
        """
        Основной метод обработки данных через GPT-4
        Стандартизирует названия товаров, определяет поставщика, приводит единицы к стандарту
        """
        try:
            logger.info(f"Начинаю обработку данных через GPT-4 (файл типа: {file_type})")
            
            # Подготовка данных для GPT
            prompt = self._build_standardization_prompt(extracted_data, file_type)
            
            # Вызов GPT с retry логикой
            response = await self._call_gpt_with_retry(prompt)
            
            if not response:
                logger.error("Не удалось получить ответ от GPT")
                return None
            
            # Парсинг и валидация ответа
            standardized_data = self._parse_gpt_response(response)
            
            if not standardized_data:
                logger.error("Не удалось распарсить ответ GPT")
                return None
            
            # Пост-обработка и валидация
            validated_data = self._validate_and_clean_data(standardized_data)
            
            logger.info(f"Успешно обработано {len(validated_data.get('products', []))} товаров")
            return validated_data
            
        except Exception as e:
            logger.error(f"Ошибка обработки данных через GPT: {e}")
            return None

    def _build_standardization_prompt(self, data: Dict[str, Any], file_type: str) -> str:
        """Построение промпта для GPT на основе извлеченных данных"""
        
        products = data.get('products', [])
        extraction_method = data.get('extraction_method', 'unknown')
        supplier_hint = data.get('supplier', {})
        
        # Ограничиваем количество товаров для одного запроса
        products_sample = products[:50] if len(products) > 50 else products
        
        # Подготовка данных о товарах
        products_text = ""
        for i, product in enumerate(products_sample, 1):
            products_text += f"{i}. {product.get('original_name', '')} | {product.get('price', '')} | {product.get('unit', '')} | источник: {product.get('source', '')}\n"
        
        # Информация о качестве данных
        quality_info = ""
        if file_type == 'pdf':
            quality_info = f"""
ОСОБЕННОСТИ PDF ДАННЫХ:
- Метод извлечения: {extraction_method}
- Возможны ошибки OCR при сканированных документах
- Некоторые символы могут быть распознаны неверно (0↔O, 1↔l↔I, 5↔S, 6↔G)
- Названия товаров могут быть разорваны или содержать артефакты
"""
        
        # Подсказка о поставщике
        supplier_hint_text = ""
        if supplier_hint:
            supplier_hint_text = f"НАЙДЕННАЯ ИНФОРМАЦИЯ О ПОСТАВЩИКЕ: {json.dumps(supplier_hint, ensure_ascii=False)}"
        
        prompt = f"""Ты эксперт по стандартизации товарных данных. Проанализируй данные из прайс-листа и выполни следующие задачи:

ПРАВИЛА СТАНДАРТИЗАЦИИ:
1. ТОВАРЫ: Переведи все названия товаров на английский язык, используя стандартные торговые наименования
2. ПОСТАВЩИК: Найди и извлеки название компании-поставщика и контактную информацию
3. ЕДИНИЦЫ ИЗМЕРЕНИЯ: Приведи к стандарту (kg, pcs, m, l, box, pack, ton, lb)
4. ЦЕНЫ: Определи валюту и убедись что цены числовые
5. КАЧЕСТВО: Оцени уверенность в каждом элементе данных

ВХОДНЫЕ ДАННЫЕ:
Источник: {file_type} файл
{quality_info}
{supplier_hint_text}

ТОВАРЫ ({len(products_sample)} из {len(products)}):
{products_text}

ФОРМАТ ОТВЕТА (СТРОГО JSON):
{{
  "supplier": {{
    "name": "Company Name",
    "contact": "phone/email если найден",
    "confidence": 0.95
  }},
  "products": [
    {{
      "original_name": "исходное название",
      "standardized_name": "Standard Product Name EN", 
      "price": 100.50,
      "unit": "kg",
      "currency": "USD",
      "confidence": 0.95,
      "category": "категория товара если определима"
    }}
  ],
  "data_quality": {{
    "source_clarity": "high/medium/low",
    "extraction_confidence": 0.85,
    "potential_errors": ["список возможных ошибок"],
    "total_products_processed": {len(products_sample)},
    "valid_products": 0
  }},
  "processing_notes": "дополнительные заметки о процессе обработки"
}}

ИНСТРУКЦИИ ПО ОБРАБОТКЕ:
- Если товар неопределенный, используй максимально близкое стандартное название
- Сохраняй оригинальные названия для трекинга
- Игнорируй пустые строки и технические записи
- Для PDF данных: исправляй очевидные ошибки OCR
- Стандартизируй единицы: кг→kg, шт→pcs, литр→l, метр→m
- Определи наиболее вероятную валюту на основе контекста
- Оценивай уверенность в каждом извлеченном элементе
- Отмечай сомнительные данные в potential_errors

СПЕЦИАЛЬНЫЕ СЛУЧАИ:
- Если цена выглядит нереалистично (слишком высоко/низко), отметь это
- Если название содержит артефакты OCR, попытайся восстановить
- Группируй похожие товары в категории (food, electronics, materials, etc.)
- При низкой уверенности укажи это в confidence < 0.7

ВАЖНО: Отвечай ТОЛЬКО валидным JSON без дополнительного текста!"""

        return prompt

    async def _call_gpt_with_retry(self, prompt: str) -> Optional[str]:
        """Вызов GPT с retry логикой и обработкой ошибок"""
        
        for attempt in range(GPT_CONFIG['RETRY_ATTEMPTS']):
            try:
                logger.info(f"Отправка запроса к GPT (попытка {attempt + 1})")
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system", 
                            "content": "Ты эксперт по стандартизации коммерческих данных. Отвечай только валидным JSON."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    max_tokens=GPT_CONFIG['MAX_TOKENS'],
                    temperature=GPT_CONFIG['TEMPERATURE'],
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                
                if content:
                    logger.info(f"Получен ответ от GPT (длина: {len(content)} символов)")
                    return content
                else:
                    logger.warning("Пустой ответ от GPT")
                    
            except Exception as e:
                logger.warning(f"Ошибка при вызове GPT (попытка {attempt + 1}): {e}")
                
                if attempt < GPT_CONFIG['RETRY_ATTEMPTS'] - 1:
                    delay = GPT_CONFIG['RETRY_DELAY'] * (2 ** attempt)  # Экспоненциальная задержка
                    logger.info(f"Ожидание {delay} сек перед повторной попыткой")
                    await asyncio.sleep(delay)
                else:
                    logger.error("Исчерпаны все попытки вызова GPT")
        
        return None

    def _parse_gpt_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Парсинг и валидация ответа от GPT"""
        try:
            # Очистка ответа от возможных артефактов
            response = response.strip()
            
            # Поиск JSON блока если есть дополнительный текст
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
            else:
                json_str = response
            
            # Парсинг JSON
            data = json.loads(json_str)
            
            # Базовая валидация структуры
            required_fields = ['supplier', 'products', 'data_quality']
            for field in required_fields:
                if field not in data:
                    logger.warning(f"Отсутствует обязательное поле: {field}")
                    return None
            
            # Валидация товаров
            if not isinstance(data['products'], list):
                logger.warning("Поле products должно быть списком")
                return None
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON от GPT: {e}")
            logger.debug(f"Ответ GPT: {response[:500]}...")
            return None
        except Exception as e:
            logger.error(f"Ошибка обработки ответа GPT: {e}")
            return None

    def _validate_and_clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация и очистка данных после обработки GPT"""
        
        # Валидация поставщика
        supplier = data.get('supplier', {})
        if isinstance(supplier, dict):
            # Очистка названия поставщика
            if 'name' in supplier:
                supplier['name'] = clean_text(str(supplier['name']))
            
            # Валидация confidence
            if 'confidence' not in supplier:
                supplier['confidence'] = 0.5
            else:
                supplier['confidence'] = max(0.0, min(1.0, float(supplier.get('confidence', 0.5))))
        
        # Валидация и очистка товаров
        products = data.get('products', [])
        cleaned_products = []
        
        for product in products:
            if not isinstance(product, dict):
                continue
            
            # Очистка и валидация названий
            original_name = clean_text(str(product.get('original_name', '')))
            standardized_name = clean_text(str(product.get('standardized_name', '')))
            
            # Пропускаем товары с пустыми названиями
            if len(original_name) < QUALITY_THRESHOLDS['MIN_PRODUCT_NAME_LENGTH']:
                continue
            
            # Валидация цены
            try:
                price = float(product.get('price', 0))
                if not validate_price(price):
                    continue
            except (ValueError, TypeError):
                continue
            
            # Стандартизация единиц измерения
            unit = self._standardize_unit(str(product.get('unit', 'pcs')))
            
            # Валидация валюты
            currency = self._standardize_currency(str(product.get('currency', 'USD')))
            
            # Валидация confidence
            confidence = max(0.0, min(1.0, float(product.get('confidence', 0.5))))
            
            # Создание очищенного товара
            cleaned_product = {
                'original_name': original_name,
                'standardized_name': standardized_name or original_name,
                'price': price,
                'unit': unit,
                'currency': currency,
                'confidence': confidence,
                'category': clean_text(str(product.get('category', 'general')))
            }
            
            cleaned_products.append(cleaned_product)
        
        # Обновление статистики качества
        data_quality = data.get('data_quality', {})
        data_quality['valid_products'] = len(cleaned_products)
        data_quality['total_products_processed'] = len(products)
        
        if len(products) > 0:
            validation_rate = len(cleaned_products) / len(products)
            # Корректировка confidence на основе процента валидных товаров
            original_confidence = data_quality.get('extraction_confidence', 0.5)
            data_quality['extraction_confidence'] = original_confidence * validation_rate
        
        # Обновление потенциальных ошибок
        potential_errors = data_quality.get('potential_errors', [])
        
        failed_products = len(products) - len(cleaned_products)
        if failed_products > 0:
            potential_errors.append(f"Не удалось валидировать {failed_products} товаров")
        
        if len(cleaned_products) == 0:
            potential_errors.append("Не найдено валидных товаров")
        
        data_quality['potential_errors'] = potential_errors
        
        # Сборка финального результата
        result = {
            'supplier': supplier,
            'products': cleaned_products,
            'data_quality': data_quality,
            'processing_notes': data.get('processing_notes', ''),
            'timestamp': time.time()
        }
        
        return result

    def _standardize_unit(self, unit: str) -> str:
        """Стандартизация единиц измерения"""
        unit = unit.lower().strip()
        
        # Словарь соответствий
        unit_mapping = {
            # Вес
            'кг': 'kg', 'килограмм': 'kg', 'kg': 'kg', 'kilogram': 'kg',
            'г': 'g', 'грамм': 'g', 'gram': 'g', 'g': 'g',
            'тонна': 'ton', 'т': 'ton', 'ton': 'ton', 'tonne': 'ton',
            'фунт': 'lb', 'lb': 'lb', 'pound': 'lb',
            
            # Объем
            'л': 'l', 'литр': 'l', 'liter': 'l', 'litre': 'l', 'l': 'l',
            'мл': 'ml', 'миллилитр': 'ml', 'ml': 'ml', 'milliliter': 'ml',
            'галлон': 'gal', 'gal': 'gal', 'gallon': 'gal',
            
            # Длина
            'м': 'm', 'метр': 'm', 'meter': 'm', 'metre': 'm', 'm': 'm',
            'см': 'cm', 'сантиметр': 'cm', 'cm': 'cm', 'centimeter': 'cm',
            'мм': 'mm', 'миллиметр': 'mm', 'mm': 'mm', 'millimeter': 'mm',
            
            # Штуки
            'шт': 'pcs', 'штука': 'pcs', 'piece': 'pcs', 'pcs': 'pcs', 'pc': 'pcs',
            'единица': 'pcs', 'unit': 'pcs', 'each': 'pcs',
            
            # Упаковка
            'упаковка': 'pack', 'pack': 'pack', 'package': 'pack',
            'коробка': 'box', 'box': 'box', 'carton': 'box',
            'мешок': 'bag', 'bag': 'bag', 'sack': 'bag',
            
            # Площадь
            'кв.м': 'sqm', 'м2': 'sqm', 'sqm': 'sqm', 'square meter': 'sqm'
        }
        
        return unit_mapping.get(unit, 'pcs')  # По умолчанию штуки

    def _standardize_currency(self, currency: str) -> str:
        """Стандартизация валют"""
        currency = currency.upper().strip()
        
        # Словарь соответствий валют
        currency_mapping = {
            'USD': 'USD', 'ДОЛЛАР': 'USD', 'DOLLAR': 'USD', '$': 'USD',
            'EUR': 'EUR', 'ЕВРО': 'EUR', 'EURO': 'EUR', '€': 'EUR',
            'RUB': 'RUB', 'РУБЛЬ': 'RUB', 'РУБ': 'RUB', '₽': 'RUB',
            'CNY': 'CNY', 'ЮАНЬ': 'CNY', 'YUAN': 'CNY', '¥': 'CNY',
            'GBP': 'GBP', 'ФУНТ': 'GBP', 'POUND': 'GBP', '£': 'GBP',
            'IDR': 'IDR', 'РУПИЯ': 'IDR', 'RUPIAH': 'IDR',
            'THB': 'THB', 'БАТ': 'THB', 'BAHT': 'THB',
            'VND': 'VND', 'ДОНГ': 'VND', 'DONG': 'VND'
        }
        
        return currency_mapping.get(currency, 'USD')  # По умолчанию USD

    async def process_batch(self, data_batches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Пакетная обработка данных для больших файлов"""
        results = []
        
        for i, batch in enumerate(data_batches):
            logger.info(f"Обрабатываю пакет {i + 1}/{len(data_batches)}")
            
            try:
                result = await self.process_data(batch)
                if result:
                    results.append(result)
                
                # Задержка между запросами для соблюдения rate limits
                if i < len(data_batches) - 1:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Ошибка обработки пакета {i + 1}: {e}")
                continue
        
        return results

    def merge_batch_results(self, batch_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Объединение результатов пакетной обработки"""
        if not batch_results:
            return {}
        
        # Берем первый результат как основу
        merged_result = batch_results[0].copy()
        
        # Объединяем товары из всех пакетов
        all_products = []
        for result in batch_results:
            all_products.extend(result.get('products', []))
        
        merged_result['products'] = all_products
        
        # Пересчитываем статистику качества
        total_confidence = sum(r.get('data_quality', {}).get('extraction_confidence', 0) for r in batch_results)
        avg_confidence = total_confidence / len(batch_results) if batch_results else 0
        
        merged_result['data_quality']['extraction_confidence'] = avg_confidence
        merged_result['data_quality']['valid_products'] = len(all_products)
        merged_result['data_quality']['total_products_processed'] = sum(
            r.get('data_quality', {}).get('total_products_processed', 0) for r in batch_results
        )
        
        # Объединяем ошибки
        all_errors = []
        for result in batch_results:
            all_errors.extend(result.get('data_quality', {}).get('potential_errors', []))
        
        # Убираем дублирующиеся ошибки
        unique_errors = list(set(all_errors))
        merged_result['data_quality']['potential_errors'] = unique_errors
        
        return merged_result