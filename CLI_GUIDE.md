# Guía Rápida del CLI - Game Description Translator

## 🚀 Inicio Rápido

### Instalación

```bash
# Instalar el paquete
pip install game-description-translator

# O en desarrollo
pip install -e .
```

### Primer Uso

```bash
# Buscar un juego
game-translator search "Hollow Knight"
```

## 📋 Comandos Disponibles

### 1. `search` - Buscar Juegos

Busca un juego y obtiene su descripción en español.

```bash
# Uso básico
game-translator search "Celeste"

# Con plataforma específica
game-translator search "Mario Kart" --platform nintendo_switch

# Mostrar descripción completa
game-translator search "Hades" --full

# Con información de depuración
game-translator search "Terraria" --verbose
```

**Opciones:**
- `game_name` (requerido): Nombre del juego a buscar
- `-p, --platform`: Plataforma específica (steam, pc, playstation, xbox, nintendo_switch, mobile)
- `--full`: Mostrar descripción completa en lugar de la corta
- `-v, --verbose`: Mostrar información de depuración

**Ejemplo de salida:**
```
🔍 Buscando 'Hollow Knight'...

======================================================================
🎮 Hollow Knight
======================================================================
Steam ID: 367520
Plataformas: STEAM, PC
Géneros: Action, Adventure, Indie
Año: 2017
Rating: 90/100

Descripción:
Forja tu propio camino en Hollow Knight! Una aventura de acción épica...

----------------------------------------------------------------------
Fuente: native
Confianza: 1.00
Tiempo de procesamiento: 245ms
======================================================================
```

### 2. `translate` - Traducir Texto

Traduce un texto directamente sin buscar un juego.

```bash
# Traducción básica (inglés → español)
game-translator translate "An epic adventure in a vast world"

# Especificar idiomas
game-translator translate "Bonjour le monde" --source fr --target es

# Elegir proveedor de traducción
game-translator translate "Hello world" --provider deepl
```

**Opciones:**
- `text` (requerido): Texto a traducir
- `-s, --source`: Idioma origen (por defecto: en)
- `-t, --target`: Idioma destino (por defecto: es)
- `--provider`: Proveedor (deepl, google, auto)

**Ejemplo de salida:**
```
🔄 Traduciendo de en a es...

======================================================================
📝 Traducción
======================================================================
Una aventura épica en un vasto mundo

----------------------------------------------------------------------
Proveedor: deepl
Confianza: 0.95
======================================================================
```

### 3. `describe` - Buscar con Descripción Proporcionada

Busca un juego proporcionando su nombre Y descripción en inglés. Si el juego tiene descripción nativa en español, la usa; si no, traduce la que proporcionas.

```bash
# Buscar con descripción (usa nativa si existe, sino traduce)
game-translator describe "Celeste" "A challenging platformer about climbing a mountain"

# Con descripción completa
game-translator describe "Indie Game" "An epic adventure in a vast fantasy world" --full
```

**Opciones:**
- `game_name` (requerido): Nombre del juego
- `description` (requerido): Descripción del juego en inglés
- `--full`: Mostrar descripción completa

**Casos de uso:**
- Tienes la descripción en inglés y quieres evitar búsquedas innecesarias
- El juego no está en las bases de datos pero tienes su descripción
- Quieres asegurar una traducción de calidad de una descripción específica

**Ejemplo de salida (con descripción nativa):**
```
🔍 Buscando 'Celeste' con descripción proporcionada...

✅ Encontrada descripción nativa en español
======================================================================
🎮 Celeste
======================================================================
Steam ID: 504230
Descripción: Ayuda a Madeline a sobrevivir a su viaje interior...
```

**Ejemplo de salida (traduciendo proporcionada):**
```
🔍 Buscando 'My Indie Game' con descripción proporcionada...

⚠️  Juego no encontrado en bases de datos, traduciendo descripción proporcionada...

======================================================================
🎮 My Indie Game
======================================================================

Descripción (traducida):
Una aventura épica en un vasto mundo de fantasía

----------------------------------------------------------------------
Proveedor de traducción: deepl
Confianza: 0.95
======================================================================
```

### 4. `info` - Información Detallada

Obtiene información completa de un juego.

```bash
# Información detallada
game-translator info "Stardew Valley"
```

**Opciones:**
- `game_name` (requerido): Nombre del juego

**Salida:** Similar a `search --full` pero con más metadatos.

### 5. `stats` - Estadísticas de Uso y Costos

Muestra estadísticas de uso de las APIs y costos estimados.

```bash
# Ver estadísticas
game-translator stats

# Ver estadísticas y resetear (próximamente)
game-translator stats --reset
```

**Opciones:**
- `--reset`: Resetear estadísticas después de mostrarlas (no implementado aún)

**Información mostrada:**
- Uso actual de cada API (requests y caracteres)
- Límites de rate limiting
- Estadísticas del caché (hit rate, tamaño, entradas)
- Costos estimados de cada API
- Tips para optimizar uso

**Ejemplo de salida:**
```
📊 Estadísticas de Uso
======================================================================

🔄 Rate Limiter - Uso de APIs
----------------------------------------------------------------------

🎮 Steam Store API
   Límite: 200 req/5min
   Costo: Gratuita
   Requests usados: 5

🎯 RAWG API
   Límite: 27 req/hora
   Costo: Gratuita (con key)
   Requests usados: 2

🌐 DeepL API
   Límite: 20 req/min
   Costo: 500k chars/mes gratis
   Requests usados: 3
   Caracteres usados: 1,245


💾 Caché
----------------------------------------------------------------------

   Entradas totales: 10
   Entradas activas: 8
   Entradas expiradas: 2
   Tamaño total: 0.15 MB
   Hit rate: 60.0%
   Hits: 6
   Misses: 4


💰 Resumen de Costos
----------------------------------------------------------------------

   APIs Gratuitas:
   • Steam Store API: ✅ Totalmente gratuita
   • RAWG API: ✅ Gratuita (requiere registro)

   APIs de Traducción:
   • DeepL Free: ✅ 500,000 caracteres/mes gratis
   • DeepL Pro: 💰 Desde €5.49/mes
   • Google Translate: 💰 $20 por 1M de caracteres

   💡 Tip: El caché reduce significativamente el uso de APIs

======================================================================
```

## 🎯 Ejemplos de Uso

### Buscar juegos populares

```bash
game-translator search "The Witcher 3"
game-translator search "Cyberpunk 2077"
game-translator search "Elden Ring"
game-translator search "Baldur's Gate 3"
```

### Buscar por plataforma

```bash
# Juegos de Steam
game-translator search "Portal 2" --platform steam

# Juegos de PlayStation
game-translator search "God of War" --platform playstation

# Juegos de Nintendo Switch
game-translator search "Zelda" --platform nintendo_switch
```

### Traducir descripciones personalizadas

```bash
# Inglés a español
game-translator translate "Explore dungeons and defeat monsters"

# Francés a español
game-translator translate "Explorez un monde fantastique" --source fr

# Alemán a español
game-translator translate "Ein episches Abenteuer" --source de
```

### Modo verbose (depuración)

```bash
# Ver logs detallados
game-translator search "Minecraft" --verbose

# Útil para diagnosticar problemas
game-translator translate "Test" --verbose
```

## 🔧 Desarrollo

### Ejecutar sin instalar

```bash
# Desde el directorio del proyecto
python -m game_translator search "Terraria"

# O directamente
python game_translator/cli.py search "Minecraft"
```

### Probar cambios

```bash
# Instalar en modo editable
pip install -e .

# Ahora los cambios se reflejan inmediatamente
game-translator search "Test"
```

## ⚙️ Configuración

El CLI usa las mismas variables de entorno que la librería:

```bash
# .env
RAWG_API_KEY=tu_key_aqui
DEEPL_API_KEY=tu_key_aqui
GOOGLE_TRANSLATE_API_KEY=tu_key_aqui

# Opcional
CACHE_ENABLED=true
CACHE_TTL_HOURS=168
LOG_LEVEL=INFO
```

## 🆘 Ayuda

### Ver ayuda general

```bash
game-translator --help
```

### Ver ayuda de un comando específico

```bash
game-translator search --help
game-translator translate --help
game-translator info --help
```

### Ver versión

```bash
game-translator --version
```

## 🐛 Solución de Problemas

### Error: "Command not found"

```bash
# Asegúrate de que el paquete está instalado
pip install -e .

# O usa Python directamente
python -m game_translator search "Test"
```

### Error: "API key not found"

```bash
# Configura tus API keys en .env
echo "RAWG_API_KEY=tu_key" >> .env

# O exporta como variable de entorno
export RAWG_API_KEY=tu_key
```

### Error: "Game not found"

```bash
# Intenta con otro nombre o sin plataforma
game-translator search "Nombre alternativo"

# Usa --verbose para ver más detalles
game-translator search "Juego" --verbose
```

### Modo verbose no funciona

```bash
# Asegúrate de usar -v ANTES del comando
game-translator -v search "Test"  # ✓ Correcto
game-translator search "Test" -v  # ✗ Incorrecto
```

## 📚 Recursos

- [README principal](README.md)
- [Documentación de la API](docs/API.md)
- [CHANGELOG](CHANGELOG.md)
- [Ejemplos de código](examples/)

## 💡 Tips

1. **Usa comillas** para nombres con espacios: `"Hollow Knight"`
2. **Modo verbose** es útil para depuración: `-v`
3. **Descripción completa** con `--full` para más detalles
4. **Caché** acelera búsquedas repetidas
5. **Plataforma específica** mejora precisión de búsqueda

## 🎮 Juegos Recomendados para Probar

```bash
# Indie populares
game-translator search "Celeste"
game-translator search "Hollow Knight"
game-translator search "Hades"
game-translator search "Stardew Valley"

# AAA recientes
game-translator search "Elden Ring"
game-translator search "Baldur's Gate 3"
game-translator search "Cyberpunk 2077"

# Clásicos
game-translator search "Portal 2"
game-translator search "The Witcher 3"
game-translator search "Skyrim"
```
