import os
import re
import gzip
import shutil
import logging
import chardet
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from fuzzywuzzy import fuzz
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity

from config import (
    TEMP_DIR, 
    MAX_FILE_SIZE, 
    ALLOWED_EXTENSIONS, 
    QUALITY_THRESHOLDS,
    LOG_CONFIG
)

logger = logging.getLogger(__name__)

def setup_logging():
    """Настройка системы логирования"""
    try:
        # Создание директории для логов
        os.makedirs('logs', exist_ok=True)
        
        # Настройка форматирования
        formatter = logging.Formatter(LOG_CONFIG['format'])
        
        # Настройка уровня логирования
        log_level = getattr(logging, LOG_CONFIG['level'].upper(), logging.INFO)
        logging.getLogger().setLevel(log_level)
        
        # Файловый обработчик для общих логов
        file_handler = logging.FileHandler('logs/app.log', encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        
        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        
        # Добавление обработчиков к root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        # Отдельный файл для PDF обработки
        pdf_handler = logging.FileHandler('logs/pdf_processing.log', encoding='utf-8')
        pdf_handler.setFormatter(formatter)
        pdf_logger = logging.getLogger('modules.file_processor')
        pdf_logger.addHandler(pdf_handler)
        
        # Отдельный файл для ошибок OCR
        ocr_handler = logging.FileHandler('logs/ocr_errors.log', encoding='utf-8')
        ocr_handler.setFormatter(formatter)
        ocr_handler.setLevel(logging.WARNING)
        ocr_logger = logging.getLogger('ocr_errors')
        ocr_logger.addHandler(ocr_handler)
        
        logger.info("Система логирования настроена")
        
    except Exception as e:
        print(f"Ошибка настройки логирования: {e}")

def validate_file(filename: str, file_size: int) -> Dict[str, Union[bool, str]]:
    """
    Валидация загружаемого файла
    Возвращает словарь с результатом валидации
    """
    try:
        # Проверка размера файла
        max_size_bytes = MAX_FILE_SIZE * 1024 * 1024  # Конвертация MB в байты
        if file_size > max_size_bytes:
            return {
                'valid': False,
                'error': f'Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE} MB'
            }
        
        # Проверка расширения файла
        file_extension = os.path.splitext(filename.lower())[1]
        if file_extension not in ALLOWED_EXTENSIONS:
            return {
                'valid': False,
                'error': f'Неподдерживаемый формат файла. Разрешены: {", ".join(ALLOWED_EXTENSIONS)}'
            }
        
        # Проверка имени файла на недопустимые символы
        if re.search(r'[<>:"/\\|?*]', filename):
            return {
                'valid': False,
                'error': 'Имя файла содержит недопустимые символы'
            }
        
        return {'valid': True, 'error': None}
        
    except Exception as e:
        logger.error(f"Ошибка валидации файла {filename}: {e}")
        return {
            'valid': False,
            'error': 'Ошибка валидации файла'
        }

def cleanup_temp_files(file_paths: List[str]):
    """Очистка временных файлов"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Удален временный файл: {file_path}")
        except Exception as e:
            logger.warning(f"Не удалось удалить временный файл {file_path}: {e}")

def clean_text(text: str) -> str:
    """Очистка текста от лишних символов и пробелов"""
    if not text or not isinstance(text, str):
        return ""
    
    # Удаление лишних пробелов
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Удаление управляющих символов
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Удаление HTML тегов если есть
    text = re.sub(r'<[^>]+>', '', text)
    
    return text

def detect_language(text: str) -> str:
    """Простое определение языка текста"""
    if not text:
        return 'unknown'
    
    text_lower = text.lower()
    
    # Подсчет символов разных языков
    english_chars = len(re.findall(r'[a-z]', text_lower))
    russian_chars = len(re.findall(r'[а-я]', text_lower))
    indonesian_words = len(re.findall(r'\b(dan|atau|untuk|dengan|dari|yang|ini|itu|akan|sudah|belum)\b', text_lower))
    
    total_chars = len(re.findall(r'[a-zа-я]', text_lower))
    
    if total_chars == 0:
        return 'unknown'
    
    # Определение по процентному соотношению
    if russian_chars / total_chars > 0.3:
        return 'russian'
    elif indonesian_words > 2:
        return 'indonesian'
    elif english_chars / total_chars > 0.7:
        return 'english'
    else:
        return 'mixed'

def validate_price(price: Union[float, int, str]) -> bool:
    """Валидация цены товара"""
    try:
        if isinstance(price, str):
            # Удаление валютных символов и пробелов
            price_clean = re.sub(r'[^\d.,\-]', '', price)
            price = float(price_clean.replace(',', '.'))
        
        price = float(price)
        
        # Проверка на разумные пределы
        if price < 0:
            return False
        
        if price > QUALITY_THRESHOLDS['MAX_PRICE_VALUE']:
            return False
        
        return True
        
    except (ValueError, TypeError):
        return False

def extract_supplier_info(text: str) -> Optional[Dict[str, str]]:
    """Извлечение информации о поставщике из текста"""
    if not text:
        return None
    
    supplier_info = {}
    
    # Паттерны для поиска названия компании
    company_patterns = [
        r'(?:company|компания|corp|corporation|ltd|limited|inc|incorporated|co\.?|ао|ооо|зао)[:\s]*([^\n\r]{3,50})',
        r'([A-Z][a-zA-Z\s&,.-]{5,50})(?:\s+(?:company|corp|ltd|inc|co\.?))',
        r'^\s*([A-ZА-Я][a-zA-Zа-я\s&,.-]{5,50})',  # Первая строка с заглавной буквы
    ]
    
    for pattern in company_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            company_name = match.group(1).strip()
            if len(company_name) > 3:
                supplier_info['name'] = company_name
                break
    
    # Поиск телефонов
    phone_patterns = [
        r'(?:phone|tel|telephone|телефон|тел)[:\s]*([+]?[\d\s\-\(\)]{7,20})',
        r'([+]?[\d\s\-\(\)]{10,20})',  # Общий паттерн для телефонов
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            phone = re.sub(r'[^\d+]', '', match.group(1))
            if len(phone) >= 7:
                supplier_info['phone'] = match.group(1).strip()
                break
    
    # Поиск email
    email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    email_match = re.search(email_pattern, text)
    if email_match:
        supplier_info['email'] = email_match.group(1)
    
    # Поиск адреса
    address_patterns = [
        r'(?:address|адрес)[:\s]*([^\n\r]{10,100})',
        r'(?:location|местоположение|расположение)[:\s]*([^\n\r]{10,100})',
    ]
    
    for pattern in address_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            supplier_info['address'] = match.group(1).strip()
            break
    
    # Если ничего не найдено, возвращаем None
    if not supplier_info:
        return None
    
    return supplier_info

def calculate_similarity(text1: str, text2: str) -> float:
    """
    Расчет similarity между двумя текстами
    Использует комбинацию методов для лучшей точности
    """
    if not text1 or not text2:
        return 0.0
    
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()
    
    # Точное совпадение
    if text1 == text2:
        return 1.0
    
    # Fuzzywuzzy similarity
    fuzzy_ratio = fuzz.ratio(text1, text2) / 100
    fuzzy_partial = fuzz.partial_ratio(text1, text2) / 100
    fuzzy_token_sort = fuzz.token_sort_ratio(text1, text2) / 100
    
    # TF-IDF cosine similarity для длинных текстов (отключено для совместимости)
    tfidf_similarity = 0.0
    # if len(text1) > 10 and len(text2) > 10:
    #     try:
    #         vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 3))
    #         tfidf_matrix = vectorizer.fit_transform([text1, text2])
    #         tfidf_similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    #     except:
    #         pass
    
    # Взвешенное среднее разных методов
    weights = {
        'fuzzy_ratio': 0.3,
        'fuzzy_partial': 0.2,
        'fuzzy_token_sort': 0.3,
        'tfidf': 0.2
    }
    
    similarity = (
        fuzzy_ratio * weights['fuzzy_ratio'] +
        fuzzy_partial * weights['fuzzy_partial'] +
        fuzzy_token_sort * weights['fuzzy_token_sort'] +
        tfidf_similarity * weights['tfidf']
    )
    
    return min(1.0, max(0.0, similarity))

def backup_file(file_path: str, compress: bool = True) -> Optional[str]:
    """Создание резервной копии файла"""
    try:
        if not os.path.exists(file_path):
            return None
        
        # Создание имени файла бэкапа
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_dir = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        file_base, file_ext = os.path.splitext(file_name)
        
        backup_name = f"{file_base}_backup_{timestamp}{file_ext}"
        backup_path = os.path.join(file_dir, backup_name)
        
        # Копирование файла
        shutil.copy2(file_path, backup_path)
        
        # Сжатие если требуется
        if compress:
            compressed_path = f"{backup_path}.gz"
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Удаление несжатого файла
            os.remove(backup_path)
            backup_path = compressed_path
        
        logger.info(f"Создан бэкап файла: {backup_path}")
        return backup_path
        
    except Exception as e:
        logger.error(f"Ошибка создания бэкапа файла {file_path}: {e}")
        return None

def detect_encoding(file_path: str) -> str:
    """Определение кодировки файла"""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # Читаем первые 10KB для определения
        
        result = chardet.detect(raw_data)
        encoding = result.get('encoding', 'utf-8')
        confidence = result.get('confidence', 0)
        
        # Если уверенность низкая, используем utf-8 по умолчанию
        if confidence < 0.7:
            encoding = 'utf-8'
        
        logger.info(f"Определена кодировка файла {file_path}: {encoding} (confidence: {confidence})")
        return encoding
        
    except Exception as e:
        logger.warning(f"Ошибка определения кодировки {file_path}: {e}, используем utf-8")
        return 'utf-8'

def format_file_size(size_bytes: int) -> str:
    """Форматирование размера файла в читаемый вид"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def sanitize_filename(filename: str) -> str:
    """Очистка имени файла от недопустимых символов"""
    # Удаление недопустимых символов
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Удаление множественных подчеркиваний
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Удаление подчеркиваний в начале и конце
    sanitized = sanitized.strip('_')
    
    # Ограничение длины
    if len(sanitized) > 100:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:100-len(ext)] + ext
    
    return sanitized

def extract_numbers_from_text(text: str) -> List[float]:
    """Извлечение всех чисел из текста"""
    if not text:
        return []
    
    # Паттерн для поиска чисел (включая десятичные)
    number_pattern = r'[-+]?(?:\d+[.,])?\d+(?:[.,]\d+)?'
    
    numbers = []
    for match in re.finditer(number_pattern, text):
        try:
            number_str = match.group().replace(',', '.')
            number = float(number_str)
            numbers.append(number)
        except ValueError:
            continue
    
    return numbers

def split_text_into_chunks(text: str, max_chunk_size: int = 2000) -> List[str]:
    """Разделение длинного текста на чанки для обработки"""
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    sentences = re.split(r'[.!?]+', text)
    
    current_chunk = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
            current_chunk += sentence + ". "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def normalize_unit(unit: str) -> str:
    """Нормализация единиц измерения"""
    if not unit:
        return 'pcs'
    
    unit = unit.lower().strip()
    
    # Словарь нормализации
    unit_map = {
        # Вес
        'кг': 'kg', 'килограмм': 'kg', 'kilogram': 'kg',
        'г': 'g', 'грамм': 'g', 'gram': 'g',
        'т': 'ton', 'тонна': 'ton', 'tonne': 'ton',
        
        # Объем
        'л': 'l', 'литр': 'l', 'liter': 'l', 'litre': 'l',
        'мл': 'ml', 'миллилитр': 'ml', 'milliliter': 'ml',
        
        # Длина
        'м': 'm', 'метр': 'm', 'meter': 'm', 'metre': 'm',
        'см': 'cm', 'сантиметр': 'cm', 'centimeter': 'cm',
        'мм': 'mm', 'миллиметр': 'mm', 'millimeter': 'mm',
        
        # Количество
        'шт': 'pcs', 'штука': 'pcs', 'piece': 'pcs', 'pc': 'pcs',
        'упаковка': 'pack', 'package': 'pack',
        'коробка': 'box', 'carton': 'box',
    }
    
    return unit_map.get(unit, unit)

def validate_json_structure(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """Валидация структуры JSON данных"""
    try:
        for field in required_fields:
            if field not in data:
                return False
        return True
    except:
        return False

def safe_float_convert(value: Any, default: float = 0.0) -> float:
    """Безопасное преобразование значения в float"""
    try:
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            # Удаление всех символов кроме цифр, точки и запятой
            cleaned = re.sub(r'[^\d.,\-]', '', value)
            cleaned = cleaned.replace(',', '.')
            return float(cleaned) if cleaned else default
        else:
            return default
    except (ValueError, TypeError):
        return default

def create_temp_file(prefix: str = "temp", suffix: str = ".tmp") -> str:
    """Создание временного файла"""
    import tempfile
    
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    fd, temp_path = tempfile.mkstemp(
        prefix=prefix,
        suffix=suffix,
        dir=TEMP_DIR
    )
    
    os.close(fd)  # Закрываем файловый дескриптор
    return temp_path

def get_file_hash(file_path: str) -> Optional[str]:
    """Получение MD5 хеша файла"""
    import hashlib
    
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"Ошибка вычисления хеша файла {file_path}: {e}")
        return None

def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """Декоратор для повторения операций при ошибках"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise e
                    else:
                        logger.warning(f"Попытка {attempt + 1} не удалась: {e}, повтор через {delay} сек")
                        time.sleep(delay * (2 ** attempt))  # Экспоненциальная задержка
            
        return wrapper
    return decorator