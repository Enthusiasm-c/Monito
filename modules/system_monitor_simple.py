#!/usr/bin/env python3
"""
Упрощенный системный монитор без проблемных зависимостей
Совместим с ARM64 архитектурой macOS
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class SimpleSystemMonitor:
    """Упрощенный монитор системы без psutil"""
    
    def __init__(self, stats_file: str = "data/system_stats.json"):
        self.stats_file = Path(stats_file)
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Инициализация статистики
        self.stats = self._load_stats()
        
    def _load_stats(self) -> Dict[str, Any]:
        """Загрузка статистики из файла"""
        try:
            if self.stats_file.exists():
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Не удалось загрузить статистику: {e}")
        
        # Базовая структура статистики
        return {
            'processing': {
                'total_files': 0,
                'successful_files': 0,
                'failed_files': 0,
                'excel_files': 0,
                'pdf_files': 0,
                'last_processed': None
            },
            'chatgpt': {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'total_tokens_used': 0,
                'last_request': None
            },
            'google_sheets': {
                'total_updates': 0,
                'successful_updates': 0,
                'failed_updates': 0,
                'products_added': 0,
                'last_update': None
            },
            'system': {
                'start_time': datetime.now().isoformat(),
                'uptime_seconds': 0,
                'last_restart': datetime.now().isoformat()
            }
        }
    
    def _save_stats(self):
        """Сохранение статистики в файл"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения статистики: {e}")
    
    def record_file_processing(self, file_type: str, success: bool, error: str = None):
        """Запись обработки файла"""
        try:
            self.stats['processing']['total_files'] += 1
            
            if success:
                self.stats['processing']['successful_files'] += 1
            else:
                self.stats['processing']['failed_files'] += 1
            
            if file_type.lower() == 'excel':
                self.stats['processing']['excel_files'] += 1
            elif file_type.lower() == 'pdf':
                self.stats['processing']['pdf_files'] += 1
            
            self.stats['processing']['last_processed'] = datetime.now().isoformat()
            
            if error:
                logger.warning(f"Ошибка обработки файла {file_type}: {error}")
            
            self._save_stats()
            logger.info(f"📊 Записана обработка файла: {file_type} ({'успех' if success else 'ошибка'})")
            
        except Exception as e:
            logger.error(f"Ошибка записи статистики файла: {e}")
    
    def record_chatgpt_request(self, success: bool, tokens_used: int = 0, error: str = None):
        """Запись запроса к ChatGPT"""
        try:
            self.stats['chatgpt']['total_requests'] += 1
            
            if success:
                self.stats['chatgpt']['successful_requests'] += 1
                self.stats['chatgpt']['total_tokens_used'] += tokens_used
            else:
                self.stats['chatgpt']['failed_requests'] += 1
            
            self.stats['chatgpt']['last_request'] = datetime.now().isoformat()
            
            if error:
                logger.warning(f"Ошибка ChatGPT запроса: {error}")
            
            self._save_stats()
            logger.info(f"🤖 Записан ChatGPT запрос: ({'успех' if success else 'ошибка'}), токенов: {tokens_used}")
            
        except Exception as e:
            logger.error(f"Ошибка записи статистики ChatGPT: {e}")
    
    def record_sheets_update(self, success: bool, products_count: int = 0, error: str = None):
        """Запись обновления Google Sheets"""
        try:
            self.stats['google_sheets']['total_updates'] += 1
            
            if success:
                self.stats['google_sheets']['successful_updates'] += 1
                self.stats['google_sheets']['products_added'] += products_count
            else:
                self.stats['google_sheets']['failed_updates'] += 1
            
            self.stats['google_sheets']['last_update'] = datetime.now().isoformat()
            
            if error:
                logger.warning(f"Ошибка обновления Google Sheets: {error}")
            
            self._save_stats()
            logger.info(f"💾 Записано обновление Sheets: ({'успех' if success else 'ошибка'}), товаров: {products_count}")
            
        except Exception as e:
            logger.error(f"Ошибка записи статистики Sheets: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение текущей статистики"""
        try:
            # Обновляем время работы
            if 'start_time' in self.stats['system']:
                start_time = datetime.fromisoformat(self.stats['system']['start_time'])
                uptime = (datetime.now() - start_time).total_seconds()
                self.stats['system']['uptime_seconds'] = int(uptime)
            
            return self.stats.copy()
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}
    
    def get_success_rates(self) -> Dict[str, float]:
        """Расчет показателей успешности"""
        try:
            rates = {}
            
            # Успешность обработки файлов
            total_files = self.stats['processing']['total_files']
            if total_files > 0:
                rates['file_processing'] = self.stats['processing']['successful_files'] / total_files
            else:
                rates['file_processing'] = 0.0
            
            # Успешность ChatGPT запросов
            total_chatgpt = self.stats['chatgpt']['total_requests']
            if total_chatgpt > 0:
                rates['chatgpt_requests'] = self.stats['chatgpt']['successful_requests'] / total_chatgpt
            else:
                rates['chatgpt_requests'] = 0.0
            
            # Успешность обновлений Sheets
            total_sheets = self.stats['google_sheets']['total_updates']
            if total_sheets > 0:
                rates['sheets_updates'] = self.stats['google_sheets']['successful_updates'] / total_sheets
            else:
                rates['sheets_updates'] = 0.0
            
            return rates
        except Exception as e:
            logger.error(f"Ошибка расчета показателей: {e}")
            return {}
    
    def get_system_info(self) -> Dict[str, Any]:
        """Получение базовой информации о системе"""
        try:
            import platform
            import sys
            
            return {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'architecture': platform.machine(),
                'python_version': sys.version,
                'working_directory': os.getcwd(),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации о системе: {e}")
            return {}
    
    def reset_stats(self):
        """Сброс статистики"""
        try:
            self.stats = self._load_stats()
            # Сохраняем время сброса
            self.stats['system']['last_restart'] = datetime.now().isoformat()
            self._save_stats()
            logger.info("📊 Статистика сброшена")
        except Exception as e:
            logger.error(f"Ошибка сброса статистики: {e}")
    
    def get_formatted_report(self) -> str:
        """Получение форматированного отчета"""
        try:
            stats = self.get_stats()
            rates = self.get_success_rates()
            
            uptime_hours = stats['system']['uptime_seconds'] / 3600
            
            report = f"""
📊 ОТЧЕТ О РАБОТЕ СИСТЕМЫ
========================

📁 Обработка файлов:
• Всего файлов: {stats['processing']['total_files']}
• Успешно: {stats['processing']['successful_files']}
• Ошибок: {stats['processing']['failed_files']}
• Успешность: {rates.get('file_processing', 0):.1%}
• Excel файлов: {stats['processing']['excel_files']}
• PDF файлов: {stats['processing']['pdf_files']}

🤖 ChatGPT запросы:
• Всего запросов: {stats['chatgpt']['total_requests']}
• Успешно: {stats['chatgpt']['successful_requests']}
• Ошибок: {stats['chatgpt']['failed_requests']}
• Успешность: {rates.get('chatgpt_requests', 0):.1%}
• Токенов использовано: {stats['chatgpt']['total_tokens_used']}

💾 Google Sheets:
• Всего обновлений: {stats['google_sheets']['total_updates']}
• Успешно: {stats['google_sheets']['successful_updates']}
• Ошибок: {stats['google_sheets']['failed_updates']}
• Успешность: {rates.get('sheets_updates', 0):.1%}
• Товаров добавлено: {stats['google_sheets']['products_added']}

⏱ Система:
• Время работы: {uptime_hours:.1f} часов
• Запущена: {stats['system']['start_time'][:19]}
"""
            return report
        except Exception as e:
            logger.error(f"Ошибка создания отчета: {e}")
            return "❌ Ошибка создания отчета"

# Глобальный экземпляр монитора
monitor = SimpleSystemMonitor()

def record_file_processing(file_type: str, success: bool, error: str = None):
    """Удобная функция для записи обработки файла"""
    monitor.record_file_processing(file_type, success, error)

def record_chatgpt_request(success: bool, tokens_used: int = 0, error: str = None):
    """Удобная функция для записи ChatGPT запроса"""
    monitor.record_chatgpt_request(success, tokens_used, error)

def record_sheets_update(success: bool, products_count: int = 0, error: str = None):
    """Удобная функция для записи обновления Sheets"""
    monitor.record_sheets_update(success, products_count, error)

def get_stats():
    """Удобная функция для получения статистики"""
    return monitor.get_stats()

def get_formatted_report():
    """Удобная функция для получения отчета"""
    return monitor.get_formatted_report()