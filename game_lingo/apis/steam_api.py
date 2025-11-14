"""
Conector para Steam Store API.

Steam Store API es gratuita y no requiere API key.
Proporciona descripciones de juegos en múltiples idiomas incluyendo español.

Endpoints utilizados:
- Store Search: https://store.steampowered.com/api/storesearch/
- App Details: https://store.steampowered.com/api/appdetails/

Límites:
- ~200 requests por 5 minutos por IP
- Sin autenticación requerida
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..exceptions import APIError, GameNotFoundError, RateLimitError
from ..models.api_response import SteamResponse
from ..models.game import GameInfo, Platform

if TYPE_CHECKING:
    from types import TracebackType

    from ..core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class SteamAPI:
    """
    Conector para Steam Store API.

    Características:
    - Búsqueda de juegos por nombre
    - Obtención de detalles completos
    - Soporte para múltiples idiomas
    - Manejo automático de rate limiting
    - Reintentos con backoff exponencial
    """

    BASE_URL = "https://store.steampowered.com/api"
    SEARCH_URL = f"{BASE_URL}/storesearch/"
    DETAILS_URL = f"{BASE_URL}/appdetails/"

    # Códigos de idioma soportados por Steam
    LANGUAGE_CODES = {
        "spanish": "spanish",
        "english": "english",
        "es": "spanish",
        "en": "english",
    }

    def __init__(
        self,
        session: Optional[aiohttp.ClientSession] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        """
        Inicializa el conector de Steam API.

        Args:
            session: Sesión HTTP personalizada (opcional)
            rate_limiter: Rate limiter para controlar uso de API (opcional)
        """
        self.session = session
        self._own_session = session is None
        self.timeout = aiohttp.ClientTimeout(total=settings.API_TIMEOUT_SECONDS)
        self.rate_limiter = rate_limiter

        logger.info("Steam API connector initialized")

    async def __aenter__(self) -> SteamAPI:
        """Context manager entry."""
        if self._own_session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Context manager exit."""
        if self._own_session and self.session:
            await self.session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def search_game(
        self,
        query: str,
        language: str = "spanish",
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Busca juegos en Steam Store.

        Args:
            query: Término de búsqueda
            language: Idioma de resultados ("spanish" o "english")
            max_results: Número máximo de resultados

        Returns:
            Lista de juegos encontrados

        Raises:
            GameNotFoundError: Si no se encuentran resultados
            APIError: Si hay error en la API
        """
        if not self.session:
            raise APIError("Steam API session not initialized", "steam")

        # Normalizar idioma
        lang_code = self.LANGUAGE_CODES.get(language.lower(), "spanish")

        # Preparar parámetros
        params = {
            "term": query,
            "l": lang_code,
            "cc": "ES",  # Country code para España
            "realm": "1",  # Steam store
            "origin": "https://store.steampowered.com",
            "f": "jsonfull",
            "start": "0",
            "count": str(max_results),
        }

        try:
            # Rate limiting
            if self.rate_limiter:
                await self.rate_limiter.wait_if_needed("steam")

            logger.debug(f"Searching Steam for: {query} (language: {lang_code})")

            async with self.session.get(self.SEARCH_URL, params=params) as response:
                await self._handle_response_errors(response)

                data = await response.json()

                # Steam search API no devuelve campo 'success', solo 'total' e 'items'
                # Verificar que la respuesta tenga la estructura esperada
                if "items" not in data:
                    raise APIError(
                        f"Steam search failed: unexpected response format: {data}",
                        "steam",
                    )

                items = data.get("items", [])

                if not items:
                    raise GameNotFoundError(query, "steam")

                logger.info(f"Found {len(items)} games on Steam for query: {query}")
                return items[:max_results]

        except aiohttp.ClientError as e:
            raise APIError(f"Steam API request failed: {e}", "steam")
        except Exception as e:
            if isinstance(e, (GameNotFoundError, APIError, RateLimitError)):
                raise
            raise APIError(f"Unexpected error in Steam search: {e}", "steam")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_game_details(
        self,
        app_id: int | str,
        language: str = "spanish",
    ) -> SteamResponse:
        """
        Obtiene detalles completos de un juego por App ID.

        Args:
            app_id: Steam App ID
            language: Idioma de la respuesta

        Returns:
            SteamResponse con detalles del juego

        Raises:
            GameNotFoundError: Si el juego no existe
            APIError: Si hay error en la API
        """
        if not self.session:
            raise APIError("Steam API session not initialized", "steam")

        # Normalizar idioma
        lang_code = self.LANGUAGE_CODES.get(language.lower(), "spanish")

        # Preparar parámetros
        params = {
            "appids": str(app_id),
            "l": lang_code,
            "cc": "ES",
            "filters": "basic,platforms,categories,genres,screenshots,movies",
        }

        try:
            # Rate limiting
            if self.rate_limiter:
                await self.rate_limiter.wait_if_needed("steam")

            logger.debug(
                f"Getting Steam details for app_id: {app_id} (language: {lang_code})",
            )

            async with self.session.get(self.DETAILS_URL, params=params) as response:
                await self._handle_response_errors(response)

                data = await response.json()

                # Steam devuelve un objeto con el app_id como clave
                app_data = data.get(str(app_id))
                if not app_data:
                    raise GameNotFoundError(str(app_id), "steam")

                if not app_data.get("success", False):
                    raise GameNotFoundError(str(app_id), "steam")

                game_data = app_data.get("data", {})
                if not game_data:
                    raise GameNotFoundError(str(app_id), "steam")

                # Crear respuesta estructurada
                steam_response = SteamResponse(
                    success=True,
                    status_code=response.status,
                    response_time_ms=0,  # Se podría calcular si es necesario
                    app_id=int(app_id),
                    name=game_data.get("name", ""),
                    short_description=game_data.get("short_description", ""),
                    detailed_description=game_data.get("detailed_description", ""),
                    about_the_game=game_data.get("about_the_game", ""),
                    supported_languages=game_data.get("supported_languages", ""),
                    platforms=self._extract_platforms(game_data.get("platforms", {})),
                    categories=self._extract_categories(
                        game_data.get("categories", []),
                    ),
                    genres=self._extract_genres(game_data.get("genres", [])),
                    release_date=self._extract_release_date(
                        game_data.get("release_date", {}),
                    ),
                    metacritic_score=game_data.get("metacritic", {}).get("score"),
                    price_overview=game_data.get("price_overview", {}),
                    screenshots=self._extract_screenshots(
                        game_data.get("screenshots", []),
                    ),
                    movies=self._extract_movies(game_data.get("movies", [])),
                    language=lang_code,
                    raw_data=data,
                )

                logger.info(
                    f"Successfully retrieved Steam details for: {steam_response.name}",
                )
                return steam_response

        except aiohttp.ClientError as e:
            raise APIError(f"Steam API request failed: {e}", "steam")
        except Exception as e:
            if isinstance(e, (GameNotFoundError, APIError, RateLimitError)):
                raise
            raise APIError(f"Unexpected error getting Steam details: {e}", "steam")

    async def find_game_by_name(
        self,
        game_name: str,
        language: str = "spanish",
    ) -> GameInfo | None:
        """
        Busca un juego por nombre y devuelve información completa.

        Args:
            game_name: Nombre del juego
            language: Idioma preferido

        Returns:
            GameInfo si se encuentra, None si no
        """
        try:
            # Buscar juegos
            search_results = await self.search_game(game_name, language, max_results=5)

            # Encontrar mejor coincidencia
            best_match = self._find_best_match(game_name, search_results)
            if not best_match:
                return None

            app_id = best_match.get("id")
            if not app_id:
                return None

            # Obtener detalles completos
            steam_response = await self.get_game_details(app_id, language)

            # Convertir a GameInfo
            return self._steam_response_to_game_info(steam_response)

        except (GameNotFoundError, APIError) as e:
            logger.warning(f"Could not find game '{game_name}' on Steam: {e}")
            return None

    def _find_best_match(
        self,
        query: str,
        results: List[Dict[str, Any]],
    ) -> Dict[str, Any] | None:
        """Encuentra la mejor coincidencia en los resultados de búsqueda."""
        if not results:
            return None

        query_lower = query.lower().strip()
        query_words = set(query_lower.split())

        # Función para calcular puntuación de coincidencia
        def calculate_match_score(name: str) -> float:
            name_lower = name.lower().strip()
            name_words = set(name_lower.split())

            # Coincidencia exacta = máxima puntuación
            if name_lower == query_lower:
                return 100.0

            # Coincidencia de palabras completas
            common_words = query_words.intersection(name_words)
            if common_words:
                word_match_ratio = len(common_words) / len(query_words)
                score = 80.0 * word_match_ratio

                # Bonus si todas las palabras del query están presentes
                if len(common_words) == len(query_words):
                    score += 15.0

                return score

            # Coincidencia por substring
            if query_lower in name_lower:
                # Bonus si el query está al principio del nombre
                if name_lower.startswith(query_lower):
                    return 70.0
                return 60.0

            # Coincidencia parcial de substring
            if any(word in name_lower for word in query_words if len(word) > 2):
                return 40.0

            return 0.0

        # Calcular puntuaciones para todos los resultados
        scored_results = []
        for item in results:
            name = item.get("name", "")
            score = calculate_match_score(name)
            scored_results.append((score, item))
            logger.debug(f"Match score for '{name}': {score:.1f}")

        # Ordenar por puntuación descendente
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # Devolver el mejor resultado si tiene puntuación > 0
        if scored_results and scored_results[0][0] > 0:
            best_score, best_match = scored_results[0]
            logger.debug(
                f"Best match: '{best_match.get('name', '')}' with score {best_score:.1f}",
            )
            return best_match

        # Si no hay coincidencias, devolver el primer resultado
        logger.debug("No good matches found, returning first result as fallback")
        return results[0]

    def _steam_response_to_game_info(self, steam_response: SteamResponse) -> GameInfo:
        """Convierte SteamResponse a GameInfo."""
        # Determinar qué descripción usar según el idioma
        if steam_response.language == "spanish":
            short_desc_es = self._clean_html(steam_response.short_description)
            detailed_desc_es = self._clean_html(
                steam_response.detailed_description or steam_response.about_the_game,
            )
            short_desc_en = None
            detailed_desc_en = None
        else:
            short_desc_es = None
            detailed_desc_es = None
            short_desc_en = self._clean_html(steam_response.short_description)
            detailed_desc_en = self._clean_html(
                steam_response.detailed_description or steam_response.about_the_game,
            )

        # Convertir release_year a datetime si está disponible
        release_date = None
        release_year = self._extract_year_from_date(steam_response.release_date)
        if release_year:
            try:
                release_date = datetime(
                    year=release_year,
                    month=1,
                    day=1,
                    tzinfo=timezone.utc,
                )
            except (ValueError, TypeError):
                pass

        return GameInfo(
            name=steam_response.name,
            steam_id=steam_response.app_id,
            short_description_en=short_desc_en or "",  # Usar string vacío si es None
            description=short_desc_en or "",  # Para compatibilidad
            short_description_es=short_desc_es or "",
            detailed_description_en=detailed_desc_en or "",
            detailed_description_es=detailed_desc_es or "",
            platforms=[Platform.STEAM, Platform.PC],  # Steam siempre incluye PC
            genres=steam_response.genres or [],
            release_date=release_date,
            metacritic_score=steam_response.metacritic_score,
            store_url=f"https://store.steampowered.com/app/{steam_response.app_id}",
            header_image=getattr(steam_response, "header_image", None),
            screenshots=getattr(steam_response, "screenshots", []) or [],
            translation_source=None,  # Steam proporciona datos nativos
            source_api="steam",
        )

    def _clean_html(self, text: str | None) -> str | None:
        """Limpia tags HTML de texto."""
        if not text:
            return None

        # Remover tags HTML básicos
        text = re.sub(r"<[^>]+>", "", text)

        # Decodificar entidades HTML comunes
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")
        text = text.replace("&nbsp;", " ")

        # Limpiar espacios extra
        text = " ".join(text.split())

        return text.strip() if text.strip() else None

    def _extract_platforms(self, platforms_data: Dict[str, Any]) -> List[str]:
        """Extrae plataformas soportadas."""
        platforms = []
        if platforms_data.get("windows"):
            platforms.append("windows")
        if platforms_data.get("mac"):
            platforms.append("mac")
        if platforms_data.get("linux"):
            platforms.append("linux")
        return platforms

    def _extract_categories(self, categories_data: List[Dict[str, Any]]) -> List[str]:
        """Extrae categorías del juego."""
        return [
            cat.get("description", "")
            for cat in categories_data
            if cat.get("description")
        ]

    def _extract_genres(self, genres_data: List[Dict[str, Any]]) -> List[str]:
        """Extrae géneros del juego."""
        return [
            genre.get("description", "")
            for genre in genres_data
            if genre.get("description")
        ]

    def _extract_release_date(self, release_data: Dict[str, Any]) -> str | None:
        """Extrae fecha de lanzamiento."""
        return (
            release_data.get("date")
            if release_data.get("coming_soon") is False
            else None
        )

    def _extract_year_from_date(self, date_str: str | None) -> int | None:
        """
        Extrae año de una fecha.

        Args:
            date_str: Cadena de fecha en varios formatos posibles

        Returns:
            Año como entero si se puede extraer, None si no es posible
        """
        if not date_str:
            return None

        try:
            # Intentar extraer año de formato YYYY
            if re.match(r"^\d{4}$", date_str):
                year = int(date_str)
                if (
                    1900 <= year <= datetime.now(timezone.utc).year + 5
                ):  # Validar año razonable
                    return year
                return None

            # Intentar extraer de formato YYYY-MM-DD o similar
            date_formats = [
                r"(\d{4})[\-/](\d{1,2})[\-/](\d{1,2})",  # YYYY-MM-DD
                r"(\d{1,2})[\-/](\d{1,2})[\-/](\d{4})",  # DD-MM-YYYY
                r"(\d{4})[/](\d{1,2})[/](\d{1,2})",  # YYYY/MM/DD
                r"(\d{1,2})[/](\d{1,2})[/](\d{4})",  # DD/MM/YYYY
                r"(\d{4})\.(\d{1,2})\.(\d{1,2})",  # YYYY.MM.DD
            ]

            for fmt in date_formats:
                match = re.search(fmt, date_str)
                if match:
                    # El primer grupo de captura es el año o el día dependiendo del formato
                    # Asumimos que cualquier número de 4 dígitos es un año
                    for group in match.groups():
                        if len(group) == 4 and group.isdigit():
                            year = int(group)
                            if 1900 <= year <= datetime.now(timezone.utc).year + 5:
                                return year
                            return None

            # Buscar cualquier secuencia de 4 dígitos como último recurso
            match = re.search(r"(\d{4})", date_str)
            if match:
                year = int(match.group(1))
                if 1900 <= year <= datetime.now(timezone.utc).year + 5:
                    return year

            logger.warning(f"No se pudo extraer un año válido de: {date_str}")
            return None

        except (ValueError, TypeError) as e:
            logger.warning(f"Error al extraer año de '{date_str}': {e}")
            return None

    def _extract_screenshots(self, screenshots_data: List[Dict[str, Any]]) -> List[str]:
        """Extrae URLs de screenshots."""
        return [
            screenshot.get("path_full", "")
            for screenshot in screenshots_data
            if screenshot.get("path_full")
        ]

    def _extract_movies(self, movies_data: List[Dict[str, Any]]) -> List[str]:
        """Extrae URLs de videos."""
        return [
            movie.get("mp4", {}).get("max", "")
            for movie in movies_data
            if movie.get("mp4", {}).get("max")
        ]

    async def _handle_response_errors(self, response: aiohttp.ClientResponse) -> None:
        """Maneja errores de respuesta HTTP."""
        if response.status == 429:
            # Rate limit exceeded
            retry_after = response.headers.get("Retry-After", "60")
            raise RateLimitError("steam", int(retry_after))

        if response.status == 403:
            raise APIError("Steam API access forbidden", "steam", response.status)

        if response.status >= 500:
            raise APIError(
                f"Steam API server error: {response.status}",
                "steam",
                response.status,
            )

        if response.status >= 400:
            text = await response.text()
            raise APIError(
                f"Steam API client error {response.status}: {text}",
                "steam",
                response.status,
            )

        # 200-299 son exitosos
        response.raise_for_status()

    def __str__(self) -> str:
        """Representación string del conector."""
        return "SteamAPI(no auth required)"

    def __repr__(self) -> str:
        """Representación detallada del conector."""
        return f"SteamAPI(base_url={self.BASE_URL}, timeout={self.timeout})"
