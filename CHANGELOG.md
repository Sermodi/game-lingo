# Changelog

Todos los cambios notables del proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [0.2.0] - 2025-11-03

### Añadido
- **Integración completa del rate limiter**: Todas las APIs ahora registran sus requests y uso de caracteres
- **Tracking de costos en tiempo real**: El comando `stats` muestra datos precisos de uso de APIs
- **Persistencia de estadísticas**: Las estadísticas se guardan después de cada request para mayor precisión

### Cambiado
- Steam API ahora acepta `rate_limiter` como parámetro opcional
- RAWG API ahora acepta `rate_limiter` como parámetro opcional (antes creaba su propia instancia)
- DeepL API ahora acepta `rate_limiter` como parámetro opcional
- Google Translate API ahora acepta `rate_limiter` como parámetro opcional
- Translator pasa el rate limiter compartido a todas las APIs para tracking unificado

### Mejorado
- Rate limiter ahora guarda estado inmediatamente después de cada request
- Estadísticas globales se actualizan correctamente entre ejecuciones
- Comando `stats` muestra datos precisos de requests y caracteres usados

## [0.1.0] - 2025-11-03

### Added
- **CLI (Command Line Interface)** para uso desde terminal
  - Comando `game-translator search` para buscar juegos
  - Comando `game-translator translate` para traducción directa
  - Comando `game-translator describe` para buscar con descripción proporcionada (usa nativa si existe, sino traduce)
  - Comando `game-translator info` para información detallada
  - Comando `game-translator stats` para ver estadísticas de uso de APIs y costos estimados
  - Soporte para ejecución con `python -m game_translator`
  - Ayuda integrada con `--help`
  - Salida formateada y coloreada
  - Soporte UTF-8 para emojis en Windows
- Sistema de traducción inteligente de descripciones de videojuegos
- Estrategia híbrida multi-API de 3 niveles:
  - Steam Store API como fuente primaria (descripciones nativas en español)
  - RAWG API como fuente secundaria (fallback para juegos no en Steam)
  - DeepL y Google Translate para traducción cuando no hay datos nativos
- Sistema de caché inteligente con SQLite:
  - Compresión de datos para optimizar espacio
  - TTL configurable por entrada
  - Estadísticas de hit/miss rate
  - Limpieza automática de entradas expiradas
- Rate limiting automático para todas las APIs:
  - Respeta límites de Steam (200 req/5min)
  - Respeta límites de RAWG (27 req/hora)
  - Respeta límites de DeepL (configurable)
  - Respeta límites de Google Translate (configurable)
- Conectores de APIs implementados:
  - `SteamAPIConnector`: Búsqueda y detalles de juegos en Steam
  - `RAWGAPIConnector`: Base de datos extensa de juegos
  - `DeepLAPIConnector`: Traducción de alta calidad
  - `GoogleTranslateAPIConnector`: Traducción con detección de idioma
- Modelos de datos con Pydantic v2:
  - `GameInfo`: Información completa del juego
  - `TranslationResult`: Resultado con metadatos de traducción
  - `Platform`: Enum de plataformas soportadas
  - Respuestas tipadas para cada API
- Sistema de excepciones personalizado:
  - `GameTranslatorError`: Base para todas las excepciones
  - `APIError`: Errores de comunicación con APIs
  - `TranslationError`: Errores en proceso de traducción
  - `GameNotFoundError`: Juego no encontrado
  - `RateLimitError`: Límite de rate alcanzado
- Configuración centralizada con `python-decouple`:
  - Carga desde archivo `.env`
  - Valores por defecto sensatos
  - Validación de configuración crítica
- Sistema de logging completo:
  - Logs a archivo y consola
  - Niveles configurables (DEBUG, INFO, WARNING, ERROR)
  - Formato estructurado con timestamps
  - Trazabilidad completa del flujo de traducción
- Soporte asíncrono con `aiohttp`:
  - Operaciones no bloqueantes
  - Procesamiento en paralelo de múltiples juegos
  - Manejo eficiente de recursos
- Reintentos automáticos con `tenacity`:
  - Exponential backoff
  - Reintentos configurables por API
  - Manejo de errores transitorios
- Suite de tests completa:
  - Tests unitarios para cada componente
  - Tests de integración con APIs reales
  - Tests manuales para validación
  - Cobertura de código con pytest-cov
  - Mocks para tests sin dependencias externas
- Herramientas de desarrollo:
  - Formateo con `black`
  - Linting con `ruff`
  - Type checking con `mypy`
  - Security scanning con `bandit`
- Documentación:
  - README completo con ejemplos de uso
  - Docstrings estilo Google en todo el código
  - Guías de configuración de API keys
  - Scripts de ejemplo (`example_usage.py`)
- Configuración de proyecto con Poetry:
  - Gestión de dependencias
  - Entornos virtuales
  - Scripts de desarrollo
  - Configuración de herramientas (black, ruff, mypy)

### Features Principales
- **Búsqueda por nombre**: Encuentra juegos por título en múltiples APIs
- **Búsqueda por plataforma**: Filtra resultados por plataforma específica
- **Traducción directa**: Traduce descripciones en inglés sin búsqueda
- **Modo híbrido**: Combina búsqueda y traducción según disponibilidad
- **Caché persistente**: Evita llamadas redundantes a APIs
- **Fallback inteligente**: Cambia automáticamente entre fuentes de datos
- **Metadatos ricos**: Incluye confianza, fuente, tiempo de procesamiento
- **Manejo robusto de errores**: Continúa funcionando aunque algunas APIs fallen

### Technical Details
- Python 3.9+ requerido
- Tipado estático completo (mypy strict compatible)
- Arquitectura en capas (dominio/infraestructura/presentación)
- Principios SOLID aplicados
- Código PEP 8 compliant
- Sin dependencias de emojis o caracteres especiales
- Logging en lugar de prints
- Configuración por variables de entorno
- Secrets nunca en código

### Known Issues
- Algunos tests asíncronos necesitan decorador `@pytest.mark.asyncio`
- Uso de `.dict()` deprecado en Pydantic v2 (debe ser `.model_dump()`)
- Error menor en manejo de JSON en sistema de caché
- Cobertura de tests en 64% (objetivo: 90%)

### Dependencies
- `requests ^2.31.0`: HTTP requests síncronos
- `pydantic ^2.5.0`: Validación de datos y modelos
- `python-decouple ^3.8`: Gestión de configuración
- `tenacity ^8.2.3`: Reintentos con backoff
- `aiohttp ^3.9.0`: HTTP requests asíncronos
- `asyncio ^3.4.3`: Soporte asíncrono

### Development Dependencies
- `pytest ^7.4.0`: Framework de testing
- `pytest-asyncio ^0.21.0`: Tests asíncronos
- `pytest-cov ^4.1.0`: Cobertura de código
- `black ^23.0.0`: Formateo de código
- `ruff ^0.1.0`: Linter rápido
- `bandit ^1.7.5`: Security scanner
- `mypy ^1.7.0`: Type checker
- `types-requests ^2.31.0`: Type stubs para requests

[0.1.0]: https://github.com/sermodi/game-description-translator/releases/tag/v0.1.0
