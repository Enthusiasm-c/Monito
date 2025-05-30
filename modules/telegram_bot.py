import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

from config import (
    TELEGRAM_BOT_TOKEN, 
    MAX_FILE_SIZE, 
    ALLOWED_EXTENSIONS, 
    TEMP_DIR
)
from modules.file_processor import FileProcessor
from modules.ai_processor import AIProcessor
from modules.data_manager import DataManager
from modules.utils import setup_logging, validate_file, cleanup_temp_files

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.file_processor = FileProcessor()
        self.ai_processor = AIProcessor()
        self.data_manager = DataManager()
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        welcome_message = """
🤖 *Добро пожаловать в Анализатор Прайс-листов!*

Я помогу вам автоматически обработать прайс-листы поставщиков и свести их в единую таблицу.

*Что я умею:*
• Обрабатывать Excel файлы (.xlsx, .xls)
• Распознавать PDF файлы с помощью OCR
• Стандартизировать названия товаров через ИИ
• Создавать сводную таблицу со всеми поставщиками

*Как использовать:*
1. Отправьте мне файл прайс-листа
2. Дождитесь обработки
3. Получите результат

*Команды:*
/start - показать это сообщение
/help - подробная справка
/stats - статистика обработки

Просто отправьте файл для начала работы! 📊
        """
        
        await update.message.reply_text(
            welcome_message, 
            parse_mode=ParseMode.MARKDOWN
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📖 *Подробная справка*

*Поддерживаемые форматы:*
• Excel: .xlsx, .xls
• PDF: любые PDF файлы (текстовые и сканированные)

*Максимальный размер файла:* 20 МБ

*Что происходит при обработке:*
1. Извлечение данных из файла
2. Определение структуры прайс-листа
3. Поиск информации о поставщике
4. Стандартизация через GPT-4
5. Обновление основной таблицы

*Качество обработки:*
• Excel файлы: 95%+ точность
• PDF с текстом: 90%+ точность  
• Сканированные PDF: 80%+ точность

*Поддерживаемые языки:*
• Русский
• Английский
• Индонезийский

Если возникают проблемы, проверьте формат файла и его размер.
        """
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN
        )

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику обработки"""
        try:
            stats = self.data_manager.get_processing_stats()
            
            stats_text = f"""
📊 *Статистика обработки*

*Всего обработано файлов:* {stats.get('files_processed', 0)}
*Успешность обработки:* {stats.get('success_rate', 0):.1f}%
*Среднее время обработки:* {stats.get('avg_processing_time', 0):.1f} сек

*По типам файлов:*
• Excel: {stats.get('excel_success_rate', 0):.1f}%
• PDF: {stats.get('pdf_success_rate', 0):.1f}%

*Данные:*
• Добавлено товаров: {stats.get('products_added', 0)}
• Добавлено поставщиков: {stats.get('suppliers_added', 0)}

*Последнее обновление:* {stats.get('last_update', 'Никогда')}
            """
            
            await update.message.reply_text(
                stats_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            await update.message.reply_text(
                "❌ Ошибка получения статистики. Попробуйте позже."
            )

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик загружаемых документов"""
        document: Document = update.message.document
        
        # Валидация файла
        validation_result = validate_file(document.file_name, document.file_size)
        if not validation_result['valid']:
            await update.message.reply_text(f"❌ {validation_result['error']}")
            return

        # Отправка уведомления о начале обработки
        processing_message = await update.message.reply_text(
            "🔄 Начинаю обработку файла...\nЭто может занять несколько минут."
        )

        try:
            start_time = datetime.now()
            
            # Скачивание файла
            file = await context.bot.get_file(document.file_id)
            file_path = os.path.join(TEMP_DIR, document.file_name)
            await file.download_to_drive(file_path)
            
            logger.info(f"Начата обработка файла: {document.file_name}")
            
            # Обновление статуса
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text="📄 Извлекаю данные из файла..."
            )
            
            # Извлечение данных
            extracted_data = await self.file_processor.process_file(file_path)
            
            if not extracted_data or not extracted_data.get('products'):
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id,
                    text="❌ Не удалось извлечь данные из файла. Проверьте формат прайс-листа."
                )
                return
            
            # Обновление статуса
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text="🤖 Стандартизирую данные через ИИ..."
            )
            
            # Обработка через GPT
            standardized_data = await self.ai_processor.process_data(
                extracted_data, 
                file_type=extracted_data.get('file_type', 'unknown')
            )
            
            if not standardized_data:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id,
                    text="❌ Ошибка обработки данных через ИИ. Попробуйте позже."
                )
                return
            
            # Обновление статуса
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text="💾 Сохраняю данные в основную таблицу..."
            )
            
            # Сохранение в основную таблицу
            save_result = await self.data_manager.update_master_table(standardized_data)
            
            # Расчет времени обработки
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Формирование отчета
            report = self._generate_processing_report(
                standardized_data, 
                save_result, 
                processing_time
            )
            
            # Отправка результата
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text=report,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Логирование успешной обработки
            logger.info(f"Файл {document.file_name} успешно обработан за {processing_time:.1f} сек")
            
        except Exception as e:
            logger.error(f"Ошибка обработки файла {document.file_name}: {e}")
            
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text=f"❌ Ошибка обработки файла:\n`{str(e)}`",
                parse_mode=ParseMode.MARKDOWN
            )
            
        finally:
            # Очистка временных файлов
            cleanup_temp_files([file_path])

    def _generate_processing_report(self, data, save_result, processing_time):
        """Генерация отчета о результатах обработки"""
        supplier_name = data.get('supplier', {}).get('name', 'Неизвестный поставщик')
        products_count = len(data.get('products', []))
        
        quality = data.get('data_quality', {})
        confidence = quality.get('extraction_confidence', 0)
        
        # Определение качества обработки
        if confidence >= 0.9:
            quality_emoji = "🟢"
            quality_text = "Отличное"
        elif confidence >= 0.7:
            quality_emoji = "🟡"
            quality_text = "Хорошее"
        else:
            quality_emoji = "🔴"
            quality_text = "Удовлетворительное"
        
        report = f"""
✅ *Файл успешно обработан!*

*Поставщик:* {supplier_name}
*Обработано товаров:* {products_count}
*Время обработки:* {processing_time:.1f} сек

*Качество обработки:* {quality_emoji} {quality_text} ({confidence:.1%})

*Результат сохранения:*
• Новых товаров: {save_result.get('new_products', 0)}
• Обновленных цен: {save_result.get('updated_prices', 0)}
• Новый поставщик: {'Да' if save_result.get('new_supplier') else 'Нет'}

Данные добавлены в основную таблицу! 📊
        """
        
        # Добавление предупреждений если есть
        errors = quality.get('potential_errors', [])
        if errors:
            report += f"\n⚠️ *Предупреждения:*\n"
            for error in errors[:3]:  # Показываем первые 3 ошибки
                report += f"• {error}\n"
        
        return report

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        await update.message.reply_text(
            "📁 Пожалуйста, отправьте файл прайс-листа (.xlsx, .xls или .pdf)\n"
            "Используйте /help для получения подробной справки."
        )

    def run(self):
        """Запуск бота"""
        setup_logging()
        
        logger.info("Запуск Telegram бота...")
        
        # Создание приложения
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Регистрация обработчиков
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Запуск бота
        logger.info("Бот запущен и готов к работе!")
        application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()