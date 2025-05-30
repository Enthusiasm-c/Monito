import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Основные настройки
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your_bot_token")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_key")
MASTER_TABLE_PATH = "data/master_table.xlsx"
TEMP_DIR = "data/temp/"
MAX_FILE_SIZE = 20  # MB
ALLOWED_EXTENSIONS = ['.xlsx', '.xls', '.pdf']

# PDF обработка
PDF_CONFIG = {
    'OCR_LANGUAGES': 'eng+ind',  # английский + индонезийский
    'OCR_CONFIG': '--psm 6 --oem 3',
    'DPI': 300,
    'MAX_PAGES': 50,
    'TIMEOUT': 300,
    'TABLE_CONFIDENCE': 0.7
}

# GPT настройки
GPT_CONFIG = {
    'MODEL': 'gpt-4-turbo-preview',
    'MAX_TOKENS': 4096,
    'TEMPERATURE': 0.1,
    'RETRY_ATTEMPTS': 3,
    'RETRY_DELAY': 2
}

# Качество данных
QUALITY_THRESHOLDS = {
    'MIN_CONFIDENCE': 0.6,
    'MIN_PRODUCT_NAME_LENGTH': 3,
    'MAX_PRICE_VALUE': 999999,
    'SIMILARITY_THRESHOLD': 0.85
}

# Tesseract конфигурация для OCR
TESSERACT_CONFIG = {
    'lang': 'eng+ind',
    'config': '--psm 6 --oem 3',
    'timeout': 300
}

# Настройки обработки PDF
PDF_SETTINGS = {
    'dpi': 300,
    'max_pages': 50,
    'table_detection_confidence': 0.7,
    'text_extraction_method': 'pdfplumber'
}

# Метрики обработки
PROCESSING_METRICS = {
    'files_processed': 0,
    'success_rate': 0.0,
    'avg_processing_time': 0.0,
    'pdf_success_rate': 0.0,
    'excel_success_rate': 0.0,
    'ocr_accuracy': 0.0,
    'products_added': 0,
    'suppliers_added': 0,
    'last_update': datetime.now()
}

# Резервное копирование
BACKUP_CONFIG = {
    'enabled': True,
    'frequency': 'daily',
    'retention_days': 30,
    'backup_location': '/backups/',
    'compress': True
}

# Логирование
LOG_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_rotation': True,
    'max_file_size': '10MB',
    'backup_count': 5
}

# Переменные окружения
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DEBUG = ENVIRONMENT == 'development'