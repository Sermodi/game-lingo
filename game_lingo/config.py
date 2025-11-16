"""
Configuración centralizada para Game Description Translator.

Este módulo maneja la configuración de la aplicación, incluyendo claves API.
Busca la configuración en el siguiente orden de prioridad:
1. Variables de entorno
2. Archivo de configuración del usuario (~/.config/game_lingo/config.ini)
"""

from __future__ import annotations

import configparser
import logging
import os
from pathlib import Path

from decouple import config

logger = logging.getLogger(__name__)

# Configuración de rutas
CONFIG_DIR = Path.home() / ".config" / "game_lingo"
CONFIG_FILE = CONFIG_DIR / "config.ini"

# Crear el directorio de configuración si no existe
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def get_config_value(section: str, key: str, default: str = "") -> str:
    """
    Obtiene un valor de configuración, primero de las variables de entorno,
    luego del archivo de configuración, o devuelve el valor por defecto.
    """
    # Primero intentar con las variables de entorno
    env_key = f"{section.upper()}_{key.upper()}"
    value = os.environ.get(env_key)
    if value is not None:
        return value

    # Luego intentar con el archivo de configuración
    config_parser = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config_parser.read(CONFIG_FILE)
        return config_parser.get(section, key, fallback=default)

    return default


def create_default_config() -> configparser.ConfigParser | None:
    """Crea un archivo de configuración por defecto si no existe."""
    if not CONFIG_FILE.exists():
        config_parser = configparser.ConfigParser()

        # Configuración de APIs
        config_parser["API_KEYS"] = {
            "steam": "",
            "rawg": "",
            "deepl": "",
            "google_translate": "",
        }

        # Configuración de la aplicación
        config_parser["APP"] = {
            "version": "1.0.0",
            "cache_enabled": "True",
            "cache_ttl_hours": "24",
            "default_source_language": "en",
            "default_target_language": "es",
        }

        with open(CONFIG_FILE, "w") as configfile:
            config_parser.write(configfile)

        return config_parser
    return None


class Settings:
    """Configuración de la aplicación."""

    def __init__(self) -> None:
        """Inicializa la configuración y valida parámetros críticos."""
        # Crear configuración por defecto si no existe
        create_default_config()

        # Cargar configuración
        self.config_parser = configparser.ConfigParser()
        if CONFIG_FILE.exists():
            self.config_parser.read(CONFIG_FILE)

        # Validar configuración
        self._validate_config()
        self._setup_logging()
        self._ensure_cache_dir()

    # Application Configuration
    VERSION: str = "1.0.0"

    # APIs Configuration
    @property
    def STEAM_API_KEY(self) -> str:
        return get_config_value(
            "API_KEYS",
            "steam",
            config("STEAM_API_KEY", default=""),
        )

    @property
    def RAWG_API_KEY(self) -> str:
        return get_config_value("API_KEYS", "rawg", config("RAWG_API_KEY", default=""))

    @property
    def DEEPL_API_KEY(self) -> str:
        return get_config_value(
            "API_KEYS",
            "deepl",
            config("DEEPL_API_KEY", default=""),
        )

    @property
    def GOOGLE_TRANSLATE_API_KEY(self) -> str:
        return get_config_value(
            "API_KEYS",
            "google_translate",
            config("GOOGLE_TRANSLATE_API_KEY", default=""),
        )

    GOOGLE_TRANSLATE_BASE_URL: str = config(
        "GOOGLE_TRANSLATE_BASE_URL",
        default="https://translation.googleapis.com/language/translate/v2",
    )
    GOOGLE_TRANSLATE_REQUESTS_PER_SECOND: int = config(
        "GOOGLE_TRANSLATE_REQUESTS_PER_SECOND",
        default=10,
        cast=int,
    )

    # API URLs
    STEAM_STORE_API_URL: str = "https://store.steampowered.com/api/appdetails"
    STEAM_APP_LIST_URL: str = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
    STEAM_BASE_URL: str = "https://store.steampowered.com/api"
    STEAM_SEARCH_URL: str = "https://store.steampowered.com/search/suggest"
    RAWG_API_URL: str = "https://api.rawg.io/api"
    RAWG_BASE_URL: str = "https://api.rawg.io/api"
    DEEPL_API_URL: str = "https://api-free.deepl.com/v2/translate"
    DEEPL_IS_PRO: bool = config("DEEPL_IS_PRO", default=False, cast=bool)
    DEEPL_REQUESTS_PER_SECOND: int = config(
        "DEEPL_REQUESTS_PER_SECOND",
        default=5,
        cast=int,
    )
    GOOGLE_TRANSLATE_API_URL: str = (
        "https://translation.googleapis.com/language/translate/v2"
    )

    # Cache Configuration
    @property
    def CACHE_ENABLED(self) -> bool:
        return (
            get_config_value(
                "APP",
                "cache_enabled",
                str(config("CACHE_ENABLED", default=True)),
            ).lower()
            == "true"
        )

    @property
    def CACHE_TTL_HOURS(self) -> int:
        return int(
            get_config_value(
                "APP",
                "cache_ttl_hours",
                str(config("CACHE_TTL_HOURS", default=24)),
            ),
        )

    CACHE_MAX_SIZE: int = config("CACHE_MAX_SIZE", default=1000, cast=int)
    CACHE_DIR: Path = Path(config("CACHE_DIR", default="cache"))

    # Translation Configuration
    @property
    def DEFAULT_SOURCE_LANGUAGE(self) -> str:
        return get_config_value(
            "APP",
            "default_source_language",
            config("DEFAULT_SOURCE_LANGUAGE", default="en"),
        )

    @property
    def DEFAULT_TARGET_LANGUAGE(self) -> str:
        return get_config_value(
            "APP",
            "default_target_language",
            config("DEFAULT_TARGET_LANGUAGE", default="es"),
        )

    TRANSLATION_PROVIDER: str = config("TRANSLATION_PROVIDER", default="deepl")
    FALLBACK_TRANSLATION_PROVIDER: str = config(
        "FALLBACK_TRANSLATION_PROVIDER",
        default="google",
    )

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = config("RATE_LIMIT_ENABLED", default=True, cast=bool)

    # API Rate Limits (requests per time window)
    STEAM_RATE_LIMIT: int = config("STEAM_RATE_LIMIT", default=200, cast=int)
    RAWG_RATE_LIMIT: int = config("RAWG_RATE_LIMIT", default=27, cast=int)
    DEEPL_RATE_LIMIT: int = config("DEEPL_RATE_LIMIT", default=20, cast=int)
    GOOGLE_RATE_LIMIT: int = config("GOOGLE_RATE_LIMIT", default=100, cast=int)

    # Character Limits for Translation APIs
    DEEPL_CHARACTER_LIMIT: int = config("DEEPL_CHARACTER_LIMIT", default=694, cast=int)
    GOOGLE_CHARACTER_LIMIT: int = config(
        "GOOGLE_CHARACTER_LIMIT",
        default=10000,
        cast=int,
    )

    # Timeouts
    API_TIMEOUT_SECONDS: int = config("API_TIMEOUT_SECONDS", default=30, cast=int)
    TRANSLATION_TIMEOUT_SECONDS: int = config(
        "TRANSLATION_TIMEOUT_SECONDS",
        default=60,
        cast=int,
    )

    # Retry Configuration
    MAX_RETRIES: int = config("MAX_RETRIES", default=3, cast=int)
    RETRY_BACKOFF_FACTOR: float = config(
        "RETRY_BACKOFF_FACTOR",
        default=1.5,
        cast=float,
    )

    # Logging Configuration
    LOG_LEVEL: str = config("LOG_LEVEL", default="INFO")
    LOG_FILE: str = config("LOG_FILE", default="game_translator.log")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    # Steam Language Codes
    STEAM_LANGUAGE_CODES: dict[str, str] = {
        "en": "english",
        "es": "spanish",
        "fr": "french",
        "de": "german",
        "it": "italian",
        "pt": "portuguese",
        "ru": "russian",
        "ja": "japanese",
        "ko": "koreana",
        "zh": "schinese",
        "zh-tw": "tchinese",
    }

    # Platform Mappings
    PLATFORM_MAPPINGS: dict[str, list[str]] = {
        "pc": ["pc", "windows", "steam"],
        "playstation": ["ps4", "ps5", "playstation", "playstation 4", "playstation 5"],
        "xbox": ["xbox", "xbox one", "xbox series", "xbox series x", "xbox series s"],
        "nintendo": ["nintendo", "switch", "nintendo switch", "3ds", "nintendo 3ds"],
        "mobile": ["mobile", "android", "ios", "iphone", "ipad"],
    }

    def _validate_config(self) -> None:
        """Valida configuración crítica."""
        if not any(
            [
                self.STEAM_API_KEY,
                self.RAWG_API_KEY,
            ],
        ):
            logger.warning(
                "No API keys configured for game data sources. "
                "Some functionality may be limited.",
            )

        if not any([self.DEEPL_API_KEY, self.GOOGLE_TRANSLATE_API_KEY]):
            logger.warning(
                "No translation API keys configured. "
                "Translation functionality will be disabled.",
            )

    def _setup_logging(self) -> None:
        """Configura el sistema de logging."""
        logging.basicConfig(
            level=getattr(logging, self.LOG_LEVEL.upper()),
            format=self.LOG_FORMAT,
            datefmt=self.LOG_DATE_FORMAT,
            handlers=[
                logging.FileHandler(self.LOG_FILE),
                logging.StreamHandler(),
            ],
        )

    def _ensure_cache_dir(self) -> None:
        """Asegura que el directorio de caché existe."""
        if self.CACHE_ENABLED:
            self.CACHE_DIR.mkdir(exist_ok=True)

    def get_steam_language_code(self, language: str) -> str:
        """Obtiene el código de idioma para Steam API."""
        return self.STEAM_LANGUAGE_CODES.get(language.lower(), "english")

    def is_api_configured(self, api_name: str) -> bool:
        """Verifica si una API está configurada."""
        api_name_lower = api_name.lower()

        # Steam siempre está disponible (no requiere API key)
        if api_name_lower == "steam":
            return True

        api_keys = {
            "rawg": self.RAWG_API_KEY,
            "deepl": self.DEEPL_API_KEY,
            "google": self.GOOGLE_TRANSLATE_API_KEY,
        }
        return bool(api_keys.get(api_name_lower))

    def get_configured_apis(self) -> list[str]:
        """Obtiene lista de APIs configuradas."""
        apis = []
        # Steam siempre está disponible
        apis.append("steam")
        if self.is_api_configured("rawg"):
            apis.append("rawg")
        return apis

    def get_configured_translation_providers(self) -> list[str]:
        """Obtiene lista de proveedores de traducción configurados."""
        providers = []
        if self.is_api_configured("deepl"):
            providers.append("deepl")
        if self.is_api_configured("google"):
            providers.append("google")
        return providers


def configure_api_key(service: str, api_key: str) -> None:
    """
    Configura una clave API para un servicio específico.

    Args:
        service: Nombre del servicio (steam, rawg, deepl, google_translate)
        api_key: Clave API a configurar
    """
    config_parser = configparser.ConfigParser()

    # Cargar configuración existente si existe
    if CONFIG_FILE.exists():
        config_parser.read(CONFIG_FILE)

    # Asegurarse de que la sección existe
    if "API_KEYS" not in config_parser:
        config_parser["API_KEYS"] = {}

    # Actualizar la clave
    config_parser["API_KEYS"][service] = api_key

    # Guardar la configuración
    with open(CONFIG_FILE, "w") as configfile:
        config_parser.write(configfile)


# Instancia global de configuración
settings = Settings()
