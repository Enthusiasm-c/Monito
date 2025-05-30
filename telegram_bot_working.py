#!/usr/bin/env python3
"""
Рабочий Telegram бот для Price List Analyzer
С Google Sheets интеграцией (без ChatGPT временно)
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

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class WorkingTelegramBot:
    """Рабочий Telegram бот с Google Sheets"""
    
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.google_sheets = GoogleSheetsManager()
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
• Извлекать товары и цены
• Сохранять данные в Google Sheets
• Создавать сводные таблицы

*Как использовать:*
1. Отправьте мне Excel файл с прайс-листом
2. Дождитесь обработки
3. Получите ссылку на обновленную Google Sheets таблицу

*Команды:*
/start - это сообщение
/help - подробная справка
/stats - статистика таблицы
/sheet - ссылка на Google Sheets

Просто отправьте Excel файл для начала! 📊
        """
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = """
📖 *Подробная справка*

*Поддерживаемые форматы:*
• Excel: .xlsx, .xls (до 20 МБ)

*Требования к файлу:*
• Должны быть столбцы с названиями товаров
• Должны быть столбцы с ценами
• Цены в числовом формате

*Процесс обработки:*
1. Загрузка и валидация файла
2. Извлечение данных из Excel
3. Автоматическое определение товаров и цен
4. Создание/обновление Google Sheets таблицы
5. Отправка результата с ссылкой

*Google Sheets структура:*
• Master Table - сводная таблица всех поставщиков
• Отдельные листы для каждого поставщика

*Статус подключений:*
"""
        
        # Проверка подключений
        sheets_status = "✅ Подключено" if self.google_sheets.is_connected() else "❌ Не подключено"
        help_text += f"• Google Sheets: {sheets_status}\n"
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats"""
        try:
            if self.google_sheets.is_connected():
                stats = self.google_sheets.get_stats()
                
                stats_text = f"""
📊 *Статистика Google Sheets*

*Общие данные:*
• Всего товаров: {stats.get('total_products', 0)}
• Поставщиков: {stats.get('total_suppliers', 0)}
• Категорий: {len(stats.get('categories', []))}

*Поставщики:*
"""
                suppliers = stats.get('suppliers', [])
                if suppliers:
                    for supplier in suppliers[:10]:  # Показываем первых 10
                        stats_text += f"• {supplier}\n"
                    if len(suppliers) > 10:
                        stats_text += f"• ... и еще {len(suppliers) - 10}\n"
                else:
                    stats_text += "• Пока нет поставщиков\n"
                
                stats_text += f"\n🔗 [Открыть таблицу]({stats.get('sheet_url', '')})"
                
            else:
                stats_text = "❌ Нет подключения к Google Sheets\nОбратитесь к администратору"
            
            await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка получения статистики: {e}")
    
    async def sheet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /sheet - ссылка на таблицу"""
        if self.google_sheets.is_connected():
            url = self.google_sheets.get_sheet_url()
            await update.message.reply_text(
                f"📊 [Открыть Google Sheets таблицу]({url})", 
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text("❌ Нет подключения к Google Sheets")
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка загруженных документов"""
        document: Document = update.message.document
        
        # Валидация файла
        validation_result = self._validate_file(document)
        if not validation_result['valid']:
            await update.message.reply_text(f"❌ {validation_result['error']}")
            return
        
        # Проверка подключения к Google Sheets
        if not self.google_sheets.is_connected():
            await update.message.reply_text(
                "❌ Нет подключения к Google Sheets. Обратитесь к администратору."
            )
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
            
            # Извлечение данных из Excel
            extracted_data = await self._extract_excel_data(file_path, document.file_name)
            
            if not extracted_data.get('products'):
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id,
                    text="❌ Не найдены товары с ценами в файле\n\nПроверьте что в файле есть:\n• Столбец с названиями товаров\n• Столбец с ценами в числовом формате"
                )
                return
            
            # Обновление статуса
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text="💾 Сохраняю данные в Google Sheets..."
            )
            
            # Простая стандартизация данных
            standardized_data = self._standardize_data(extracted_data)
            
            # Сохранение в Google Sheets
            sheets_result = self.google_sheets.update_master_table(standardized_data)
            
            if 'error' in sheets_result:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id,
                    text=f"❌ Ошибка сохранения в Google Sheets:\n{sheets_result['error']}"
                )
                return
            
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
            
            error_text = f"""❌ Ошибка обработки файла:
`{str(e)}`

*Попробуйте:*
• Проверить формат Excel файла
• Убедиться что есть столбцы с товарами и ценами
• Отправить файл меньшего размера
• Использовать более простую структуру данных"""
            
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
    
    def _validate_file(self, document: Document) -> dict:
        """Валидация загружаемого файла"""
        # Проверка расширения
        if not document.file_name.lower().endswith(('.xlsx', '.xls')):
            return {
                'valid': False,
                'error': 'Поддерживаются только Excel файлы (.xlsx, .xls)'
            }
        
        # Проверка размера
        max_size = 20 * 1024 * 1024  # 20 MB
        if document.file_size > max_size:
            return {
                'valid': False,
                'error': 'Файл слишком большой. Максимальный размер: 20 МБ'
            }
        
        return {'valid': True}
    
    async def _extract_excel_data(self, file_path: str, file_name: str) -> dict:
        """Извлечение данных из Excel файла"""
        import pandas as pd
        
        # Определение поставщика из имени файла
        supplier_name = os.path.splitext(file_name)[0]
        
        # Чтение Excel файла
        df = pd.read_excel(file_path)
        
        logger.info(f"Excel файл прочитан: {len(df)} строк, {len(df.columns)} столбцов")
        
        # Поиск столбцов с товарами и ценами
        product_col = None
        price_col = None
        
        # Поиск по ключевым словам
        for col in df.columns:
            col_lower = str(col).lower()
            
            # Поиск столбца с товарами
            if any(keyword in col_lower for keyword in ['product', 'название', 'товар', 'item', 'name', 'наименование']):
                product_col = col
                
            # Поиск столбца с ценами
            if any(keyword in col_lower for keyword in ['price', 'цена', 'cost', 'стоимость', 'руб', 'usd', '$']):
                price_col = col
        
        logger.info(f"Найденные столбцы - товары: {product_col}, цены: {price_col}")
        
        # Извлечение товаров
        products = []
        for idx, row in df.iterrows():
            try:
                # Название товара
                if product_col:
                    name = str(row[product_col]).strip()
                else:
                    name = str(row.iloc[0]).strip()  # Первый столбец
                
                # Цена
                if price_col:
                    price_str = str(row[price_col])
                else:
                    # Ищем в других столбцах
                    price_str = ""
                    for col_val in row:
                        val_str = str(col_val)
                        if any(char.isdigit() for char in val_str):
                            price_str = val_str
                            break
                
                # Очистка цены от нечисловых символов
                import re
                price_clean = re.sub(r'[^\d.,]', '', price_str)
                if price_clean:
                    price = float(price_clean.replace(',', '.'))
                else:
                    continue
                
                # Проверка валидности данных
                if len(name) > 2 and price > 0 and price < 1000000:
                    products.append({
                        'original_name': name,
                        'price': price,
                        'unit': 'pcs',
                        'row_index': idx
                    })
                    
            except Exception as e:
                logger.debug(f"Ошибка обработки строки {idx}: {e}")
                continue
        
        logger.info(f"Извлечено товаров: {len(products)}")
        
        return {
            'file_type': 'excel',
            'supplier': {'name': supplier_name},
            'products': products,
            'total_rows': len(df)
        }
    
    def _standardize_data(self, data: dict) -> dict:
        """Простая стандартизация данных"""
        products = []
        for product in data.get('products', []):
            products.append({
                'original_name': product.get('original_name', ''),
                'standardized_name': product.get('original_name', ''),  # Пока без изменений
                'price': product.get('price', 0),
                'unit': product.get('unit', 'pcs'),
                'category': 'general',
                'confidence': 0.8
            })
        
        return {
            'supplier': {
                'name': data.get('supplier', {}).get('name', 'Unknown'),
                'contact': '',
                'confidence': 0.9
            },
            'products': products,
            'data_quality': {
                'extraction_confidence': 0.8,
                'source_clarity': 'high',
                'potential_errors': []
            }
        }
    
    def _generate_success_report(self, data: dict, sheets_result: dict, processing_time: float) -> str:
        """Генерация отчета об успешной обработке"""
        supplier_name = data.get('supplier', {}).get('name', 'Unknown')
        products_count = len(data.get('products', []))
        
        report = f"""
✅ *Файл успешно обработан!*

*Результат обработки:*
• Поставщик: {supplier_name}
• Найдено товаров: {products_count}
• Время обработки: {processing_time:.1f} сек

*Сохранено в Google Sheets:*
• Новых товаров добавлено: {sheets_result.get('new_products', 0)}
• Цен обновлено: {sheets_result.get('updated_prices', 0)}
• Обработано успешно: {sheets_result.get('processed_products', 0)}

🔗 [Открыть Google Sheets таблицу]({self.google_sheets.get_sheet_url()})

📊 Данные успешно добавлены в облачную таблицу!

*Что дальше:*
• Откройте таблицу по ссылке выше
• Проверьте лист "Master Table" для сводных данных  
• Найдите лист "Supplier_{supplier_name.replace(' ', '_')}" для детальной информации
        """
        
        return report
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        await update.message.reply_text(
            "📁 Отправьте мне Excel файл (.xlsx или .xls) с прайс-листом\n\n"
            "*Структура файла должна содержать:*\n"
            "• Столбец с названиями товаров\n"
            "• Столбец с ценами\n\n"
            "Используйте /help для подробной справки",
            parse_mode=ParseMode.MARKDOWN
        )
    
    def run(self):
        """Запуск бота"""
        logger.info("🤖 Запуск Telegram бота...")
        
        # Проверка подключений
        if self.google_sheets.is_connected():
            logger.info("✅ Google Sheets подключен")
            sheet_url = self.google_sheets.get_sheet_url()
            print(f"📊 Google Sheets: {sheet_url}")
        else:
            logger.warning("❌ Google Sheets не подключен")
            print("❌ Google Sheets не подключен - проверьте настройки")
        
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
        print("\n" + "="*50)
        print("🤖 TELEGRAM BOT ЗАПУЩЕН!")
        print("="*50)
        print("📱 Найдите своего бота в Telegram и отправьте /start")
        print("📊 Отправьте Excel файл для тестирования")
        print("🔗 Данные будут автоматически сохраняться в Google Sheets")
        print("\nНажмите Ctrl+C для остановки")
        print("="*50)
        
        application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    try:
        bot = WorkingTelegramBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        print("\nПроверьте:")
        print("• TELEGRAM_BOT_TOKEN в .env файле")
        print("• Подключение к интернету")
        print("• Настройки Google Sheets")