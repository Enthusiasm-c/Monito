"""
=============================================================================
MONITO REST API PACKAGE
=============================================================================
FastAPI REST API для unified системы управления ценами поставщиков Бали
=============================================================================
"""

from .main import create_app

__version__ = "3.0.0"
__all__ = ["create_app"] 