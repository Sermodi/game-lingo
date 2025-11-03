"""
Modelos de datos para Game Description Translator.

Contiene las estructuras de datos principales:
- GameInfo: Información completa del juego
- Platform: Enumeración de plataformas soportadas
- TranslationResult: Resultado de traducción
- APIResponse: Respuestas de APIs
"""

from __future__ import annotations

from .game import GameInfo, Platform, TranslationResult
from .api_response import APIResponse, SteamResponse, RAWGResponse

__all__ = [
    "GameInfo",
    "Platform", 
    "TranslationResult",
    "APIResponse",
    "SteamResponse",
    "RAWGResponse",
]