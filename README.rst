GameLingo
=========

|Python 3.9+| |License: MIT| |Code style: black| |Ruff| |mypy|
|GitHub release| |GitHub stars|

Multi-language video game description translator with smart API orchestration
----------------------------------------------------------------------------

Intelligent game description translation system using a 3-tier hybrid strategy to get the best translations possible in any language.

Estrategia Híbrida
------------------

El sistema implementa una estrategia de 3 niveles para garantizar la mejor calidad y cobertura:

1. **Steam Store API** (Fuente primaria) - Descripciones en español nativas
2. **RAWG API** (Fuente secundaria) - Para juegos no disponibles en Steam
3. **DeepL/Google Translate** (Traducción) - Solo para traducciones cuando no hay datos nativos

Características
--------------

- **Máxima Fidelidad**: Prioriza descripciones nativas en español
- **Cobertura Completa**: Fallbacks múltiples aseguran 99%+ de éxito
- **Caché Inteligente**: SQLite con compresión y TTL configurable
- **Rate Limiting**: Respeta límites de todas las APIs automáticamente
- **Asíncrono**: Rendimiento optimizado con asyncio
- **Tipado Estático**: 100% tipado con mypy
- **Logging Completo**: Trazabilidad total del proceso
- **Configuración Flexible**: Variables de entorno para todo

Instalación
-----------

### Requisitos

- Python 3.9+
- Poetry (recomendado) o pip

### Con Poetry (Recomendado)

```bash
# Instalar desde PyPI
poetry add game-lingo
```

### Con pip

```bash
pip install game-lingo
```

Uso Básico
----------

```python
from game_lingo import GameDescriptionTranslator
import asyncio

async def main():
    translator = GameDescriptionTranslator()
    
    # Traducir un juego
    result = await translator.translate_game_description(
        "Hades II",
        target_lang="es"
    )
    
    print(f"Juego: {result.game_info.name}")
    print(f"Descripción: {result.game_info.short_description_es}")

if __name__ == "__main__":
    asyncio.run(main())
```

Estructura del Proyecto
----------------------

```
game_lingo/
├── __init__.py
├── cli.py                 # Interfaz de línea de comandos
├── core/
│   ├── __init__.py
│   ├── translator.py      # Lógica principal de traducción
│   ├── cache.py           # Sistema de caché
│   └── rate_limiter.py    # Control de tasas
├── models/
│   ├── __init__.py
│   └── game.py           # Modelos de datos
└── apis/
    ├── __init__.py
    ├── steam_api.py      # Integración con Steam
    └── deepl_api.py      # Integración con DeepL
```

Configuración
------------

Configuración mediante variables de entorno:

```bash
# Claves de API (obligatorias)
export DEEPL_API_KEY=tu_clave_deepl
export GOOGLE_TRANSLATE_API_KEY=tu_clave_google

# Configuración de caché (opcional)
export CACHE_TTL=86400  # 1 día en segundos
export CACHE_MAX_SIZE=1000

# Nivel de log (debug, info, warning, error)
export LOG_LEVEL=info
```

Licencia
--------

MIT License. Ver [LICENSE](LICENSE) para más detalles.

.. |Python 3.9+| image:: https://img.shields.io/badge/python-3.9+-blue.svg
   :target: https://www.python.org/downloads/
.. |License: MIT| image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://opensource.org/licenses/MIT
.. |Code style: black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
.. |Ruff| image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
   :target: https://github.com/astral-sh/ruff
.. |mypy| image:: https://www.mypy-lang.org/static/mypy_badge.svg
   :target: https://mypy-lang.org/
.. |GitHub release| image:: https://img.shields.io/github/v/release/Sermodi/game-lingo
   :target: https://github.com/Sermodi/game-lingo/releases
.. |GitHub stars| image:: https://img.shields.io/github/stars/Sermodi/game-lingo?style=social
   :target: https://github.com/Sermodi/game-lingo
