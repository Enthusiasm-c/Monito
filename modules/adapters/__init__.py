"""
=============================================================================
MONITO ADAPTERS PACKAGE
=============================================================================
Адаптеры для интеграции существующих модулей с новой unified системой
=============================================================================
"""

from .parser_adapter import ParserAdapter
from .normalizer_adapter import NormalizerAdapter
from .legacy_integration_adapter import LegacyIntegrationAdapter

__all__ = [
    'ParserAdapter',
    'NormalizerAdapter', 
    'LegacyIntegrationAdapter'
] 