"""
=============================================================================
MONITO MIGRATION VALIDATOR
=============================================================================
Версия: 3.0
Цель: Валидация данных до и после миграции из legacy в unified систему
=============================================================================
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass

from modules.unified_database_manager import UnifiedDatabaseManager
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ValidationIssue:
    """Проблема валидации"""
    type: str
    severity: str  # 'critical', 'warning', 'info'
    message: str
    file_path: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

@dataclass
class ValidationResult:
    """Результат валидации"""
    success: bool
    total_checks: int
    passed_checks: int
    failed_checks: int
    critical_errors: int
    warnings: int
    issues: List[ValidationIssue]
    summary: Dict[str, Any]

class MigrationValidator:
    """
    Валидатор данных для процесса миграции
    """
    
    def __init__(self):
        """Инициализация валидатора"""
        self.supported_formats = ['.xlsx', '.xls', '.pdf']
        self.min_file_size = 100  # байт
        self.max_file_size = 100 * 1024 * 1024  # 100 MB
        
        logger.info("MigrationValidator initialized")
    
    # =============================================================================
    # SOURCE DATA VALIDATION
    # =============================================================================
    
    def validate_source_directory(self, data_directory: str) -> Dict[str, Any]:
        """
        Валидация директории с исходными данными
        
        Args:
            data_directory: Путь к директории с данными
            
        Returns:
            Результат валидации
        """
        logger.info(f"Validating source directory: {data_directory}")
        
        issues = []
        checks_performed = 0
        
        try:
            data_dir = Path(data_directory)
            
            # Проверка 1: Существование директории
            checks_performed += 1
            if not data_dir.exists():
                issues.append(ValidationIssue(
                    type='directory_not_found',
                    severity='critical',
                    message=f'Data directory does not exist: {data_directory}'
                ))
                return self._create_validation_result(issues, checks_performed)
            
            # Проверка 2: Поиск файлов данных
            checks_performed += 1
            data_files = self._find_data_files(data_dir)
            
            if not data_files:
                issues.append(ValidationIssue(
                    type='no_data_files',
                    severity='critical',
                    message='No supported data files found in directory',
                    details={'supported_formats': self.supported_formats}
                ))
            else:
                logger.info(f"Found {len(data_files)} data files")
            
            # Проверка 3: Валидация каждого файла
            for file_path in data_files:
                file_issues = self._validate_single_file(file_path)
                issues.extend(file_issues)
                checks_performed += len(file_issues) + 1
            
            # Проверка 4: Анализ структуры данных
            checks_performed += 1
            structure_issues = self._analyze_data_structure(data_files)
            issues.extend(structure_issues)
            
            result = self._create_validation_result(issues, checks_performed)
            result['files_found'] = len(data_files)
            result['files_validated'] = len(data_files)
            
            logger.info(f"Source validation completed: {result['passed_checks']}/{result['total_checks']} checks passed")
            
            return result
            
        except Exception as e:
            logger.error(f"Source validation failed: {e}")
            return {
                'error': str(e),
                'critical_errors': 1,
                'success': False
            }
    
    def _find_data_files(self, directory: Path) -> List[Path]:
        """Поиск файлов данных в директории"""
        data_files = []
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                data_files.append(file_path)
        
        return data_files
    
    def _validate_single_file(self, file_path: Path) -> List[ValidationIssue]:
        """Валидация отдельного файла"""
        issues = []
        
        try:
            # Проверка размера файла
            file_size = file_path.stat().st_size
            
            if file_size < self.min_file_size:
                issues.append(ValidationIssue(
                    type='file_too_small',
                    severity='warning',
                    message=f'File is very small ({file_size} bytes)',
                    file_path=str(file_path)
                ))
            
            if file_size > self.max_file_size:
                issues.append(ValidationIssue(
                    type='file_too_large',
                    severity='warning',
                    message=f'File is very large ({file_size} bytes)',
                    file_path=str(file_path)
                ))
            
            # Проверка доступности файла
            try:
                if file_path.suffix.lower() in ['.xlsx', '.xls']:
                    self._validate_excel_file(file_path, issues)
                elif file_path.suffix.lower() == '.pdf':
                    self._validate_pdf_file(file_path, issues)
                    
            except Exception as e:
                issues.append(ValidationIssue(
                    type='file_read_error',
                    severity='critical',
                    message=f'Cannot read file: {str(e)}',
                    file_path=str(file_path)
                ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                type='file_access_error',
                severity='critical',
                message=f'Cannot access file: {str(e)}',
                file_path=str(file_path)
            ))
        
        return issues
    
    def _validate_excel_file(self, file_path: Path, issues: List[ValidationIssue]):
        """Валидация Excel файла"""
        try:
            import pandas as pd
            
            # Пытаемся прочитать файл
            excel_file = pd.ExcelFile(file_path)
            
            if not excel_file.sheet_names:
                issues.append(ValidationIssue(
                    type='no_sheets',
                    severity='warning',
                    message='Excel file has no sheets',
                    file_path=str(file_path)
                ))
                return
            
            # Проверяем каждый лист
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    if df.empty:
                        issues.append(ValidationIssue(
                            type='empty_sheet',
                            severity='warning',
                            message=f'Sheet "{sheet_name}" is empty',
                            file_path=str(file_path)
                        ))
                    elif len(df.columns) < 2:
                        issues.append(ValidationIssue(
                            type='insufficient_columns',
                            severity='warning',
                            message=f'Sheet "{sheet_name}" has only {len(df.columns)} columns',
                            file_path=str(file_path)
                        ))
                        
                except Exception as e:
                    issues.append(ValidationIssue(
                        type='sheet_read_error',
                        severity='warning',
                        message=f'Cannot read sheet "{sheet_name}": {str(e)}',
                        file_path=str(file_path)
                    ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                type='excel_validation_error',
                severity='critical',
                message=f'Excel validation failed: {str(e)}',
                file_path=str(file_path)
            ))
    
    def _validate_pdf_file(self, file_path: Path, issues: List[ValidationIssue]):
        """Валидация PDF файла"""
        try:
            # Проверяем, что можем открыть PDF
            with open(file_path, 'rb') as f:
                header = f.read(5)
                if not header.startswith(b'%PDF-'):
                    issues.append(ValidationIssue(
                        type='invalid_pdf',
                        severity='critical',
                        message='File is not a valid PDF',
                        file_path=str(file_path)
                    ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                type='pdf_validation_error',
                severity='critical',
                message=f'PDF validation failed: {str(e)}',
                file_path=str(file_path)
            ))
    
    def _analyze_data_structure(self, data_files: List[Path]) -> List[ValidationIssue]:
        """Анализ структуры данных в файлах"""
        issues = []
        
        if not data_files:
            return issues
        
        # Анализируем распределение форматов файлов
        format_counts = {}
        for file_path in data_files:
            ext = file_path.suffix.lower()
            format_counts[ext] = format_counts.get(ext, 0) + 1
        
        # Проверяем разнообразие форматов
        if len(format_counts) == 1 and len(data_files) > 10:
            issues.append(ValidationIssue(
                type='format_homogeneity',
                severity='info',
                message=f'All files have the same format: {list(format_counts.keys())[0]}',
                details={'format_distribution': format_counts}
            ))
        
        return issues
    
    # =============================================================================
    # UNIFIED DATABASE VALIDATION
    # =============================================================================
    
    def validate_unified_database(self, db_manager: UnifiedDatabaseManager) -> Dict[str, Any]:
        """
        Валидация unified базы данных после миграции
        
        Args:
            db_manager: Менеджер unified базы данных
            
        Returns:
            Результат валидации
        """
        logger.info("Validating unified database")
        
        issues = []
        checks_performed = 0
        
        try:
            # Проверка 1: Базовая целостность данных
            checks_performed += 1
            integrity_issues = self._check_data_integrity(db_manager)
            issues.extend(integrity_issues)
            
            # Проверка 2: Товары без цен
            checks_performed += 1
            orphaned_products_issues = self._check_orphaned_products(db_manager)
            issues.extend(orphaned_products_issues)
            
            # Проверка 3: Цены без товаров
            checks_performed += 1
            orphaned_prices_issues = self._check_orphaned_prices(db_manager)
            issues.extend(orphaned_prices_issues)
            
            # Проверка 4: Дубликаты
            checks_performed += 1
            duplicate_issues = self._check_potential_duplicates(db_manager)
            issues.extend(duplicate_issues)
            
            # Проверка 5: Качество данных
            checks_performed += 1
            quality_issues = self._check_data_quality(db_manager)
            issues.extend(quality_issues)
            
            # Проверка 6: Статистики системы
            checks_performed += 1
            stats_issues = self._check_system_statistics(db_manager)
            issues.extend(stats_issues)
            
            result = self._create_validation_result(issues, checks_performed)
            
            # Добавляем статистики базы данных
            system_stats = db_manager.get_system_statistics()
            result['database_statistics'] = system_stats
            
            logger.info(f"Database validation completed: {result['passed_checks']}/{result['total_checks']} checks passed")
            
            return result
            
        except Exception as e:
            logger.error(f"Database validation failed: {e}")
            return {
                'error': str(e),
                'critical_errors': 1,
                'success': False
            }
    
    def _check_data_integrity(self, db_manager: UnifiedDatabaseManager) -> List[ValidationIssue]:
        """Проверка целостности данных"""
        issues = []
        
        try:
            # Получаем статистики
            stats = db_manager.get_system_statistics()
            
            if stats['total_products'] == 0:
                issues.append(ValidationIssue(
                    type='no_products',
                    severity='critical',
                    message='No products found in database after migration'
                ))
            
            if stats['total_suppliers'] == 0:
                issues.append(ValidationIssue(
                    type='no_suppliers',
                    severity='critical',
                    message='No suppliers found in database after migration'
                ))
            
            if stats['total_prices'] == 0:
                issues.append(ValidationIssue(
                    type='no_prices',
                    severity='critical',
                    message='No prices found in database after migration'
                ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                type='integrity_check_error',
                severity='critical',
                message=f'Data integrity check failed: {str(e)}'
            ))
        
        return issues
    
    def _check_orphaned_products(self, db_manager: UnifiedDatabaseManager) -> List[ValidationIssue]:
        """Проверка товаров без цен"""
        issues = []
        
        try:
            products_without_prices = 0
            
            # Получаем все товары
            all_products = db_manager.search_master_products("", limit=1000)
            
            for product in all_products:
                prices = db_manager.get_current_prices_for_product(str(product.product_id))
                if not prices:
                    products_without_prices += 1
            
            if products_without_prices > 0:
                severity = 'critical' if products_without_prices > len(all_products) * 0.1 else 'warning'
                issues.append(ValidationIssue(
                    type='products_without_prices',
                    severity=severity,
                    message=f'Found {products_without_prices} products without prices',
                    details={'count': products_without_prices, 'total_products': len(all_products)}
                ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                type='orphaned_products_check_error',
                severity='warning',
                message=f'Orphaned products check failed: {str(e)}'
            ))
        
        return issues
    
    def _check_orphaned_prices(self, db_manager: UnifiedDatabaseManager) -> List[ValidationIssue]:
        """Проверка цен без товаров"""
        issues = []
        
        try:
            # В unified системе цены связаны с товарами через foreign key,
            # поэтому orphaned prices не должны существовать
            # Но проверим логическую целостность
            
            with db_manager.get_session() as session:
                from models.unified_database import SupplierPrice, MasterProduct
                
                # Подсчитываем цены без соответствующих товаров
                orphaned_count = session.query(SupplierPrice).join(
                    MasterProduct, SupplierPrice.product_id == MasterProduct.product_id, isouter=True
                ).filter(MasterProduct.product_id == None).count()
                
                if orphaned_count > 0:
                    issues.append(ValidationIssue(
                        type='prices_without_products',
                        severity='critical',
                        message=f'Found {orphaned_count} prices without corresponding products'
                    ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                type='orphaned_prices_check_error',
                severity='warning',
                message=f'Orphaned prices check failed: {str(e)}'
            ))
        
        return issues
    
    def _check_potential_duplicates(self, db_manager: UnifiedDatabaseManager) -> List[ValidationIssue]:
        """Проверка потенциальных дубликатов"""
        issues = []
        
        try:
            # Получаем непроверенные совпадения
            unreviewed_matches = db_manager.get_unreviewed_matches(limit=100)
            
            if len(unreviewed_matches) > 50:
                issues.append(ValidationIssue(
                    type='many_unreviewed_matches',
                    severity='warning',
                    message=f'Found {len(unreviewed_matches)} unreviewed product matches',
                    details={'unreviewed_count': len(unreviewed_matches)}
                ))
            
            # Проверяем товары с очень похожими названиями
            similar_names_count = self._count_similar_product_names(db_manager)
            
            if similar_names_count > 0:
                issues.append(ValidationIssue(
                    type='similar_product_names',
                    severity='info',
                    message=f'Found {similar_names_count} groups of products with similar names',
                    details={'similar_groups': similar_names_count}
                ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                type='duplicates_check_error',
                severity='warning',
                message=f'Duplicates check failed: {str(e)}'
            ))
        
        return issues
    
    def _check_data_quality(self, db_manager: UnifiedDatabaseManager) -> List[ValidationIssue]:
        """Проверка качества данных"""
        issues = []
        
        try:
            # Проверяем товары с пустыми/некачественными названиями
            quality_stats = self._analyze_data_quality(db_manager)
            
            if quality_stats['empty_names'] > 0:
                issues.append(ValidationIssue(
                    type='empty_product_names',
                    severity='warning',
                    message=f'Found {quality_stats["empty_names"]} products with empty names'
                ))
            
            if quality_stats['short_names'] > quality_stats['total_products'] * 0.1:
                issues.append(ValidationIssue(
                    type='many_short_names',
                    severity='warning',
                    message=f'Found {quality_stats["short_names"]} products with very short names'
                ))
            
            if quality_stats['zero_prices'] > 0:
                issues.append(ValidationIssue(
                    type='zero_prices',
                    severity='warning',
                    message=f'Found {quality_stats["zero_prices"]} prices with zero or negative values'
                ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                type='quality_check_error',
                severity='warning',
                message=f'Data quality check failed: {str(e)}'
            ))
        
        return issues
    
    def _check_system_statistics(self, db_manager: UnifiedDatabaseManager) -> List[ValidationIssue]:
        """Проверка системных статистик"""
        issues = []
        
        try:
            stats = db_manager.get_system_statistics()
            
            # Проверяем разумность пропорций
            if stats['total_products'] > 0 and stats['total_prices'] > 0:
                prices_per_product = stats['total_prices'] / stats['total_products']
                
                if prices_per_product < 1.1:
                    issues.append(ValidationIssue(
                        type='low_price_coverage',
                        severity='info',
                        message=f'Low price coverage: {prices_per_product:.2f} prices per product',
                        details={'prices_per_product': prices_per_product}
                    ))
                elif prices_per_product > 10:
                    issues.append(ValidationIssue(
                        type='high_price_coverage',
                        severity='info',
                        message=f'High price coverage: {prices_per_product:.2f} prices per product',
                        details={'prices_per_product': prices_per_product}
                    ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                type='statistics_check_error',
                severity='warning',
                message=f'Statistics check failed: {str(e)}'
            ))
        
        return issues
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def _count_similar_product_names(self, db_manager: UnifiedDatabaseManager) -> int:
        """Подсчет товаров с похожими названиями"""
        try:
            # Упрощенная проверка - ищем товары с одинаковыми первыми словами
            products = db_manager.search_master_products("", limit=1000)
            
            first_words = {}
            for product in products:
                first_word = product.standard_name.split()[0].lower() if product.standard_name else ""
                if len(first_word) > 3:  # Игнорируем очень короткие слова
                    first_words[first_word] = first_words.get(first_word, 0) + 1
            
            # Считаем группы с более чем одним товаром
            similar_groups = sum(1 for count in first_words.values() if count > 1)
            
            return similar_groups
            
        except Exception:
            return 0
    
    def _analyze_data_quality(self, db_manager: UnifiedDatabaseManager) -> Dict[str, int]:
        """Анализ качества данных"""
        quality_stats = {
            'total_products': 0,
            'empty_names': 0,
            'short_names': 0,
            'zero_prices': 0
        }
        
        try:
            # Анализируем товары
            products = db_manager.search_master_products("", limit=1000)
            quality_stats['total_products'] = len(products)
            
            for product in products:
                if not product.standard_name or len(product.standard_name.strip()) == 0:
                    quality_stats['empty_names'] += 1
                elif len(product.standard_name.strip()) < 3:
                    quality_stats['short_names'] += 1
            
            # Анализируем цены
            with db_manager.get_session() as session:
                from models.unified_database import SupplierPrice
                
                zero_prices = session.query(SupplierPrice).filter(SupplierPrice.price <= 0).count()
                quality_stats['zero_prices'] = zero_prices
            
        except Exception as e:
            logger.warning(f"Data quality analysis failed: {e}")
        
        return quality_stats
    
    def _create_validation_result(self, issues: List[ValidationIssue], checks_performed: int) -> Dict[str, Any]:
        """Создание результата валидации"""
        critical_errors = sum(1 for issue in issues if issue.severity == 'critical')
        warnings = sum(1 for issue in issues if issue.severity == 'warning')
        
        passed_checks = checks_performed - len(issues)
        success = critical_errors == 0
        
        result = {
            'success': success,
            'total_checks': checks_performed,
            'passed_checks': passed_checks,
            'failed_checks': len(issues),
            'critical_errors': critical_errors,
            'warnings': warnings,
            'issues': [
                {
                    'type': issue.type,
                    'severity': issue.severity,
                    'message': issue.message,
                    'file_path': issue.file_path,
                    'details': issue.details
                }
                for issue in issues
            ],
            'summary': {
                'validation_passed': success,
                'issues_by_severity': {
                    'critical': critical_errors,
                    'warning': warnings,
                    'info': sum(1 for issue in issues if issue.severity == 'info')
                }
            }
        }
        
        return result 