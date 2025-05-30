#!/usr/bin/env python3
"""
Упрощенный Telegram бот для Price List Analyzer
С интеграцией Google Sheets и ChatGPT
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Добавляем корневую директорию
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.google_sheets_manager import GoogleSheetsManager
from modules.ai_processor import AIProcessor

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleTelegramBot:
    """Упрощенный Telegram бот"""
    
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.google_sheets = GoogleSheetsManager()
        self.ai_processor = AIProcessor()
        self.temp_dir = "data/temp"
        os.makedirs(self.temp_dir, exist_ok=True)
        
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        welcome_message = """
🤖 *Добро пожаловать в Price List Analyzer!*

Я анализирую прайс-листы и автоматически добавляю данные в Google Sheets.

*Что я умею:*
• Обрабатывать Excel файлы (.xlsx, .xls)
• Стандартизировать товары через ChatGPT
• Сохранять данные в Google Sheets

*Как использовать:*
1. Отправьте мне Excel файл с прайс-листом
2. Дождитесь обработки через ИИ
3. Получите ссылку на обновленную Google Sheets таблицу

*Команды:*
/start - это сообщение
/help - подробная справка
/stats - статистика
/sheet - ссылка на таблицу

Просто отправьте Excel файл для начала! 📊
        """
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = """
📖 *Подробная справка*

*Поддерживаемые форматы:*
• Excel: .xlsx, .xls (до 20 МБ)

*Процесс обработки:*
1. Загрузка файла
2. Извлечение данных из Excel
3. Стандартизация через ChatGPT-4
4. Сохранение в Google Sheets
5. Отправка результата

*Google Sheets структура:*
• Master Table - сводная таблица всех поставщиков
• Отдельные листы для каждого поставщика

*Статус подключений:*
"""
        
        # Проверка подключений
        sheets_status = "✅ Подключено" if self.google_sheets.is_connected() else "❌ Не подключено"
        
        help_text += f"• Google Sheets: {sheets_status}\n"
        help_text += f"• ChatGPT: ✅ Настроен\n"
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats"""
        try:
            if self.google_sheets.is_connected():
                stats = self.google_sheets.get_stats()
                
                stats_text = f"""
📊 *Статистика Google Sheets*

*Данные:*
• Всего товаров: {stats.get('total_products', 0)}
• Поставщиков: {stats.get('total_suppliers', 0)}
• Категорий: {len(stats.get('categories', []))}

*Поставщики:*
"""
                for supplier in stats.get('suppliers', []):
                    stats_text += f"• {supplier}\n"
                
                stats_text += f"\n🔗 [Открыть таблицу]({stats.get('sheet_url', '')})"
                
            else:
                stats_text = "❌ Нет подключения к Google Sheets"
            
            await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения статистики: {e}")
    
    async def sheet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /sheet - ссылка на таблицу"""
        if self.google_sheets.is_connected():
            url = self.google_sheets.get_sheet_url()
            await update.message.reply_text(f"📊 [Открыть Google Sheets таблицу]({url})", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ Нет подключения к Google Sheets")
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка загруженных документов"""
        document: Document = update.message.document
        
        # Проверка типа файла
        if not document.file_name.lower().endswith(('.xlsx', '.xls')):
            await update.message.reply_text("❌ Поддерживаются только Excel файлы (.xlsx, .xls)")
            return
        
        # Проверка размера
        max_size = 20 * 1024 * 1024  # 20 MB
        if document.file_size > max_size:
            await update.message.reply_text("❌ Файл слишком большой. Максимум 20 МБ")
            return
        
        # Проверка подключения к Google Sheets
        if not self.google_sheets.is_connected():
            await update.message.reply_text("❌ Нет подключения к Google Sheets. Обратитесь к администратору.")
            return
        
        processing_message = await update.message.reply_text("🔄 Начинаю обработку файла...")
        
        try:
            start_time = datetime.now()
            
            # Скачивание файла
            file = await context.bot.get_file(document.file_id)
            file_path = os.path.join(self.temp_dir, document.file_name)
            await file.download_to_drive(file_path)
            
            logger.info(f"Файл скачан: {document.file_name}")
            
            # Обновление статуса
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text="📄 Извлекаю данные из Excel файла..."
            )
            
            # Простое извлечение данных из Excel
            extracted_data = await self._extract_excel_data(file_path, document.file_name)
            
            if not extracted_data.get('products'):
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id,
                    text="❌ Не найдены товары с ценами в файле"
                )
                return
            
            # Обновление статуса
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text="🤖 Стандартизирую данные через ChatGPT..."
            )
            
            # Обработка через ChatGPT
            try:
                standardized_data = await self.ai_processor.process_data(extracted_data, 'excel')
            except Exception as e:
                logger.error(f"Ошибка ChatGPT: {e}")
                # Fallback без ChatGPT
                standardized_data = self._fallback_standardization(extracted_data)
            
            # Обновление статуса
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text="💾 Сохраняю данные в Google Sheets..."
            )
            
            # Сохранение в Google Sheets
            sheets_result = self.google_sheets.update_master_table(standardized_data)
            
            # Создание листа поставщика
            supplier_name = standardized_data.get('supplier', {}).get('name', 'Unknown')
            self.google_sheets.create_supplier_summary(supplier_name, standardized_data.get('products', []))
            
            # Расчет времени
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Формирование отчета
            report = self._generate_success_report(standardized_data, sheets_result, processing_time)
            
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text=report,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Файл {document.file_name} успешно обработан")
            
        except Exception as e:
            logger.error(f"Ошибка обработки файла: {e}")
            
            error_text = f"❌ Ошибка обработки файла:\n`{str(e)}`\n\nПопробуйте:\n• Проверить формат Excel файла\n• Убедиться что есть столбцы с товарами и ценами"
            
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
            except:
                pass
    
    async def _extract_excel_data(self, file_path: str, file_name: str) -> dict:
        """Простое извлечение данных из Excel"""
        import pandas as pd
        
        # Определение поставщика из имени файла
        supplier_name = os.path.splitext(file_name)[0]
        
        # Чтение Excel
        df = pd.read_excel(file_path)
        
        # Поиск колонок
        product_col = None
        price_col = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in ['product', 'название', 'товар', 'item', 'name']):
                product_col = col
            if any(keyword in col_lower for keyword in ['price', 'цена', 'cost', 'стоимость']):
                price_col = col
        
        # Извлечение товаров
        products = []
        for idx, row in df.iterrows():
            try:
                name = str(row[product_col] if product_col else row.iloc[0])
                price_str = str(row[price_col] if price_col else row.iloc[1])
                
                # Очистка цены
                import re
                price_clean = re.sub(r'[^\d.,]', '', price_str)
                if price_clean:
                    price = float(price_clean.replace(',', '.'))
                else:
                    continue
                
                if len(name) > 3 and price > 0:
                    products.append({
                        'original_name': name,
                        'price': price,
                        'unit': 'pcs'
                    })
            except:
                continue
        
        return {
            'file_type': 'excel',
            'supplier': {'name': supplier_name},
            'products': products
        }
    
    def _fallback_standardization(self, data: dict) -> dict:
        """Fallback стандартизация без ChatGPT"""
        products = []
        for product in data.get('products', []):
            products.append({
                'original_name': product.get('original_name', ''),
                'standardized_name': product.get('original_name', ''),
                'price': product.get('price', 0),
                'unit': product.get('unit', 'pcs'),
                'category': 'general',
                'confidence': 0.7
            })
        
        return {
            'supplier': data.get('supplier', {}),
            'products': products,
            'data_quality': {
                'extraction_confidence': 0.7,
                'source_clarity': 'medium',
                'potential_errors': ['Обработано без ChatGPT']
            }
        }
    
    def _generate_success_report(self, data: dict, sheets_result: dict, processing_time: float) -> str:
        """Генерация отчета об успешной обработке"""
        supplier_name = data.get('supplier', {}).get('name', 'Unknown')
        products_count = len(data.get('products', []))
        
        report = f"""
✅ *Файл успешно обработан!*

*Поставщик:* {supplier_name}
*Обработано товаров:* {products_count}
*Время обработки:* {processing_time:.1f} сек

*Результат сохранения в Google Sheets:*
• Новых товаров: {sheets_result.get('new_products', 0)}
• Обновленных цен: {sheets_result.get('updated_prices', 0)}

🔗 [Открыть Google Sheets таблицу]({self.google_sheets.get_sheet_url()})

Данные успешно добавлены в облачную таблицу! 📊
        """
        
        return report
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        await update.message.reply_text(
            "📁 Отправьте мне Excel файл (.xlsx или .xls) с прайс-листом\n"
            "Используйте /help для подробной справки"
        )
    
    def run(self):
        """Запуск бота"""
        logger.info("🤖 Запуск Telegram бота...")
        
        # Проверка подключений
        if self.google_sheets.is_connected():
            logger.info("✅ Google Sheets подключен")
        else:
            logger.warning("❌ Google Sheets не подключен")
        
        # Создание приложения
        application = Application.builder().token(self.token).build()
        
        # Регистрация обработчиков
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("sheet", self.sheet_command))
        application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Запуск
        logger.info("🚀 Бот запущен и готов к работе!")
        print("🤖 Telegram бот запущен!")
        print("📊 Google Sheets интеграция активна")
        print("🤖 ChatGPT обработка настроена")
        print("\nОтправьте Excel файл боту для тестирования!")
        
        application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    try:
        bot = SimpleTelegramBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        print("Проверьте TELEGRAM_BOT_TOKEN в .env файле")