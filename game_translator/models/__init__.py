"""
Modelos de datos para Game Description Translator.

Contiene las estructuras de datos principales:
- GameInfo: Información completa del juego
- Platform: Enumeración de plataformas soportadas
- TranslationResult: Resultado de traducción
- APIResponse: Respuestas de APIs
"""

from __future__ import annotations

from .api_response import APIResponse, RAWGResponse, SteamResponse
from .game import GameInfo, Platform, TranslationResult

__all__ = [
    "APIResponse",
    "GameInfo",
    "Platform",
    "RAWGResponse",
    "SteamResponse",
    "TranslationResult",
]
