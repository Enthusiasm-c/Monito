"""
=============================================================================
MONITO API TELEGRAM WEBHOOK ROUTER
=============================================================================
Версия: 3.0
Цель: Webhook интеграция Telegram бота с unified API системой
=============================================================================
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from api.schemas.base import BaseResponse
from modules.adapters.legacy_integration_adapter import LegacyIntegrationAdapter
from api.helpers.telegram_sender import get_telegram_sender
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

def get_integration_adapter(request: Request) -> LegacyIntegrationAdapter:
    """Dependency для получения integration adapter"""
    return request.app.state.integration_adapter

# =============================================================================
# PYDANTIC SCHEMAS для Telegram Webhook
# =============================================================================

class TelegramUser(BaseModel):
    """Telegram пользователь"""
    id: int
    is_bot: bool
    first_name: str
    username: Optional[str] = None
    language_code: Optional[str] = None

class TelegramChat(BaseModel):
    """Telegram чат"""
    id: int
    type: str
    username: Optional[str] = None
    first_name: Optional[str] = None

class TelegramMessage(BaseModel):
    """Telegram сообщение"""
    message_id: int
    from_: Optional[TelegramUser] = None
    chat: TelegramChat
    date: int
    text: Optional[str] = None
    document: Optional[Dict[str, Any]] = None
    
    class Config:
        fields = {'from_': 'from'}

class TelegramCallbackQuery(BaseModel):
    """Telegram callback query от inline клавиатуры"""
    id: str
    from_: TelegramUser
    message: Optional[TelegramMessage] = None
    data: Optional[str] = None
    
    class Config:
        fields = {'from_': 'from'}

class TelegramUpdate(BaseModel):
    """Telegram webhook update"""
    update_id: int
    message: Optional[TelegramMessage] = None
    callback_query: Optional[TelegramCallbackQuery] = None

# =============================================================================
# TELEGRAM BOT HANDLERS
# =============================================================================

class UnifiedTelegramBot:
    """Unified Telegram бот с интеграцией к API"""
    
    def __init__(self, integration_adapter: LegacyIntegrationAdapter):
        """
        Инициализация unified Telegram бота
        
        Args:
            integration_adapter: Адаптер для работы с unified системой
        """
        self.integration_adapter = integration_adapter
        self.commands = {
            '/start': self.handle_start,
            '/help': self.handle_help,
            '/search': self.handle_search,
            '/catalog': self.handle_catalog,
            '/deals': self.handle_top_deals,
            '/categories': self.handle_categories,
            '/recommend': self.handle_recommendations,
            '/stats': self.handle_stats
        }
        
        logger.info("🤖 UnifiedTelegramBot initialized with unified API integration")
    
    async def process_update(self, update: TelegramUpdate) -> Dict[str, Any]:
        """
        Обработка Telegram webhook update
        
        Args:
            update: Telegram update объект
            
        Returns:
            Ответ для отправки пользователю
        """
        try:
            if update.message:
                return await self.handle_message(update.message)
            elif update.callback_query:
                return await self.handle_callback_query(update.callback_query)
            else:
                logger.warning("Unknown update type received")
                return {"method": "sendMessage", "text": "❓ Неизвестный тип сообщения"}
                
        except Exception as e:
            logger.error(f"Error processing Telegram update: {e}")
            return {
                "method": "sendMessage",
                "text": "❌ Произошла ошибка при обработке вашего запроса. Попробуйте позже."
            }
    
    async def handle_message(self, message: TelegramMessage) -> Dict[str, Any]:
        """Обработка текстового сообщения"""
        
        user_id = message.from_.id if message.from_ else message.chat.id
        username = message.from_.username if message.from_ else "Unknown"
        text = message.text or ""
        
        logger.info(f"📨 Message from {username} (ID: {user_id}): {text[:50]}...")
        
        # Обработка команд
        if text.startswith('/'):
            command = text.split()[0].lower()
            if command in self.commands:
                return await self.commands[command](message)
            else:
                return {
                    "method": "sendMessage",
                    "chat_id": message.chat.id,
                    "text": f"❓ Неизвестная команда: {command}\n\nИспользуйте /help для списка команд"
                }
        
        # Обработка документов
        if message.document:
            return await self.handle_document(message)
        
        # Обработка обычного текста как поиска
        return await self.handle_search_query(message, text)
    
    async def handle_callback_query(self, callback: TelegramCallbackQuery) -> Dict[str, Any]:
        """Обработка нажатий inline клавиатуры"""
        
        user_id = callback.from_.id
        username = callback.from_.username or "Unknown"
        data = callback.data or ""
        
        logger.info(f"🔘 Callback from {username} (ID: {user_id}): {data}")
        
        try:
            # Парсим callback data
            action_data = json.loads(data)
            action = action_data.get('action')
            
            if action == 'search_category':
                return await self.handle_category_search(callback, action_data.get('category'))
            elif action == 'show_product':
                return await self.handle_show_product(callback, action_data.get('product_id'))
            elif action == 'get_deals':
                return await self.handle_deals_callback(callback, action_data.get('category'))
            elif action == 'recommend_products':
                return await self.handle_recommendations_callback(callback, action_data)
            else:
                return {
                    "method": "answerCallbackQuery",
                    "callback_query_id": callback.id,
                    "text": "❓ Неизвестное действие"
                }
                
        except json.JSONDecodeError:
            logger.error(f"Invalid callback data: {data}")
            return {
                "method": "answerCallbackQuery", 
                "callback_query_id": callback.id,
                "text": "❌ Ошибка обработки команды"
            }
    
    # =============================================================================
    # COMMAND HANDLERS
    # =============================================================================
    
    async def handle_start(self, message: TelegramMessage) -> Dict[str, Any]:
        """Команда /start"""
        
        welcome_text = """
🏝️ *Добро пожаловать в Monito Unified!*

Я современный бот для поиска лучших цен от поставщиков Бали!

🔍 *Возможности:*
• Поиск товаров по unified каталогу
• Сравнение цен от всех поставщиков
• Топовые предложения с максимальной экономией
• AI-рекомендации по закупкам
• Анализ категорий и трендов

🚀 *Команды:*
/search [товар] - поиск товара
/catalog - browse каталог по категориям
/deals - топовые предложения
/categories - список категорий
/recommend - рекомендации по закупкам
/stats - статистика системы

💡 *Или просто напишите название товара для поиска!*
        """
        
        # Создаем inline клавиатуру
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🔍 Поиск товаров", "callback_data": json.dumps({"action": "catalog"})},
                    {"text": "🔥 Топ предложения", "callback_data": json.dumps({"action": "get_deals"})}
                ],
                [
                    {"text": "📋 Категории", "callback_data": json.dumps({"action": "categories"})},
                    {"text": "🛒 Рекомендации", "callback_data": json.dumps({"action": "recommend_products"})}
                ]
            ]
        }
        
        return {
            "method": "sendMessage",
            "chat_id": message.chat.id,
            "text": welcome_text,
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        }
    
    async def handle_help(self, message: TelegramMessage) -> Dict[str, Any]:
        """Команда /help"""
        
        help_text = """
📖 *Подробная справка Monito Unified*

🔍 *Поиск товаров:*
• `/search кока-кола` - поиск по названию
• `/search category:beverages` - поиск по категории
• `/search price:5000-15000` - поиск по цене
• Или просто напишите название товара

🏪 *Каталог и категории:*
• `/catalog` - browse по категориям
• `/categories` - список всех категорий
• `/deals` - топ предложения с экономией

🛒 *Рекомендации:*
• `/recommend` - AI рекомендации по закупкам
• Учитывает цены, надежность поставщиков
• Оптимизация бюджета

📊 *Аналитика:*
• `/stats` - статистика unified системы
• Информация о товарах, ценах, поставщиках

💡 *Inline клавиатуры:*
Используйте кнопки для быстрой навигации!

🚀 *Powered by Monito Unified API v3.0*
        """
        
        return {
            "method": "sendMessage",
            "chat_id": message.chat.id,
            "text": help_text,
            "parse_mode": "Markdown"
        }
    
    async def handle_search(self, message: TelegramMessage) -> Dict[str, Any]:
        """Команда /search"""
        
        # Извлекаем поисковый запрос
        text = message.text or ""
        query_parts = text.split(maxsplit=1)
        
        if len(query_parts) < 2:
            return {
                "method": "sendMessage",
                "chat_id": message.chat.id,
                "text": "🔍 Введите поисковый запрос после команды:\n\n`/search кока-кола`\n`/search category:beverages`",
                "parse_mode": "Markdown"
            }
        
        query = query_parts[1]
        return await self.handle_search_query(message, query)
    
    async def handle_search_query(self, message: TelegramMessage, query: str) -> Dict[str, Any]:
        """Обработка поискового запроса через unified API"""
        
        logger.info(f"🔍 Search query: '{query}'")
        
        try:
            # Парсим поисковые параметры
            search_params = self._parse_search_query(query)
            
            # Отправляем сообщение о поиске
            search_message = {
                "method": "sendMessage",
                "chat_id": message.chat.id,
                "text": f"🔍 Ищу товары: *{query}*...",
                "parse_mode": "Markdown"
            }
            
            # Выполняем поиск через unified систему
            products = self.integration_adapter.db_manager.search_master_products(
                search_params.get('query', query), 
                limit=10
            )
            
            if not products:
                return {
                    "method": "editMessageText",
                    "chat_id": message.chat.id,
                    "text": f"😕 Товары по запросу '*{query}*' не найдены.\n\nПопробуйте:\n• Изменить запрос\n• Использовать /categories для просмотра категорий",
                    "parse_mode": "Markdown"
                }
            
            # Получаем цены для каждого товара
            search_results = []
            for product in products:
                prices = self.integration_adapter.db_manager.get_current_prices_for_product(str(product.product_id))
                
                if prices:
                    price_values = [p.price for p in prices]
                    best_price = min(price_values)
                    avg_price = sum(price_values) / len(price_values)
                    best_price_obj = min(prices, key=lambda p: p.price)
                    
                    savings = avg_price - best_price if avg_price > best_price else 0
                    savings_pct = (savings / avg_price * 100) if avg_price > 0 else 0
                    
                    search_results.append({
                        'product': product,
                        'best_price': best_price,
                        'best_supplier': best_price_obj.supplier_name,
                        'price_count': len(prices),
                        'savings': savings,
                        'savings_pct': savings_pct,
                        'unit': best_price_obj.unit
                    })
            
            # Сортируем по лучшей цене
            search_results.sort(key=lambda x: x['best_price'])
            
            # Формируем ответ
            result_text = f"🔍 *Результаты поиска:* {query}\n\n"
            result_text += f"Найдено товаров: *{len(search_results)}*\n\n"
            
            # Показываем топ 5 результатов
            for i, result in enumerate(search_results[:5], 1):
                product = result['product']
                savings_text = ""
                if result['savings_pct'] > 5:
                    savings_text = f" 💸 *-{result['savings_pct']:.0f}%*"
                
                result_text += f"*{i}. {product.standard_name}*\n"
                result_text += f"💰 {result['best_price']:,.0f} IDR/{result['unit']}{savings_text}\n"
                result_text += f"🏪 {result['best_supplier']}\n"
                result_text += f"📊 {result['price_count']} предложений\n\n"
            
            # Добавляем inline кнопки
            keyboard = {
                "inline_keyboard": [
                    [{"text": f"📦 Показать все {len(search_results)}", "callback_data": json.dumps({"action": "show_all_results", "query": query})}],
                    [
                        {"text": "🔥 Топ предложения", "callback_data": json.dumps({"action": "get_deals"})},
                        {"text": "🛒 Рекомендации", "callback_data": json.dumps({"action": "recommend_products"})}
                    ]
                ]
            }
            
            return {
                "method": "editMessageText",
                "chat_id": message.chat.id,
                "text": result_text,
                "parse_mode": "Markdown",
                "reply_markup": keyboard
            }
            
        except Exception as e:
            logger.error(f"Search query failed: {e}")
            return {
                "method": "editMessageText",
                "chat_id": message.chat.id,
                "text": f"❌ Ошибка поиска: {str(e)}\n\nПопробуйте позже или обратитесь к администратору.",
                "parse_mode": "Markdown"
            }
    
    async def handle_catalog(self, message: TelegramMessage) -> Dict[str, Any]:
        """Команда /catalog - просмотр каталога по категориям"""
        
        try:
            # Получаем категории через unified систему
            products = self.integration_adapter.db_manager.search_master_products("", limit=500)
            
            # Группируем по категориям
            categories = {}
            for product in products:
                category = product.category or "uncategorized"
                if category not in categories:
                    categories[category] = 0
                categories[category] += 1
            
            # Сортируем по количеству товаров
            sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
            
            catalog_text = "🏪 *Unified каталог товаров*\n\n"
            catalog_text += f"Всего категорий: *{len(sorted_categories)}*\n"
            catalog_text += f"Всего товаров: *{sum(categories.values())}*\n\n"
            
            # Создаем inline клавиатуру с категориями
            keyboard_rows = []
            for i in range(0, min(len(sorted_categories), 8), 2):  # По 2 в ряд, максимум 4 ряда
                row = []
                for j in range(2):
                    if i + j < len(sorted_categories):
                        cat_name, cat_count = sorted_categories[i + j]
                        display_name = cat_name.replace('_', ' ').title()
                        button_text = f"{display_name} ({cat_count})"
                        callback_data = json.dumps({"action": "search_category", "category": cat_name})
                        row.append({"text": button_text, "callback_data": callback_data})
                
                if row:
                    keyboard_rows.append(row)
            
            # Добавляем дополнительные кнопки
            keyboard_rows.append([
                {"text": "🔥 Топ предложения", "callback_data": json.dumps({"action": "get_deals"})},
                {"text": "📊 Статистика", "callback_data": json.dumps({"action": "stats"})}
            ])
            
            keyboard = {"inline_keyboard": keyboard_rows}
            
            return {
                "method": "sendMessage",
                "chat_id": message.chat.id,
                "text": catalog_text,
                "parse_mode": "Markdown",
                "reply_markup": keyboard
            }
            
        except Exception as e:
            logger.error(f"Catalog command failed: {e}")
            return {
                "method": "sendMessage",
                "chat_id": message.chat.id,
                "text": f"❌ Ошибка загрузки каталога: {str(e)}"
            }
    
    async def handle_top_deals(self, message: TelegramMessage) -> Dict[str, Any]:
        """Команда /deals - топовые предложения"""
        
        try:
            # Получаем все товары
            products = self.integration_adapter.db_manager.search_master_products("", limit=200)
            
            deals = []
            for product in products:
                prices = self.integration_adapter.db_manager.get_current_prices_for_product(str(product.product_id))
                
                if len(prices) >= 2:  # Нужно минимум 2 цены для сравнения
                    price_values = [p.price for p in prices]
                    best_price = min(price_values)
                    avg_price = sum(price_values) / len(price_values)
                    
                    savings_amount = avg_price - best_price
                    savings_pct = (savings_amount / avg_price * 100) if avg_price > 0 else 0
                    
                    if savings_pct >= 10:  # Минимум 10% экономии
                        best_price_obj = min(prices, key=lambda p: p.price)
                        deals.append({
                            'product': product,
                            'best_price': best_price,
                            'regular_price': avg_price,
                            'savings_amount': savings_amount,
                            'savings_pct': savings_pct,
                            'supplier': best_price_obj.supplier_name,
                            'unit': best_price_obj.unit
                        })
            
            # Сортируем по проценту экономии
            deals.sort(key=lambda x: x['savings_pct'], reverse=True)
            top_deals = deals[:5]
            
            if not top_deals:
                return {
                    "method": "sendMessage",
                    "chat_id": message.chat.id,
                    "text": "😕 Пока нет предложений с значительной экономией.\n\nПопробуйте /catalog для просмотра всех товаров."
                }
            
            deals_text = f"🔥 *Топ предложения с экономией*\n\n"
            deals_text += f"Найдено предложений: *{len(deals)}*\n\n"
            
            for i, deal in enumerate(top_deals, 1):
                product = deal['product']
                deals_text += f"*{i}. {product.standard_name}*\n"
                deals_text += f"💰 {deal['best_price']:,.0f} IDR/{deal['unit']} "
                deals_text += f"(обычно {deal['regular_price']:,.0f})\n"
                deals_text += f"💸 Экономия: *{deal['savings_pct']:.0f}%* "
                deals_text += f"({deal['savings_amount']:,.0f} IDR)\n"
                deals_text += f"🏪 {deal['supplier']}\n\n"
            
            # Inline клавиатура
            keyboard = {
                "inline_keyboard": [
                    [{"text": f"📦 Показать все {len(deals)} предложений", "callback_data": json.dumps({"action": "show_all_deals"})}],
                    [
                        {"text": "🔍 Поиск товаров", "callback_data": json.dumps({"action": "catalog"})},
                        {"text": "🛒 Рекомендации", "callback_data": json.dumps({"action": "recommend_products"})}
                    ]
                ]
            }
            
            return {
                "method": "sendMessage",
                "chat_id": message.chat.id,
                "text": deals_text,
                "parse_mode": "Markdown",
                "reply_markup": keyboard
            }
            
        except Exception as e:
            logger.error(f"Top deals command failed: {e}")
            return {
                "method": "sendMessage",
                "chat_id": message.chat.id,
                "text": f"❌ Ошибка загрузки предложений: {str(e)}"
            }
    
    async def handle_categories(self, message: TelegramMessage) -> Dict[str, Any]:
        """Команда /categories"""
        return await self.handle_catalog(message)
    
    async def handle_recommendations(self, message: TelegramMessage) -> Dict[str, Any]:
        """Команда /recommend"""
        
        recommend_text = """
🛒 *AI-рекомендации по закупкам*

Для получения персональных рекомендаций укажите:

*Способ 1: Быстрый*
Просто укажите товары через запятую:
`/recommend кока-кола, пиво бинтанг, рис`

*Способ 2: Подробный*
Укажите товары с количеством:
```
/recommend
Coca-Cola 330ml - 100 шт
Bintang Beer - 50 шт
Рис жасмин - 20 кг
```

*Способ 3: Интерактивный*
Используйте кнопки ниже для пошаговой настройки рекомендаций.

🎯 *AI анализирует:*
• Лучшие цены от всех поставщиков
• Надежность поставщиков
• Оптимизацию бюджета
• Потенциальную экономию
        """
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🍹 Напитки", "callback_data": json.dumps({"action": "recommend_category", "category": "beverages"})}],
                [{"text": "🍚 Продукты", "callback_data": json.dumps({"action": "recommend_category", "category": "food"})}],
                [{"text": "🧹 Хоз. товары", "callback_data": json.dumps({"action": "recommend_category", "category": "household"})}],
                [{"text": "🛒 Настроить закупку", "callback_data": json.dumps({"action": "custom_recommendation"})}]
            ]
        }
        
        return {
            "method": "sendMessage",
            "chat_id": message.chat.id,
            "text": recommend_text,
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        }
    
    async def handle_stats(self, message: TelegramMessage) -> Dict[str, Any]:
        """Команда /stats"""
        
        try:
            # Получаем статистику через unified систему
            system_stats = self.integration_adapter.db_manager.get_system_statistics()
            
            stats_text = f"""
📊 *Статистика Monito Unified*

*🏪 Unified каталог:*
• Товаров: *{system_stats.get('total_products', 0):,}*
• Поставщиков: *{system_stats.get('total_suppliers', 0):,}*
• Цен: *{system_stats.get('total_prices', 0):,}*
• Категорий: *{system_stats.get('categories_count', 0):,}*

*💰 Ценовая аналитика:*
• Средняя цена: {system_stats.get('average_price', 0):,.0f} IDR
• Диапазон цен: {system_stats.get('price_range', {}).get('min', 0):,.0f} - {system_stats.get('price_range', {}).get('max', 0):,.0f} IDR

*🔥 Активность:*
• Обновления за день: {system_stats.get('daily_updates', 0)}
• Последнее обновление: {system_stats.get('last_update', 'Неизвестно')}

*🤖 API версия:* 3.0.0
*📅 Данные актуальны на:* {datetime.now().strftime('%d.%m.%Y %H:%M')}
            """
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "🔍 Каталог", "callback_data": json.dumps({"action": "catalog"})},
                        {"text": "🔥 Предложения", "callback_data": json.dumps({"action": "get_deals"})}
                    ]
                ]
            }
            
            return {
                "method": "sendMessage",
                "chat_id": message.chat.id,
                "text": stats_text,
                "parse_mode": "Markdown",
                "reply_markup": keyboard
            }
            
        except Exception as e:
            logger.error(f"Stats command failed: {e}")
            return {
                "method": "sendMessage",
                "chat_id": message.chat.id,
                "text": f"❌ Ошибка загрузки статистики: {str(e)}"
            }
    
    async def handle_document(self, message: TelegramMessage) -> Dict[str, Any]:
        """Обработка загруженных документов"""
        
        return {
            "method": "sendMessage",
            "chat_id": message.chat.id,
            "text": """
📎 *Загрузка файлов временно недоступна*

В новой unified версии загрузка файлов переведена на legacy систему.

🔍 *Альтернативы:*
• Используйте поиск: `/search товар`
• Просмотрите каталог: `/catalog`
• Получите рекомендации: `/recommend`

*Legacy бот доступен отдельно для обработки Excel файлов.*
            """,
            "parse_mode": "Markdown"
        }
    
    # =============================================================================
    # CALLBACK HANDLERS
    # =============================================================================
    
    async def handle_category_search(self, callback: TelegramCallbackQuery, category: str) -> Dict[str, Any]:
        """Поиск товаров по категории"""
        
        try:
            # Получаем товары категории
            all_products = self.integration_adapter.db_manager.search_master_products("", limit=500)
            category_products = [p for p in all_products if p.category == category]
            
            if not category_products:
                return {
                    "method": "answerCallbackQuery",
                    "callback_query_id": callback.id,
                    "text": f"В категории {category} товары не найдены"
                }
            
            # Получаем цены и формируем результаты
            results = []
            for product in category_products[:10]:  # Топ 10 товаров
                prices = self.integration_adapter.db_manager.get_current_prices_for_product(str(product.product_id))
                if prices:
                    best_price = min(p.price for p in prices)
                    best_supplier = min(prices, key=lambda p: p.price).supplier_name
                    results.append({
                        'product': product,
                        'best_price': best_price,
                        'supplier': best_supplier,
                        'unit': prices[0].unit
                    })
            
            results.sort(key=lambda x: x['best_price'])
            
            category_display = category.replace('_', ' ').title()
            result_text = f"🏪 *Категория: {category_display}*\n\n"
            result_text += f"Найдено: *{len(category_products)}* товаров\n\n"
            
            for i, result in enumerate(results[:7], 1):
                product = result['product']
                result_text += f"*{i}. {product.standard_name}*\n"
                result_text += f"💰 {result['best_price']:,.0f} IDR/{result['unit']}\n"
                result_text += f"🏪 {result['supplier']}\n\n"
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔙 Назад к категориям", "callback_data": json.dumps({"action": "catalog"})}],
                    [{"text": "🔥 Лучшие предложения", "callback_data": json.dumps({"action": "get_deals", "category": category})}]
                ]
            }
            
            return {
                "method": "editMessageText",
                "chat_id": callback.message.chat.id,
                "message_id": callback.message.message_id,
                "text": result_text,
                "parse_mode": "Markdown",
                "reply_markup": keyboard
            }
            
        except Exception as e:
            logger.error(f"Category search failed: {e}")
            return {
                "method": "answerCallbackQuery",
                "callback_query_id": callback.id,
                "text": f"❌ Ошибка поиска в категории: {str(e)}"
            }
    
    async def handle_deals_callback(self, callback: TelegramCallbackQuery, category: str = None) -> Dict[str, Any]:
        """Обработка callback для показа топ предложений"""
        
        # Создаем фиктивное сообщение для использования существующего обработчика
        fake_message = TelegramMessage(
            message_id=callback.message.message_id,
            chat=callback.message.chat,
            date=callback.message.date
        )
        
        result = await self.handle_top_deals(fake_message)
        
        # Модифицируем для editMessageText
        result["method"] = "editMessageText"
        result["message_id"] = callback.message.message_id
        
        # Отвечаем на callback
        await self._answer_callback_query(callback.id, "🔥 Загружаю лучшие предложения...")
        
        return result
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def _parse_search_query(self, query: str) -> Dict[str, Any]:
        """Парсинг поискового запроса"""
        
        params = {'query': query}
        
        # Парсим специальные параметры
        if 'category:' in query:
            parts = query.split('category:')
            if len(parts) > 1:
                category = parts[1].split()[0]
                params['category'] = category
                params['query'] = parts[0].strip()
        
        if 'price:' in query:
            parts = query.split('price:')
            if len(parts) > 1:
                price_range = parts[1].split()[0]
                if '-' in price_range:
                    try:
                        min_price, max_price = price_range.split('-')
                        params['price_min'] = float(min_price)
                        params['price_max'] = float(max_price)
                    except ValueError:
                        pass
        
        return params
    
    async def _answer_callback_query(self, callback_query_id: str, text: str):
        """Утилита для ответа на callback query"""
        return {
            "method": "answerCallbackQuery",
            "callback_query_id": callback_query_id,
            "text": text
        }

# =============================================================================
# WEBHOOK ENDPOINTS
# =============================================================================

@router.post("/webhook",
           response_model=BaseResponse,
           summary="🤖 Telegram Webhook",
           description="Webhook endpoint для получения обновлений от Telegram")
async def telegram_webhook(
    update_data: Dict[str, Any],
    request: Request,
    background_tasks: BackgroundTasks,
    integration_adapter: LegacyIntegrationAdapter = Depends(get_integration_adapter)
) -> BaseResponse:
    """
    Webhook endpoint для Telegram бота
    
    Получает обновления от Telegram и обрабатывает их через unified систему
    
    Args:
        update_data: Данные update от Telegram
        request: FastAPI request
        background_tasks: Background tasks для асинхронной обработки
        integration_adapter: Адаптер unified системы
        
    Returns:
        Подтверждение получения webhook'a
    """
    logger.info(f"🤖 Telegram webhook received: {update_data.get('update_id')}")
    
    try:
        # Парсим Telegram update
        telegram_update = TelegramUpdate(**update_data)
        
        # Создаем бот
        bot = UnifiedTelegramBot(integration_adapter)
        
        # Обрабатываем в фоновом режиме
        background_tasks.add_task(process_telegram_update_background, bot, telegram_update)
        
        return BaseResponse(
            message="Webhook received and processing started",
            request_id=getattr(request.state, 'request_id', None)
        )
        
    except Exception as e:
        logger.error(f"❌ Telegram webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

async def process_telegram_update_background(bot: UnifiedTelegramBot, update: TelegramUpdate):
    """
    Фоновая обработка Telegram update
    
    Args:
        bot: Unified Telegram бот
        update: Telegram update для обработки
    """
    try:
        # Обрабатываем update
        response = await bot.process_update(update)
        
        if response and 'method' in response:
            # Отправляем ответ в Telegram через TelegramSender
            telegram_sender = get_telegram_sender()
            success = await telegram_sender.send_response(response)
            
            if success:
                logger.info(f"📤 Response sent successfully: {response['method']}")
            else:
                logger.error(f"❌ Failed to send response: {response['method']}")
        
    except Exception as e:
        logger.error(f"❌ Background processing failed: {e}")

@router.get("/webhook/info",
          response_model=Dict[str, Any],
          summary="ℹ️ Webhook информация",
          description="Информация о настройке Telegram webhook")
async def webhook_info() -> Dict[str, Any]:
    """
    Информация о настройке Telegram webhook
    
    Returns:
        Инструкции по настройке webhook
    """
    return {
        "telegram_webhook": {
            "endpoint": "/api/v1/telegram/webhook",
            "method": "POST",
            "description": "Endpoint для получения Telegram updates",
            "setup_instructions": {
                "1": "Получите токен бота от @BotFather",
                "2": "Установите webhook: https://api.telegram.org/bot<TOKEN>/setWebhook?url=<YOUR_API_URL>/api/v1/telegram/webhook",
                "3": "Проверьте статус: https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
            },
            "supported_updates": [
                "message",
                "callback_query"
            ],
            "supported_commands": [
                "/start", "/help", "/search", "/catalog", 
                "/deals", "/categories", "/recommend", "/stats"
            ]
        }
    }

@router.post("/webhook/setup",
           response_model=BaseResponse,
           summary="🔧 Установка Webhook",
           description="Установка webhook URL для Telegram бота")
async def setup_webhook(
    webhook_url: str,
    request: Request
) -> BaseResponse:
    """
    Установка webhook URL для Telegram бота
    
    Args:
        webhook_url: URL для установки webhook
        request: FastAPI request
        
    Returns:
        Результат установки webhook
    """
    logger.info(f"🔧 Setting up Telegram webhook: {webhook_url}")
    
    try:
        telegram_sender = get_telegram_sender()
        result = await telegram_sender.set_webhook(webhook_url)
        
        if result.get('ok'):
            return BaseResponse(
                message=f"Webhook установлен успешно: {webhook_url}",
                request_id=getattr(request.state, 'request_id', None)
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Ошибка установки webhook: {result.get('description', 'Unknown error')}"
            )
            
    except Exception as e:
        logger.error(f"❌ Failed to setup webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook setup failed: {str(e)}")

@router.get("/webhook/status",
          response_model=Dict[str, Any],
          summary="📊 Статус Webhook",
          description="Получение текущего статуса Telegram webhook")
async def webhook_status() -> Dict[str, Any]:
    """
    Получение статуса Telegram webhook
    
    Returns:
        Информация о статусе webhook
    """
    telegram_sender = get_telegram_sender()
    webhook_info = await telegram_sender.get_webhook_info()
    
    return {
        "webhook_status": webhook_info,
        "timestamp": datetime.now().isoformat()
    }

@router.delete("/webhook",
             response_model=BaseResponse,
             summary="🗑️ Удаление Webhook",
             description="Удаление Telegram webhook (переключение на polling)")
async def delete_webhook(request: Request) -> BaseResponse:
    """
    Удаление Telegram webhook
    
    Args:
        request: FastAPI request
        
    Returns:
        Результат удаления webhook
    """
    logger.info("🗑️ Deleting Telegram webhook")
    
    try:
        telegram_sender = get_telegram_sender()
        result = await telegram_sender.delete_webhook()
        
        if result.get('ok'):
            return BaseResponse(
                message="Webhook удален успешно. Бот переключен на polling режим.",
                request_id=getattr(request.state, 'request_id', None)
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Ошибка удаления webhook: {result.get('description', 'Unknown error')}"
            )
            
    except Exception as e:
        logger.error(f"❌ Failed to delete webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook deletion failed: {str(e)}")

@router.post("/test-message",
           response_model=BaseResponse,
           summary="🧪 Тест сообщения",
           description="Отправка тестового сообщения через Telegram API")
async def send_test_message(
    chat_id: int,
    message: str = "🤖 Тестовое сообщение от Monito Unified API",
    request: Request = None
) -> BaseResponse:
    """
    Отправка тестового сообщения
    
    Args:
        chat_id: ID чата для отправки
        message: Текст сообщения
        request: FastAPI request
        
    Returns:
        Результат отправки сообщения
    """
    logger.info(f"🧪 Sending test message to chat {chat_id}")
    
    try:
        telegram_sender = get_telegram_sender()
        success = await telegram_sender.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown"
        )
        
        if success:
            return BaseResponse(
                message=f"Тестовое сообщение отправлено в чат {chat_id}",
                request_id=getattr(request.state, 'request_id', None) if request else None
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Не удалось отправить тестовое сообщение"
            )
            
    except Exception as e:
        logger.error(f"❌ Failed to send test message: {e}")
        raise HTTPException(status_code=500, detail=f"Test message failed: {str(e)}") 