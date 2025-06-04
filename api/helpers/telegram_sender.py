"""
=============================================================================
MONITO API TELEGRAM SENDER
=============================================================================
Версия: 3.0
Цель: Модуль для отправки сообщений в Telegram Bot API
=============================================================================
"""

import os
import json
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

class TelegramSender:
    """
    Класс для отправки сообщений в Telegram Bot API
    """
    
    def __init__(self, bot_token: Optional[str] = None):
        """
        Инициализация Telegram sender
        
        Args:
            bot_token: Токен Telegram бота
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not self.bot_token:
            logger.warning("⚠️ Telegram bot token not provided. Telegram features will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        logger.info(f"🤖 TelegramSender initialized: {'enabled' if self.enabled else 'disabled'}")
    
    async def send_response(self, response_data: Dict[str, Any]) -> bool:
        """
        Отправка ответа в Telegram
        
        Args:
            response_data: Данные ответа для Telegram API
            
        Returns:
            True если отправлено успешно
        """
        if not self.enabled:
            logger.warning("Telegram sender disabled - response not sent")
            return False
        
        method = response_data.get('method')
        
        if not method:
            logger.error("No method specified in response data")
            return False
        
        try:
            url = f"{self.base_url}/{method}"
            
            # Удаляем method из данных
            send_data = {k: v for k, v in response_data.items() if k != 'method'}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=send_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('ok'):
                            logger.debug(f"✅ Telegram {method} sent successfully")
                            return True
                        else:
                            logger.error(f"❌ Telegram API error: {result.get('description')}")
                            return False
                    else:
                        logger.error(f"❌ HTTP error {response.status} sending {method}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Failed to send {method}: {e}")
            return False
    
    async def send_message(self, chat_id: int, text: str, **kwargs) -> bool:
        """
        Отправка простого сообщения
        
        Args:
            chat_id: ID чата
            text: Текст сообщения
            **kwargs: Дополнительные параметры
            
        Returns:
            True если отправлено успешно
        """
        response_data = {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': text,
            **kwargs
        }
        
        return await self.send_response(response_data)
    
    async def edit_message(self, chat_id: int, message_id: int, text: str, **kwargs) -> bool:
        """
        Редактирование сообщения
        
        Args:
            chat_id: ID чата
            message_id: ID сообщения
            text: Новый текст
            **kwargs: Дополнительные параметры
            
        Returns:
            True если отредактировано успешно
        """
        response_data = {
            'method': 'editMessageText',
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            **kwargs
        }
        
        return await self.send_response(response_data)
    
    async def answer_callback_query(self, callback_query_id: str, text: str = "", show_alert: bool = False) -> bool:
        """
        Ответ на callback query
        
        Args:
            callback_query_id: ID callback query
            text: Текст уведомления
            show_alert: Показать как alert
            
        Returns:
            True если отправлено успешно
        """
        response_data = {
            'method': 'answerCallbackQuery',
            'callback_query_id': callback_query_id,
            'text': text,
            'show_alert': show_alert
        }
        
        return await self.send_response(response_data)
    
    async def set_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """
        Установка webhook URL
        
        Args:
            webhook_url: URL для webhook
            
        Returns:
            Результат установки webhook
        """
        if not self.enabled:
            return {"ok": False, "error": "Telegram sender disabled"}
        
        try:
            url = f"{self.base_url}/setWebhook"
            data = {"url": webhook_url}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    
                    if result.get('ok'):
                        logger.info(f"✅ Webhook set successfully: {webhook_url}")
                    else:
                        logger.error(f"❌ Failed to set webhook: {result.get('description')}")
                    
                    return result
                    
        except Exception as e:
            logger.error(f"❌ Error setting webhook: {e}")
            return {"ok": False, "error": str(e)}
    
    async def get_webhook_info(self) -> Dict[str, Any]:
        """
        Получение информации о webhook
        
        Returns:
            Информация о webhook
        """
        if not self.enabled:
            return {"ok": False, "error": "Telegram sender disabled"}
        
        try:
            url = f"{self.base_url}/getWebhookInfo"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    result = await response.json()
                    return result
                    
        except Exception as e:
            logger.error(f"❌ Error getting webhook info: {e}")
            return {"ok": False, "error": str(e)}
    
    async def delete_webhook(self) -> Dict[str, Any]:
        """
        Удаление webhook (переключение на polling)
        
        Returns:
            Результат удаления webhook
        """
        if not self.enabled:
            return {"ok": False, "error": "Telegram sender disabled"}
        
        try:
            url = f"{self.base_url}/deleteWebhook"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url) as response:
                    result = await response.json()
                    
                    if result.get('ok'):
                        logger.info("✅ Webhook deleted successfully")
                    else:
                        logger.error(f"❌ Failed to delete webhook: {result.get('description')}")
                    
                    return result
                    
        except Exception as e:
            logger.error(f"❌ Error deleting webhook: {e}")
            return {"ok": False, "error": str(e)}

# Глобальный экземпляр sender'а
_telegram_sender: Optional[TelegramSender] = None

def get_telegram_sender() -> TelegramSender:
    """
    Получение глобального экземпляра TelegramSender
    
    Returns:
        TelegramSender экземпляр
    """
    global _telegram_sender
    
    if _telegram_sender is None:
        _telegram_sender = TelegramSender()
    
    return _telegram_sender 