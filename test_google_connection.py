#!/usr/bin/env python3
"""
Детальный тест подключения к Google Sheets
"""

import os
import sys
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

print("🔍 ДЕТАЛЬНЫЙ ТЕСТ GOOGLE SHEETS")
print("="*50)

# Проверка переменных окружения
print("📋 Проверка переменных окружения:")
sheet_id = os.getenv('GOOGLE_SHEET_ID')
creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'google_credentials.json')

print(f"GOOGLE_SHEET_ID: {sheet_id}")
print(f"GOOGLE_CREDENTIALS_FILE: {creds_file}")
print(f"Файл существует: {os.path.exists(creds_file)}")

if not sheet_id:
    print("❌ GOOGLE_SHEET_ID не установлен!")
    exit(1)

if not os.path.exists(creds_file):
    print(f"❌ Файл {creds_file} не найден!")
    exit(1)

print("\n🔗 Попытка подключения к Google Sheets...")

try:
    import gspread
    from google.auth.exceptions import GoogleAuthError
    
    print("✅ Библиотеки gspread импортированы")
    
    # Попытка аутентификации
    print("🔐 Аутентификация...")
    client = gspread.service_account(filename=creds_file)
    print("✅ Аутентификация прошла успешно")
    
    # Попытка открыть таблицу
    print("📊 Открытие таблицы...")
    sheet = client.open_by_key(sheet_id)
    print(f"✅ Таблица открыта: {sheet.title}")
    
    # Получение информации о листах
    worksheets = sheet.worksheets()
    print(f"📋 Найдено листов: {len(worksheets)}")
    for ws in worksheets:
        print(f"  - {ws.title}")
    
    # Попытка записи тестовых данных
    print("\n✏️  Тест записи данных...")
    
    # Получаем или создаем лист "Test"
    try:
        test_ws = sheet.worksheet("Test")
        print("✅ Найден существующий лист 'Test'")
    except gspread.WorksheetNotFound:
        test_ws = sheet.add_worksheet(title="Test", rows=10, cols=5)
        print("✅ Создан новый лист 'Test'")
    
    # Запись тестовых данных
    test_data = [
        ["Product", "Price", "Date"],
        ["Test Item 1", 100.50, "2025-05-30"],
        ["Test Item 2", 200.75, "2025-05-30"]
    ]
    
    test_ws.update('A1:C3', test_data)
    print("✅ Тестовые данные записаны")
    
    # Чтение данных обратно
    read_data = test_ws.get('A1:C3')
    print("✅ Тестовые данные прочитаны")
    print(f"Данные: {read_data}")
    
    print(f"\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print(f"🔗 Ссылка на таблицу: https://docs.google.com/spreadsheets/d/{sheet_id}")
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Установите зависимости: pip3 install gspread google-auth")
    
except GoogleAuthError as e:
    print(f"❌ Ошибка аутентификации Google: {e}")
    print("Проверьте:")
    print("  - Правильность JSON файла")
    print("  - Включены ли Google Sheets API и Google Drive API")
    
except gspread.SpreadsheetNotFound:
    print(f"❌ Таблица не найдена по ID: {sheet_id}")
    print("Проверьте:")
    print("  - Правильность GOOGLE_SHEET_ID")
    print("  - Предоставлен ли доступ Service Account к таблице")
    
except Exception as e:
    print(f"❌ Неожиданная ошибка: {e}")
    print(f"Тип ошибки: {type(e).__name__}")
    import traceback
    traceback.print_exc()