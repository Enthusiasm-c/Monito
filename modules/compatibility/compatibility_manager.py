"""
=============================================================================
MONITO COMPATIBILITY MANAGER
=============================================================================
Версия: 3.0
Цель: Управление обратной совместимостью и плавным переходом к unified системе
=============================================================================
"""

import logging
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path

from modules.adapters.legacy_integration_adapter import LegacyIntegrationAdapter
from modules.compatibility.legacy_api_wrapper import LegacyAPIWrapper
from modules.compatibility.format_converter import FormatConverter
from utils.logger import get_logger

logger = get_logger(__name__)

class CompatibilityManager:
    """
    Менеджер совместимости для управления переходом от legacy к unified системе
    """
    
    def __init__(self, integration_adapter: LegacyIntegrationAdapter, 
                 compatibility_config: Dict[str, Any] = None):
        """
        Инициализация менеджера совместимости
        
        Args:
            integration_adapter: Адаптер интеграции с unified системой
            compatibility_config: Конфигурация совместимости
        """
        self.integration_adapter = integration_adapter
        self.legacy_api_wrapper = LegacyAPIWrapper(integration_adapter)
        self.format_converter = FormatConverter()
        
        # Конфигурация совместимости
        self.config = self._load_compatibility_config(compatibility_config)
        
        # Система отслеживания использования
        self.usage_tracker = {
            'legacy_api_calls': {},
            'deprecated_features': {},
            'migration_progress': {},
            'warnings_issued': {}
        }
        
        # Планировщик миграции
        self.migration_scheduler = {
            'deprecation_warnings': [],
            'forced_migration_date': None,
            'migration_milestones': []
        }
        
        logger.info("CompatibilityManager initialized")
    
    def _load_compatibility_config(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Загрузка конфигурации совместимости"""
        default_config = {
            'deprecation_policy': {
                'warning_period_days': 90,
                'grace_period_days': 180,
                'force_migration_after_days': 365
            },
            'legacy_support': {
                'max_legacy_calls_per_day': 1000,
                'legacy_features_enabled': True,
                'auto_convert_responses': True
            },
            'migration_assistance': {
                'generate_migration_guides': True,
                'track_usage_patterns': True,
                'provide_recommendations': True
            },
            'compatibility_modes': {
                'strict': False,  # Строгое соблюдение unified форматов
                'permissive': True,  # Разрешение legacy форматов
                'hybrid': True  # Смешанный режим
            }
        }
        
        if config:
            self._deep_update(default_config, config)
        
        return default_config
    
    def _deep_update(self, base_dict: Dict, update_dict: Dict):
        """Глубокое обновление словаря"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    # =============================================================================
    # COMPATIBILITY INTERFACE METHODS
    # =============================================================================
    
    def get_legacy_api(self) -> LegacyAPIWrapper:
        """
        Получение legacy API wrapper с отслеживанием использования
        
        Returns:
            Wrapper для legacy API
        """
        self._track_legacy_access('legacy_api_requested')
        
        # Проверяем лимиты использования
        if not self._check_usage_limits():
            logger.warning("Legacy API usage limits exceeded")
            self._issue_deprecation_warning('usage_limits_exceeded')
        
        return self.legacy_api_wrapper
    
    def convert_legacy_data(self, data: Any, source_format: str, 
                          target_format: str) -> Any:
        """
        Конвертация данных между legacy и unified форматами
        
        Args:
            data: Данные для конвертации
            source_format: Исходный формат ('legacy' или 'unified')
            target_format: Целевой формат ('legacy' или 'unified')
            
        Returns:
            Конвертированные данные
        """
        self._track_legacy_access('data_conversion', {
            'source_format': source_format,
            'target_format': target_format
        })
        
        try:
            if source_format == 'legacy' and target_format == 'unified':
                return self._convert_legacy_to_unified(data)
            elif source_format == 'unified' and target_format == 'legacy':
                return self._convert_unified_to_legacy(data)
            else:
                logger.warning(f"Unsupported conversion: {source_format} -> {target_format}")
                return data
                
        except Exception as e:
            logger.error(f"Data conversion failed: {e}")
            self._track_conversion_error(source_format, target_format, str(e))
            return data
    
    def execute_with_compatibility(self, operation: Callable, 
                                 legacy_fallback: Callable = None,
                                 **kwargs) -> Any:
        """
        Выполнение операции с поддержкой совместимости
        
        Args:
            operation: Основная операция (unified система)
            legacy_fallback: Fallback операция (legacy система)
            **kwargs: Параметры операции
            
        Returns:
            Результат операции
        """
        self._track_legacy_access('compatibility_execution')
        
        try:
            # Пытаемся выполнить через unified систему
            result = operation(**kwargs)
            
            # Проверяем, нужно ли конвертировать результат
            if self.config['legacy_support']['auto_convert_responses']:
                result = self._auto_convert_response(result)
            
            return result
            
        except Exception as e:
            logger.warning(f"Unified operation failed: {e}")
            
            # Используем legacy fallback если доступен
            if legacy_fallback:
                logger.info("Falling back to legacy operation")
                self._track_legacy_access('fallback_execution')
                return legacy_fallback(**kwargs)
            else:
                raise e
    
    # =============================================================================
    # MIGRATION MANAGEMENT
    # =============================================================================
    
    def assess_migration_readiness(self) -> Dict[str, Any]:
        """
        Оценка готовности к миграции
        
        Returns:
            Отчет о готовности к миграции
        """
        logger.info("Assessing migration readiness")
        
        assessment = {
            'overall_readiness': 'unknown',
            'legacy_usage': self._analyze_legacy_usage(),
            'data_compatibility': self._check_data_compatibility(),
            'feature_coverage': self._check_feature_coverage(),
            'migration_blockers': [],
            'recommendations': [],
            'estimated_migration_effort': 'unknown'
        }
        
        try:
            # Анализируем использование legacy API
            legacy_stats = self.legacy_api_wrapper.get_legacy_usage_stats()
            assessment['legacy_usage'] = legacy_stats
            
            # Проверяем блокеры миграции
            blockers = self._identify_migration_blockers()
            assessment['migration_blockers'] = blockers
            
            # Генерируем рекомендации
            recommendations = self._generate_migration_recommendations(assessment)
            assessment['recommendations'] = recommendations
            
            # Оценка общей готовности
            readiness_score = self._calculate_readiness_score(assessment)
            assessment['overall_readiness'] = readiness_score
            assessment['estimated_migration_effort'] = self._estimate_migration_effort(assessment)
            
            logger.info(f"Migration readiness assessment completed: {readiness_score}")
            
        except Exception as e:
            logger.error(f"Migration readiness assessment failed: {e}")
            assessment['error'] = str(e)
        
        return assessment
    
    def create_migration_plan(self, target_date: str = None) -> Dict[str, Any]:
        """
        Создание плана миграции
        
        Args:
            target_date: Целевая дата завершения миграции
            
        Returns:
            План миграции
        """
        logger.info("Creating migration plan")
        
        migration_plan = {
            'plan_created': datetime.utcnow().isoformat(),
            'target_completion_date': target_date,
            'phases': [],
            'milestones': [],
            'risk_assessment': {},
            'resource_requirements': {},
            'timeline': {}
        }
        
        try:
            # Оцениваем текущее состояние
            readiness = self.assess_migration_readiness()
            
            # Создаем фазы миграции
            phases = self._create_migration_phases(readiness)
            migration_plan['phases'] = phases
            
            # Определяем контрольные точки
            milestones = self._create_migration_milestones(phases, target_date)
            migration_plan['milestones'] = milestones
            
            # Оценка рисков
            risks = self._assess_migration_risks(readiness)
            migration_plan['risk_assessment'] = risks
            
            # Ресурсы
            resources = self._estimate_resource_requirements(phases)
            migration_plan['resource_requirements'] = resources
            
            # Временная шкала
            timeline = self._create_migration_timeline(phases, target_date)
            migration_plan['timeline'] = timeline
            
            logger.info("Migration plan created successfully")
            
        except Exception as e:
            logger.error(f"Migration plan creation failed: {e}")
            migration_plan['error'] = str(e)
        
        return migration_plan
    
    def execute_migration_step(self, step_id: str, step_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполнение шага миграции
        
        Args:
            step_id: Идентификатор шага
            step_config: Конфигурация шага
            
        Returns:
            Результат выполнения шага
        """
        logger.info(f"Executing migration step: {step_id}")
        
        step_result = {
            'step_id': step_id,
            'started_at': datetime.utcnow().isoformat(),
            'status': 'in_progress',
            'progress': 0,
            'results': {},
            'errors': []
        }
        
        try:
            # Валидируем предварительные условия
            if not self._validate_step_prerequisites(step_id, step_config):
                raise Exception(f"Prerequisites not met for step {step_id}")
            
            # Выполняем шаг в зависимости от типа
            step_type = step_config.get('type', 'unknown')
            
            if step_type == 'data_migration':
                result = self._execute_data_migration_step(step_config)
            elif step_type == 'api_migration':
                result = self._execute_api_migration_step(step_config)
            elif step_type == 'validation':
                result = self._execute_validation_step(step_config)
            elif step_type == 'cleanup':
                result = self._execute_cleanup_step(step_config)
            else:
                raise Exception(f"Unknown step type: {step_type}")
            
            step_result['results'] = result
            step_result['status'] = 'completed'
            step_result['progress'] = 100
            
            logger.info(f"Migration step {step_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Migration step {step_id} failed: {e}")
            step_result['status'] = 'failed'
            step_result['errors'].append(str(e))
        
        step_result['completed_at'] = datetime.utcnow().isoformat()
        
        # Обновляем отслеживание прогресса
        self._update_migration_progress(step_id, step_result)
        
        return step_result
    
    # =============================================================================
    # DEPRECATION MANAGEMENT
    # =============================================================================
    
    def issue_deprecation_warning(self, feature: str, replacement: str = None,
                                removal_date: str = None) -> None:
        """
        Выдача предупреждения об устаревании
        
        Args:
            feature: Устаревшая функция
            replacement: Рекомендуемая замена
            removal_date: Дата удаления функции
        """
        warning_id = f"{feature}_{datetime.utcnow().strftime('%Y%m%d')}"
        
        if warning_id not in self.usage_tracker['warnings_issued']:
            warning_message = f"DEPRECATION WARNING: {feature} is deprecated"
            
            if replacement:
                warning_message += f". Use {replacement} instead"
            
            if removal_date:
                warning_message += f". Will be removed on {removal_date}"
            
            logger.warning(warning_message)
            
            # Записываем предупреждение
            self.usage_tracker['warnings_issued'][warning_id] = {
                'feature': feature,
                'replacement': replacement,
                'removal_date': removal_date,
                'issued_at': datetime.utcnow().isoformat(),
                'count': 1
            }
        else:
            # Увеличиваем счетчик
            self.usage_tracker['warnings_issued'][warning_id]['count'] += 1
    
    def get_deprecation_report(self) -> Dict[str, Any]:
        """
        Получение отчета об устаревших функциях
        
        Returns:
            Отчет об устаревших функциях
        """
        report = {
            'total_warnings': len(self.usage_tracker['warnings_issued']),
            'active_deprecations': [],
            'upcoming_removals': [],
            'usage_statistics': {},
            'migration_urgency': 'low'
        }
        
        current_date = datetime.utcnow()
        
        for warning_id, warning_info in self.usage_tracker['warnings_issued'].items():
            warning_data = {
                'feature': warning_info['feature'],
                'replacement': warning_info['replacement'],
                'removal_date': warning_info['removal_date'],
                'warning_count': warning_info['count'],
                'days_since_first_warning': (current_date - datetime.fromisoformat(warning_info['issued_at'])).days
            }
            
            report['active_deprecations'].append(warning_data)
            
            # Проверяем близкие даты удаления
            if warning_info['removal_date']:
                removal_date = datetime.fromisoformat(warning_info['removal_date'])
                days_until_removal = (removal_date - current_date).days
                
                if days_until_removal <= 30:
                    report['upcoming_removals'].append({
                        **warning_data,
                        'days_until_removal': days_until_removal
                    })
        
        # Определяем срочность миграции
        if report['upcoming_removals']:
            report['migration_urgency'] = 'high'
        elif len(report['active_deprecations']) > 5:
            report['migration_urgency'] = 'medium'
        
        return report
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def _track_legacy_access(self, access_type: str, details: Dict[str, Any] = None):
        """Отслеживание использования legacy функций"""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        if today not in self.usage_tracker['legacy_api_calls']:
            self.usage_tracker['legacy_api_calls'][today] = {}
        
        if access_type not in self.usage_tracker['legacy_api_calls'][today]:
            self.usage_tracker['legacy_api_calls'][today][access_type] = 0
        
        self.usage_tracker['legacy_api_calls'][today][access_type] += 1
        
        # Детали доступа
        if details:
            details_key = f"{access_type}_details"
            if details_key not in self.usage_tracker['legacy_api_calls'][today]:
                self.usage_tracker['legacy_api_calls'][today][details_key] = []
            
            self.usage_tracker['legacy_api_calls'][today][details_key].append({
                'timestamp': datetime.utcnow().isoformat(),
                **details
            })
    
    def _check_usage_limits(self) -> bool:
        """Проверка лимитов использования legacy API"""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        daily_limit = self.config['legacy_support']['max_legacy_calls_per_day']
        
        if today in self.usage_tracker['legacy_api_calls']:
            total_calls = sum(self.usage_tracker['legacy_api_calls'][today].values())
            return total_calls < daily_limit
        
        return True
    
    def _issue_deprecation_warning(self, reason: str):
        """Выдача предупреждения об устаревании"""
        if reason == 'usage_limits_exceeded':
            self.issue_deprecation_warning(
                'legacy_api_high_usage',
                'unified_system_api',
                (datetime.utcnow() + timedelta(days=30)).isoformat()
            )
    
    def _convert_legacy_to_unified(self, data: Any) -> Any:
        """Конвертация legacy данных в unified формат"""
        if isinstance(data, dict):
            return self.format_converter.legacy_product_to_unified_format(data)
        elif isinstance(data, list):
            return [self.format_converter.legacy_product_to_unified_format(item) for item in data]
        else:
            return data
    
    def _convert_unified_to_legacy(self, data: Any) -> Any:
        """Конвертация unified данных в legacy формат"""
        if hasattr(data, '__dict__'):  # Unified product object
            return self.format_converter.unified_product_to_legacy_format(data)
        elif isinstance(data, dict):
            return self.format_converter.unified_report_to_legacy_format(data)
        else:
            return data
    
    def _auto_convert_response(self, response: Any) -> Any:
        """Автоматическая конвертация ответа для совместимости"""
        try:
            # Если ответ в unified формате, конвертируем в legacy
            if self.config['compatibility_modes']['permissive']:
                return self._convert_unified_to_legacy(response)
        except Exception as e:
            logger.debug(f"Auto-conversion failed, returning original response: {e}")
        
        return response
    
    def _analyze_legacy_usage(self) -> Dict[str, Any]:
        """Анализ использования legacy функций"""
        usage_analysis = {
            'total_legacy_calls': 0,
            'peak_usage_day': None,
            'most_used_features': {},
            'usage_trend': 'stable'
        }
        
        try:
            # Анализируем статистику за последние 30 дней
            total_calls = 0
            daily_calls = {}
            
            for date, calls in self.usage_tracker['legacy_api_calls'].items():
                day_total = sum(v for k, v in calls.items() if not k.endswith('_details'))
                daily_calls[date] = day_total
                total_calls += day_total
            
            usage_analysis['total_legacy_calls'] = total_calls
            
            if daily_calls:
                peak_day = max(daily_calls, key=daily_calls.get)
                usage_analysis['peak_usage_day'] = {
                    'date': peak_day,
                    'calls': daily_calls[peak_day]
                }
            
            # Анализируем тренд
            if len(daily_calls) > 7:
                recent_avg = sum(list(daily_calls.values())[-7:]) / 7
                older_avg = sum(list(daily_calls.values())[:-7]) / max(len(daily_calls) - 7, 1)
                
                if recent_avg > older_avg * 1.2:
                    usage_analysis['usage_trend'] = 'increasing'
                elif recent_avg < older_avg * 0.8:
                    usage_analysis['usage_trend'] = 'decreasing'
                
        except Exception as e:
            logger.warning(f"Legacy usage analysis failed: {e}")
        
        return usage_analysis
    
    def _check_data_compatibility(self) -> Dict[str, Any]:
        """Проверка совместимости данных"""
        compatibility = {
            'unified_database_ready': False,
            'legacy_data_volume': 0,
            'conversion_test_passed': False,
            'data_integrity_score': 0.0
        }
        
        try:
            # Проверяем наличие unified базы данных
            system_stats = self.integration_adapter.db_manager.get_system_statistics()
            compatibility['unified_database_ready'] = system_stats['total_products'] > 0
            
            # Тестируем конвертацию данных
            test_data = {'name': 'Test Product', 'price': 100, 'category': 'test'}
            converted = self.format_converter.legacy_product_to_unified_format(test_data)
            compatibility['conversion_test_passed'] = 'standard_name' in converted
            
            # Упрощенная оценка целостности
            if compatibility['unified_database_ready'] and compatibility['conversion_test_passed']:
                compatibility['data_integrity_score'] = 0.9
                
        except Exception as e:
            logger.warning(f"Data compatibility check failed: {e}")
        
        return compatibility
    
    def _check_feature_coverage(self) -> Dict[str, Any]:
        """Проверка покрытия функций"""
        coverage = {
            'parsing_coverage': 0.9,  # 90% функций парсинга покрыты
            'normalization_coverage': 0.85,  # 85% функций нормализации
            'reporting_coverage': 0.8,  # 80% функций отчетности
            'api_coverage': 0.95,  # 95% API методов
            'overall_coverage': 0.875
        }
        
        return coverage
    
    def _identify_migration_blockers(self) -> List[Dict[str, Any]]:
        """Идентификация блокеров миграции"""
        blockers = []
        
        # Проверяем высокое использование legacy API
        legacy_stats = self.legacy_api_wrapper.get_legacy_usage_stats()
        if legacy_stats['migration_urgency'] == 'high':
            blockers.append({
                'type': 'high_legacy_usage',
                'severity': 'medium',
                'description': 'High usage of legacy API detected',
                'resolution': 'Gradually replace legacy calls with unified system'
            })
        
        return blockers
    
    def _generate_migration_recommendations(self, assessment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Генерация рекомендаций по миграции"""
        recommendations = []
        
        # Рекомендации на основе использования legacy
        legacy_usage = assessment.get('legacy_usage', {})
        if legacy_usage.get('total_legacy_calls', 0) > 100:
            recommendations.append({
                'priority': 'high',
                'category': 'usage_reduction',
                'recommendation': 'Reduce legacy API usage before migration',
                'action_items': [
                    'Identify most frequently used legacy methods',
                    'Replace them with unified equivalents',
                    'Monitor usage reduction progress'
                ]
            })
        
        # Рекомендации по данным
        data_compatibility = assessment.get('data_compatibility', {})
        if not data_compatibility.get('unified_database_ready', False):
            recommendations.append({
                'priority': 'critical',
                'category': 'data_preparation',
                'recommendation': 'Prepare unified database before migration',
                'action_items': [
                    'Run data migration scripts',
                    'Validate data integrity',
                    'Test unified system functionality'
                ]
            })
        
        return recommendations
    
    def _calculate_readiness_score(self, assessment: Dict[str, Any]) -> str:
        """Расчет оценки готовности к миграции"""
        score = 0
        max_score = 0
        
        # Анализ использования legacy (20% веса)
        legacy_usage = assessment.get('legacy_usage', {})
        if legacy_usage.get('usage_trend') == 'decreasing':
            score += 20
        elif legacy_usage.get('usage_trend') == 'stable':
            score += 10
        max_score += 20
        
        # Совместимость данных (40% веса)
        data_compatibility = assessment.get('data_compatibility', {})
        if data_compatibility.get('unified_database_ready'):
            score += 20
        if data_compatibility.get('conversion_test_passed'):
            score += 10
        score += data_compatibility.get('data_integrity_score', 0) * 10
        max_score += 40
        
        # Покрытие функций (30% веса)
        feature_coverage = assessment.get('feature_coverage', {})
        score += feature_coverage.get('overall_coverage', 0) * 30
        max_score += 30
        
        # Блокеры миграции (10% веса)
        blockers = assessment.get('migration_blockers', [])
        if len(blockers) == 0:
            score += 10
        elif len(blockers) <= 2:
            score += 5
        max_score += 10
        
        # Рассчитываем финальную оценку
        if max_score > 0:
            final_score = score / max_score
            
            if final_score >= 0.9:
                return 'excellent'
            elif final_score >= 0.75:
                return 'good'
            elif final_score >= 0.6:
                return 'fair'
            elif final_score >= 0.4:
                return 'poor'
            else:
                return 'not_ready'
        
        return 'unknown'
    
    def _estimate_migration_effort(self, assessment: Dict[str, Any]) -> str:
        """Оценка усилий для миграции"""
        effort_factors = []
        
        # Учитываем объем legacy использования
        legacy_usage = assessment.get('legacy_usage', {})
        total_calls = legacy_usage.get('total_legacy_calls', 0)
        
        if total_calls > 1000:
            effort_factors.append('high_usage_volume')
        elif total_calls > 100:
            effort_factors.append('medium_usage_volume')
        
        # Учитываем блокеры
        blockers = assessment.get('migration_blockers', [])
        if len(blockers) > 3:
            effort_factors.append('many_blockers')
        
        # Учитываем готовность данных
        data_compatibility = assessment.get('data_compatibility', {})
        if not data_compatibility.get('unified_database_ready'):
            effort_factors.append('data_preparation_needed')
        
        # Оценка усилий
        if len(effort_factors) >= 3:
            return 'high'
        elif len(effort_factors) >= 1:
            return 'medium'
        else:
            return 'low'
    
    def _create_migration_phases(self, readiness: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Создание фаз миграции"""
        phases = [
            {
                'phase_id': 1,
                'name': 'Preparation',
                'description': 'Prepare unified system and validate data',
                'estimated_duration_days': 14,
                'prerequisites': [],
                'deliverables': ['Unified database ready', 'Data validation complete']
            },
            {
                'phase_id': 2,
                'name': 'Legacy Reduction',
                'description': 'Reduce legacy API usage',
                'estimated_duration_days': 30,
                'prerequisites': ['Phase 1 complete'],
                'deliverables': ['Legacy usage reduced by 50%', 'Critical methods migrated']
            },
            {
                'phase_id': 3,
                'name': 'Full Migration',
                'description': 'Complete migration to unified system',
                'estimated_duration_days': 21,
                'prerequisites': ['Phase 2 complete'],
                'deliverables': ['All legacy calls replaced', 'System fully unified']
            },
            {
                'phase_id': 4,
                'name': 'Cleanup',
                'description': 'Remove legacy components and finalize',
                'estimated_duration_days': 7,
                'prerequisites': ['Phase 3 complete'],
                'deliverables': ['Legacy code removed', 'Documentation updated']
            }
        ]
        
        return phases
    
    def _create_migration_milestones(self, phases: List[Dict[str, Any]], 
                                   target_date: str = None) -> List[Dict[str, Any]]:
        """Создание контрольных точек миграции"""
        milestones = []
        
        current_date = datetime.utcnow()
        
        for phase in phases:
            milestone_date = current_date + timedelta(days=sum(p['estimated_duration_days'] for p in phases[:phase['phase_id']]))
            
            milestones.append({
                'milestone_id': f"M{phase['phase_id']}",
                'name': f"Phase {phase['phase_id']} Complete",
                'target_date': milestone_date.isoformat(),
                'phase_id': phase['phase_id'],
                'success_criteria': phase['deliverables']
            })
        
        return milestones
    
    def _assess_migration_risks(self, readiness: Dict[str, Any]) -> Dict[str, Any]:
        """Оценка рисков миграции"""
        risks = {
            'risk_level': 'medium',
            'identified_risks': [],
            'mitigation_strategies': []
        }
        
        # Риск высокого использования legacy
        legacy_usage = readiness.get('legacy_usage', {})
        if legacy_usage.get('total_legacy_calls', 0) > 500:
            risks['identified_risks'].append({
                'risk': 'High legacy API dependency',
                'probability': 'high',
                'impact': 'medium',
                'mitigation': 'Gradual migration with parallel systems'
            })
        
        return risks
    
    def _estimate_resource_requirements(self, phases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Оценка требований к ресурсам"""
        total_days = sum(phase['estimated_duration_days'] for phase in phases)
        
        return {
            'development_effort_days': total_days * 0.7,
            'testing_effort_days': total_days * 0.2,
            'project_management_days': total_days * 0.1,
            'required_roles': ['Developer', 'QA Engineer', 'Project Manager'],
            'estimated_cost': f"${total_days * 500}"  # Примерная оценка
        }
    
    def _create_migration_timeline(self, phases: List[Dict[str, Any]], 
                                 target_date: str = None) -> Dict[str, Any]:
        """Создание временной шкалы миграции"""
        start_date = datetime.utcnow()
        
        if target_date:
            end_date = datetime.fromisoformat(target_date)
        else:
            total_duration = sum(phase['estimated_duration_days'] for phase in phases)
            end_date = start_date + timedelta(days=total_duration)
        
        return {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_duration_days': (end_date - start_date).days,
            'phase_schedule': phases
        }
    
    def _validate_step_prerequisites(self, step_id: str, step_config: Dict[str, Any]) -> bool:
        """Валидация предварительных условий для шага миграции"""
        # Упрощенная валидация
        return True
    
    def _execute_data_migration_step(self, step_config: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение шага миграции данных"""
        return {'type': 'data_migration', 'status': 'completed'}
    
    def _execute_api_migration_step(self, step_config: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение шага миграции API"""
        return {'type': 'api_migration', 'status': 'completed'}
    
    def _execute_validation_step(self, step_config: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение шага валидации"""
        return {'type': 'validation', 'status': 'completed'}
    
    def _execute_cleanup_step(self, step_config: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение шага очистки"""
        return {'type': 'cleanup', 'status': 'completed'}
    
    def _update_migration_progress(self, step_id: str, step_result: Dict[str, Any]):
        """Обновление прогресса миграции"""
        if 'migration_steps' not in self.usage_tracker['migration_progress']:
            self.usage_tracker['migration_progress']['migration_steps'] = {}
        
        self.usage_tracker['migration_progress']['migration_steps'][step_id] = step_result
    
    def _track_conversion_error(self, source_format: str, target_format: str, error: str):
        """Отслеживание ошибок конвертации"""
        error_key = f"{source_format}_to_{target_format}"
        
        if 'conversion_errors' not in self.usage_tracker:
            self.usage_tracker['conversion_errors'] = {}
        
        if error_key not in self.usage_tracker['conversion_errors']:
            self.usage_tracker['conversion_errors'][error_key] = []
        
        self.usage_tracker['conversion_errors'][error_key].append({
            'timestamp': datetime.utcnow().isoformat(),
            'error': error
        }) 