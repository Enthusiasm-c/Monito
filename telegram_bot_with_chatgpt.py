#!/usr/bin/env python3
"""
Telegram бот с ChatGPT обработкой для Price List Analyzer
"""

import os
import sys
import json
import asyncio
import logging
import requests
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

class TelegramBotWithChatGPT:
    """Telegram бот с ChatGPT и Google Sheets"""
    
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.google_sheets = GoogleSheetsManager()
        self.temp_dir = "data/temp"
        os.makedirs(self.temp_dir, exist_ok=True)
        
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
        if not self.openai_key:
            raise ValueError("OPENAI_API_KEY не установлен")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        welcome_message = """
🤖 *Добро пожаловать в Price List Analyzer с ChatGPT!*

Я анализирую прайс-листы с помощью ИИ и автоматически добавляю данные в Google Sheets.

*Что я умею:*
• Обрабатывать Excel файлы (.xlsx, .xls)
• Стандартизировать товары через ChatGPT-4
• Переводить названия на английский
• Сохранять данные в Google Sheets
• Создавать сводные таблицы по поставщикам

*Как использовать:*
1. Отправьте мне Excel файл с прайс-листом
2. ИИ проанализирует и стандартизирует данные
3. Получите ссылку на обновленную Google Sheets таблицу

*Команды:*
/start - это сообщение
/help - подробная справка
/stats - статистика таблицы
/sheet - ссылка на Google Sheets
/test - тест системы

Просто отправьте Excel файл для начала! 📊
        """
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = """
📖 *Подробная справка*

*Поддерживаемые форматы:*
• Excel: .xlsx, .xls (до 20 МБ)

*ИИ обработка:*
• Автоматическое определение товаров и цен
• Стандартизация названий на английский язык
• Приведение единиц измерения к стандарту
• Определение категорий товаров
• Оценка качества данных

*Google Sheets структура:*
• Master Table - сводная таблица всех поставщиков
• Отдельные листы для каждого поставщика
• Автоматическое добавление новых столбцов

*Статус системы:*
"""
        
        # Проверка подключений
        sheets_status = "✅ Подключено" if self.google_sheets.is_connected() else "❌ Не подключено"
        chatgpt_status = "✅ Настроен" if self.openai_key else "❌ Не настроен"
        
        help_text += f"• Google Sheets: {sheets_status}\n"
        help_text += f"• ChatGPT API: {chatgpt_status}\n"
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats"""
        try:
            if self.google_sheets.is_connected():
                stats = self.google_sheets.get_stats()
                
                # Получаем реальные данные из таблицы
                worksheet = self.google_sheets.get_or_create_worksheet("Master Table")
                if worksheet:
                    all_records = worksheet.get_all_records()
                    total_products = len(all_records)
                    
                    # Подсчет поставщиков из заголовков
                    headers = worksheet.row_values(1) if worksheet.row_count > 0 else []
                    suppliers = [h.replace('_Price', '') for h in headers if h.endswith('_Price')]
                    
                    stats_text = f"""
📊 *Статистика Google Sheets*

*Актуальные данные:*
• Всего товаров: {total_products}
• Поставщиков: {len(suppliers)}
• Категорий: {len(set(r.get('Category', '') for r in all_records if r.get('Category')))}

*Поставщики:*
"""
                    if suppliers:
                        for supplier in suppliers[:10]:
                            stats_text += f"• {supplier}\n"
                        if len(suppliers) > 10:
                            stats_text += f"• ... и еще {len(suppliers) - 10}\n"
                    else:
                        stats_text += "• Пока нет поставщиков\n"
                    
                    stats_text += f"\n🔗 [Открыть таблицу]({self.google_sheets.get_sheet_url()})"
                else:
                    stats_text = "❌ Не удалось получить данные таблицы"
            else:
                stats_text = "❌ Нет подключения к Google Sheets"
            
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
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /test - тест системы"""
        test_message = await update.message.reply_text("🔍 Тестирую систему...")
        
        try:
            # Тест ChatGPT
            chatgpt_ok = await self._test_chatgpt()
            
            # Тест Google Sheets
            sheets_ok = self.google_sheets.is_connected()
            
            result_text = f"""
🔍 *Результаты тестирования системы*

🤖 *ChatGPT API:* {'✅ Работает' if chatgpt_ok else '❌ Ошибка'}
💾 *Google Sheets:* {'✅ Подключено' if sheets_ok else '❌ Не подключено'}

*Готовность к работе:* {'🟢 Полная' if chatgpt_ok and sheets_ok else '🟡 Частичная' if chatgpt_ok or sheets_ok else '🔴 Не готов'}
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
        """Обработка загруженных документов"""
        document: Document = update.message.document
        
        # Валидация файла
        validation_result = self._validate_file(document)
        if not validation_result['valid']:
            await update.message.reply_text(f"❌ {validation_result['error']}")
            return
        
        # Проверка подключений
        if not self.google_sheets.is_connected():
            await update.message.reply_text("❌ Нет подключения к Google Sheets")
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
                    text="❌ Не найдены товары с ценами в файле"
                )
                return
            
            # Обновление статуса
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text="🤖 Обрабатываю данные через ChatGPT..."
            )
            
            # Обработка через ChatGPT
            standardized_data = await self._process_with_chatgpt(extracted_data)
            
            if not standardized_data:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id,
                    text="❌ Ошибка обработки через ChatGPT"
                )
                return
            
            # Обновление статуса
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id,
                text="💾 Сохраняю данные в Google Sheets..."
            )
            
            # Сохранение в Google Sheets
            sheets_result = self.google_sheets.update_master_table(standardized_data)
            
            if 'error' in sheets_result:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=processing_message.message_id,
                    text=f"❌ Ошибка сохранения: {sheets_result['error']}"
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
            
            logger.info(f"Файл {document.file_name} успешно обработан через ChatGPT")
            
        except Exception as e:
            logger.error(f"Ошибка обработки файла: {e}")
            
            error_text = f"❌ Ошибка обработки файла: `{str(e)}`"
            
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
        """Валидация файла"""
        if not document.file_name.lower().endswith(('.xlsx', '.xls')):
            return {'valid': False, 'error': 'Поддерживаются только Excel файлы (.xlsx, .xls)'}
        
        max_size = 20 * 1024 * 1024  # 20 MB
        if document.file_size > max_size:
            return {'valid': False, 'error': 'Файл слишком большой. Максимум 20 МБ'}
        
        return {'valid': True}
    
    async def _extract_excel_data(self, file_path: str, file_name: str) -> dict:
        """Извлечение данных из Excel"""
        import pandas as pd
        
        supplier_name = os.path.splitext(file_name)[0]
        df = pd.read_excel(file_path)
        
        # Поиск столбцов
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
                name = str(row[product_col] if product_col else row.iloc[0]).strip()
                price_str = str(row[price_col] if price_col else row.iloc[1])
                
                # Очистка цены
                import re
                price_clean = re.sub(r'[^\d.,]', '', price_str)
                if price_clean:
                    price = float(price_clean.replace(',', '.'))
                else:
                    continue
                
                if len(name) > 2 and price > 0:
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
    
    async def _process_with_chatgpt(self, data: dict) -> dict:
        """Обработка данных через ChatGPT"""
        try:
            products = data.get('products', [])[:20]  # Ограничиваем 20 товарами
            supplier_name = data.get('supplier', {}).get('name', 'Unknown')
            
            # Подготовка данных для ChatGPT
            products_text = ""
            for i, product in enumerate(products, 1):
                products_text += f"{i}. {product['original_name']} | {product['price']} | {product['unit']}\n"
            
            prompt = f"""Проанализируй прайс-лист поставщика "{supplier_name}" и стандартизируй данные.

ТОВАРЫ:
{products_text}

Верни JSON в строгом формате:
{{
  "supplier": {{
    "name": "стандартизированное название поставщика",
    "contact": "",
    "confidence": 0.9
  }},
  "products": [
    {{
      "original_name": "исходное название",
      "standardized_name": "Стандартизированное название на английском",
      "price": цена_число,
      "unit": "стандартная_единица(pcs/kg/l/m/box)",
      "category": "категория_товара",
      "confidence": 0.95
    }}
  ],
  "data_quality": {{
    "extraction_confidence": 0.9,
    "source_clarity": "high",
    "potential_errors": []
  }}
}}

ПРАВИЛА:
- Переводи названия товаров на английский
- Стандартизируй единицы: шт→pcs, кг→kg, л→l, м→m
- Определи категории: electronics, food, materials, etc.
- Убери лишние символы и сокращения
- Сохраняй оригинальные названия в original_name"""
            
            headers = {
                'Authorization': f'Bearer {self.openai_key}',
                'Content-Type': 'application/json'
            }
            
            data_payload = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {'role': 'system', 'content': 'Ты эксперт по стандартизации товарных данных. Отвечай только валидным JSON.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 2000,
                'temperature': 0.1
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data_payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Улучшенная очистка ответа от возможных артефактов
                content = content.strip()
                
                # Удаление markdown блоков кода
                if content.startswith('```json'):
                    content = content[7:]
                elif content.startswith('```'):
                    content = content[3:]
                    
                if content.endswith('```'):
                    content = content[:-3]
                
                content = content.strip()
                
                # Поиск JSON блока в тексте
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                
                # Парсинг JSON
                parsed_data = json.loads(content)
                logger.info(f"ChatGPT успешно обработал {len(parsed_data.get('products', []))} товаров")
                return parsed_data
                
            else:
                logger.error(f"Ошибка ChatGPT API: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка обработки ChatGPT: {e}")
            return None
    
    async def _test_chatgpt(self) -> bool:
        """Тест ChatGPT API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.openai_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'gpt-3.5-turbo',
                'messages': [{'role': 'user', 'content': 'Test message'}],
                'max_tokens': 10
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Ошибка тестирования ChatGPT: {e}")
            return False
    
    def _generate_success_report(self, data: dict, sheets_result: dict, processing_time: float) -> str:
        """Генерация отчета об успешной обработке"""
        supplier_name = data.get('supplier', {}).get('name', 'Unknown')
        products_count = len(data.get('products', []))
        confidence = data.get('data_quality', {}).get('extraction_confidence', 0)
        
        report = f"""
✅ *Файл успешно обработан через ChatGPT!*

🏪 *Поставщик:* {supplier_name}
📦 *Обработано товаров:* {products_count}
🤖 *Качество ИИ обработки:* {confidence:.1%}
⏱ *Время обработки:* {processing_time:.1f} сек

💾 *Сохранено в Google Sheets:*
• Новых товаров: {sheets_result.get('new_products', 0)}
• Обновленных цен: {sheets_result.get('updated_prices', 0)}

🔗 [Открыть Google Sheets таблицу]({self.google_sheets.get_sheet_url()})

*Что сделал ChatGPT:*
• Стандартизировал названия на английский
• Привел единицы к стандарту
• Определил категории товаров
• Оценил качество данных

📊 Данные готовы к использованию!
        """
        
        return report
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        await update.message.reply_text(
            "📁 Отправьте мне Excel файл с прайс-листом\n"
            "🤖 Я обработаю его через ChatGPT и сохраню в Google Sheets\n\n"
            "Используйте /help для справки или /test для проверки системы",
            parse_mode=ParseMode.MARKDOWN
        )
    
    def run(self):
        """Запуск бота"""
        logger.info("🤖 Запуск Telegram бота с ChatGPT...")
        
        # Проверка подключений
        sheets_connected = self.google_sheets.is_connected()
        
        print("\n" + "="*60)
        print("🤖 TELEGRAM BOT С CHATGPT ЗАПУЩЕН!")
        print("="*60)
        print(f"📊 Google Sheets: {'✅ Подключено' if sheets_connected else '❌ Не подключено'}")
        print(f"🤖 ChatGPT API: {'✅ Настроен' if self.openai_key else '❌ Не настроен'}")
        if sheets_connected:
            print(f"🔗 Таблица: {self.google_sheets.get_sheet_url()}")
        print("\n📱 Найдите бота в Telegram и отправьте /start")
        print("📊 Отправьте Excel файл для обработки через ИИ")
        print("\nНажмите Ctrl+C для остановки")
        print("="*60)
        
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
        bot = TelegramBotWithChatGPT()
        bot.run()
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        print("\nПроверьте:")
        print("• TELEGRAM_BOT_TOKEN в .env")
        print("• OPENAI_API_KEY в .env")  
        print("• Google Sheets настройки")