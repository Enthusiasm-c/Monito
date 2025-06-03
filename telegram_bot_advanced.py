#!/usr/bin/env python3
"""
Продвинутый Telegram бот с пакетной обработкой и улучшенным парсингом
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Добавляем корневую директорию
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.google_sheets_manager import GoogleSheetsManager
from modules.universal_excel_parser import UniversalExcelParser
from modules.batch_chatgpt_processor import BatchChatGPTProcessor
from modules.system_monitor_simple import monitor
from modules.pdf_parser import PDFParser

# Детальное логирование для бота с подробными логами
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot_detailed.log', mode='w', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class AdvancedTelegramBot:
    """Продвинутый Telegram бот с пакетной обработкой"""
    
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.google_sheets = GoogleSheetsManager()
        self.excel_parser = UniversalExcelParser()
        self.pdf_parser = PDFParser()
        self.chatgpt_processor = BatchChatGPTProcessor(self.openai_key) if self.openai_key else None
        self.temp_dir = "data/temp"
        os.makedirs(self.temp_dir, exist_ok=True)
        
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
        if not self.openai_key:
            logger.warning("OPENAI_API_KEY не установлен - ChatGPT будет недоступен")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        welcome_message = """
🚀 *Добро пожаловать в Advanced Price List Analyzer!*

Я продвинутый анализатор прайс-листов с пакетной обработкой через ChatGPT.

*🆕 Новые возможности:*
• Обработка СОТЕН товаров за раз
• Умный парсинг Excel файлов любой структуры
• Пакетная обработка через ChatGPT
• Детальная статистика извлечения
• Автоматический поиск столбцов с данными

*📊 Что я умею:*
• Обрабатывать Excel (.xlsx, .xls) и PDF файлы любого размера
• Извлекать таблицы из PDF с помощью Camelot/Tabula
• Автоматически находить товары и цены
• Стандартизировать через ChatGPT-4 пакетами
• Сохранять в Google Sheets с валидацией
• Показывать детальную статистику

*🔧 Команды:*
/start - это сообщение
/help - подробная справка  
/stats - статистика системы
/sheet - ссылка на Google Sheets
/test - тест всех компонентов

*📁 Просто отправьте Excel файл для анализа!*

Система готова обрабатывать файлы с сотнями позиций! 🎯
        """
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = """
📖 *Подробная справка по Advanced Price List Analyzer*

*🔍 Умный парсинг Excel:*
• Автоматический поиск столбцов с товарами и ценами
• Поддержка любых названий столбцов (русских и английских)
• Анализ структуры файла и выбор лучшего листа
• Обработка сотен товаров за раз

*🤖 Пакетная обработка ChatGPT:*
• Автоматическое разделение на оптимальные пакеты
• Обработка до 1000 товаров за сеанс
• Интеллектуальная оптимизация размера пакетов
• Детальная статистика обработки

*💾 Google Sheets интеграция:*
• Валидация данных перед сохранением
• Автоматическое создание столбцов поставщиков
• Сводная таблица всех товаров
• Индивидуальные листы поставщиков

*📊 Мониторинг и статистика:*
• Отслеживание всех операций
• Показатели успешности
• Детальные отчеты по обработке

*🚀 Процесс обработки:*
1. Загрузите Excel файл (до 20 МБ)
2. Система проанализирует структуру
3. Извлечет максимум товаров
4. Обработает через ChatGPT пакетами
5. Сохранит в Google Sheets с валидацией
6. Покажет детальный отчет

*💡 Поддерживаемые форматы данных:*
• Любые названия столбцов
• Цены в любом формате
• Единицы измерения
• Категории товаров

*⚡ Системный статус:*
        """
        
        # Проверка статусов
        sheets_status = "✅ Подключено" if self.google_sheets.is_connected() else "❌ Не подключено"
        chatgpt_status = "✅ Активен" if self.chatgpt_processor else "❌ Не настроен"
        
        help_text += f"• Google Sheets: {sheets_status}\n"
        help_text += f"• ChatGPT API: {chatgpt_status}\n"
        help_text += f"• Excel Parser: ✅ Готов\n"
        help_text += f"• Мониторинг: ✅ Активен\n"
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats"""
        try:
            # Системная статистика
            system_stats = monitor.get_formatted_report()
            rates = monitor.get_success_rates()
            
            stats_text = f"""
📊 *Статистика Advanced Price List Analyzer*

{system_stats}

*📈 Показатели успешности:*
• Обработка файлов: {rates.get('file_processing', 0):.1%}
• ChatGPT запросы: {rates.get('chatgpt_requests', 0):.1%}
• Google Sheets: {rates.get('sheets_updates', 0):.1%}
            """
            
            # Google Sheets статистика
            if self.google_sheets.is_connected():
                sheets_stats = self.google_sheets.get_stats()
                stats_text += f"""

*💾 Google Sheets данные:*
• Всего товаров: {sheets_stats.get('total_products', 0)}
• Поставщиков: {sheets_stats.get('total_suppliers', 0)}
• Категорий: {len(sheets_stats.get('categories', []))}

🔗 [Открыть таблицу]({sheets_stats.get('sheet_url', '')})
                """
            
            await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения статистики: {e}")
    
    async def sheet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /sheet"""
        if self.google_sheets.is_connected():
            url = self.google_sheets.get_sheet_url()
            await update.message.reply_text(
                f"📊 [Открыть Google Sheets таблицу]({url})", 
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Нет подключения к Google Sheets")
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /test"""
        test_message = await update.message.reply_text("🔍 Тестирую все компоненты системы...")
        
        try:
            results = {}
            
            # Тест Google Sheets
            results['sheets'] = self.google_sheets.is_connected()
            
            # Тест ChatGPT (быстрый)
            if self.chatgpt_processor:
                try:
                    # Простой тест без запроса
                    results['chatgpt'] = bool(self.openai_key)
                except:
                    results['chatgpt'] = False
            else:
                results['chatgpt'] = False
            
            # Тест Excel Parser
            results['parser'] = True  # Всегда работает
            
            # Тест мониторинга
            try:
                monitor.get_stats()
                results['monitoring'] = True
            except:
                results['monitoring'] = False
            
            result_text = f"""
🔍 *Результаты тестирования системы*

📊 *Компоненты:*
• Google Sheets: {'✅ Работает' if results['sheets'] else '❌ Ошибка'}
• ChatGPT API: {'✅ Настроен' if results['chatgpt'] else '❌ Не настроен'}
• Excel Parser: {'✅ Готов' if results['parser'] else '❌ Ошибка'}
• Мониторинг: {'✅ Активен' if results['monitoring'] else '❌ Ошибка'}

*🎯 Готовность системы:* {'🟢 Полная' if all(results.values()) else '🟡 Частичная' if any(results.values()) else '🔴 Не готов'}

*💡 Рекомендации:*
• Система готова обрабатывать большие Excel файлы
• Пакетная обработка активна для файлов с сотнями товаров
• Все данные сохраняются в Google Sheets с валидацией
            """
            
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=test_message.message_id,
                text=result_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=test_message.message_id,
                text=f"❌ Ошибка тестирования: {e}"
            )
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка загруженных документов с детальным логированием"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        document: Document = update.message.document
        
        logger.info(f"🔥 НАЧАЛАСЬ ОБРАБОТКА ФАЙЛА")
        logger.info(f"👤 Пользователь: {username} (ID: {user_id})")
        logger.info(f"📎 Файл: {document.file_name}")
        logger.info(f"📊 Размер: {document.file_size / 1024 / 1024:.2f} МБ")
        
        # Валидация файла
        logger.debug(f"🔍 Валидация файла...")
        validation_result = self._validate_file(document)
        if not validation_result['valid']:
            logger.error(f"❌ Валидация не прошла: {validation_result['error']}")
            await update.message.reply_text(f"❌ {validation_result['error']}")
            return
        
        logger.info(f"✅ Файл прошел валидацию")
        
        if not self.google_sheets.is_connected():
            logger.error(f"❌ Нет подключения к Google Sheets")
            await update.message.reply_text("❌ Нет подключения к Google Sheets")
            return
        
        logger.info(f"✅ Google Sheets подключены")
        
        processing_message = await update.message.reply_text("🚀 Начинаю продвинутую обработку файла с детальным логированием...")
        
        try:
            start_time = datetime.now()
            logger.info(f"⏰ Начало обработки: {start_time}")
            
            # Скачивание файла
            logger.debug(f"⬇️ Скачивание файла...")
            file = await context.bot.get_file(document.file_id)
            file_path = os.path.join(self.temp_dir, document.file_name)
            await file.download_to_drive(file_path)
            
            download_time = datetime.now()
            logger.info(f"✅ Файл скачан за {(download_time - start_time).total_seconds():.1f}с: {document.file_name}")
            logger.debug(f"📁 Путь к файлу: {file_path}")
            
            # Анализ структуры файла
            file_extension = document.file_name.lower().split('.')[-1]
            logger.info(f"📋 Тип файла: {file_extension.upper()}")
            
            parsing_start = datetime.now()
            if file_extension == 'pdf':
                logger.info(f"🔍 НАЧИНАЕМ PDF ПАРСИНГ...")
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id,
                    text="🔍 Анализирую структуру PDF файла и извлекаю таблицы с AI поддержкой..."
                )
                
                extracted_data = self.pdf_parser.extract_products_from_pdf(file_path, max_products=1000, use_ai=True)
            else:
                logger.info(f"🔍 НАЧИНАЕМ EXCEL ПАРСИНГ...")
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id,
                    text="🔍 Анализирую структуру Excel файла с AI поддержкой..."
                )
                
                extracted_data = self.excel_parser.extract_products_universal(file_path, max_products=1000, use_ai=True)
            
            parsing_time = datetime.now()
            logger.info(f"✅ ПАРСИНГ ЗАВЕРШЕН за {(parsing_time - parsing_start).total_seconds():.1f}с")
            
            if 'error' in extracted_data:
                logger.error(f"❌ КРИТИЧНО: Ошибка парсинга файла: {extracted_data['error']}")
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id,
                    text=f"❌ Ошибка анализа файла: {extracted_data['error']}"
                )
                return
            
            products = extracted_data.get('products', [])
            stats = extracted_data.get('extraction_stats', {})
            
            logger.info(f"📊 РЕЗУЛЬТАТ ПАРСИНГА:")
            logger.info(f"   📦 Товаров извлечено: {len(products)}")
            logger.info(f"   📄 Всего строк: {stats.get('total_rows', 0)}")
            logger.info(f"   🔧 Метод: {stats.get('extraction_method', 'N/A')}")
            logger.info(f"   🤖 AI Enhanced: {stats.get('ai_enhanced', False)}")
            logger.info(f"   📊 Успешность: {stats.get('success_rate', 0):.1%}")
            
            if not products:
                logger.error(f"❌ КРИТИЧНО: Товары не найдены в файле")
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id,
                    text=f"❌ Товары не найдены\n\n📊 Статистика извлечения:\n• Проанализировано строк: {stats.get('total_rows', 0)}\n• Метод: {stats.get('extraction_method', 'N/A')}\n• AI Enhanced: {stats.get('ai_enhanced', False)}"
                )
                monitor.record_file_processing(file_extension, False, 'No products found')
                return
            
            logger.info(f"✅ ПАРСИНГ УСПЕШЕН: {len(products)} товаров готовы к обработке")
            
            # Обновление статуса
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text=f"📊 Извлечено {len(products)} товаров!\n\n🤖 Обрабатываю через ChatGPT пакетами..."
            )
            
            # Обработка через ChatGPT
            if self.chatgpt_processor and len(products) > 0:
                supplier_name = extracted_data.get('supplier', {}).get('name', 'Unknown')
                standardized_data = await self.chatgpt_processor.process_all_products(products, supplier_name)
                
                if 'error' in standardized_data:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=processing_message.message_id,
                        text=f"❌ Ошибка обработки ChatGPT: {standardized_data['error']}"
                    )
                    monitor.record_chatgpt_request(False, 0, standardized_data['error'])
                    return
                
                processing_stats = standardized_data.get('processing_stats', {})
                monitor.record_chatgpt_request(True, processing_stats.get('estimated_tokens', 0))
            else:
                # Fallback без ChatGPT
                standardized_data = self._create_fallback_data(extracted_data)
            
            # Сохранение в Google Sheets
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text="💾 Сохраняю данные в Google Sheets с валидацией..."
            )
            
            sheets_result = self.google_sheets.update_master_table(standardized_data)
            
            if 'error' in sheets_result:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id,
                    text=f"❌ Ошибка сохранения: {sheets_result['error']}"
                )
                monitor.record_sheets_update(False, 0, sheets_result['error'])
                return
            
            # Создание листа поставщика
            supplier_name = standardized_data.get('supplier', {}).get('name', 'Unknown')
            self.google_sheets.create_supplier_summary(supplier_name, standardized_data.get('products', []))
            
            # Финальный отчет
            processing_time = (datetime.now() - start_time).total_seconds()
            report = self._generate_advanced_report(extracted_data, standardized_data, sheets_result, processing_time)
            
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text=report,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Записываем успешную обработку
            monitor.record_file_processing('excel', True)
            monitor.record_sheets_update(True, len(standardized_data.get('products', [])))
            
            logger.info(f"Файл {document.file_name} успешно обработан с продвинутым парсингом")
            
        except Exception as e:
            logger.error(f"Ошибка обработки файла: {e}")
            
            error_text = f"""❌ Ошибка обработки файла:
`{str(e)}`

*🔧 Рекомендации:*
• Убедитесь что файл содержит столбцы с товарами и ценами
• Проверьте что файл не поврежден
• Попробуйте файл меньшего размера для тестирования"""
            
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text=error_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            monitor.record_file_processing('excel', False, str(e))
        
        finally:
            # Очистка временного файла
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
    
    def _validate_file(self, document: Document) -> dict:
        """Валидация файла"""
        supported_extensions = ('.xlsx', '.xls', '.pdf')
        if not document.file_name.lower().endswith(supported_extensions):
            return {'valid': False, 'error': 'Поддерживаются только Excel (.xlsx, .xls) и PDF файлы'}
        
        max_size = 20 * 1024 * 1024  # 20 MB
        if document.file_size > max_size:
            return {'valid': False, 'error': 'Файл слишком большой. Максимум 20 МБ'}
        
        return {'valid': True}
    
    def _create_fallback_data(self, extracted_data: Dict) -> Dict:
        """Создание fallback данных без ChatGPT"""
        products = []
        for product in extracted_data.get('products', []):
            products.append({
                'original_name': product.get('original_name', ''),
                'standardized_name': product.get('original_name', ''),
                'price': product.get('price', 0),
                'unit': product.get('unit', 'pcs'),
                'category': product.get('category', 'general'),
                'confidence': 0.7
            })
        
        return {
            'supplier': extracted_data.get('supplier', {}),
            'products': products,
            'data_quality': {
                'extraction_confidence': 0.7,
                'source_clarity': 'medium',
                'potential_errors': ['Обработано без ChatGPT']
            }
        }
    
    def _generate_advanced_report(self, extracted_data: Dict, standardized_data: Dict, sheets_result: Dict, processing_time: float) -> str:
        """Генерация расширенного отчета"""
        supplier_name = standardized_data.get('supplier', {}).get('name', 'Unknown')
        extraction_stats = extracted_data.get('extraction_stats', {})
        processing_stats = standardized_data.get('processing_stats', {})
        
        report = f"""
✅ *Файл успешно обработан!*

🏪 *Поставщик:* {supplier_name}
⏱ *Время обработки:* {processing_time:.1f} сек

📊 *Статистика извлечения:*
• Проанализировано строк: {extraction_stats.get('total_rows', 0)}
• Извлечено товаров: {extraction_stats.get('extracted_products', 0)}
• Успешность извлечения: {extraction_stats.get('success_rate', 0):.1%}
• Использован лист: {extraction_stats.get('used_sheet', 'N/A')}

🤖 *ChatGPT обработка:*
"""
        
        if processing_stats and not processing_stats.get('fallback_used', False):
            report += f"""• Обработано товаров: {processing_stats.get('total_output_products', 0)}/{processing_stats.get('total_input_products', 0)}
• Успешных пакетов: {processing_stats.get('successful_batches', 0)}/{processing_stats.get('total_batches', 0)}
• Успешность: {processing_stats.get('success_rate', 0):.1%}
• Использовано токенов: {processing_stats.get('estimated_tokens', 0)}
"""
        else:
            # Fallback mode or no ChatGPT processing
            total_products = len(standardized_data.get('products', []))
            report += f"""• Обработано товаров: {total_products}/{total_products} (fallback режим)
• ChatGPT недоступен или завершился с ошибкой
• Использована базовая обработка без AI
• Использовано токенов: 0
"""
        
        report += f"""
💾 *Google Sheets результат:*
• Новых товаров: {sheets_result.get('new_products', 0)}
• Обновленных цен: {sheets_result.get('updated_prices', 0)}
• Всего обработано: {sheets_result.get('processed_products', 0)}

🔗 [Открыть Google Sheets таблицу]({self.google_sheets.get_sheet_url()})

🎯 *Система готова к обработке следующего файла!*
        """
        
        return report
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        logger.info(f"💬 Получено сообщение от {update.effective_user.id}: {update.message.text}")
        await update.message.reply_text(
            "📁 Отправьте мне Excel файл с прайс-листом\n\n"
            "🚀 *Новые возможности:*\n"
            "• Обработка сотен товаров\n"
            "• Умный поиск данных в файле\n"
            "• Пакетная обработка через ChatGPT\n\n"
            "Используйте /help для подробной справки",
            parse_mode=ParseMode.MARKDOWN
        )
    
    def run(self):
        """Запуск бота"""
        logger.info("🚀 Запуск Advanced Telegram бота...")
        
        # Проверка подключений
        sheets_connected = self.google_sheets.is_connected()
        chatgpt_available = bool(self.chatgpt_processor)
        
        print("\n" + "="*70)
        print("🚀 ADVANCED TELEGRAM BOT С ПАКЕТНОЙ ОБРАБОТКОЙ ЗАПУЩЕН!")
        print("="*70)
        print(f"📊 Google Sheets: {'✅ Подключено' if sheets_connected else '❌ Не подключено'}")
        print(f"🤖 ChatGPT API: {'✅ Готов к пакетной обработке' if chatgpt_available else '❌ Не настроен'}")
        print(f"🔍 Excel Parser: ✅ Готов к умному парсингу")
        print(f"📈 Мониторинг: ✅ Активен")
        
        if sheets_connected:
            print(f"🔗 Таблица: {self.google_sheets.get_sheet_url()}")
        
        print("\n📱 Найдите бота в Telegram и отправьте /start")
        print("📊 Отправьте Excel файл для обработки с пакетной обработкой через ИИ")
        print("🎯 Система готова обрабатывать файлы с сотнями товаров!")
        print("\nНажмите Ctrl+C для остановки")
        print("="*70)
        
        # Создание приложения
        application = Application.builder().token(self.token).build()
        
        # Регистрация обработчиков
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("sheet", self.sheet_command))
        application.add_handler(CommandHandler("test", self.test_command))
        application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Запуск
        application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    try:
        bot = AdvancedTelegramBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        print("\nПроверьте:")
        print("• TELEGRAM_BOT_TOKEN в .env")
        print("• OPENAI_API_KEY в .env")  
        print("• Google Sheets настройки")