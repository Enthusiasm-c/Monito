"""
=============================================================================
MONITO DATA MIGRATION SCRIPT
=============================================================================
Версия: 3.0
Цель: Основной скрипт для миграции данных из legacy системы в unified систему
=============================================================================
"""

import os
import sys
import logging
import argparse
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.adapters.legacy_integration_adapter import LegacyIntegrationAdapter
from utils.logger import get_logger

logger = get_logger(__name__)

class DataMigrationScript:
    """
    Скрипт для миграции данных из legacy системы в unified систему
    """
    
    def __init__(self, config_file: str = None):
        """
        Инициализация миграционного скрипта
        
        Args:
            config_file: Путь к файлу конфигурации
        """
        self.config = self._load_config(config_file)
        self.integration_adapter = None
        
        # Настройка логирования
        self._setup_logging()
        
        logger.info("DataMigrationScript initialized")
    
    def _load_config(self, config_file: str = None) -> Dict[str, Any]:
        """Загрузка конфигурации миграции"""
        default_config = {
            'database': {
                'url': os.getenv('DATABASE_URL', 'sqlite:///monito_unified.db'),
                'backup_before_migration': True
            },
            'migration': {
                'data_directory': './data/legacy',
                'file_patterns': ['*.xlsx', '*.xls', '*.pdf'],
                'batch_size': 100,
                'auto_merge_duplicates': True,
                'validation_enabled': True
            },
            'logging': {
                'level': 'INFO',
                'file': './logs/migration.log'
            },
            'output': {
                'report_file': './reports/migration_report.json',
                'create_backup': True
            }
        }
        
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    custom_config = json.load(f)
                
                # Объединяем конфигурации
                self._deep_update(default_config, custom_config)
                logger.info(f"Configuration loaded from: {config_file}")
                
            except Exception as e:
                logger.warning(f"Failed to load config file {config_file}: {e}")
                logger.info("Using default configuration")
        
        return default_config
    
    def _deep_update(self, base_dict: Dict, update_dict: Dict):
        """Глубокое обновление словаря"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _setup_logging(self):
        """Настройка логирования"""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO').upper())
        log_file = log_config.get('file', './logs/migration.log')
        
        # Создаем директорию для логов
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Настраиваем логгер
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    # =============================================================================
    # MAIN MIGRATION METHODS
    # =============================================================================
    
    def run_full_migration(self) -> Dict[str, Any]:
        """
        Запуск полной миграции данных
        
        Returns:
            Результат миграции
        """
        logger.info("🚀 Starting full data migration")
        
        migration_result = {
            'migration_type': 'full',
            'start_time': datetime.utcnow().isoformat(),
            'config': self.config,
            'steps': {},
            'summary': {}
        }
        
        try:
            # Шаг 1: Инициализация
            logger.info("📋 Step 1: Initialization")
            init_result = self._initialize_migration()
            migration_result['steps']['initialization'] = init_result
            
            if init_result.get('error'):
                migration_result['error'] = init_result['error']
                return migration_result
            
            # Шаг 2: Создание резервной копии
            if self.config['database']['backup_before_migration']:
                logger.info("💾 Step 2: Creating database backup")
                backup_result = self._create_backup()
                migration_result['steps']['backup'] = backup_result
            
            # Шаг 3: Валидация исходных данных
            if self.config['migration']['validation_enabled']:
                logger.info("✅ Step 3: Validating source data")
                validation_result = self._validate_source_data()
                migration_result['steps']['validation'] = validation_result
                
                if validation_result.get('critical_errors', 0) > 0:
                    migration_result['error'] = "Critical validation errors found"
                    return migration_result
            
            # Шаг 4: Основная миграция
            logger.info("🔄 Step 4: Main data migration")
            main_migration_result = self._run_main_migration()
            migration_result['steps']['main_migration'] = main_migration_result
            
            if main_migration_result.get('error'):
                migration_result['error'] = main_migration_result['error']
                return migration_result
            
            # Шаг 5: Пост-миграционная валидация
            if self.config['migration']['validation_enabled']:
                logger.info("🔍 Step 5: Post-migration validation")
                post_validation_result = self._validate_migrated_data()
                migration_result['steps']['post_validation'] = post_validation_result
            
            # Шаг 6: Генерация отчета
            logger.info("📊 Step 6: Generating migration report")
            report_result = self._generate_migration_report(migration_result)
            migration_result['steps']['report_generation'] = report_result
            
            # Финальная сводка
            end_time = datetime.utcnow()
            start_time = datetime.fromisoformat(migration_result['start_time'])
            duration = (end_time - start_time).total_seconds()
            
            migration_result['summary'] = {
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'success': True,
                'files_processed': main_migration_result.get('statistics', {}).get('total_files_processed', 0),
                'products_migrated': main_migration_result.get('statistics', {}).get('total_products_imported', 0),
                'duplicates_found': main_migration_result.get('statistics', {}).get('duplicates_merged', 0)
            }
            
            logger.info(f"✅ Full migration completed successfully in {duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            migration_result['error'] = str(e)
            migration_result['summary'] = {
                'end_time': datetime.utcnow().isoformat(),
                'success': False,
                'error': str(e)
            }
        
        return migration_result
    
    def run_incremental_migration(self, data_directory: str) -> Dict[str, Any]:
        """
        Запуск инкрементальной миграции (только новые файлы)
        
        Args:
            data_directory: Директория с новыми данными
            
        Returns:
            Результат миграции
        """
        logger.info(f"🔄 Starting incremental migration from: {data_directory}")
        
        migration_result = {
            'migration_type': 'incremental',
            'start_time': datetime.utcnow().isoformat(),
            'data_directory': data_directory,
            'steps': {}
        }
        
        try:
            # Инициализация
            init_result = self._initialize_migration()
            if init_result.get('error'):
                migration_result['error'] = init_result['error']
                return migration_result
            
            # Поиск новых файлов
            logger.info("🔍 Finding new files")
            new_files = self._find_new_files(data_directory)
            migration_result['steps']['file_discovery'] = {
                'new_files_found': len(new_files),
                'files': [str(f) for f in new_files]
            }
            
            if not new_files:
                logger.info("No new files found for migration")
                migration_result['summary'] = {
                    'end_time': datetime.utcnow().isoformat(),
                    'success': True,
                    'files_processed': 0,
                    'message': 'No new files to process'
                }
                return migration_result
            
            # Обработка новых файлов
            logger.info(f"📄 Processing {len(new_files)} new files")
            processing_result = self._process_files_batch(new_files)
            migration_result['steps']['file_processing'] = processing_result
            
            # Сводка
            end_time = datetime.utcnow()
            start_time = datetime.fromisoformat(migration_result['start_time'])
            duration = (end_time - start_time).total_seconds()
            
            migration_result['summary'] = {
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'success': True,
                'files_processed': len(new_files),
                'products_added': processing_result.get('total_products_integrated', 0)
            }
            
            logger.info(f"✅ Incremental migration completed in {duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"❌ Incremental migration failed: {e}")
            migration_result['error'] = str(e)
        
        return migration_result
    
    # =============================================================================
    # STEP IMPLEMENTATIONS
    # =============================================================================
    
    def _initialize_migration(self) -> Dict[str, Any]:
        """Инициализация миграции"""
        try:
            # Создаем adapter
            database_url = self.config['database']['url']
            self.integration_adapter = LegacyIntegrationAdapter(database_url)
            
            # Создаем необходимые директории
            self._create_directories()
            
            return {
                'success': True,
                'database_url': database_url,
                'directories_created': True
            }
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return {'error': str(e)}
    
    def _create_directories(self):
        """Создание необходимых директорий"""
        dirs_to_create = [
            './logs',
            './reports',
            './backups',
            self.config['migration']['data_directory']
        ]
        
        for dir_path in dirs_to_create:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def _create_backup(self) -> Dict[str, Any]:
        """Создание резервной копии базы данных"""
        try:
            database_url = self.config['database']['url']
            
            if database_url.startswith('sqlite:'):
                # Для SQLite создаем копию файла
                db_file = database_url.replace('sqlite:///', '')
                if Path(db_file).exists():
                    backup_file = f"./backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    
                    import shutil
                    shutil.copy2(db_file, backup_file)
                    
                    return {
                        'success': True,
                        'backup_file': backup_file,
                        'original_size': Path(db_file).stat().st_size
                    }
            else:
                # Для других БД можно использовать pg_dump, mysqldump и т.д.
                logger.warning("Backup not implemented for non-SQLite databases")
                return {
                    'success': False,
                    'message': 'Backup not implemented for this database type'
                }
            
            return {'success': True, 'message': 'No database file to backup'}
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return {'error': str(e)}
    
    def _validate_source_data(self) -> Dict[str, Any]:
        """Валидация исходных данных"""
        try:
            from migrations.migration_validator import MigrationValidator
            
            validator = MigrationValidator()
            data_directory = self.config['migration']['data_directory']
            
            validation_result = validator.validate_source_directory(data_directory)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Source data validation failed: {e}")
            return {
                'error': str(e),
                'critical_errors': 1
            }
    
    def _run_main_migration(self) -> Dict[str, Any]:
        """Основная миграция данных"""
        try:
            data_directory = self.config['migration']['data_directory']
            file_patterns = self.config['migration']['file_patterns']
            
            migration_result = self.integration_adapter.migrate_legacy_data_to_unified(
                data_directory, file_patterns
            )
            
            return migration_result
            
        except Exception as e:
            logger.error(f"Main migration failed: {e}")
            return {'error': str(e)}
    
    def _validate_migrated_data(self) -> Dict[str, Any]:
        """Валидация мигрированных данных"""
        try:
            from migrations.migration_validator import MigrationValidator
            
            validator = MigrationValidator()
            validation_result = validator.validate_unified_database(
                self.integration_adapter.db_manager
            )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Post-migration validation failed: {e}")
            return {'error': str(e)}
    
    def _generate_migration_report(self, migration_result: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация отчета о миграции"""
        try:
            report_file = self.config['output']['report_file']
            
            # Создаем директорию для отчета
            Path(report_file).parent.mkdir(parents=True, exist_ok=True)
            
            # Добавляем дополнительную информацию в отчет
            enhanced_report = {
                **migration_result,
                'system_info': {
                    'python_version': sys.version,
                    'working_directory': str(Path.cwd()),
                    'config_used': self.config
                }
            }
            
            # Сохраняем отчет
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(enhanced_report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Migration report saved to: {report_file}")
            
            return {
                'success': True,
                'report_file': report_file,
                'report_size': Path(report_file).stat().st_size
            }
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {'error': str(e)}
    
    def _find_new_files(self, data_directory: str) -> List[Path]:
        """Поиск новых файлов для инкрементальной миграции"""
        import glob
        
        data_dir = Path(data_directory)
        if not data_dir.exists():
            return []
        
        # Получаем все файлы
        all_files = []
        for pattern in self.config['migration']['file_patterns']:
            all_files.extend(glob.glob(str(data_dir / pattern)))
        
        # В реальной реализации здесь должна быть логика определения новых файлов
        # На основе метки времени, размера файла, хеша и т.д.
        # Для простоты возвращаем все файлы
        
        return [Path(f) for f in all_files]
    
    def _process_files_batch(self, files: List[Path]) -> Dict[str, Any]:
        """Обработка пакета файлов"""
        try:
            file_paths = [str(f) for f in files]
            
            result = self.integration_adapter.parser_adapter.process_multiple_files(
                file_paths, auto_match_duplicates=True
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return {'error': str(e)}


def main():
    """Основная функция для запуска миграции из командной строки"""
    parser = argparse.ArgumentParser(description='Monito Data Migration Script')
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--mode', '-m',
        choices=['full', 'incremental'],
        default='full',
        help='Migration mode (default: full)'
    )
    
    parser.add_argument(
        '--data-directory', '-d',
        type=str,
        help='Data directory for incremental migration'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without actual migration'
    )
    
    args = parser.parse_args()
    
    try:
        # Создаем миграционный скрипт
        migration_script = DataMigrationScript(args.config)
        
        if args.dry_run:
            print("🔍 DRY RUN MODE - No actual migration will be performed")
            # В dry-run режиме можно только валидировать данные
            return
        
        # Запускаем миграцию
        if args.mode == 'full':
            result = migration_script.run_full_migration()
        else:  # incremental
            data_dir = args.data_directory or migration_script.config['migration']['data_directory']
            result = migration_script.run_incremental_migration(data_dir)
        
        # Выводим результат
        if result.get('error'):
            print(f"❌ Migration failed: {result['error']}")
            sys.exit(1)
        else:
            print("✅ Migration completed successfully!")
            summary = result.get('summary', {})
            print(f"📊 Files processed: {summary.get('files_processed', 0)}")
            print(f"📦 Products migrated: {summary.get('products_migrated', 0)}")
            print(f"⏱️  Duration: {summary.get('duration_seconds', 0):.2f} seconds")
    
    except KeyboardInterrupt:
        print("\n⚠️ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Migration script failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 