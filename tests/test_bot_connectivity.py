#!/usr/bin/env python3
"""
Простой тест подключения к Telegram боту
"""

import os
import asyncio
import requests
from dotenv import load_dotenv

load_dotenv()

def test_bot_token():
    """Тест токена бота"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не найден в .env")
        return False
    
    print(f"✅ Токен найден: {token[:10]}...")
    
    # Проверка через API
    url = f"https://api.telegram.org/bot{token}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                print(f"✅ Бот активен: @{bot_info.get('username', 'unknown')}")
                print(f"📝 Имя: {bot_info.get('first_name', 'unknown')}")
                print(f"🆔 ID: {bot_info.get('id', 'unknown')}")
                return True
            else:
                print(f"❌ API ошибка: {data.get('description', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def test_bot_updates():
    """Проверка получения обновлений"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                updates = data.get('result', [])
                print(f"📥 Получено обновлений: {len(updates)}")
                
                if updates:
                    last_update = updates[-1]
                    print(f"🕐 Последнее обновление: {last_update.get('update_id')}")
                    
                    if 'message' in last_update:
                        msg = last_update['message']
                        user = msg.get('from', {})
                        print(f"👤 От пользователя: {user.get('first_name', 'Unknown')} (@{user.get('username', 'no_username')})")
                        
                        if 'text' in msg:
                            print(f"💬 Текст: {msg['text']}")
                        elif 'document' in msg:
                            doc = msg['document']
                            print(f"📎 Документ: {doc.get('file_name', 'no_name')}")
                
                return True
            else:
                print(f"❌ Ошибка получения обновлений: {data.get('description')}")
                return False
        else:
            print(f"❌ HTTP ошибка при получении обновлений: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ Ошибка получения обновлений: {e}")
        return False

def main():
    """Главная функция теста"""
    print("🔍 ТЕСТ ПОДКЛЮЧЕНИЯ К TELEGRAM БОТУ")
    print("=" * 50)
    
    # Тест токена
    print("\n1️⃣ Проверка токена бота...")
    token_ok = test_bot_token()
    
    if not token_ok:
        print("\n❌ Бот недоступен. Проверьте токен.")
        return
    
    # Тест обновлений
    print("\n2️⃣ Проверка обновлений...")
    updates_ok = test_bot_updates()
    
    if updates_ok:
        print("\n✅ Бот работает корректно!")
        print("\n📱 Если бот не отвечает на файлы:")
        print("1. Убедитесь что отправляете файл как документ (📎)")
        print("2. Проверьте что файл имеет расширение .xlsx или .xls")
        print("3. Убедитесь что размер файла не превышает 20 МБ")
        print("4. Попробуйте сначала отправить /start")
    else:
        print("\n❌ Проблемы с получением обновлений")
    
    print("\n💡 Для запуска бота: python3 telegram_bot_advanced.py")

if __name__ == "__main__":
    main()