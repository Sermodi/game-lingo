"""
Conectores para APIs externas.

Este módulo contiene los conectores para todas las APIs utilizadas:
- Steam Store API: Descripciones nativas en español
- RAWG API: Base de datos completa de juegos
- DeepL API: Traducción de alta calidad
- Google Translate API: Traducción como fallback
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional, Type, TypeVar, cast

# Definir __all__ al inicio
__all__ = [
    "DeepLAPIConnector",
    "GoogleTranslateAPIConnector",
    "RAWGAPIConnector",
    "SteamAPI",
    "deepl_translate",
    "google_detect_language",
    "google_translate",
]

# Variables de tipo
T = TypeVar("T")

# Importar conectores cuando estén disponibles
try:
    from .steam_api import SteamAPI as _SteamAPI

    SteamAPI: Type[_SteamAPI] = _SteamAPI
except ImportError:
    SteamAPI = None  # type: ignore[assignment]

try:
    from .rawg_api import RAWGAPIConnector as _RAWGAPIConnector

    RAWGAPIConnector: Type[_RAWGAPIConnector] = _RAWGAPIConnector
except ImportError:
    RAWGAPIConnector = None  # type: ignore[assignment]
    if not TYPE_CHECKING:
        RAWGAPI = None  # type: ignore[misc]

# Tipos para las funciones de DeepL
# DeepL API
try:
    from .deepl_api import DeepLAPIConnector as _DeepLAPIConnector
    from .deepl_api import translate_game_description as _deepl_translate

    DeepLAPIConnector: Type[_DeepLAPIConnector] = _DeepLAPIConnector
    deepl_translate: Callable[..., Any] = _deepl_translate
except ImportError:
    DeepLAPIConnector = None  # type: ignore[assignment]
    deepl_translate = None  # type: ignore[assignment]

# Google Translate API
try:
    from .google_translate_api import (
        GoogleTranslateAPIConnector as _GoogleTranslateAPIConnector,
    )
    from .google_translate_api import detect_language as _google_detect_language
    from .google_translate_api import translate_game_description as _google_translate

    GoogleTranslateAPIConnector: Type[_GoogleTranslateAPIConnector] = (
        _GoogleTranslateAPIConnector
    )
    google_translate: Callable[..., Any] = _google_translate
    google_detect_language: Callable[..., Any] = _google_detect_language
except ImportError:
    GoogleTranslateAPIConnector = None  # type: ignore[assignment]
    google_translate = None  # type: ignore[assignment]
    google_detect_language = None  # type: ignore[assignment]
