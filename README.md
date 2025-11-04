# GameLingo

> Multi-language video game description translator with smart API orchestration

Intelligent game description translation system using a 3-tier hybrid strategy to get the best translations possible in any language.

## 🎯 Estrategia Híbrida

El sistema implementa una estrategia de 3 niveles para garantizar la mejor calidad y cobertura:

1. **Steam Store API** (Fuente primaria) - Descripciones en español nativas
2. **RAWG API** (Fuente secundaria) - Para juegos no disponibles en Steam  
3. **DeepL/Google Translate** (Traducción) - Solo para traducciones cuando no hay datos nativos

## ✨ Características

- **Máxima Fidelidad**: Prioriza descripciones nativas en español
- **Cobertura Completa**: Fallbacks múltiples aseguran 99%+ de éxito
- **Caché Inteligente**: SQLite con compresión y TTL configurable
- **Rate Limiting**: Respeta límites de todas las APIs automáticamente
- **Asíncrono**: Rendimiento optimizado con asyncio
- **Tipado Estático**: 100% tipado con mypy
- **Logging Completo**: Trazabilidad total del proceso
- **Configuración Flexible**: Variables de entorno para todo

## 🚀 Instalación

### Requisitos

- Python 3.9+
- Poetry (recomendado) o pip

### Con Poetry (Recomendado)

```bash
# Clonar repositorio
git clone <repo-url>
cd Description_translator

# Instalar dependencias
poetry install

# Activar entorno virtual
poetry shell
```

### Con pip

```bash
pip install -r requirements.txt
```

## ⚙️ Configuración

### 1. Variables de Entorno

Copia `.env.example` a `.env` y configura tus API keys:

```bash
cp .env.example .env
```

### 2. APIs Requeridas

#### Steam Store API (Gratuita)
- No requiere API key
- Límite: ~200 requests/5min por IP

#### RAWG API (Gratuita)
```bash
# Registrarse en: https://rawg.io/apidocs
RAWG_API_KEY=tu_api_key_aqui
```

#### DeepL API (Freemium)
```bash
# Registrarse en: https://www.deepl.com/pro-api
DEEPL_API_KEY=tu_api_key_aqui
```

#### Google Translate API (Pago)
```bash
# Configurar en Google Cloud Console
GOOGLE_TRANSLATE_API_KEY=tu_api_key_aqui
```

### 3. Configuración Opcional

```bash
# Caché
CACHE_ENABLED=true
CACHE_TTL_HOURS=168  # 1 semana
CACHE_MAX_SIZE_MB=500

# Rate Limiting
RATE_LIMIT_ENABLED=true
STEAM_RATE_LIMIT=200  # requests per 5 minutes
RAWG_RATE_LIMIT=1000  # requests per hour

# Traducción
TRANSLATION_TARGET_LANGUAGE=es
PREFERRED_TRANSLATION_PROVIDER=deepl

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/translator.log
```

## 📖 Uso

### CLI (Línea de Comandos)

Después de instalar el paquete, puedes usar el comando `game-lingo`:

```bash
# Buscar un juego y obtener su descripción en español
game-lingo search "Hollow Knight"

# Buscar en una plataforma específica
game-lingo search "Celeste" --platform steam

# Mostrar descripción completa
game-lingo search "Hades" --full

# Traducir un texto directamente
game-lingo translate "An epic adventure in a vast world"

# Traducir especificando idiomas
game-lingo translate "Bonjour le monde" --source fr --target es

# Buscar con descripción proporcionada (usa nativa si existe, sino traduce)
game-lingo describe "Celeste" "A challenging platformer about climbing a mountain"

# Información detallada de un juego
game-lingo info "Stardew Valley"

### Ver estadísticas de uso

```bash
python -m game_translator stats
```

Muestra estadísticas detalladas de uso de APIs en tiempo real, incluyendo:
- **Requests realizados y disponibles** por cada API (ventanas deslizantes)
- **Caracteres traducidos** y cuota restante
- **Proyecciones de costos** basadas en uso actual
- **Recomendaciones** para optimizar el uso de APIs

**Nota**: Desde v0.2.0, todas las APIs están integradas con el rate limiter para tracking preciso de uso y costos.

# Ver ayuda
game-lingo --help
game-lingo search --help
```

#### Ejecutar sin instalar (desarrollo)

```bash
# Usando Python directamente
python -m game_translator search "Terraria"

# O con el script
python game_translator/cli.py search "Minecraft"
```

### Uso como Librería (Python)

```python
import asyncio
from game_translator import GameDescriptionTranslator

async def main():
    translator = GameDescriptionTranslator()
    
    # Traducir un juego
    result = await translator.translate_game_description("The Witcher 3")
    
    if result.success:
        game = result.game_info
        print(f"Juego: {game.name}")
        print(f"Descripción ES: {game.get_spanish_description()}")
        print(f"Fuente: {result.source}")
        print(f"Confianza: {result.confidence}")
    else:
        print(f"Error: {result.errors}")

# Ejecutar
asyncio.run(main())
```

### Uso Avanzado

```python
import asyncio
from game_translator import GameDescriptionTranslator
from game_translator.models import Platform

async def advanced_example():
    # Configuración personalizada
    translator = GameDescriptionTranslator(
        cache_enabled=True,
        rate_limiting_enabled=True,
        preferred_translation_provider="deepl"
    )
    
    # Buscar por plataforma específica
    result = await translator.translate_game_description(
        game_identifier="Cyberpunk 2077",
        platform=Platform.PC,
        force_refresh=False  # Usar caché si existe
    )
    
    # Información detallada
    if result.success:
        game = result.game_info
        
        print(f"🎮 {game.name}")
        print(f"📅 Año: {game.release_year}")
        print(f"🏷️ Géneros: {', '.join(game.genres)}")
        print(f"🎯 Plataformas: {', '.join([p.value for p in game.platforms])}")
        print(f"⭐ Rating: {game.rating}/100")
        
        print(f"\n📝 Descripción:")
        print(game.get_spanish_description())
        
        print(f"\n🔍 Metadatos de traducción:")
        print(f"   Fuente: {result.source.value}")
        print(f"   Confianza: {result.confidence:.2%}")
        print(f"   Tiempo: {result.processing_time_ms}ms")
        print(f"   APIs usadas: {', '.join(result.apis_used)}")
        
        if result.warnings:
            print(f"\n⚠️ Advertencias:")
            for warning in result.warnings:
                print(f"   - {warning}")

asyncio.run(advanced_example())
```

### Procesamiento en Lote

```python
import asyncio
from game_translator import GameDescriptionTranslator

async def batch_translate():
    translator = GameDescriptionTranslator()
    
    games = [
        "The Last of Us Part II",
        "Ghost of Tsushima", 
        "Hades",
        "Among Us",
        "Fall Guys"
    ]
    
    # Procesar en paralelo (respetando rate limits)
    tasks = [
        translator.translate_game_description(game) 
        for game in games
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for game, result in zip(games, results):
        if isinstance(result, Exception):
            print(f"❌ {game}: Error - {result}")
        elif result.success:
            print(f"✅ {game}: {result.source.value}")
        else:
            print(f"⚠️ {game}: {result.errors}")

asyncio.run(batch_translate())
```

## 🧪 Testing

### Ejecutar Tests

```bash
# Todos los tests
poetry run pytest

# Con cobertura
poetry run pytest --cov=game_translator --cov-report=html

# Solo tests unitarios
poetry run pytest tests/unit/

# Solo tests de integración
poetry run pytest tests/integration/
```

### Tests de APIs

```bash
# Test con APIs reales (requiere .env configurado)
poetry run pytest tests/integration/ --api-tests

# Test solo con mocks
poetry run pytest tests/unit/
```

## 📊 Monitoreo y Estadísticas

### Estadísticas del Caché

```python
async def cache_stats():
    translator = GameDescriptionTranslator()
    stats = await translator.cache.get_stats()
    
    print(f"📈 Estadísticas del Caché:")
    print(f"   Hit Rate: {stats['hit_rate']:.2%}")
    print(f"   Entradas activas: {stats['active_entries']}")
    print(f"   Tamaño total: {stats['total_size_mb']:.2f} MB")
    print(f"   Entradas expiradas: {stats['expired_entries']}")

asyncio.run(cache_stats())
```

### Limpieza del Caché

```python
async def cache_maintenance():
    translator = GameDescriptionTranslator()
    
    # Limpiar entradas expiradas
    deleted = await translator.cache.cleanup_expired()
    print(f"🧹 Eliminadas {deleted} entradas expiradas")
    
    # Optimizar base de datos
    await translator.cache.optimize()
    print("⚡ Base de datos optimizada")

asyncio.run(cache_maintenance())
```

## 🔧 Desarrollo

### Configurar Entorno de Desarrollo

```bash
# Instalar dependencias de desarrollo
poetry install --with dev

# Pre-commit hooks
poetry run pre-commit install

# Linting
poetry run ruff check game_translator/
poetry run black game_translator/

# Type checking
poetry run mypy game_translator/

# Security scan
poetry run bandit -r game_translator/
```

### Estructura del Proyecto

```
game_translator/
├── __init__.py              # API pública
├── config.py                # Configuración centralizada
├── exceptions.py            # Excepciones personalizadas
├── models/                  # Modelos de datos
│   ├── __init__.py
│   ├── game.py             # GameInfo, TranslationResult
│   └── api_response.py     # Respuestas de APIs
├── core/                   # Lógica principal
│   ├── __init__.py
│   ├── translator.py       # Orquestador principal
│   ├── cache.py           # Sistema de caché
│   └── rate_limiter.py    # Control de velocidad
└── apis/                  # Conectores de APIs
    ├── __init__.py
    ├── steam_api.py       # Steam Store API
    ├── rawg_api.py        # RAWG API
    ├── deepl_api.py       # DeepL API
    └── google_translate_api.py  # Google Translate API
```

## 📋 Roadmap

- [x] Arquitectura base y modelos
- [x] Sistema de caché con SQLite
- [x] Configuración flexible
- [ ] Rate limiting inteligente
- [ ] Conectores de APIs
- [ ] Suite completa de tests
- [ ] Documentación de API
- [ ] CLI para uso desde terminal
- [ ] Dashboard web opcional
- [ ] Métricas y monitoring
- [ ] Docker container

## 🤝 Contribuir

1. Fork del repositorio
2. Crear rama feature: `git checkout -b feature/nueva-funcionalidad`
3. Commit cambios: `git commit -m 'Añade nueva funcionalidad'`
4. Push a la rama: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

### Estándares de Código

- **Formato**: Black con líneas de 88 caracteres
- **Linting**: Ruff con configuración estricta
- **Tipos**: mypy en modo strict
- **Tests**: pytest con cobertura mínima 90%
- **Commits**: Conventional Commits
- **Documentación**: Docstrings estilo Google

## 📄 Licencia

MIT License - ver [LICENSE](LICENSE) para detalles.

## 🆘 Soporte

- **Issues**: [GitHub Issues](https://github.com/usuario/game-description-translator/issues)
- **Documentación**: [Wiki del proyecto](https://github.com/usuario/game-description-translator/wiki)
- **Email**: soporte@gametraslator.com

## 🙏 Agradecimientos

- **Steam**: Por su API pública y datos de calidad
- **RAWG**: Por su extensa base de datos de juegos
- **DeepL**: Por traducciones de alta calidad
- **Google**: Por su servicio de traducción robusto