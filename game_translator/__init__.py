"""
Game Description Translator - Traductor inteligente de descripciones de videojuegos.

Estrategia híbrida multi-API de 3 niveles:
1. Steam Store API (Fuente primaria) - Descripciones en español nativas
2. RAWG API (Fuente secundaria) - Para juegos no disponibles en Steam
3. DeepL/Google Translate (Traducción) - Solo para traducciones cuando no hay datos nativos

Características:
- Máxima fidelidad con descripciones nativas
- Cobertura completa con fallbacks múltiples
- Caché inteligente con SQLite y compresión
- Rate limiting automático para todas las APIs
- Manejo robusto de errores con reintentos
- Soporte asíncrono para alto rendimiento
- Tipado estático completo con mypy
- Logging detallado y configurable
- Configuración flexible por variables de entorno
"""

from __future__ import annotations

from .core.translator import GameDescriptionTranslator
from .exceptions import (
    APIError,
    GameNotFoundError,
    GameTranslatorError,
    RateLimitError,
    TranslationError,
)
from .models.game import GameInfo, Platform, TranslationResult

__version__ = "0.2.0"
__author__ = "Sermodi"
__email__ = "sermodsoftware@gmail.com"

__all__ = [
    "APIError",
    "GameDescriptionTranslator",
    "GameInfo",
    "GameNotFoundError",
    "GameTranslatorError",
    "Platform",
    "RateLimitError",
    "TranslationError",
    "TranslationResult",
    "__author__",
    "__email__",
    "__version__",
]
