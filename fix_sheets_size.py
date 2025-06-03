#!/usr/bin/env python3
"""Исправляет размер Google Sheets таблицы"""

from modules.google_sheets_manager import GoogleSheetsManager

def fix_sheets_size():
    """Расширяет таблицу для поддержки дополнительных столбцов"""
    
    print('🔧 Исправление размера Google Sheets таблицы...')
    
    sheets = GoogleSheetsManager()
    if not sheets.is_connected():
        print('❌ Нет подключения к Google Sheets')
        return False
    
    print('✅ Подключение установлено')
    
    try:
        worksheet = sheets.get_or_create_worksheet('Master Table')
        
        # Получаем текущие размеры
        current_rows = worksheet.row_count
        current_cols = worksheet.col_count
        
        print(f'📊 Текущий размер: {current_rows} строк x {current_cols} столбцов')
        
        # Расширяем до 20 столбцов если нужно
        if current_cols < 20:
            worksheet.resize(rows=max(current_rows, 1000), cols=20)
            print(f'✅ Таблица расширена до {worksheet.row_count} строк x {worksheet.col_count} столбцов')
        else:
            print('✅ Таблица уже имеет достаточный размер')
        
        print(f'🔗 URL таблицы: {sheets.get_sheet_url()}')
        return True
        
    except Exception as e:
        print(f'❌ Ошибка расширения таблицы: {e}')
        return False

if __name__ == "__main__":
    fix_sheets_size() 