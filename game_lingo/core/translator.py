"""
Clase principal GameDescriptionTranslator.

Orquesta el proceso completo de traducción:
1. Steam Store API (español nativo)
2. RAWG API (inglés)
3. DeepL/Google Translate (traducción)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional, TypeVar

from ..apis import deepl_api, google_translate_api
from ..apis.deepl_api import DeepLAPIConnector
from ..apis.google_translate_api import GoogleTranslateAPIConnector
from ..apis.rawg_api import RAWGAPIConnector
from ..apis.steam_api import SteamAPI
from ..config import settings
from ..exceptions import ValidationError
from ..models.game import (
    GameInfo,
    Language,
    Platform,
    TranslationResult,
    TranslationSource,
)
from .cache import Cache
from .rate_limiter import RateLimiter

# Type variables for API connectors
T = TypeVar("T")

# Type aliases for API connectors
DeepLAPIType = (
    deepl_api.DeepLAPIConnector if hasattr(deepl_api, "DeepLAPIConnector") else Any
)
GoogleTranslateAPIType = (
    google_translate_api.GoogleTranslateAPIConnector
    if hasattr(google_translate_api, "GoogleTranslateAPIConnector")
    else Any
)

logger = logging.getLogger(__name__)


class GameDescriptionTranslator:
    """
    Traductor principal de descripciones de videojuegos.

    Implementa estrategia híbrida:
    1. Steam Store API para descripciones nativas en español
    2. RAWG API para datos en inglés de otras plataformas
    3. DeepL/Google Translate para traducción automática
    """

    def __init__(
        self,
        cache_enabled: bool = True,
        rate_limiting_enabled: bool = True,
        preferred_translation_provider: str = "deepl",
    ) -> None:
        """
        Inicializa el traductor.

        Args:
            cache_enabled: Habilitar sistema de caché
            rate_limiting_enabled: Habilitar rate limiting
            preferred_translation_provider: Proveedor preferido ("deepl" o "google")
        """
        self.cache = Cache() if cache_enabled else None
        self.rate_limiter = RateLimiter() if rate_limiting_enabled else None
        self.preferred_translation_provider = preferred_translation_provider

        # Initialize API clients
        self.steam_api: Optional[SteamAPI] = SteamAPI(rate_limiter=self.rate_limiter)
        self.rawg_api: Optional[RAWGAPIConnector] = None
        self.deepl_api: Optional[DeepLAPIConnector] = None
        self.google_api: Optional[GoogleTranslateAPIConnector] = None

        # Inicializar APIs
        self._init_apis()

        logger.info("GameDescriptionTranslator initialized")
        logger.info(f"Configured APIs: {settings.get_configured_apis()}")
        logger.info(
            f"Translation providers: {settings.get_configured_translation_providers()}",
        )

    def _init_apis(self) -> None:
        """Inicializa las APIs disponibles."""
        # Steam API siempre disponible (no requiere API key)
        self.steam_api = SteamAPI(rate_limiter=self.rate_limiter)

        # RAWG API requiere API key
        if settings.is_api_configured("rawg"):
            self.rawg_api = RAWGAPIConnector(rate_limiter=self.rate_limiter)

        # APIs de traducción requieren API keys
        if settings.is_api_configured("deepl"):
            self.deepl_api = DeepLAPIConnector(
                api_key=settings.DEEPL_API_KEY,
                rate_limiter=self.rate_limiter,
            )

        if settings.is_api_configured("google"):
            self.google_api = GoogleTranslateAPIConnector(
                api_key=settings.GOOGLE_TRANSLATE_API_KEY,
                rate_limiter=self.rate_limiter,
            )

    async def translate_game_description(
        self,
        game_identifier: str | None = None,
        english_description: str | None = None,
        platform: Platform | str | None = None,
        target_lang: Language | str = Language.SPANISH,
        force_refresh: bool = False,
    ) -> TranslationResult:
        # Initialize with required fields
        result = TranslationResult(
            game_info=GameInfo(name=game_identifier or "Unknown Game"),
            success=False,
            source=TranslationSource.NATIVE,  # Will be updated later if needed
            confidence=0.0,
            processing_time_ms=0,
        )
        cache_key = (
            f"{game_identifier or 'direct'}:{target_lang}"
            if game_identifier
            else f"direct_translation:{target_lang}"
        )
        """
        Traduce la descripción de un videojuego.

        Args:
            game_identifier: Nombre del juego, Steam ID, o identificador (opcional si se proporciona descripción)
            english_description: Descripción en inglés (opcional, si se proporciona se usa directamente)
            platform: Plataforma específica (opcional)
            target_lang: Idioma destino para la traducción (default: Spanish)
            force_refresh: Forzar actualización ignorando caché

        Returns:
            TranslationResult con información del juego y traducción

        Raises:
            GameNotFoundError: Si no se encuentra el juego
            ValidationError: Si los parámetros son inválidos
            GameTranslatorError: Para otros errores del sistema
        """
        start_time = time.time()

        # Validar entrada - debe haber al menos nombre o descripción
        if not game_identifier and not english_description:
            raise ValidationError(
                "Must provide either game_identifier or english_description",
            )

        if not game_identifier:
            game_identifier = "Unknown Game"

        if isinstance(platform, str):
            platform = Platform.from_string(platform)
        try:
            # Verificar si tenemos una descripción en inglés proporcionada
            if english_description:
                result.game_info = GameInfo(
                    name=game_identifier or "Unknown Game",
                    short_description_en=english_description,
                    translation_source=TranslationSource.MANUAL,
                )
                result.success = True
                result.source = TranslationSource.MANUAL
            else:
                if not game_identifier:
                    raise ValidationError(
                        "game_identifier is required when english_description is not provided",
                    )

                # Buscar en caché primero
                if self.cache and not force_refresh:
                    cached_result = await self.cache.get(cache_key)
                    if cached_result:
                        logger.info(f"Cache hit for {cache_key}")
                        return cached_result

                # Obtener información del juego de las APIs
                game_info = await self._get_game_info_from_apis(
                    game_identifier,
                    platform,
                )
                if game_info:
                    result.game_info = game_info
                    if hasattr(game_info, "translation_source"):
                        result.source = (
                            game_info.translation_source or TranslationSource.NATIVE
                        )
                    result.success = True
                else:
                    result.add_error(
                        f"No se pudo encontrar información para {game_identifier}",
                    )
                    return result

            # Traducir si es necesario
            target_lang_str = (
                target_lang.value if hasattr(target_lang, "value") else str(target_lang)
            )
            if target_lang_str.lower() != "en" or (
                not getattr(result.game_info, "short_description_es", None)
                and not getattr(result.game_info, "detailed_description_es", None)
            ):
                translated_info = await self._translate_game_info(
                    result.game_info,
                    target_lang_str,
                )
                if translated_info:
                    result.game_info = translated_info
                    # Update source to indicate translation occurred
                    result.source = (
                        TranslationSource.GOOGLE
                        if self.preferred_translation_provider == "google"
                        else TranslationSource.DEEPL
                    )

            # Actualizar caché
            if self.cache and result.success and not force_refresh:
                await self.cache.set_value(cache_key, result)

        except Exception as e:
            logger.exception("Error en translate_game_description")
            result.add_error(str(e))
        finally:
            result.processing_time_ms = int((time.time() - start_time) * 1000)

        return result

    async def translate_description(
        self,
        english_description: str,
        game_name: str | None = None,
        target_lang: Language | str = Language.SPANISH,
    ) -> TranslationResult:
        """
        Traduce una descripción en inglés directamente, sin buscar el juego.

        Args:
            english_description: Descripción en inglés a traducir
            game_name: Nombre del juego (opcional, para referencia)
            target_lang: Idioma destino para la traducción (default: Spanish)

        Returns:
            TranslationResult con la traducción

        Raises:
            ValidationError: Si la descripción está vacía
        """
        return await self.translate_game_description(
            game_identifier=game_name,
            english_description=english_description,
            target_lang=target_lang,
        )

    async def _search_game_hybrid(
        self,
        game_identifier: str,
        platform: Optional[Platform],
        result: TranslationResult,
    ) -> Optional[GameInfo]:
        """
        Búsqueda híbrida usando múltiples APIs.

        Estrategia:
        1. Steam API (si es Steam o PC)
        2. RAWG API (para múltiples plataformas)
        """
        game_info: Optional[GameInfo] = None

        # 1. Intentar Steam API primero (mejor calidad para PC/Steam)
        if self._should_try_steam(platform) and self.steam_api:
            try:
                game_info = await self._get_steam_description(game_identifier)
                if game_info and (
                    game_info.short_description_es or game_info.detailed_description_es
                ):
                    logger.info(
                        f"Found Spanish description in Steam for: {game_identifier}",
                    )
                    return game_info
            except Exception as e:
                if hasattr(result, "add_warning"):
                    result.add_warning(f"Steam API error: {e}")
                logger.warning(f"Steam API failed for {game_identifier}: {e}")

        # 2. Intentar RAWG API (buena cobertura multi-plataforma)
        if self.rawg_api:
            try:
                rawg_info = await self._get_rawg_description(game_identifier)
                if rawg_info:
                    game_info = (
                        rawg_info  # Simple assignment since we don't have merge logic
                    )
                    logger.info(f"Found game info in RAWG for: {game_identifier}")
            except Exception as e:
                if hasattr(result, "add_warning"):
                    result.add_warning(f"RAWG API error: {e}")
                logger.warning(f"RAWG API failed for {game_identifier}: {e}")

        return game_info

    async def _get_game_info_from_apis(
        self,
        game_identifier: str,
        platform: Optional[Platform] = None,
    ) -> Optional[GameInfo]:
        """Obtiene la información del juego de las APIs disponibles."""
        # Create a minimal result for search_game_hybrid
        result = TranslationResult(
            game_info=GameInfo(name=game_identifier or "Unknown Game"),
            success=False,
            source=TranslationSource.NATIVE,
            confidence=0.0,
            processing_time_ms=0,
        )
        game_info = await self._search_game_hybrid(game_identifier, platform, result)
        return game_info if game_info else None

    async def _translate_game_info(
        self,
        game_info: GameInfo,
        target_lang: str = "es",
    ) -> Optional[GameInfo]:
        """Traduce la información del juego al idioma objetivo."""
        if not game_info:
            return None

        # Si ya está en el idioma objetivo, devolver sin cambios
        if target_lang.lower() == "es" and game_info.short_description_es:
            return game_info

        # Traducir la descripción corta si está en inglés
        if game_info.short_description_en:
            translation = await self._get_translation(
                game_info.short_description_en,
                target_lang,
                "en",
            )
            if translation and "text" in translation:
                game_info.short_description_es = translation["text"]

        # Traducir la descripción detallada si está en inglés
        if game_info.detailed_description_en:
            translation = await self._get_translation(
                game_info.detailed_description_en,
                target_lang,
                "en",
            )
            if translation and "text" in translation:
                game_info.detailed_description_es = translation["text"]

        return game_info

    async def _get_translation(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "en",
    ) -> Optional[dict]:
        """
        Obtiene la traducción del texto usando el proveedor preferido o fallback.

        Returns:
            dict: Dictionary with 'text' and optionally 'detected_source_language'
        """
        if not text.strip():
            return None

        # Intentar con el proveedor preferido primero
        if self.preferred_translation_provider == "deepl" and self.deepl_api:
            result = await self._translate_with_deepl(text, target_lang, source_lang)
            if result:
                return result

        # Si falla o no está disponible, intentar con Google
        if self.google_api:
            result = await self._translate_with_google(text, target_lang, source_lang)
            if result:
                return result

        # Si no hay proveedores disponibles o fallan
        return None

    async def _translate_with_google(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "en",
    ) -> Optional[dict]:
        """Traduce texto usando Google."""
        if not self.google_api or not settings.GOOGLE_TRANSLATE_API_KEY:
            return None

        try:
            # Asegurarse de que self.google_api es del tipo correcto
            google = self.google_api
            result = google.translate_text(
                text=text,
                target_language=target_lang,
                source_language=source_lang,
            )
            if result and hasattr(result, "text"):
                return {
                    "text": result.text,
                    "detected_source_language": getattr(
                        result,
                        "detected_source_language",
                        None,
                    ),
                }
            return None
        except Exception as e:
            logger.warning(f"Error en traducción Google: {e}")
            return None

    async def _translate_with_deepl(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "EN",
    ) -> Optional[dict]:
        """Traduce texto usando DeepL."""
        if not self.deepl_api or not settings.DEEPL_API_KEY:
            return None

        try:
            # Asegurarse de que self.deepl_api es del tipo correcto
            deepl = self.deepl_api
            result = deepl.translate_text(
                text=text,
                target_language=target_lang.upper(),
                source_language=source_lang.upper(),
            )
            if result and hasattr(result, "text"):
                return {
                    "text": result.text,
                    "detected_source_language": getattr(
                        result,
                        "detected_source_language",
                        None,
                    ),
                }
            return None
        except Exception as e:
            logger.warning(f"Error en traducción DeepL: {e}")
            return None

    def _should_try_steam(self, platform: Optional[Platform]) -> bool:
        """Determina si debe intentar Steam API basado en la plataforma."""
        if not platform:
            return True  # Intentar Steam por defecto

        steam_platforms = {Platform.PC, Platform.STEAM}
        return platform in steam_platforms

    async def _get_steam_description(
        self,
        game_identifier: str,
        language: str = "spanish",
    ) -> Optional[GameInfo]:
        """Obtiene la descripción de un juego desde Steam."""
        if not self.steam_api:
            return None

        try:
            # Buscar el juego en Steam
            game_info = await self.steam_api.find_game_by_name(
                game_identifier,
                language=language,
            )

            # Si se encontró y tiene descripción en español, devolver
            if game_info and (
                game_info.short_description_es or game_info.detailed_description_es
            ):
                game_info.source_api = "steam"
                return game_info

        except Exception as e:
            logger.warning(f"Error al buscar en Steam: {e}")

        return None

    async def _get_rawg_description(
        self,
        game_identifier: str,
    ) -> Optional[GameInfo]:
        """Obtiene la descripción de un juego desde RAWG."""
        if not self.rawg_api:
            return None

        try:
            # Buscar el juego en RAWG
            game_info = await self.rawg_api.find_game_by_name(
                game_identifier,
                exact_match=False,
            )

            # Si se encontró, devolver
            if game_info:
                game_info.source_api = "rawg"
                return game_info

        except Exception as e:
            logger.warning(f"Error al buscar en RAWG: {e}")

        return None
