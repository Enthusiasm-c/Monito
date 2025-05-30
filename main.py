#!/usr/bin/env python3
"""
Система анализа прайс-листов поставщиков
Главная точка входа приложения
"""

import os
import sys
import signal
import asyncio
import logging
from datetime import datetime

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    TELEGRAM_BOT_TOKEN, 
    OPENAI_API_KEY, 
    ENVIRONMENT,
    DEBUG
)
from modules.telegram_bot import TelegramBot
from modules.utils import setup_logging

logger = logging.getLogger(__name__)

class PriceListAnalyzer:
    """Главный класс приложения"""
    
    def __init__(self):
        self.bot = None
        self.running = False
        
    async def initialize(self):
        """Инициализация системы"""
        try:
            logger.info("=" * 60)
            logger.info("🚀 Запуск системы анализа прайс-листов")
            logger.info("=" * 60)
            
            # Проверка конфигурации
            if not self._validate_configuration():
                raise RuntimeError("Ошибка конфигурации")
            
            # Создание необходимых директорий
            self._create_directories()
            
            # Инициализация Telegram бота
            self.bot = TelegramBot()
            
            logger.info("✅ Система успешно инициализирована")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            raise

    def _validate_configuration(self) -> bool:
        """Валидация конфигурации приложения"""
        logger.info("🔍 Проверка конфигурации...")
        
        # Проверка обязательных переменных окружения
        if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_bot_token":
            logger.error("❌ Не установлен TELEGRAM_BOT_TOKEN")
            return False
        
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_key":
            logger.error("❌ Не установлен OPENAI_API_KEY")
            return False
        
        logger.info(f"✅ Окружение: {ENVIRONMENT}")
        logger.info(f"✅ Режим отладки: {DEBUG}")
        logger.info("✅ Конфигурация валидна")
        
        return True

    def _create_directories(self):
        """Создание необходимых директорий"""
        directories = [
            'data',
            'data/temp',
            'logs',
            'backups'
        ]
        
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"📁 Директория создана/проверена: {directory}")
            except Exception as e:
                logger.error(f"❌ Ошибка создания директории {directory}: {e}")
                raise

    async def run(self):
        """Запуск основного цикла приложения"""
        try:
            await self.initialize()
            
            self.running = True
            
            # Настройка обработчиков сигналов для graceful shutdown
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            logger.info("🤖 Запуск Telegram бота...")
            
            # Запуск бота в отдельной задаче
            bot_task = asyncio.create_task(self._run_bot())
            
            # Запуск системы мониторинга
            monitoring_task = asyncio.create_task(self._run_monitoring())
            
            # Ожидание завершения всех задач
            await asyncio.gather(bot_task, monitoring_task, return_exceptions=True)
            
        except KeyboardInterrupt:
            logger.info("⏹️  Получен сигнал прерывания")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            raise
        finally:
            await self.shutdown()

    async def _run_bot(self):
        """Запуск Telegram бота"""
        try:
            # Запуск бота в отдельном потоке, так как bot.run() блокирующий
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.bot.run)
        except Exception as e:
            logger.error(f"❌ Ошибка работы бота: {e}")
            raise

    async def _run_monitoring(self):
        """Запуск системы мониторинга"""
        from modules.data_manager import DataManager
        
        data_manager = DataManager()
        
        while self.running:
            try:
                # Периодический сбор статистики
                await asyncio.sleep(300)  # Каждые 5 минут
                
                stats = data_manager.get_processing_stats()
                logger.info(f"📊 Статистика: обработано файлов: {stats.get('files_processed', 0)}, "
                           f"успешность: {stats.get('success_rate', 0):.1f}%")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка мониторинга: {e}")
                await asyncio.sleep(60)  # Ожидание перед повтором

    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для graceful shutdown"""
        logger.info(f"⚠️  Получен сигнал {signum}")
        self.running = False

    async def shutdown(self):
        """Graceful shutdown системы"""
        try:
            logger.info("🛑 Остановка системы...")
            
            self.running = False
            
            # Здесь можно добавить код для graceful shutdown компонентов
            # например, сохранение состояния, закрытие соединений и т.д.
            
            logger.info("✅ Система остановлена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки системы: {e}")

def main():
    """Главная функция"""
    try:
        # Настройка логирования
        setup_logging()
        
        # Вывод информации о системе
        print_system_info()
        
        # Создание и запуск приложения
        app = PriceListAnalyzer()
        
        # Запуск в asyncio event loop
        if sys.platform == 'win32':
            # Для Windows используем ProactorEventLoop
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        asyncio.run(app.run())
        
    except KeyboardInterrupt:
        print("\n⏹️  Приложение остановлено пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

def print_system_info():
    """Вывод информации о системе"""
    print("\n" + "=" * 60)
    print("🔍 СИСТЕМА АНАЛИЗА ПРАЙС-ЛИСТОВ ПОСТАВЩИКОВ")
    print("=" * 60)
    print(f"📅 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python версия: {sys.version.split()[0]}")
    print(f"🖥️  Платформа: {sys.platform}")
    print(f"🌍 Окружение: {ENVIRONMENT}")
    print(f"🔧 Режим отладки: {DEBUG}")
    print("=" * 60)
    print("📋 ВОЗМОЖНОСТИ СИСТЕМЫ:")
    print("  • Обработка Excel файлов (.xlsx, .xls)")
    print("  • Обработка PDF файлов с OCR")
    print("  • Стандартизация данных через GPT-4")
    print("  • Автоматическое создание сводных таблиц")
    print("  • Telegram бот интерфейс")
    print("  • Система мониторинга и логирования")
    print("=" * 60)
    print("🚀 Запуск...")
    print()

def check_dependencies():
    """Проверка наличия всех зависимостей"""
    required_packages = [
        'telegram',
        'openai', 
        'pandas',
        'openpyxl',
        'pdfplumber',
        'pytesseract',
        'PIL',
        'pdf2image',
        'tabula',
        'fuzzywuzzy',
        'sklearn'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Отсутствуют необходимые пакеты:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\n💡 Установите зависимости командой:")
        print("pip install -r requirements.txt")
        sys.exit(1)

def create_systemd_service():
    """Создание systemd service файла для Linux"""
    if len(sys.argv) > 1 and sys.argv[1] == '--create-service':
        service_content = f"""[Unit]
Description=Price List Analyzer Bot
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'ubuntu')}
WorkingDirectory={os.path.dirname(os.path.abspath(__file__))}
Environment=PATH={os.path.dirname(os.path.abspath(__file__))}/venv/bin
ExecStart={sys.executable} {os.path.abspath(__file__)}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        
        service_path = '/etc/systemd/system/price-list-analyzer.service'
        print(f"Создание systemd service файла: {service_path}")
        print("Содержимое файла:")
        print(service_content)
        print("\nДля установки выполните:")
        print(f"sudo tee {service_path} << EOF")
        print(service_content)
        print("EOF")
        print("sudo systemctl daemon-reload")
        print("sudo systemctl enable price-list-analyzer")
        print("sudo systemctl start price-list-analyzer")
        sys.exit(0)

if __name__ == "__main__":
    # Проверка аргументов командной строки
    create_systemd_service()
    
    # Проверка зависимостей
    check_dependencies()
    
    # Запуск приложения
    main()