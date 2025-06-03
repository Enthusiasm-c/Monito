#!/usr/bin/env python3
"""
Debug тест для выявления проблемы зависания
"""

import sys
from pathlib import Path

# Добавляем модули в path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("1. Начинаем debug тест...")

try:
    print("2. Импортируем QuotaLimits...")
    from modules.quota_manager import QuotaLimits
    print("3. QuotaLimits импортирован успешно")
    
    print("4. Создаем QuotaLimits...")
    limits = QuotaLimits()
    print("5. QuotaLimits создан успешно")
    
    print("6. Импортируем QuotaManager...")
    from modules.quota_manager import QuotaManager
    print("7. QuotaManager импортирован успешно")
    
    print("8. Создаем QuotaManager...")
    # QuotaManager теперь настраивает логирование самостоятельно
    manager = QuotaManager()
    print("9. QuotaManager создан успешно")
    
except Exception as e:
    print(f"❌ Ошибка на этапе: {e}")
    import traceback
    traceback.print_exc()

print("10. Debug тест завершен") 