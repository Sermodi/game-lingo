"""
Módulo core con la lógica principal de Game Description Translator.

Contiene:
- GameDescriptionTranslator: Clase principal del traductor
- Cache: Sistema de caché inteligente
- RateLimiter: Control de límites de velocidad
- Validators: Validadores de datos
"""

from __future__ import annotations

from .translator import GameDescriptionTranslator
from .cache import Cache
from .rate_limiter import RateLimiter

__all__ = [
    "GameDescriptionTranslator",
    "Cache", 
    "RateLimiter",
]