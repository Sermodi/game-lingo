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

import sys
from pathlib import Path
from typing import Any, Dict, cast

# Importaciones estándar primero
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from .core.translator import GameDescriptionTranslator
from .exceptions import (
    APIError,
    GameNotFoundError,
    GameTranslatorError,
    RateLimitError,
    TranslationError,
)
from .models.game import GameInfo, Platform, TranslationResult

# Constantes
__author__ = "Sermodi"
__email__ = "sermodsoftware@gmail.com"


def _get_project_meta() -> Dict[str, Any]:
    """Obtiene los metadatos del proyecto desde pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"

    try:
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)
        return cast("Dict[str, Any]", pyproject.get("tool", {}).get("poetry", {}))
    except Exception as e:
        print(f"Error al leer pyproject.toml: {e}", file=sys.stderr)
        return {}


# Obtener la versión del proyecto
_project_meta = _get_project_meta()
__version__ = _project_meta.get("version", "0.0.0")

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
