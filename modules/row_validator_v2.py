#!/usr/bin/env python3
"""
Row Validator V2 для MON-003 - валидация данных и кэширование
Основные улучшения:
- Pandera schema validation для качества данных
- Redis кэширование для ускорения обработки
- Intelligent data quality scoring
- Smart caching strategy для повторяющихся товаров
"""

import os
import time
import json
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class ValidationStats:
    """Статистика валидации для MON-003"""
    input_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    cached_hits: int = 0
    cached_misses: int = 0
    validation_time_ms: int = 0
    cache_time_ms: int = 0
    quality_score: float = 0.0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class RowValidatorV2:
    """
    Row Validator V2 для MON-003 оптимизации
    
    Ключевые улучшения:
    - 📊 Pandera schema validation
    - 💾 Redis кэширование результатов
    - ✅ Intelligent data quality scoring
    - 🔄 Smart caching strategy
    """
    
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379, 
                 redis_db: int = 0, cache_ttl: int = 3600):
        # Статистика
        self.stats = ValidationStats()
        
        # Redis настройки
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.cache_ttl = cache_ttl  # TTL кэша в секундах (1 час по умолчанию)
        
        # Настройки качества данных
        self.min_quality_score = 0.7  # Минимальный приемлемый score
        self.price_tolerance = 0.01   # Допустимая погрешность цен
        
        # Проверяем зависимости
        self._check_dependencies()
        
        # Инициализируем Redis подключение
        self._init_redis()
        
        # Создаем схемы валидации
        self._init_validation_schemas()
        
        logger.info("✅ RowValidatorV2 инициализирован с MON-003 оптимизациями")
    
    def _check_dependencies(self):
        """Проверка зависимостей MON-003"""
        self.pandera_available = False
        self.redis_available = False
        
        try:
            import pandera as pa
            self.pandera_available = True
            logger.info("✅ Pandera доступен для schema validation")
        except ImportError:
            logger.warning("⚠️ Pandera не найден, валидация ограничена")
        
        try:
            import redis
            self.redis_available = True
            logger.info("✅ Redis доступен для кэширования")
        except ImportError:
            logger.warning("⚠️ Redis не найден, кэширование отключено")
    
    def _init_redis(self):
        """Инициализация Redis подключения"""
        self.redis_client = None
        
        if not self.redis_available:
            logger.info("📝 Redis недоступен, кэширование отключено")
            return
        
        try:
            import redis
            
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # Проверяем подключение
            self.redis_client.ping()
            logger.info(f"✅ Redis подключен: {self.redis_host}:{self.redis_port}")
            
        except Exception as e:
            logger.warning(f"⚠️ Не удалось подключиться к Redis: {e}")
            self.redis_client = None
    
    def _init_validation_schemas(self):
        """Создание схем валидации с Pandera"""
        if not self.pandera_available:
            logger.info("📝 Pandera недоступен, используем базовую валидацию")
            return
        
        try:
            import pandera as pa
            
            # Схема для товаров
            self.product_schema = pa.DataFrameSchema({
                'original_name': pa.Column(
                    str, 
                    checks=[
                        pa.Check.str_length(min_value=2, max_value=200),
                        pa.Check(lambda s: s.str.strip().str.len() > 0, 
                                error="Empty product names not allowed")
                    ],
                    nullable=False
                ),
                'price': pa.Column(
                    float,
                    checks=[
                        pa.Check.greater_than(0, error="Price must be positive"),
                        pa.Check.less_than(1000000, error="Price too high")
                    ],
                    nullable=False
                ),
                'unit': pa.Column(
                    str,
                    checks=[
                        pa.Check.isin(['pcs', 'kg', 'g', 'l', 'ml', 'm', 'cm', 'box', 'pack']),
                    ],
                    nullable=False
                ),
                'currency': pa.Column(
                    str,
                    checks=[
                        pa.Check.isin(['USD', 'EUR', 'RUB', 'CNY', 'GBP']),
                    ],
                    nullable=True
                )
            })
            
            # Схема для стандартизированных товаров
            self.standardized_schema = pa.DataFrameSchema({
                'standardized_name': pa.Column(str, nullable=False),
                'brand': pa.Column(str, nullable=True),
                'category': pa.Column(str, nullable=True),
                'confidence': pa.Column(
                    float,
                    checks=[
                        pa.Check.between(0.0, 1.0, include_min=True, include_max=True)
                    ],
                    nullable=False
                )
            })
            
            logger.info("✅ Pandera схемы валидации созданы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания схем валидации: {e}")
            self.product_schema = None
            self.standardized_schema = None
    
    def validate_and_cache(self, df: pd.DataFrame, 
                          cache_key_prefix: str = "products") -> Tuple[pd.DataFrame, ValidationStats]:
        """
        MON-003: Валидация данных с кэшированием
        
        Args:
            df: DataFrame с товарами для валидации
            cache_key_prefix: Префикс для ключей кэша
        
        Returns:
            Tuple[pd.DataFrame, ValidationStats]: Валидные данные и статистика
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔍 MON-003: Начинаем валидацию {len(df)} строк")
            
            # Сброс статистики
            self.stats = ValidationStats()
            self.stats.input_rows = len(df)
            
            if df.empty:
                logger.warning("⚠️ Пустой DataFrame для валидации")
                return df, self.stats
            
            # Шаг 1: Проверка кэша (MON-003.1)
            cached_df = self._check_cache(df, cache_key_prefix)
            
            # Шаг 2: Schema validation (MON-003.2)
            valid_df = self._validate_schema(df)
            
            # Шаг 3: Data quality scoring (MON-003.3)
            quality_score = self._calculate_quality_score(valid_df)
            
            # Шаг 4: Сохранение в кэш (MON-003.4)
            self._save_to_cache(valid_df, cache_key_prefix)
            
            # Финальная статистика
            total_time = int((time.time() - start_time) * 1000)
            self.stats.validation_time_ms = total_time
            self.stats.quality_score = quality_score
            
            logger.info(f"✅ MON-003 COMPLETED: {len(valid_df)} валидных строк за {total_time}ms")
            logger.info(f"   📊 Quality score: {quality_score:.3f}")
            logger.info(f"   💾 Cache hits: {self.stats.cached_hits}")
            
            return valid_df, self.stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка валидации и кэширования: {e}")
            error_stats = ValidationStats()
            error_stats.input_rows = len(df)
            error_stats.errors.append(str(e))
            return df, error_stats
    
    def _check_cache(self, df: pd.DataFrame, cache_key_prefix: str) -> Optional[pd.DataFrame]:
        """
        MON-003.1: Проверка Redis кэша
        Цель: Ускорение обработки повторяющихся данных
        """
        if not self.redis_client:
            logger.info("📝 Redis недоступен, пропускаем проверку кэша")
            self.stats.cached_misses = len(df)
            return None
        
        start_time = time.time()
        
        try:
            logger.info(f"💾 MON-003.1: Проверяем кэш для {len(df)} строк")
            
            cached_results = []
            cache_hits = 0
            cache_misses = 0
            
            for idx, row in df.iterrows():
                # Создаем уникальный ключ для строки
                cache_key = self._generate_cache_key(row, cache_key_prefix)
                
                # Проверяем кэш
                cached_data = self.redis_client.get(cache_key)
                
                if cached_data:
                    try:
                        cached_row = json.loads(cached_data)
                        cached_results.append(cached_row)
                        cache_hits += 1
                    except json.JSONDecodeError:
                        cache_misses += 1
                        continue
                else:
                    cache_misses += 1
            
            cache_time = int((time.time() - start_time) * 1000)
            self.stats.cache_time_ms = cache_time
            self.stats.cached_hits = cache_hits
            self.stats.cached_misses = cache_misses
            
            logger.info(f"✅ Кэш проверен за {cache_time}ms:")
            logger.info(f"   💾 Hits: {cache_hits}")
            logger.info(f"   ❌ Misses: {cache_misses}")
            
            if cached_results:
                return pd.DataFrame(cached_results)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки кэша: {e}")
            self.stats.cached_misses = len(df)
            return None
    
    def _validate_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        MON-003.2: Schema validation с Pandera
        Цель: Обеспечение качества данных
        """
        if not self.pandera_available or not self.product_schema:
            logger.info("📝 Pandera недоступен, используем базовую валидацию")
            return self._basic_validation(df)
        
        try:
            import pandera as pa
            
            logger.info(f"📊 MON-003.2: Schema validation...")
            
            # Подготавливаем данные для валидации
            df_to_validate = df.copy()
            
            # Убеждаемся что нужные колонки есть
            required_columns = ['original_name', 'price', 'unit']
            missing_columns = [col for col in required_columns if col not in df_to_validate.columns]
            
            if missing_columns:
                logger.warning(f"⚠️ Отсутствуют колонки: {missing_columns}")
                # Добавляем недостающие колонки с дефолтными значениями
                for col in missing_columns:
                    if col == 'original_name':
                        df_to_validate[col] = 'Unknown Product'
                    elif col == 'price':
                        df_to_validate[col] = 0.0
                    elif col == 'unit':
                        df_to_validate[col] = 'pcs'
            
            # Добавляем currency если отсутствует
            if 'currency' not in df_to_validate.columns:
                df_to_validate['currency'] = 'USD'
            
            # Приводим типы данных
            df_to_validate['price'] = pd.to_numeric(df_to_validate['price'], errors='coerce')
            df_to_validate['original_name'] = df_to_validate['original_name'].astype(str)
            df_to_validate['unit'] = df_to_validate['unit'].astype(str)
            df_to_validate['currency'] = df_to_validate['currency'].astype(str)
            
            # Валидация через Pandera
            validated_df = self.product_schema.validate(df_to_validate, lazy=True)
            
            self.stats.valid_rows = len(validated_df)
            self.stats.invalid_rows = len(df) - len(validated_df)
            
            logger.info(f"✅ Schema validation завершена:")
            logger.info(f"   ✅ Валидных: {self.stats.valid_rows}")
            logger.info(f"   ❌ Невалидных: {self.stats.invalid_rows}")
            
            return validated_df
            
        except pa.errors.SchemaErrors as e:
            logger.warning(f"⚠️ Schema validation errors:")
            
            # Собираем ошибки
            failure_cases = e.failure_cases
            error_messages = []
            
            for _, error_case in failure_cases.iterrows():
                error_msg = f"Row {error_case.get('index', 'N/A')}: {error_case.get('failure_case', 'Unknown error')}"
                error_messages.append(error_msg)
                logger.warning(f"   • {error_msg}")
            
            self.stats.errors.extend(error_messages[:10])  # Сохраняем первые 10 ошибок
            
            # Возвращаем только валидные строки
            try:
                valid_data = e.data.dropna()
                self.stats.valid_rows = len(valid_data)
                self.stats.invalid_rows = len(df) - len(valid_data)
                return valid_data
            except:
                # Fallback на базовую валидацию
                return self._basic_validation(df)
                
        except Exception as e:
            logger.error(f"❌ Ошибка schema validation: {e}")
            return self._basic_validation(df)
    
    def _basic_validation(self, df: pd.DataFrame) -> pd.DataFrame:
        """Базовая валидация без Pandera"""
        try:
            logger.info("📝 Выполняем базовую валидацию...")
            
            valid_df = df.copy()
            
            # Убираем строки с пустыми названиями товаров
            if 'original_name' in valid_df.columns:
                valid_df = valid_df[valid_df['original_name'].notna()]
                valid_df = valid_df[valid_df['original_name'].str.strip() != '']
            
            # Убираем строки с некорректными ценами
            if 'price' in valid_df.columns:
                valid_df['price'] = pd.to_numeric(valid_df['price'], errors='coerce')
                valid_df = valid_df[valid_df['price'] > 0]
            
            self.stats.valid_rows = len(valid_df)
            self.stats.invalid_rows = len(df) - len(valid_df)
            
            logger.info(f"✅ Базовая валидация: {self.stats.valid_rows}/{len(df)} строк валидны")
            
            return valid_df
            
        except Exception as e:
            logger.error(f"❌ Ошибка базовой валидации: {e}")
            self.stats.valid_rows = len(df)
            self.stats.invalid_rows = 0
            return df
    
    def _calculate_quality_score(self, df: pd.DataFrame) -> float:
        """
        MON-003.3: Intelligent data quality scoring
        Цель: Оценка качества данных от 0.0 до 1.0
        """
        try:
            if df.empty:
                return 0.0
            
            logger.info(f"📊 MON-003.3: Расчет quality score...")
            
            scores = []
            
            # 1. Полнота данных (completeness)
            required_columns = ['original_name', 'price', 'unit']
            completeness_scores = []
            
            for col in required_columns:
                if col in df.columns:
                    non_null_ratio = df[col].notna().sum() / len(df)
                    completeness_scores.append(non_null_ratio)
                else:
                    completeness_scores.append(0.0)
            
            completeness_score = sum(completeness_scores) / len(completeness_scores)
            scores.append(('completeness', completeness_score, 0.3))
            
            # 2. Корректность цен (validity)
            price_validity = 0.0
            if 'price' in df.columns:
                valid_prices = df['price'] > 0
                price_validity = valid_prices.sum() / len(df) if len(df) > 0 else 0
            
            scores.append(('price_validity', price_validity, 0.25))
            
            # 3. Качество названий товаров (consistency)
            name_quality = 0.0
            if 'original_name' in df.columns:
                # Проверяем длину названий
                good_length = df['original_name'].str.len().between(3, 100)
                # Проверяем что нет только чисел
                not_only_numbers = ~df['original_name'].str.match(r'^\d+$', na=False)
                
                name_quality = (good_length & not_only_numbers).sum() / len(df) if len(df) > 0 else 0
            
            scores.append(('name_quality', name_quality, 0.25))
            
            # 4. Стандартизация единиц измерения (standardization)
            unit_standardization = 0.0
            if 'unit' in df.columns:
                standard_units = ['pcs', 'kg', 'g', 'l', 'ml', 'm', 'cm', 'box', 'pack']
                standardized = df['unit'].isin(standard_units)
                unit_standardization = standardized.sum() / len(df) if len(df) > 0 else 0
            
            scores.append(('unit_standardization', unit_standardization, 0.2))
            
            # Итоговый взвешенный score
            total_score = sum(score * weight for name, score, weight in scores)
            
            logger.info(f"✅ Quality score рассчитан: {total_score:.3f}")
            for name, score, weight in scores:
                logger.debug(f"   • {name}: {score:.3f} (вес: {weight})")
            
            return round(total_score, 3)
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета quality score: {e}")
            return 0.5  # Средний score при ошибке
    
    def _save_to_cache(self, df: pd.DataFrame, cache_key_prefix: str):
        """
        MON-003.4: Сохранение результатов в Redis кэш
        Цель: Ускорение повторных обращений
        """
        if not self.redis_client or df.empty:
            logger.info("📝 Redis недоступен или нет данных для кэширования")
            return
        
        try:
            logger.info(f"💾 MON-003.4: Сохраняем {len(df)} строк в кэш...")
            
            saved_count = 0
            
            for idx, row in df.iterrows():
                cache_key = self._generate_cache_key(row, cache_key_prefix)
                cache_data = json.dumps(row.to_dict(), ensure_ascii=False)
                
                try:
                    self.redis_client.setex(cache_key, self.cache_ttl, cache_data)
                    saved_count += 1
                except Exception as e:
                    logger.debug(f"⚠️ Не удалось сохранить в кэш: {e}")
                    continue
            
            logger.info(f"✅ В кэш сохранено {saved_count}/{len(df)} строк")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в кэш: {e}")
    
    def _generate_cache_key(self, row: pd.Series, prefix: str) -> str:
        """Генерация уникального ключа для кэша"""
        try:
            # Используем название товара и цену для ключа
            name = str(row.get('original_name', '')).strip().lower()
            price = str(row.get('price', ''))
            unit = str(row.get('unit', ''))
            
            # Создаем хэш для ключа
            data_string = f"{name}|{price}|{unit}"
            hash_object = hashlib.md5(data_string.encode('utf-8'))
            hash_hex = hash_object.hexdigest()
            
            return f"{prefix}:{hash_hex}"
            
        except Exception as e:
            logger.debug(f"⚠️ Ошибка генерации ключа кэша: {e}")
            return f"{prefix}:unknown_{int(time.time())}"
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша"""
        if not self.redis_client:
            return {'cache_available': False}
        
        try:
            info = self.redis_client.info()
            return {
                'cache_available': True,
                'redis_version': info.get('redis_version', 'unknown'),
                'used_memory_human': info.get('used_memory_human', 'unknown'),
                'connected_clients': info.get('connected_clients', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'cache_hit_ratio': round(
                    info.get('keyspace_hits', 0) / 
                    max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1), 3
                )
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики кэша: {e}")
            return {'cache_available': True, 'error': str(e)}
    
    def clear_cache(self, pattern: str = None) -> int:
        """Очистка кэша"""
        if not self.redis_client:
            logger.warning("⚠️ Redis недоступен, нельзя очистить кэш")
            return 0
        
        try:
            if pattern:
                keys = self.redis_client.keys(pattern)
                if keys:
                    deleted = self.redis_client.delete(*keys)
                    logger.info(f"✅ Удалено {deleted} ключей по паттерну {pattern}")
                    return deleted
                else:
                    logger.info(f"📝 Ключи по паттерну {pattern} не найдены")
                    return 0
            else:
                self.redis_client.flushdb()
                logger.info("✅ Весь кэш очищен")
                return -1  # Все ключи
                
        except Exception as e:
            logger.error(f"❌ Ошибка очистки кэша: {e}")
            return 0
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Отчет о валидации MON-003"""
        return {
            'mon_003_validation': {
                'pandera_available': self.pandera_available,
                'redis_available': self.redis_available and self.redis_client is not None,
                'min_quality_score': self.min_quality_score,
                'cache_ttl_seconds': self.cache_ttl
            },
            'validation_stats': {
                'input_rows': self.stats.input_rows,
                'valid_rows': self.stats.valid_rows,
                'invalid_rows': self.stats.invalid_rows,
                'validation_time_ms': self.stats.validation_time_ms,
                'quality_score': self.stats.quality_score,
                'errors_count': len(self.stats.errors)
            },
            'cache_stats': {
                'cached_hits': self.stats.cached_hits,
                'cached_misses': self.stats.cached_misses,
                'cache_time_ms': self.stats.cache_time_ms,
                'cache_hit_ratio': round(
                    self.stats.cached_hits / 
                    max(self.stats.cached_hits + self.stats.cached_misses, 1), 3
                )
            },
            'version': 'RowValidatorV2_MON003'
        } 