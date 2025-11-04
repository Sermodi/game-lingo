"""
Clase principal GameDescriptionTranslator.

Orquesta el proceso completo de traducción:
1. Steam Store API (español nativo)
2. RAWG API (inglés)
3. DeepL/Google Translate (traducción)
"""

from __future__ import annotations

import asyncio
import logging
import time

from ..apis import DeepLAPI, GoogleTranslateAPI, SteamAPI
from ..apis.rawg_api import RAWGAPIConnector
from ..config import settings
from ..exceptions import GameNotFoundError, ValidationError
from ..models.game import GameInfo, Language, Platform, TranslationResult, TranslationSource
from .cache import Cache
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class GameDescriptionTranslator:
    """
    Traductor principal de descripciones de videojuegos.

    Implementa estrategia híbrida:
    1. Steam Store API para descripciones nativas en español
    2. RAWG API para datos en inglés de otras plataformas
    3. DeepL/Google Translate para traducción automática

    Características:
    - Caché inteligente para optimizar rendimiento
    - Rate limiting para respetar límites de APIs
    - Manejo robusto de errores con fallbacks
    - Soporte asíncrono para mejor rendimiento
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
        self.steam_api = SteamAPI(rate_limiter=self.rate_limiter) if SteamAPI else None
        # RAWG API requiere API key - usar RAWGAPIConnector directamente
        self.rawg_api = (
            RAWGAPIConnector(rate_limiter=self.rate_limiter)
            if (RAWGAPIConnector and settings.is_api_configured("rawg"))
            else None
        )
        # APIs de traducción requieren API keys
        self.deepl_api = (
            DeepLAPI(api_key=settings.DEEPL_API_KEY, rate_limiter=self.rate_limiter)
            if (DeepLAPI and settings.is_api_configured("deepl"))
            else None
        )
        self.google_api = (
            GoogleTranslateAPI(
                api_key=settings.GOOGLE_TRANSLATE_API_KEY,
                rate_limiter=self.rate_limiter,
            )
            if (GoogleTranslateAPI and settings.is_api_configured("google"))
            else None
        )

    async def translate_game_description(
        self,
        game_identifier: str | None = None,
        english_description: str | None = None,
        platform: Platform | str | None = None,
        target_lang: Language | str = Language.SPANISH,
        force_refresh: bool = False,
    ) -> TranslationResult:
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
        
        # Normalizar idioma destino
        if isinstance(target_lang, str):
            target_lang = Language.from_string(target_lang)

        # Crear resultado inicial
        result = TranslationResult(
            game_info=GameInfo(name=game_identifier),
            success=False,
            source=TranslationSource.NATIVE,
            confidence=0.0,
            processing_time_ms=0,
        )

        try:
            # Si se proporciona descripción en inglés, usarla directamente
            if english_description:
                game_info = GameInfo(
                    name=game_identifier,
                    short_description_en=english_description,
                )
                # Procesar traducción directamente
                await self._process_translation(game_info, result, target_lang)
                result.game_info = game_info
                result.success = True
                result.processing_time_ms = int((time.time() - start_time) * 1000)
                logger.info(
                    f"Successfully translated description for: {game_identifier}",
                )
                return result

            # Verificar caché solo si no hay descripción directa
            if not force_refresh and self.cache:
                cached_result = await self._check_cache(game_identifier, platform)
                if cached_result:
                    cached_result.cache_hit = True
                    return cached_result

            # Estrategia de búsqueda híbrida
            game_info = await self._search_game_hybrid(
                game_identifier, platform, result,
            )

            if not game_info:
                raise GameNotFoundError(
                    game_identifier, str(platform) if platform else None,
                )

            # Procesar traducción si es necesario
            await self._process_translation(game_info, result, target_lang)

            # Actualizar resultado
            result.game_info = game_info
            result.success = True
            result.processing_time_ms = int((time.time() - start_time) * 1000)

            # Guardar en caché
            if self.cache:
                await self._save_to_cache(game_identifier, platform, result)

            logger.info(f"Successfully translated game: {game_info.name}")
            return result

        except Exception as e:
            result.add_error(str(e))
            result.processing_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Error translating game {game_identifier}: {e}")
            raise

    async def translate_description(
        self,
        english_description: str,
        game_name: str | None = None,
    ) -> TranslationResult:
        """
        Traduce una descripción en inglés directamente, sin buscar el juego.

        Args:
            english_description: Descripción en inglés a traducir
            game_name: Nombre del juego (opcional, para referencia)

        Returns:
            TranslationResult con la traducción

        Raises:
            ValidationError: Si la descripción está vacía
        """
        return await self.translate_game_description(
            game_identifier=game_name or "Unknown Game",
            english_description=english_description,
            force_refresh=True,
        )

    async def _search_game_hybrid(
        self,
        game_identifier: str,
        platform: Platform | None,
        result: TranslationResult,
    ) -> GameInfo | None:
        """
        Búsqueda híbrida usando múltiples APIs.

        Estrategia:
        1. Steam API (si es Steam o PC)
        2. RAWG API (para múltiples plataformas)
        """
        game_info = None

        # 1. Intentar Steam API primero (mejor calidad para PC/Steam)
        if self._should_try_steam(platform) and self.steam_api:
            try:
                game_info = await self._search_steam(game_identifier, result)
                if game_info and game_info.has_spanish_description():
                    logger.info(
                        f"Found Spanish description in Steam for: {game_identifier}",
                    )
                    return game_info
            except Exception as e:
                result.add_warning(f"Steam API error: {e}")
                logger.warning(f"Steam API failed for {game_identifier}: {e}")

        # 2. Intentar RAWG API (buena cobertura multi-plataforma)
        if self.rawg_api:
            try:
                rawg_info = await self._search_rawg(game_identifier, platform, result)
                if rawg_info:
                    game_info = self._merge_game_info(game_info, rawg_info)
                    logger.info(f"Found game info in RAWG for: {game_identifier}")
            except Exception as e:
                result.add_warning(f"RAWG API error: {e}")
                logger.warning(f"RAWG API failed for {game_identifier}: {e}")

        return game_info

    async def _process_translation(
        self, game_info: GameInfo, result: TranslationResult, target_lang: Language,
    ) -> None:
        """Procesa la traducción si es necesaria."""
        # Verificar si ya tiene descripción en el idioma destino
        if game_info.has_description(target_lang):
            # Ya tiene descripción nativa en el idioma destino
            result.source = TranslationSource.NATIVE
            result.confidence = 1.0
            return

        # Necesita traducción desde inglés
        english_description = game_info.get_best_description_en()
        if not english_description:
            result.add_warning("No English description available for translation")
            return

        # Intentar traducción al idioma destino
        translated_text, provider, confidence = await self._translate_text(
            english_description,
            target_lang,
            result,
        )

        if translated_text:
            # Guardar traducción usando el método helper
            game_info.set_description(target_lang, translated_text)

            game_info.translation_source = TranslationSource(provider)
            game_info.translation_confidence = confidence

            result.source = TranslationSource(provider)
            result.confidence = confidence

            logger.info(
                f"Translated description to {target_lang.value} using {provider} (confidence: {confidence})",
            )

    async def _translate_text(
        self,
        text: str,
        target_lang: Language,
        result: TranslationResult,
    ) -> tuple[str | None, str, float]:
        """
        Traduce texto usando el proveedor preferido con fallback.

        Las APIs de traducción son síncronas, así que las ejecutamos en un thread.

        Args:
            text: Texto a traducir (siempre en inglés)
            target_lang: Idioma destino
            result: Objeto resultado para tracking

        Returns:
            Tuple de (texto_traducido, proveedor_usado, confianza)
        """
        providers = self._get_translation_providers()
        target_code = target_lang.value

        for provider_name in providers:
            try:
                if provider_name == "deepl" and self.deepl_api:
                    # DeepL usa códigos en mayúsculas (ES, FR, DE, etc.)
                    deepl_target = target_code.upper()
                    # DeepL API es síncrona, ejecutar en thread
                    translation_result = await asyncio.to_thread(
                        self.deepl_api.translate_text,
                        text=text,
                        target_language=deepl_target,
                        source_language="EN",
                    )
                    result.add_api_used("deepl")
                    confidence = 0.9  # DeepL tiene alta confianza
                    return translation_result.text, "deepl", confidence

                if provider_name == "google" and self.google_api:
                    # Google usa códigos en minúsculas (es, fr, de, etc.)
                    # Google Translate API es síncrona, ejecutar en thread
                    translation_result = await asyncio.to_thread(
                        self.google_api.translate_text,
                        text=text,
                        target_language=target_code,
                        source_language="en",
                    )
                    result.add_api_used("google")
                    confidence = 0.8  # Google Translate confianza estándar
                    return translation_result.text, "google", confidence

            except Exception as e:
                result.add_warning(f"{provider_name} translation failed: {e}")
                logger.warning(f"{provider_name} translation failed: {e}")
                continue

        return None, "", 0.0

    def _get_translation_providers(self) -> list[str]:
        """Obtiene lista ordenada de proveedores de traducción."""
        providers = []

        # Proveedor preferido primero
        if self.preferred_translation_provider in ["deepl", "google"]:
            providers.append(self.preferred_translation_provider)

        # Fallback
        fallback = (
            "google" if self.preferred_translation_provider == "deepl" else "deepl"
        )
        if fallback not in providers:
            providers.append(fallback)

        # Filtrar solo los configurados
        configured = settings.get_configured_translation_providers()
        return [p for p in providers if p in configured]

    def _should_try_steam(self, platform: Platform | None) -> bool:
        """Determina si debe intentar Steam API basado en la plataforma."""
        if not platform:
            return True  # Intentar Steam por defecto

        steam_platforms = {Platform.PC, Platform.STEAM}
        return platform in steam_platforms

    def _validate_input(
        self, game_identifier: str, platform: Platform | str | None,
    ) -> None:
        """Valida parámetros de entrada."""
        if not game_identifier or not game_identifier.strip():
            raise ValidationError("Game identifier cannot be empty")

        if isinstance(platform, str) and not platform.strip():
            raise ValidationError("Platform cannot be empty string")

    def _merge_game_info(self, base: GameInfo | None, new: GameInfo) -> GameInfo:
        """Combina información de múltiples fuentes."""
        if not base:
            return new

        # Lógica de merge inteligente
        # Priorizar datos más completos y confiables
        merged = base.copy(deep=True)

        # Actualizar campos vacíos
        for field, value in new.model_dump().items():
            if value and not getattr(merged, field, None):
                setattr(merged, field, value)

        return merged

    async def _check_cache(
        self,
        game_identifier: str,
        platform: Platform | None,
    ) -> TranslationResult | None:
        """Verifica caché para resultado existente."""
        if not self.cache:
            return None

        cache_key = self._generate_cache_key(game_identifier, platform)
        return await self.cache.get(cache_key)

    async def _save_to_cache(
        self,
        game_identifier: str,
        platform: Platform | None,
        result: TranslationResult,
    ) -> None:
        """Guarda resultado en caché."""
        if not self.cache:
            return

        cache_key = self._generate_cache_key(game_identifier, platform)
        await self.cache.set(cache_key, result)

    def _generate_cache_key(
        self, game_identifier: str, platform: Platform | None,
    ) -> str:
        """Genera clave única para caché."""
        platform_str = platform.value if platform else "any"
        return f"game:{game_identifier.lower()}:platform:{platform_str}"

    async def _search_steam(
        self, game_identifier: str, result: TranslationResult,
    ) -> GameInfo | None:
        """Busca juego en Steam API."""
        if not self.steam_api:
            return None

        try:
            # Steam API siempre está disponible (no requiere API key)
            async with SteamAPI(rate_limiter=self.rate_limiter) as steam:
                result.add_api_used("steam")
                game_info = await steam.find_game_by_name(
                    game_identifier, language="spanish",
                )
                if game_info:
                    logger.info(f"Found game in Steam: {game_info.name}")
                return game_info
        except Exception as e:
            logger.warning(f"Steam search failed for {game_identifier}: {e}")
            return None

    async def _search_rawg(
        self,
        game_identifier: str,
        platform: Platform | None,
        result: TranslationResult,
    ) -> GameInfo | None:
        """Busca juego en RAWG API."""
        if not self.rawg_api:
            return None

        try:
            # RAWG API requiere contexto async
            async with self.rawg_api as rawg:
                result.add_api_used("rawg")
                game_info = await rawg.find_game_by_name(
                    game_identifier, exact_match=False,
                )
                if game_info:
                    logger.info(f"Found game in RAWG: {game_info.name}")
                return game_info
        except Exception as e:
            logger.warning(f"RAWG search failed for {game_identifier}: {e}")
            return None
