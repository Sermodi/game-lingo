"""
Modelos de datos para Game Description Translator.

Contiene las estructuras de datos principales:
- GameInfo: Información completa del juego
- Platform: Enumeración de plataformas soportadas
- TranslationResult: Resultado de traducción
- APIResponse: Respuestas de APIs
- Language: Enumeración de idiomas soportados
"""

from __future__ import annotations

from .api_response import APIResponse, RAWGResponse, SteamResponse
from .game import GameInfo, Language, Platform, TranslationResult

__all__ = [
    "APIResponse",
    "GameInfo",
    "Language",
    "Platform",
    "RAWGResponse",
    "SteamResponse",
    "TranslationResult",
]
