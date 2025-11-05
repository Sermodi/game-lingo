"""
Modelos de datos principales para información de juegos y resultados de traducción.

Utiliza Pydantic para validación de tipos y serialización.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, validator


class Platform(str, Enum):
    """Plataformas de videojuegos soportadas."""

    PC = "pc"
    STEAM = "steam"
    PLAYSTATION_5 = "ps5"
    PLAYSTATION_4 = "ps4"
    XBOX_SERIES = "xbox_series"
    XBOX_ONE = "xbox_one"
    NINTENDO_SWITCH = "nintendo_switch"
    NINTENDO_3DS = "nintendo_3ds"
    MOBILE = "mobile"
    WEB = "web"

    @classmethod
    def from_string(cls, platform_str: str) -> Platform:
        """Convierte string a Platform, con normalización."""
        platform_map = {
            "pc": cls.PC,
            "steam": cls.STEAM,
            "ps5": cls.PLAYSTATION_5,
            "playstation 5": cls.PLAYSTATION_5,
            "playstation5": cls.PLAYSTATION_5,
            "ps4": cls.PLAYSTATION_4,
            "playstation 4": cls.PLAYSTATION_4,
            "playstation4": cls.PLAYSTATION_4,
            "xbox series x": cls.XBOX_SERIES,
            "xbox series s": cls.XBOX_SERIES,
            "xbox series": cls.XBOX_SERIES,
            "xbox one": cls.XBOX_ONE,
            "nintendo switch": cls.NINTENDO_SWITCH,
            "switch": cls.NINTENDO_SWITCH,
            "nintendo 3ds": cls.NINTENDO_3DS,
            "3ds": cls.NINTENDO_3DS,
            "mobile": cls.MOBILE,
            "android": cls.MOBILE,
            "ios": cls.MOBILE,
            "web": cls.WEB,
        }

        normalized = platform_str.lower().strip()
        return platform_map.get(normalized, cls.PC)


class Language(str, Enum):
    """Idiomas soportados para traducción."""

    # Idiomas principales
    SPANISH = "es"
    ENGLISH = "en"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    JAPANESE = "ja"
    KOREAN = "ko"
    CHINESE_SIMPLIFIED = "zh"
    CHINESE_TRADITIONAL = "zh-TW"
    DUTCH = "nl"
    POLISH = "pl"
    SWEDISH = "sv"
    DANISH = "da"
    FINNISH = "fi"
    NORWEGIAN = "no"
    CZECH = "cs"
    TURKISH = "tr"
    GREEK = "el"
    HUNGARIAN = "hu"
    ROMANIAN = "ro"
    BULGARIAN = "bg"
    UKRAINIAN = "uk"
    ARABIC = "ar"
    HINDI = "hi"
    THAI = "th"
    VIETNAMESE = "vi"
    INDONESIAN = "id"

    @classmethod
    def from_string(cls, lang_str: str) -> Language:
        """Convierte string a Language, con normalización."""
        normalized = lang_str.lower().strip()

        # Mapeo de códigos comunes
        lang_map = {
            "es": cls.SPANISH,
            "spa": cls.SPANISH,
            "spanish": cls.SPANISH,
            "español": cls.SPANISH,
            "en": cls.ENGLISH,
            "eng": cls.ENGLISH,
            "english": cls.ENGLISH,
            "fr": cls.FRENCH,
            "fra": cls.FRENCH,
            "french": cls.FRENCH,
            "français": cls.FRENCH,
            "de": cls.GERMAN,
            "deu": cls.GERMAN,
            "german": cls.GERMAN,
            "deutsch": cls.GERMAN,
            "it": cls.ITALIAN,
            "ita": cls.ITALIAN,
            "italian": cls.ITALIAN,
            "italiano": cls.ITALIAN,
            "pt": cls.PORTUGUESE,
            "por": cls.PORTUGUESE,
            "portuguese": cls.PORTUGUESE,
            "português": cls.PORTUGUESE,
            "ru": cls.RUSSIAN,
            "rus": cls.RUSSIAN,
            "russian": cls.RUSSIAN,
            "ja": cls.JAPANESE,
            "jpn": cls.JAPANESE,
            "japanese": cls.JAPANESE,
            "ko": cls.KOREAN,
            "kor": cls.KOREAN,
            "korean": cls.KOREAN,
            "zh": cls.CHINESE_SIMPLIFIED,
            "zho": cls.CHINESE_SIMPLIFIED,
            "chinese": cls.CHINESE_SIMPLIFIED,
            "zh-tw": cls.CHINESE_TRADITIONAL,
            "nl": cls.DUTCH,
            "nld": cls.DUTCH,
            "dutch": cls.DUTCH,
            "pl": cls.POLISH,
            "pol": cls.POLISH,
            "polish": cls.POLISH,
        }

        return lang_map.get(normalized, cls.SPANISH)  # Default to Spanish


class TranslationSource(str, Enum):
    """Fuentes de traducción disponibles."""

    NATIVE = "native"  # Descripción nativa en español
    DEEPL = "deepl"  # Traducido con DeepL
    GOOGLE = "google"  # Traducido con Google Translate
    MANUAL = "manual"  # Traducción manual


class GameInfo(BaseModel):
    """Información completa de un videojuego."""

    # Identificadores
    name: str = Field(..., description="Nombre del juego")
    steam_id: int | None = Field(None, description="Steam App ID")
    rawg_id: int | None = Field(None, description="RAWG Game ID")
    igdb_id: int | None = Field(None, description="IGDB Game ID")

    # Información básica
    platforms: list[Platform] = Field(
        default_factory=list,
        description="Plataformas disponibles",
    )
    release_date: datetime | None = Field(None, description="Fecha de lanzamiento")
    developer: str | None = Field(None, description="Desarrollador")
    publisher: str | None = Field(None, description="Distribuidor")
    genres: list[str] = Field(default_factory=list, description="Géneros del juego")

    # Descripciones
    short_description_en: str | None = Field(
        None,
        description="Descripción corta en inglés",
    )
    # Compat: aceptar `description` en tests y exponer alias
    description: str | None = Field(
        None,
        description="Alias para short_description_en (compat)",
    )
    short_description_es: str | None = Field(
        None,
        description="Descripción corta en español",
    )
    detailed_description_en: str | None = Field(
        None,
        description="Descripción detallada en inglés",
    )
    detailed_description_es: str | None = Field(
        None,
        description="Descripción detallada en español",
    )

    # Descripciones traducidas (almacena traducciones en diferentes idiomas)
    # Formato: {"fr": "description en francés", "de": "description en alemán", ...}
    translated_descriptions: dict[str, str] = Field(
        default_factory=dict,
        description="Descripciones traducidas por idioma (código ISO)",
    )

    # Metadatos
    metacritic_score: int | None = Field(
        None,
        ge=0,
        le=100,
        description="Puntuación Metacritic",
    )
    user_score: float | None = Field(
        None,
        ge=0,
        le=10,
        description="Puntuación de usuarios",
    )
    price: float | None = Field(None, ge=0, description="Precio en USD")
    is_free: bool = Field(False, description="¿Es gratuito?")

    # URLs e imágenes
    store_url: str | None = Field(None, description="URL de la tienda")
    header_image: str | None = Field(None, description="URL imagen de cabecera")
    screenshots: list[str] = Field(default_factory=list, description="URLs de capturas")

    # Metadatos de traducción
    translation_source: TranslationSource | None = Field(
        None,
        description="Fuente de la traducción",
    )
    translation_confidence: float | None = Field(
        None,
        ge=0,
        le=1,
        description="Confianza en la traducción",
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Última actualización",
    )
    # Fuente de los datos brutos (por ejemplo 'rawg', 'steam') - usado en tests
    source_api: str | None = Field(
        None,
        description="Fuente original de datos (rawg, steam, ...)",
    )

    @validator("platforms", pre=True)
    def validate_platforms(cls, v: Any) -> list[Platform]:
        """Valida y convierte plataformas a enum."""
        if isinstance(v, str):
            return [Platform.from_string(v)]
        if isinstance(v, list):
            return [Platform.from_string(p) if isinstance(p, str) else p for p in v]
        return v or []

    @validator("genres", pre=True)
    def validate_genres(cls, v: Any) -> list[str]:
        """Valida géneros."""
        if isinstance(v, str):
            return [v.strip()]
        if isinstance(v, list):
            return [str(g).strip() for g in v if g]
        return v or []

    def has_spanish_description(self) -> bool:
        """Verifica si tiene descripción en español."""
        return bool(self.short_description_es or self.detailed_description_es)

    def has_description(self, lang: Language | str) -> bool:
        """Verifica si tiene descripción en el idioma especificado."""
        if isinstance(lang, str):
            lang = Language.from_string(lang)

        lang_code = lang.value

        # Verificar campos específicos de español
        if lang_code == "es":
            return self.has_spanish_description()

        # Verificar en translated_descriptions
        return lang_code in self.translated_descriptions

    def get_description(self, lang: Language | str) -> str | None:
        """Obtiene la descripción en el idioma especificado."""
        if isinstance(lang, str):
            lang = Language.from_string(lang)

        lang_code = lang.value

        # Casos especiales para español e inglés (campos legacy)
        if lang_code == "es":
            return self.get_best_description_es()
        if lang_code == "en":
            return self.get_best_description_en()

        # Buscar en translated_descriptions
        return self.translated_descriptions.get(lang_code)

    def set_description(self, lang: Language | str, description: str) -> None:
        """Establece la descripción en el idioma especificado."""
        if isinstance(lang, str):
            lang = Language.from_string(lang)

        lang_code = lang.value

        # Casos especiales para español e inglés (campos legacy)
        if lang_code == "es":
            if not self.short_description_es:
                self.short_description_es = description
            else:
                self.detailed_description_es = description
        elif lang_code == "en":
            if not self.short_description_en:
                self.short_description_en = description
            else:
                self.detailed_description_en = description
        else:
            # Guardar en translated_descriptions
            self.translated_descriptions[lang_code] = description

    @validator("short_description_en", pre=True, always=True)
    def _populate_short_description_from_description(cls, v: Any, values: Any) -> Any:
        """Si el campo `description` fue pasado en la creación, usarlo como short_description_en."""
        if v:
            return v
        # values contiene otros campos pasados al constructor; si description existe, usarla
        desc = values.get("description")
        if desc:
            return desc
        return v

    @property
    def description_text(self) -> str | None:
        """Compat: obtener la descripción preferida (español si existe, sino inglés)."""
        return self.get_best_description_es() or self.get_best_description_en()

    def get_best_description_es(self) -> str | None:
        """Obtiene la mejor descripción disponible en español."""
        return self.detailed_description_es or self.short_description_es

    def get_best_description_en(self) -> str | None:
        """Obtiene la mejor descripción disponible en inglés."""
        return self.detailed_description_en or self.short_description_en


class TranslationResult(BaseModel):
    """Resultado de una operación de traducción."""

    # Datos del juego
    game_info: GameInfo = Field(..., description="Información del juego")

    # Resultado de traducción
    success: bool = Field(..., description="¿Traducción exitosa?")
    source: TranslationSource = Field(..., description="Fuente de la traducción")
    confidence: float = Field(..., ge=0, le=1, description="Confianza en la traducción")

    # Metadatos de proceso
    processing_time_ms: int = Field(
        ...,
        ge=0,
        description="Tiempo de procesamiento en ms",
    )
    apis_used: list[str] = Field(default_factory=list, description="APIs utilizadas")
    cache_hit: bool = Field(False, description="¿Resultado desde caché?")

    # Errores y advertencias
    errors: list[str] = Field(default_factory=list, description="Errores encontrados")
    warnings: list[str] = Field(default_factory=list, description="Advertencias")

    # Timestamp
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Momento de la traducción",
    )

    def add_error(self, error: str) -> None:
        """Añade un error al resultado."""
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str) -> None:
        """Añade una advertencia al resultado."""
        self.warnings.append(warning)

    def add_api_used(self, api_name: str) -> None:
        """Registra el uso de una API."""
        if api_name not in self.apis_used:
            self.apis_used.append(api_name)
