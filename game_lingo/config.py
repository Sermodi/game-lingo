"""
Configuración centralizada para Game Description Translator.

Utiliza python-decouple para cargar variables de entorno de forma segura.
"""

from __future__ import annotations

import logging
from pathlib import Path

from decouple import config


class Settings:
    """Configuración de la aplicación."""

    # Application Configuration
    VERSION: str = "1.0.0"

    # APIs Configuration
    STEAM_API_KEY: str = config("STEAM_API_KEY", default="")
    RAWG_API_KEY: str = config("RAWG_API_KEY", default="")
    DEEPL_API_KEY: str = config("DEEPL_API_KEY", default="")
    GOOGLE_TRANSLATE_API_KEY: str = config("GOOGLE_TRANSLATE_API_KEY", default="")
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
    CACHE_ENABLED: bool = config("CACHE_ENABLED", default=True, cast=bool)
    CACHE_TTL_HOURS: int = config("CACHE_TTL_HOURS", default=24, cast=int)
    CACHE_MAX_SIZE: int = config("CACHE_MAX_SIZE", default=1000, cast=int)
    CACHE_DIR: Path = Path(config("CACHE_DIR", default="cache"))

    # Translation Configuration
    DEFAULT_SOURCE_LANGUAGE: str = config("DEFAULT_SOURCE_LANGUAGE", default="en")
    DEFAULT_TARGET_LANGUAGE: str = config("DEFAULT_TARGET_LANGUAGE", default="es")
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

    def __init__(self) -> None:
        """Inicializa la configuración y valida parámetros críticos."""
        self._validate_config()
        self._setup_logging()
        self._ensure_cache_dir()

    def _validate_config(self) -> None:
        """Valida configuración crítica."""
        if not any(
            [
                self.STEAM_API_KEY,
                self.RAWG_API_KEY,
            ],
        ):
            logging.warning(
                "No API keys configured for game data sources. "
                "Some functionality may be limited.",
            )

        if not any([self.DEEPL_API_KEY, self.GOOGLE_TRANSLATE_API_KEY]):
            logging.warning(
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


# Instancia global de configuración
settings = Settings()
