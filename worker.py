#!/usr/bin/env python3
"""
Celery Worker запуск для MON-007
Скрипт для запуска асинхронных воркеров Monito
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Настройка окружения для Celery worker"""
    
    # Устанавливаем переменные окружения если не заданы
    os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    os.environ.setdefault('CELERY_APP_NAME', 'monito')
    
    logger.info("🔧 Окружение Celery настроено")
    logger.info(f"   📡 Broker: {os.environ.get('CELERY_BROKER_URL')}")
    logger.info(f"   💾 Backend: {os.environ.get('CELERY_RESULT_BACKEND')}")

def create_celery_app():
    """Создание и настройка Celery приложения"""
    try:
        from modules.celery_worker_v2 import CeleryWorkerV2, init_global_celery_worker
        
        # Инициализируем глобальный worker
        worker = init_global_celery_worker(
            app_name=os.environ.get('CELERY_APP_NAME', 'monito'),
            broker_url=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
            result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
        )
        
        if worker.celery_app:
            logger.info("✅ Celery приложение создано")
            return worker.celery_app
        else:
            logger.warning("⚠️ Celery работает в mock режиме")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания Celery приложения: {e}")
        raise

def main():
    """Главная функция запуска worker"""
    
    print("🚀 ЗАПУСК MONITO CELERY WORKER")
    print("=" * 40)
    
    # Настройка окружения
    setup_environment()
    
    # Создание Celery app
    celery_app = create_celery_app()
    
    if not celery_app:
        print("⚠️ Celery недоступен, завершаем работу")
        print("💡 Для запуска воркера:")
        print("   pip install celery redis")
        print("   docker run -d -p 6379:6379 redis")
        sys.exit(1)
    
    print("✅ Celery worker готов к запуску")
    print("\n📋 Доступные команды:")
    print("   python worker.py worker          # Запуск worker")
    print("   python worker.py flower          # Запуск Flower UI")
    print("   python worker.py status          # Статус воркеров")
    print("   python worker.py purge           # Очистка очередей")
    
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "worker":
            start_worker(celery_app)
        elif command == "flower":
            start_flower(celery_app)
        elif command == "status":
            show_status(celery_app)
        elif command == "purge":
            purge_queues(celery_app)
        else:
            print(f"❌ Неизвестная команда: {command}")
            sys.exit(1)
    else:
        # По умолчанию запускаем worker
        start_worker(celery_app)

def start_worker(celery_app):
    """Запуск Celery worker"""
    print("\n🔄 ЗАПУСК CELERY WORKER")
    print("-" * 25)
    
    try:
        # Настройки воркера
        worker_args = [
            '--loglevel=info',
            '--concurrency=4',  # 4 параллельных процесса
            '--queues=file_processing,llm_processing,data_validation,sheets_writing,notifications',
            '--hostname=monito-worker@%h'
        ]
        
        print(f"⚙️ Настройки воркера:")
        print(f"   🔄 Concurrency: 4")
        print(f"   📦 Очереди: file_processing, llm_processing, data_validation, sheets_writing, notifications")
        print(f"   📝 Log level: info")
        
        print(f"\n🚀 Запускаем воркер...")
        
        # Запуск воркера
        celery_app.worker_main(argv=['worker'] + worker_args)
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Воркер остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка запуска воркера: {e}")
        sys.exit(1)

def start_flower(celery_app):
    """Запуск Flower UI для мониторинга"""
    print("\n🌸 ЗАПУСК FLOWER UI")
    print("-" * 20)
    
    try:
        import flower
        
        flower_args = [
            '--broker=' + os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
            '--port=5555',
            '--url_prefix=flower'
        ]
        
        print(f"🌐 Flower UI будет доступен на: http://localhost:5555/flower")
        print(f"🔄 Запускаем Flower...")
        
        from flower.command import FlowerCommand
        cmd = FlowerCommand()
        cmd.execute_from_commandline(['flower'] + flower_args)
        
    except ImportError:
        print(f"❌ Flower не установлен")
        print(f"💡 Установите: pip install flower")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка запуска Flower: {e}")
        sys.exit(1)

def show_status(celery_app):
    """Показать статус воркеров и очередей"""
    print("\n📊 СТАТУС CELERY WORKERS")
    print("-" * 30)
    
    try:
        from modules.celery_worker_v2 import get_global_celery_worker
        
        worker = get_global_celery_worker()
        
        # Статус очередей
        queue_status = worker.get_queue_status()
        print(f"🔄 Режим: {queue_status.get('mode', 'unknown')}")
        
        # Воркеры
        workers = queue_status.get('workers', {})
        print(f"👥 Воркеры: {workers.get('active', 0)} активных / {workers.get('total', 0)} всего")
        
        # Очереди
        queues = queue_status.get('queues', {})
        print(f"\n📦 Очереди:")
        for queue_name, queue_info in queues.items():
            pending = queue_info.get('pending', 0)
            active = queue_info.get('active', 0)
            print(f"   {queue_name}: {pending} ожидают / {active} активных")
        
        # Статистика
        stats = worker.get_worker_stats()
        print(f"\n📈 Статистика:")
        print(f"   Всего задач: {stats.total_tasks}")
        print(f"   Успешных: {stats.successful_tasks}")
        print(f"   Ошибок: {stats.failed_tasks}")
        print(f"   В очереди: {stats.pending_tasks}")
        
        if stats.errors:
            print(f"\n❌ Последние ошибки:")
            for error in stats.errors[-3:]:  # Показываем последние 3 ошибки
                print(f"   • {error}")
        
    except Exception as e:
        print(f"❌ Ошибка получения статуса: {e}")

def purge_queues(celery_app):
    """Очистка всех очередей"""
    print("\n🧹 ОЧИСТКА ОЧЕРЕДЕЙ")
    print("-" * 20)
    
    try:
        from modules.celery_worker_v2 import get_global_celery_worker
        
        worker = get_global_celery_worker()
        
        # Спрашиваем подтверждение
        confirm = input("❓ Очистить все очереди? (y/N): ").strip().lower()
        
        if confirm == 'y':
            purged = worker.purge_queue()
            print(f"✅ Очищено {purged} задач из очередей")
        else:
            print("🚫 Очистка отменена")
        
    except Exception as e:
        print(f"❌ Ошибка очистки очередей: {e}")

if __name__ == "__main__":
    main() 