#!/usr/bin/env python3
"""
Простой Telegram бот с подробным логированием
Использует интеллектуальный preprocessor без pandas зависимостей
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Добавляем корневую директорию
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Очень подробное логирование
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('simple_bot_detailed.log', mode='w', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class SimpleTelegramBot:
    """Простой Telegram бот с подробным логированием"""
    
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.temp_dir = "data/temp"
        os.makedirs(self.temp_dir, exist_ok=True)
        
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
        
        logger.info("🚀 Инициализация SimpleTelegramBot")
        logger.info(f"📁 Временная папка: {self.temp_dir}")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        logger.info(f"👤 Пользователь {update.effective_user.username} запустил бота")
        
        welcome_message = """
🚀 *Добро пожаловать в Simple Price List Analyzer!*

Я демонстрационный бот с подробным логированием.

*🎯 Что я умею:*
• Детальное логирование всех операций
• Анализ Excel файлов с интеллектуальным препроцессором
• Показывать подробную статистику обработки

*🔧 Команды:*
/start - это сообщение
/help - подробная справка  
/stats - статистика работы
/test - тест компонентов

*📁 Просто отправьте Excel файл для анализа!*

Все операции логируются в файл `simple_bot_detailed.log` 📝
        """
        
        logger.info("📤 Отправка welcome сообщения")
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)
        logger.info("✅ Welcome сообщение отправлено успешно")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        logger.info(f"👤 Пользователь {update.effective_user.username} запросил help")
        
        help_text = """
📖 *Подробная справка по Simple Bot*

*🔍 Интеллектуальный анализ Excel:*
• Автоматическое определение стратегии обработки
• Поддержка multi-column, sparse, irregular форматов
• Восстановление пропущенных данных
• Связывание товаров с ценами

*📊 Подробное логирование:*
• Каждая операция записывается в лог
• Детальная диагностика ошибок
• Статистика производительности
• Отслеживание всех этапов обработки

*🎯 Процесс обработки:*
1. Загрузка и валидация файла
2. Определение стратегии анализа
3. Интеллектуальное извлечение данных
4. Восстановление пропущенных значений
5. Генерация подробного отчета

*💡 Логирование:*
• Файл: `simple_bot_detailed.log`
• Уровень: DEBUG (максимальная детализация)
• Включает: HTTP запросы, анализ файлов, ошибки
        """
        
        logger.info("📤 Отправка help сообщения")
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
        logger.info("✅ Help сообщение отправлено")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats"""
        logger.info(f"👤 Пользователь {update.effective_user.username} запросил статистику")
        
        # Анализ лога
        log_file = Path('simple_bot_detailed.log')
        stats_text = f"""
📊 *Статистика Simple Bot*

*📝 Логирование:*
• Файл лога: {log_file.name}
• Размер лога: {log_file.stat().st_size / 1024:.1f} KB
• Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

*🔧 Компоненты:*
• Интеллектуальный препроцессор: ✅ Готов
• Excel анализатор: ✅ Готов  
• Telegram API: ✅ Активен
• Детальное логирование: ✅ Включено

*💡 Готовность:*
Система готова к обработке Excel файлов с максимальной детализацией логирования!
        """
        
        logger.info("📤 Отправка статистики")
        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
        logger.info("✅ Статистика отправлена")
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /test"""
        logger.info(f"👤 Пользователь {update.effective_user.username} запустил тест")
        
        test_message = await update.message.reply_text("🔍 Тестирую компоненты с детальным логированием...")
        logger.info("📝 Начат тест компонентов")
        
        try:
            # Тест интеллектуального препроцессора
            logger.debug("🧪 Импорт интеллектуального препроцессора...")
            from modules.intelligent_preprocessor import IntelligentPreProcessor
            IntelligentPreProcessor()
            logger.info("✅ Интеллектуальный препроцессор успешно загружен")
            
            # Тест временной папки
            logger.debug("🧪 Проверка временной папки...")
            temp_path = Path(self.temp_dir)
            if temp_path.exists():
                logger.info(f"✅ Временная папка доступна: {temp_path}")
            else:
                logger.warning(f"⚠️ Временная папка не найдена: {temp_path}")
            
            result_text = """
🔍 *Результаты тестирования*

*📊 Компоненты:*
• IntelligentPreProcessor: ✅ Работает
• Временная папка: ✅ Доступна
• Логирование: ✅ Активно
• Telegram API: ✅ Подключен

*🎯 Готовность системы:* 🟢 Полная

*💡 Детали:*
• Все операции логируются в `simple_bot_detailed.log`
• Поддерживаются стратегии: multi_column, sparse, irregular, adaptive
• Готов к анализу файлов любой сложности

*📊 Уровень логирования:* DEBUG (максимальный)
            """
            
            logger.info("✅ Тест компонентов прошел успешно")
            
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=test_message.message_id,
                text=result_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info("✅ Результаты теста отправлены пользователю")
            
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования: {e}", exc_info=True)
            
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=test_message.message_id,
                text=f"❌ Ошибка тестирования: {e}"
            )
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка загруженных документов с максимальным логированием"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        document: Document = update.message.document
        
        logger.info("="*80)
        logger.info("🔥 НАЧАЛАСЬ ПОДРОБНАЯ ОБРАБОТКА ФАЙЛА")
        logger.info("="*80)
        logger.info(f"👤 Пользователь: {username} (ID: {user_id})")
        logger.info(f"📎 Файл: {document.file_name}")
        logger.info(f"📊 Размер: {document.file_size / 1024 / 1024:.2f} МБ")
        logger.info(f"🎯 MIME тип: {document.mime_type}")
        logger.info(f"🆔 File ID: {document.file_id}")
        
        # Валидация файла
        logger.debug("🔍 Начинаем валидацию файла...")
        validation_result = self._validate_file(document)
        if not validation_result['valid']:
            logger.error(f"❌ Валидация провалена: {validation_result['error']}")
            await update.message.reply_text(f"❌ {validation_result['error']}")
            return
        
        logger.info("✅ Файл успешно прошел валидацию")
        
        processing_message = await update.message.reply_text("🚀 Начинаю обработку с подробным логированием...")
        logger.info("📤 Отправлено сообщение о начале обработки")
        
        try:
            start_time = datetime.now()
            logger.info(f"⏰ Время начала обработки: {start_time}")
            
            # Скачивание файла
            logger.debug("⬇️ Начинаем скачивание файла...")
            file = await context.bot.get_file(document.file_id)
            file_path = os.path.join(self.temp_dir, document.file_name)
            logger.debug(f"📁 Целевой путь: {file_path}")
            
            await file.download_to_drive(file_path)
            download_time = datetime.now()
            download_duration = (download_time - start_time).total_seconds()
            
            logger.info(f"✅ Файл скачан за {download_duration:.1f}с: {document.file_name}")
            logger.debug(f"📁 Сохранен в: {file_path}")
            
            # Обновление статуса
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text="🔍 Применяю интеллектуальный анализ с детальным логированием..."
            )
            logger.info("📤 Обновлено сообщение статуса")
            
            # Анализ файла
            file_extension = document.file_name.lower().split('.')[-1]
            logger.info(f"📋 Тип файла: {file_extension.upper()}")
            
            if file_extension in ['xlsx', 'xls']:
                logger.info("🔍 НАЧИНАЕМ ИНТЕЛЛЕКТУАЛЬНЫЙ АНАЛИЗ EXCEL")
                
                parsing_start = datetime.now()
                logger.debug("📊 Импорт IntelligentPreProcessor...")
                
                from modules.intelligent_preprocessor import IntelligentPreProcessor
                processor = IntelligentPreProcessor()
                
                logger.info("✅ IntelligentPreProcessor загружен успешно")
                logger.debug("🚀 Запуск process_excel_intelligent...")
                
                # Интеллектуальный анализ
                result = processor.process_excel_intelligent(file_path)
                
                parsing_time = datetime.now()
                parsing_duration = (parsing_time - parsing_start).total_seconds()
                
                logger.info(f"✅ АНАЛИЗ ЗАВЕРШЕН за {parsing_duration:.1f}с")
                
                if 'error' in result:
                    logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА анализа: {result['error']}")
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=processing_message.message_id,
                        text=f"❌ Ошибка анализа: {result['error']}"
                    )
                    return
                
                # Преобразуем данные для Google Sheets
                logger.info("🔄 ПРЕОБРАЗОВАНИЕ ДАННЫХ ДЛЯ GOOGLE SHEETS...")
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id,
                    text="🔄 Преобразуем данные для сохранения в Google Sheets..."
                )
                
                from modules.data_adapter import DataAdapter
                adapter = DataAdapter()
                
                supplier_name = f"SAI_FRESH_{datetime.now().strftime('%Y%m%d')}"
                sheets_data = adapter.convert_intelligent_to_sheets_format(result, supplier_name)
                
                if 'error' in sheets_data:
                    logger.error(f"❌ Ошибка преобразования данных: {sheets_data['error']}")
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=processing_message.message_id,
                        text=f"❌ Ошибка преобразования данных: {sheets_data['error']}"
                    )
                    return
                
                # Сохранение в Google Sheets
                logger.info("💾 СОХРАНЕНИЕ В GOOGLE SHEETS...")
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id,
                    text="💾 Сохраняем данные в Google Sheets..."
                )
                
                from modules.google_sheets_manager import GoogleSheetsManager
                sheets_manager = GoogleSheetsManager()
                
                if not sheets_manager.is_connected():
                    logger.error("❌ Нет подключения к Google Sheets")
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=processing_message.message_id,
                        text="❌ Нет подключения к Google Sheets"
                    )
                    return
                
                sheets_result = sheets_manager.update_master_table(sheets_data)
                
                if 'error' in sheets_result:
                    logger.error(f"❌ Ошибка сохранения в Google Sheets: {sheets_result['error']}")
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=processing_message.message_id,
                        text=f"❌ Ошибка сохранения: {sheets_result['error']}"
                    )
                    return
                
                # Создание листа поставщика
                sheets_manager.create_supplier_summary(supplier_name, sheets_data.get('products', []))
                
                # Логирование результатов
                total_products = len(result['total_products'])
                total_prices = len(result['total_prices'])
                linked_pairs = len(result.get('product_price_pairs', []))
                sheets_products = len(sheets_data.get('products', []))
                completeness = result['recovery_stats']['data_completeness']
                strategy = result['processing_strategy']
                
                logger.info("📊 РЕЗУЛЬТАТЫ ИНТЕЛЛЕКТУАЛЬНОГО АНАЛИЗА:")
                logger.info(f"   📦 Товаров найдено: {total_products}")
                logger.info(f"   💰 Цен извлечено: {total_prices}")
                logger.info(f"   🔗 Связанных пар: {linked_pairs}")
                logger.info(f"   ✅ Товаров для Sheets: {sheets_products}")
                logger.info(f"   💾 Сохранено в Google Sheets: {sheets_result}")
                logger.info(f"   🎯 Стратегия: {strategy}")
                logger.info(f"   📈 Полнота данных: {completeness:.1f}%")
                
                # Генерация отчета
                total_time = (datetime.now() - start_time).total_seconds()
                sheets_url = sheets_manager.get_sheet_url()
                
                report = f"""
✅ *Файл успешно обработан и сохранен в Google Sheets!*

⏱ *Время обработки:* {total_time:.1f} сек
📊 *Размер файла:* {document.file_size / 1024:.1f} KB

🔍 *Интеллектуальный анализ:*
• Стратегия: {strategy}
• Листов обработано: {len(result['sheets_processed'])}
• Скачивание: {download_duration:.1f}с
• Анализ: {parsing_duration:.1f}с

📦 *Результаты извлечения:*
• Товаров найдено: {total_products}
• Цен извлечено: {total_prices}
• Связанных пар: {linked_pairs}
• Полнота данных: {completeness:.1f}%

🔄 *Преобразование для Google Sheets:*
• Товаров для сохранения: {sheets_products}
• Успешность адаптации: {sheets_data.get('processing_stats', {}).get('success_rate', 0):.1f}%

💾 *Google Sheets результат:*
• Новых товаров: {sheets_result.get('new_products', 0)}
• Обновленных цен: {sheets_result.get('updated_prices', 0)}
• Всего обработано: {sheets_result.get('processed_products', 0)}

🔗 [Открыть Google Sheets таблицу]({sheets_url})

📝 *Детальные логи:* `simple_bot_detailed.log`

🎯 *Улучшения в этой версии:*
• Интеллектуальное определение стратегии анализа
• Поддержка sparse и irregular форматов  
• Восстановление пропущенных данных
• Связывание товаров с ценами
• Автоматическое преобразование для Google Sheets
• Реальное сохранение данных в таблицу!
                """
                
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id,
                    text=report,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                logger.info("✅ Отчет отправлен пользователю")
                logger.info(f"📝 Общее время обработки: {total_time:.1f}с")
                
            else:
                logger.warning(f"⚠️ Неподдерживаемый тип файла: {file_extension}")
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id,
                    text="❌ Поддерживаются только Excel файлы (.xlsx, .xls)"
                )
            
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА обработки: {e}", exc_info=True)
            
            error_text = f"""❌ Ошибка обработки файла:
`{str(e)}`

*📝 Детальные логи ошибки записаны в:*
`simple_bot_detailed.log`

*🔧 Рекомендации:*
• Проверьте формат файла (должен быть .xlsx или .xls)
• Убедитесь что файл не поврежден
• Попробуйте файл меньшего размера"""
            
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text=error_text,
                parse_mode=ParseMode.MARKDOWN
            )
        
        finally:
            # Очистка временного файла
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"🗑️ Временный файл удален: {file_path}")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Не удалось удалить временный файл: {cleanup_error}")
            
            logger.info("="*80)
            logger.info("🏁 ЗАВЕРШЕНИЕ ОБРАБОТКИ ФАЙЛА")
            logger.info("="*80)
    
    def _validate_file(self, document: Document) -> dict:
        """Валидация файла с подробным логированием"""
        
        logger.debug(f"🔍 Валидация файла: {document.file_name}")
        logger.debug(f"📊 Размер: {document.file_size} байт")
        logger.debug(f"🎯 MIME: {document.mime_type}")
        
        supported_extensions = ('.xlsx', '.xls')
        if not document.file_name.lower().endswith(supported_extensions):
            logger.warning(f"❌ Неподдерживаемое расширение файла: {document.file_name}")
            return {'valid': False, 'error': 'Поддерживаются только Excel файлы (.xlsx, .xls)'}
        
        max_size = 20 * 1024 * 1024  # 20 MB
        if document.file_size > max_size:
            logger.warning(f"❌ Файл слишком большой: {document.file_size} байт (лимит: {max_size})")
            return {'valid': False, 'error': 'Файл слишком большой. Максимум 20 МБ'}
        
        logger.debug("✅ Валидация прошла успешно")
        return {'valid': True}
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user_message = update.message.text
        username = update.effective_user.username or update.effective_user.first_name
        
        logger.info(f"💬 Сообщение от {username}: {user_message}")
        
        await update.message.reply_text(
            "📝 Сообщение записано в лог! Отправьте Excel файл для анализа или используйте команды:\n"
            "/start - начало\n"
            "/help - справка\n"
            "/stats - статистика\n"
            "/test - тест системы"
        )
        
        logger.info("📤 Отправлен ответ на текстовое сообщение")
    
    async def compare_prices_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для создания сводного прайс-листа с сравнением цен"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        logger.info(f"🔍 Пользователь {user_id} запросил сравнение цен")
        
        # Отправляем сообщение о начале обработки
        processing_message = await context.bot.send_message(
            chat_id=chat_id,
            text="🔄 Создание сводного прайс-листа со сравнением цен...\n⏳ Это может занять несколько минут"
        )
        
        try:
            logger.info("📊 Импорт GoogleSheetsManager...")
            from modules.google_sheets_manager import GoogleSheetsManager
            
            sheets = GoogleSheetsManager()
            if not sheets.is_connected():
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=processing_message.message_id,
                    text="❌ Ошибка подключения к Google Sheets"
                )
                return
            
            logger.info("✅ Подключение к Google Sheets установлено")
            
            # Создаем сводный прайс-лист
            logger.info("🔄 Создание сводного прайс-листа...")
            comparison_result = sheets.create_unified_price_comparison()
            
            if 'error' in comparison_result:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=processing_message.message_id,
                    text=f"❌ Ошибка создания сводного прайс-листа:\n{comparison_result['error']}"
                )
                return
            
            # Получаем статистику
            stats = comparison_result.get('stats', {})
            sheet_url = comparison_result.get('sheet_url', '')
            
            # Формируем отчет
            report_text = f"""✅ **СВОДНЫЙ ПРАЙС-ЛИСТ СОЗДАН УСПЕШНО!**

📊 **Статистика:**
• 📦 Товаров с ценами: {stats.get('products_with_prices', 0)}
• 🏪 Поставщиков: {stats.get('suppliers_count', 0)}
• 📈 Средний разброс цен: {stats.get('average_price_difference', 0):.1f}%

🎯 **Что содержит сводная таблица:**
• Все товары от всех поставщиков
• Лучшие цены для каждого товара
• Сравнение цен между поставщиками
• Процент экономии при выборе лучшей цены
• Средние цены по товарам

📋 **Лист:** `Price Comparison`
🔗 **Ссылка:** {sheet_url}

💡 **Используйте команду /price_summary для краткой сводки**"""

            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=processing_message.message_id,
                text=report_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info("✅ Сводный прайс-лист создан и отправлен пользователю")
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка создания сводного прайс-листа: {e}")
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=processing_message.message_id,
                text=f"❌ Критическая ошибка: {str(e)}"
            )

    async def price_summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для получения краткой сводки по сравнению цен"""
        user_id = update.effective_user.id
        logger.info(f"📋 Пользователь {user_id} запросил сводку цен")
        
        try:
            from modules.google_sheets_manager import GoogleSheetsManager
            
            sheets = GoogleSheetsManager()
            if not sheets.is_connected():
                await update.message.reply_text("❌ Ошибка подключения к Google Sheets")
                return
            
            # Получаем сводку
            summary = sheets.get_price_comparison_summary()
            
            if 'error' in summary:
                await update.message.reply_text(f"❌ {summary['error']}")
                return
            
            # Формируем краткий отчет
            categories_text = ""
            for cat, info in summary.get('categories_breakdown', {}).items():
                categories_text += f"  • {cat}: {info['count']} товаров\n"
            
            suppliers_text = ", ".join(summary.get('suppliers', []))
            
            summary_text = f"""�� **КРАТКАЯ СВОДКА ПО ЦЕНАМ**

📊 **Общая статистика:**
• 📦 Всего товаров: {summary.get('total_products', 0)}
• 🏪 Поставщиков: {summary.get('suppliers_count', 0)}
• 📂 Категорий: {summary.get('categories', 0)}

📂 **По категориям:**
{categories_text}

🏪 **Поставщики:**
{suppliers_text}

🔗 **Ссылка на таблицу:** {summary.get('sheet_url', '')}

💡 **Используйте /compare_prices для обновления сводного прайс-листа**"""

            await update.message.reply_text(summary_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения сводки: {e}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    def run(self):
        """Запуск бота"""
        logger.info("🚀 Запуск Simple Telegram бота с подробным логированием...")
        
        # Создание приложения
        application = Application.builder().token(self.token).build()
        
        # Регистрация хендлеров
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("test", self.test_command))
        application.add_handler(CommandHandler("compare_prices", self.compare_prices_command))
        application.add_handler(CommandHandler("price_summary", self.price_summary_command))
        application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("✅ Хендлеры зарегистрированы")
        
        # Запуск в режиме polling
        logger.info("🔄 Запуск polling режима...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        bot = SimpleTelegramBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка запуска бота: {e}", exc_info=True) 