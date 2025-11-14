"""
RAWG API Connector

Conector para la API de RAWG (rawg.io), una base de datos de videojuegos.
Requiere API key gratuita disponible en https://rawg.io/apidocs

Características:
- Búsqueda de juegos por nombre
- Obtención de detalles completos
- Información de plataformas y géneros
- Rate limiting respetado
- Manejo de errores robusto
"""

import asyncio
import logging
import types
from typing import Any, Dict, Optional

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import settings
from ..core.rate_limiter import RateLimiter
from ..exceptions import (
    APIError,
    AuthenticationError,
    GameNotFoundError,
    RateLimitError,
    ValidationError,
)
from ..models.game import GameInfo

logger = logging.getLogger(__name__)


class RAWGResponse:
    """Modelo para respuestas de RAWG API."""

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.count = data.get("count", 0)
        self.results = data.get("results", [])

    @property
    def has_results(self) -> bool:
        return len(self.results) > 0


class RAWGAPIConnector:
    """
    Conector para RAWG API.

    RAWG es una base de datos de videojuegos que proporciona información
    detallada sobre juegos, incluyendo descripciones, capturas, ratings, etc.

    API Key: Gratuita en https://rawg.io/apidocs
    Rate Limits: 20,000 requests/month (gratuita)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Inicializa el conector RAWG.

        Args:
            api_key: API key de RAWG (opcional, se puede obtener de config)
            rate_limiter: Rate limiter para controlar uso de API (opcional)
        """
        self.api_key = api_key or settings.RAWG_API_KEY
        self.base_url = settings.RAWG_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = rate_limiter

        if not self.api_key:
            raise AuthenticationError(
                api_name="rawg",
                message="RAWG API key is required. Get one at https://rawg.io/apidocs",
            )

    async def __aenter__(self) -> "RAWGAPIConnector":
        """Context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[types.TracebackType],
    ) -> None:
        """Context manager exit."""
        await self.close()

    async def initialize(self) -> None:
        """Inicializa la sesión HTTP."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=settings.API_TIMEOUT_SECONDS)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": f"GameDescriptionTranslator/{settings.VERSION}",
                    "Accept": "application/json",
                },
            )

    async def close(self) -> None:
        """Cierra la sesión HTTP."""
        if self.session:
            await self.session.close()
            self.session = None

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    )
    async def search_game(self, query: str, limit: int = 10) -> RAWGResponse:
        """
        Busca juegos en RAWG por nombre.

        Args:
            query: Término de búsqueda
            limit: Número máximo de resultados (1-40)

        Returns:
            RAWGResponse con los resultados de búsqueda

        Raises:
            GameNotFoundError: Si no se encuentran juegos
            APIError: Si hay error en la API
            RateLimitError: Si se excede el rate limit
        """
        if not self.session:
            raise APIError("RAWG API session not initialized", "rawg")

        # Validar parámetros
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty")

        if not 1 <= limit <= 40:
            raise ValidationError("Limit must be between 1 and 40")

        # Aplicar rate limiting
        if self.rate_limiter:
            await self.rate_limiter.wait_if_needed("rawg")

        # Preparar parámetros
        params = {
            "key": self.api_key,
            "search": query.strip(),
            "page_size": limit,
            "ordering": "-rating",  # Ordenar por rating descendente
            "search_precise": "true",  # Búsqueda más precisa
        }

        url = f"{self.base_url}/games"

        try:
            logger.info(f"Searching RAWG for: {query}")

            async with self.session.get(url, params=params) as response:
                await self._handle_response_errors(response)
                data: Dict[str, Any] = await response.json()

                rawg_response = RAWGResponse(data)

                if not rawg_response.has_results:
                    raise GameNotFoundError(f"No games found for '{query}' in RAWG")

                logger.info(f"Found {rawg_response.count} games in RAWG for '{query}'")
                return rawg_response

        except aiohttp.ClientError as e:
            raise APIError(f"RAWG API request failed: {e}", "rawg")
        except Exception as e:
            if isinstance(e, (GameNotFoundError, APIError, RateLimitError)):
                raise
            raise APIError(f"Unexpected error in RAWG search: {e}", "rawg")

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    )
    async def get_game_details(self, game_id: int) -> dict[str, Any]:
        """
        Obtiene detalles completos de un juego por ID.

        Args:
            game_id: ID del juego en RAWG

        Returns:
            Diccionario con detalles completos del juego

        Raises:
            GameNotFoundError: Si el juego no existe
            APIError: Si hay error en la API
            RateLimitError: Si se excede el rate limit
        """
        if not self.session:
            raise APIError("RAWG API session not initialized", "rawg")

        # Validar parámetros
        if not isinstance(game_id, int) or game_id <= 0:
            raise ValidationError("Game ID must be a positive integer")

        # Aplicar rate limiting
        if self.rate_limiter:
            await self.rate_limiter.wait_if_needed("rawg")

        params = {"key": self.api_key}
        url = f"{self.base_url}/games/{game_id}"

        try:
            logger.info(f"Getting RAWG details for game ID: {game_id}")

            async with self.session.get(url, params=params) as response:
                await self._handle_response_errors(response)
                data = await response.json()

                logger.info(
                    f"Retrieved RAWG details for game: {data.get('name', 'Unknown')}",
                )
                return data

        except aiohttp.ClientError as e:
            raise APIError(f"RAWG API request failed: {e}", "rawg")
        except Exception as e:
            if isinstance(e, (GameNotFoundError, APIError, RateLimitError)):
                raise
            raise APIError(f"Unexpected error getting RAWG details: {e}", "rawg")

    async def find_game_by_name(
        self,
        name: str,
        exact_match: bool = False,
    ) -> Optional[GameInfo]:
        """
        Busca un juego específico por nombre y devuelve GameInfo.

        Args:
            name: Nombre del juego a buscar
            exact_match: Si True, busca coincidencia exacta

        Returns:
            GameInfo del juego encontrado o None si no se encuentra

        Raises:
            APIError: Si hay error en la API
            RateLimitError: Si se excede el rate limit
        """
        try:
            # Buscar juegos
            response = await self.search_game(name, limit=20)

            if not response.has_results:
                return None

            # Buscar coincidencia exacta o mejor match
            best_match = None
            best_score = 0.0  # Usar float para manejar divisiones

            for game_data in response.results:
                game_name = game_data.get("name", "").lower()
                search_name = name.lower()

                # Coincidencia exacta
                if exact_match and game_name == search_name:
                    best_match = game_data
                    break

                # Scoring para mejor match
                if search_name in game_name:
                    score = len(search_name) / len(game_name)
                    if score > best_score:
                        best_score = score
                        best_match = game_data
                elif game_name in search_name:
                    score = len(game_name) / len(search_name)
                    if score > best_score:
                        best_score = score
                        best_match = game_data

            if not best_match:
                # Si no hay match directo, tomar el primero (mejor rating)
                best_match = response.results[0]

            # Obtener detalles completos
            game_details = await self.get_game_details(best_match["id"])

            # Convertir a GameInfo
            return self._convert_to_game_info(game_details)

        except GameNotFoundError:
            return None

    def _convert_to_game_info(self, rawg_data: Dict[str, Any]) -> GameInfo:
        """
        Convierte datos de RAWG a GameInfo.

        Args:
            rawg_data: Datos del juego desde RAWG API

        Returns:
            GameInfo con los datos convertidos
        """
        # Extraer información básica
        name = rawg_data.get("name", "Unknown")
        description = rawg_data.get("description_raw", "") or rawg_data.get(
            "description",
            "",
        )

        # Limpiar HTML si existe
        if description:
            description = self._clean_html(description)

        # Extraer plataformas
        from ..models.game import Platform

        platforms = []
        for platform_data in rawg_data.get("platforms", []):
            platform_info = platform_data.get("platform", {})
            platform_name = platform_info.get("name", "")
            if platform_name:
                # Convertir a enum Platform si es posible, de lo contrario usar el nombre como string
                try:
                    platform = Platform(platform_name.lower())
                    platforms.append(platform)
                except ValueError:
                    platforms.append(platform_name)

        # Extraer géneros
        genres = [
            genre.get("name", "")
            for genre in rawg_data.get("genres", [])
            if genre.get("name")
        ]

        # Extraer desarrolladores
        developers = [
            dev.get("name", "")
            for dev in rawg_data.get("developers", [])
            if dev.get("name")
        ]

        # Extraer publishers
        publishers = [
            pub.get("name", "")
            for pub in rawg_data.get("publishers", [])
            if pub.get("name")
        ]

        # Fecha de lanzamiento
        release_date = rawg_data.get("released", "")

        # Rating
        rating = rawg_data.get("rating", 0.0)

        # Metacritic score
        metacritic_score = rawg_data.get("metacritic")
        if metacritic_score is not None:
            # Asegurar que el puntuación esté en el rango 0-100
            metacritic_score = max(0, min(100, int(metacritic_score)))

        # Screenshots
        screenshots = []
        for screenshot in rawg_data.get("short_screenshots", []):
            if screenshot.get("image"):
                screenshots.append(screenshot["image"])

        # Convertir fecha si existe
        release_datetime = None
        if release_date:
            try:
                from datetime import datetime

                release_datetime = datetime.strptime(release_date, "%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        # Convertir rating (RAWG usa 0-5, GameInfo espera 0-10)
        user_score = float(rating * 2) if rating is not None else None
        if user_score is not None:
            # Asegurar que el puntuación esté en el rango 0-10
            user_score = max(0.0, min(10.0, user_score))

        # URL de la tienda
        store_url = rawg_data.get("website", "")
        if not store_url and "reddit_url" in rawg_data:
            store_url = rawg_data["reddit_url"]

        # Imagen de cabecera
        header_image = rawg_data.get("background_image", "")

        return GameInfo(
            name=name,
            short_description_en=description,
            description=description,  # Para compatibilidad
            rawg_id=rawg_data.get("id"),
            platforms=platforms,
            genres=genres,
            developer=developers[0] if developers else None,
            publisher=publishers[0] if publishers else None,
            release_date=release_datetime,
            user_score=user_score,
            metacritic_score=metacritic_score,
            store_url=store_url,
            header_image=header_image,
            screenshots=screenshots,
            translation_source=None,  # RAWG no traduce, solo proporciona datos
            source_api="rawg",  # Establecer la fuente de los datos
        )

    async def _handle_response_errors(self, response: aiohttp.ClientResponse) -> None:
        """Maneja errores de respuesta HTTP."""
        if response.status == 429:
            # Rate limit exceeded
            retry_after = response.headers.get("Retry-After")
            retry_seconds = (
                int(retry_after) if retry_after and retry_after.isdigit() else 60
            )
            raise RateLimitError(
                api_name="rawg",
                retry_after=retry_seconds,
                message=f"Rate limit exceeded. Retry after {retry_seconds} seconds",
                status_code=429,
            )

        if response.status == 401:
            raise AuthenticationError(api_name="rawg", message="Invalid RAWG API key")

        if response.status == 403:
            raise APIError("RAWG API access forbidden", "rawg", response.status)

        if response.status == 404:
            raise GameNotFoundError("Game not found in RAWG")

        if response.status >= 500:
            raise APIError(
                f"RAWG API server error: {response.status}",
                "rawg",
                response.status,
            )

        if response.status >= 400:
            text = await response.text()
            raise APIError(
                f"RAWG API client error {response.status}: {text}",
                "rawg",
                response.status,
            )

        # 200-299 son exitosos
        response.raise_for_status()

    def _clean_html(self, text: str) -> str:
        """
        Limpia tags HTML básicos del texto.

        Args:
            text: Texto con posibles tags HTML

        Returns:
            Texto limpio sin tags HTML
        """
        import re

        if not text:
            return ""

        # Remover tags HTML
        text = re.sub(r"<[^>]+>", "", text)

        # Decodificar entidades HTML comunes
        html_entities = {
            "&amp;": "&",
            "&lt;": "<",
            "&gt;": ">",
            "&quot;": '"',
            "&#39;": "'",
            "&nbsp;": " ",
        }

        for entity, char in html_entities.items():
            text = text.replace(entity, char)

        # Limpiar espacios múltiples
        text = re.sub(r"\s+", " ", text).strip()

        return text


# Función de conveniencia para uso directo
async def search_rawg_game(
    query: str,
    api_key: Optional[str] = None,
) -> Optional[GameInfo]:
    """
    Función de conveniencia para buscar un juego en RAWG.

    Args:
        query: Nombre del juego a buscar
        api_key: API key de RAWG (opcional)

    Returns:
        GameInfo del juego encontrado o None
    """
    async with RAWGAPIConnector(api_key) as connector:
        return await connector.find_game_by_name(query)
