"""
Conectores para APIs externas.

Este módulo contiene los conectores para todas las APIs utilizadas:
- Steam Store API: Descripciones nativas en español
- RAWG API: Base de datos completa de juegos
- DeepL API: Traducción de alta calidad
- Google Translate API: Traducción como fallback
"""

from __future__ import annotations

# Definir __all__ al inicio
__all__ = [
    "SteamAPI",
    "RAWGAPI", 
    "DeepLAPI",
    "GoogleTranslateAPI",
]

# Importar conectores cuando estén disponibles
try:
    from .steam_api import SteamAPI
except ImportError:
    SteamAPI = None

try:
    from .rawg_api import RAWGAPI
except ImportError:
    RAWGAPI = None

try:
    from .deepl_api import DeepLAPIConnector, translate_game_description as deepl_translate
    DeepLAPI = DeepLAPIConnector
    __all__.extend(['DeepLAPIConnector', 'deepl_translate'])
except ImportError:
    DeepLAPIConnector = None
    deepl_translate = None

try:
    from .google_translate_api import (
        GoogleTranslateAPIConnector, 
        translate_game_description as google_translate,
        detect_language as google_detect_language
    )
    GoogleTranslateAPI = GoogleTranslateAPIConnector
    __all__.extend(['GoogleTranslateAPIConnector', 'google_translate', 'google_detect_language'])
except ImportError:
    GoogleTranslateAPIConnector = None
    google_translate = None
    google_detect_language = None