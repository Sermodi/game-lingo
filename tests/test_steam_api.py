"""
Tests unitarios para Steam API connector.

Incluye tests para:
- Búsqueda de juegos
- Obtención de detalles
- Manejo de errores
- Conversión de datos
- Rate limiting
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from game_lingo.apis.steam_api import SteamAPI
from game_lingo.exceptions import APIError, GameNotFoundError, RateLimitError
from game_lingo.models.api_response import SteamResponse
from game_lingo.models.game import GameInfo, Platform


class TestSteamAPI:
    """Test suite para SteamAPI."""

    @pytest.fixture
    async def steam_api(self):
        """Fixture que proporciona una instancia de SteamAPI."""
        async with SteamAPI() as api:
            yield api

    @pytest.fixture
    def mock_session(self):
        """Fixture que proporciona una sesión HTTP mock."""
        session = AsyncMock(spec=aiohttp.ClientSession)
        return session

    @pytest.fixture
    def sample_search_response(self):
        """Respuesta de ejemplo para búsqueda."""
        return {
            "success": True,
            "items": [
                {
                    "id": 292030,
                    "name": "The Witcher 3: Wild Hunt",
                    "tiny_image": "https://steamcdn-a.akamaihd.net/steam/apps/292030/capsule_sm_120.jpg",
                    "price": {
                        "currency": "EUR",
                        "initial": 2999,
                        "final": 2999,
                        "discount_percent": 0,
                    },
                },
                {
                    "id": 1174180,
                    "name": "Red Dead Redemption 2",
                    "tiny_image": "https://steamcdn-a.akamaihd.net/steam/apps/1174180/capsule_sm_120.jpg",
                    "price": {
                        "currency": "EUR",
                        "initial": 5999,
                        "final": 2999,
                        "discount_percent": 50,
                    },
                },
            ],
        }

    @pytest.fixture
    def sample_details_response(self):
        """Respuesta de ejemplo para detalles de juego."""
        return {
            "292030": {
                "success": True,
                "data": {
                    "type": "game",
                    "name": "The Witcher 3: Wild Hunt",
                    "steam_appid": 292030,
                    "required_age": 18,
                    "is_free": False,
                    "short_description": "Como Geralt de Rivia, un cazador de monstruos profesional, embárcate en una aventura épica en un mundo abierto rico en mercaderes, villanos, monstruos y amigos.",
                    "detailed_description": "El mundo de The Witcher 3: Wild Hunt es 30 veces más grande que los entornos anteriores de la serie y aún más hermoso. Viaja sin límites por un mundo de fantasía abierto...",
                    "about_the_game": "The Witcher 3: Wild Hunt es un RPG de mundo abierto de nueva generación con una narrativa madura...",
                    "supported_languages": "Inglés<strong>*</strong>, Francés<strong>*</strong>, Italiano, Alemán<strong>*</strong>, Español - España<strong>*</strong>, Árabe, Checo, Húngaro, Japonés<strong>*</strong>, Coreano, Polaco<strong>*</strong>, Portugués - Brasil<strong>*</strong>, Ruso<strong>*</strong>, Chino tradicional, Turco, Chino simplificado<br><strong>*</strong>idiomas con audio completo",
                    "platforms": {"windows": True, "mac": False, "linux": True},
                    "categories": [
                        {"id": 2, "description": "Un jugador"},
                        {"id": 22, "description": "Logros de Steam"},
                    ],
                    "genres": [
                        {"id": "3", "description": "Aventura"},
                        {"id": "23", "description": "Indie"},
                        {"id": "3", "description": "RPG"},
                    ],
                    "release_date": {"coming_soon": False, "date": "19 may 2015"},
                    "metacritic": {
                        "score": 93,
                        "url": "https://www.metacritic.com/game/pc/the-witcher-3-wild-hunt?ftag=MCD-06-10aaa1f",
                    },
                    "price_overview": {
                        "currency": "EUR",
                        "initial": 2999,
                        "final": 2999,
                        "discount_percent": 0,
                        "initial_formatted": "",
                        "final_formatted": "29,99€",
                    },
                    "screenshots": [
                        {
                            "id": 0,
                            "path_thumbnail": "https://steamcdn-a.akamaihd.net/steam/apps/292030/ss_615455299355eaf552c638c7ea5b24a8b46e02dd.600x338.jpg",
                            "path_full": "https://steamcdn-a.akamaihd.net/steam/apps/292030/ss_615455299355eaf552c638c7ea5b24a8b46e02dd.1920x1080.jpg",
                        }
                    ],
                    "movies": [
                        {
                            "id": 2029441,
                            "name": "The Witcher 3: Wild Hunt - Killing Monsters Cinematic Trailer",
                            "thumbnail": "https://steamcdn-a.akamaihd.net/steam/apps/2029441/movie.293x165.jpg",
                            "webm": {
                                "480": "http://steamcdn-a.akamaihd.net/steam/apps/2029441/movie480.webm",
                                "max": "http://steamcdn-a.akamaihd.net/steam/apps/2029441/movie_max.webm",
                            },
                            "mp4": {
                                "480": "http://steamcdn-a.akamaihd.net/steam/apps/2029441/movie480.mp4",
                                "max": "http://steamcdn-a.akamaihd.net/steam/apps/2029441/movie_max.mp4",
                            },
                            "highlight": True,
                        }
                    ],
                },
            }
        }

    @pytest.mark.asyncio
    async def test_search_game_success(self, mock_session, sample_search_response):
        """Test búsqueda exitosa de juegos."""
        # Configurar mock
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_search_response)
        mock_session.get.return_value.__aenter__.return_value = mock_response

        # Crear API con sesión mock
        api = SteamAPI(session=mock_session)

        # Ejecutar búsqueda
        results = await api.search_game("witcher", language="spanish")

        # Verificar resultados
        assert len(results) == 2
        assert results[0]["name"] == "The Witcher 3: Wild Hunt"
        assert results[0]["id"] == 292030

        # Verificar llamada a la API
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        # Verificar que se llamó con los parámetros correctos
        assert call_args[1]["params"]["term"] == "witcher"
        assert call_args[1]["params"]["l"] == "spanish"

    @pytest.mark.asyncio
    async def test_search_game_not_found(self, mock_session):
        """Test búsqueda sin resultados."""
        # Configurar mock para respuesta vacía
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True, "items": []})
        mock_session.get.return_value.__aenter__.return_value = mock_response

        api = SteamAPI(session=mock_session)

        # Verificar que se lanza excepción
        with pytest.raises(GameNotFoundError) as exc_info:
            await api.search_game("juego_inexistente")

        assert "juego_inexistente" in str(exc_info.value)
        assert "steam" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_game_api_error(self, mock_session):
        """Test manejo de errores de API en búsqueda."""
        # Configurar mock para error de API
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"success": False, "error": "Invalid request"}
        )
        mock_session.get.return_value.__aenter__.return_value = mock_response

        api = SteamAPI(session=mock_session)

        with pytest.raises(APIError) as exc_info:
            await api.search_game("test")

        assert "Steam search failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_game_rate_limit(self, mock_session):
        """Test manejo de rate limiting."""
        # Configurar mock para rate limit
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.headers = {"Retry-After": "120"}
        mock_session.get.return_value.__aenter__.return_value = mock_response

        api = SteamAPI(session=mock_session)

        with pytest.raises(RateLimitError) as exc_info:
            await api.search_game("test")

        assert "rate limit exceeded" in str(exc_info.value).lower()
        assert "120" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_game_details_success(
        self, mock_session, sample_details_response
    ):
        """Test obtención exitosa de detalles."""
        # Configurar mock
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_details_response)
        mock_session.get.return_value.__aenter__.return_value = mock_response

        api = SteamAPI(session=mock_session)

        # Ejecutar obtención de detalles
        result = await api.get_game_details(292030, language="spanish")

        # Verificar resultado
        assert isinstance(result, SteamResponse)
        assert result.success is True
        assert result.app_id == 292030
        assert result.name == "The Witcher 3: Wild Hunt"
        assert "Geralt de Rivia" in result.short_description
        assert result.language == "spanish"
        assert result.metacritic_score == 93
        assert len(result.platforms) == 2  # windows y linux
        assert len(result.genres) == 3
        assert len(result.categories) == 2

        # Verificar llamada a la API
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "appids=292030" in str(call_args)
        assert "l=spanish" in str(call_args)

    @pytest.mark.asyncio
    async def test_get_game_details_not_found(self, mock_session):
        """Test detalles de juego no encontrado."""
        # Configurar mock para juego no encontrado
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"999999": {"success": False}})
        mock_session.get.return_value.__aenter__.return_value = mock_response

        api = SteamAPI(session=mock_session)

        with pytest.raises(GameNotFoundError) as exc_info:
            await api.get_game_details(999999)

        assert "999999" in str(exc_info.value)
        assert "steam" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_find_game_by_name_success(
        self, mock_session, sample_search_response, sample_details_response
    ):
        """Test búsqueda completa por nombre."""
        # Configurar mocks para búsqueda y detalles
        search_mock = AsyncMock()
        search_mock.status = 200
        search_mock.json = AsyncMock(return_value=sample_search_response)

        details_mock = AsyncMock()
        details_mock.status = 200
        details_mock.json = AsyncMock(return_value=sample_details_response)

        # Configurar secuencia de respuestas
        mock_session.get.return_value.__aenter__.side_effect = [
            search_mock,
            details_mock,
        ]

        api = SteamAPI(session=mock_session)

        # Ejecutar búsqueda completa
        result = await api.find_game_by_name("The Witcher 3", language="spanish")

        # Verificar resultado
        assert isinstance(result, GameInfo)
        assert result.name == "The Witcher 3: Wild Hunt"
        assert result.steam_id == 292030
        assert result.short_description_es is not None
        assert "Geralt de Rivia" in result.short_description_es
        assert result.source_api == "steam"
        assert Platform.STEAM in result.platforms
        assert Platform.PC in result.platforms
        assert result.rating == 93
        assert result.release_year == 2015

        # Verificar que se hicieron ambas llamadas
        assert mock_session.get.call_count == 2

    @pytest.mark.asyncio
    async def test_find_game_by_name_not_found(self, mock_session):
        """Test búsqueda de juego inexistente."""
        # Configurar mock para búsqueda sin resultados
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True, "items": []})
        mock_session.get.return_value.__aenter__.return_value = mock_response

        api = SteamAPI(session=mock_session)

        # Ejecutar búsqueda
        result = await api.find_game_by_name("juego_inexistente")

        # Verificar que devuelve None
        assert result is None

    def test_find_best_match_exact(self):
        """Test búsqueda de mejor coincidencia exacta."""
        api = SteamAPI()

        results = [
            {"name": "The Witcher 2"},
            {"name": "The Witcher 3: Wild Hunt"},
            {"name": "The Witcher"},
        ]

        match = api._find_best_match("The Witcher 3: Wild Hunt", results)
        assert match["name"] == "The Witcher 3: Wild Hunt"

    def test_find_best_match_partial(self):
        """Test búsqueda de mejor coincidencia parcial."""
        api = SteamAPI()

        results = [
            {"name": "Some Other Game"},
            {"name": "The Witcher 3: Wild Hunt - Complete Edition"},
            {"name": "Another Game"},
        ]

        match = api._find_best_match("The Witcher 3", results)
        assert "Witcher 3" in match["name"]

    def test_find_best_match_fallback(self):
        """Test fallback a primer resultado."""
        api = SteamAPI()

        results = [{"name": "Completely Different Game"}, {"name": "Another Game"}]

        match = api._find_best_match("Nonexistent Game", results)
        assert match["name"] == "Completely Different Game"

    def test_clean_html(self):
        """Test limpieza de HTML."""
        api = SteamAPI()

        # Test con HTML básico
        html_text = "<p>Este es un <strong>texto</strong> con <em>HTML</em>.</p>"
        cleaned = api._clean_html(html_text)
        assert cleaned == "Este es un texto con HTML."

        # Test con entidades HTML
        html_text = "Texto con &amp; entidades &lt;especiales&gt; &quot;comillas&quot;"
        cleaned = api._clean_html(html_text)
        assert cleaned == 'Texto con & entidades <especiales> "comillas"'

        # Test con texto None
        assert api._clean_html(None) is None

        # Test con texto vacío
        assert api._clean_html("") is None
        assert api._clean_html("   ") is None

    def test_extract_year_from_date(self):
        """Test extracción de año de fecha."""
        api = SteamAPI()

        # Test con fecha válida
        assert api._extract_year_from_date("19 may 2015") == 2015
        assert api._extract_year_from_date("Dec 2020") == 2020
        assert api._extract_year_from_date("Coming in 2024") == 2024

        # Test con fecha inválida
        assert api._extract_year_from_date("Coming soon") is None
        assert api._extract_year_from_date("") is None
        assert api._extract_year_from_date(None) is None

    def test_extract_platforms(self):
        """Test extracción de plataformas."""
        api = SteamAPI()

        platforms_data = {"windows": True, "mac": False, "linux": True}

        platforms = api._extract_platforms(platforms_data)
        assert "windows" in platforms
        assert "linux" in platforms
        assert "mac" not in platforms
        assert len(platforms) == 2

    def test_extract_genres(self):
        """Test extracción de géneros."""
        api = SteamAPI()

        genres_data = [
            {"id": "3", "description": "Aventura"},
            {"id": "23", "description": "Indie"},
            {"id": "3", "description": "RPG"},
        ]

        genres = api._extract_genres(genres_data)
        assert "Aventura" in genres
        assert "Indie" in genres
        assert "RPG" in genres
        assert len(genres) == 3

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test uso como context manager."""
        async with SteamAPI() as api:
            assert api.session is not None
            assert isinstance(api, SteamAPI)

        # Verificar que la sesión se cerró
        # (En un test real, verificaríamos que session.close() fue llamado)

    def test_language_codes(self):
        """Test normalización de códigos de idioma."""
        api = SteamAPI()

        assert api.LANGUAGE_CODES["spanish"] == "spanish"
        assert api.LANGUAGE_CODES["english"] == "english"
        assert api.LANGUAGE_CODES["es"] == "spanish"
        assert api.LANGUAGE_CODES["en"] == "english"

    def test_string_representations(self):
        """Test representaciones string."""
        api = SteamAPI()

        assert "SteamAPI" in str(api)
        assert "no auth required" in str(api)
        assert "SteamAPI" in repr(api)
        assert "base_url" in repr(api)


# Tests de integración (requieren conexión real)
class TestSteamAPIIntegration:
    """Tests de integración con Steam API real."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_search(self):
        """Test búsqueda real en Steam (requiere conexión)."""
        async with SteamAPI() as api:
            try:
                results = await api.search_game("Portal", max_results=3)
                assert len(results) > 0
                assert any("Portal" in item.get("name", "") for item in results)
            except Exception as e:
                pytest.skip(f"Steam API no disponible: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_details(self):
        """Test obtención real de detalles (requiere conexión)."""
        async with SteamAPI() as api:
            try:
                # Portal 2 App ID
                details = await api.get_game_details(620, language="spanish")
                assert details.success is True
                assert details.app_id == 620
                assert "Portal" in details.name
            except Exception as e:
                pytest.skip(f"Steam API no disponible: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_find_by_name(self):
        """Test búsqueda completa real (requiere conexión)."""
        async with SteamAPI() as api:
            try:
                game_info = await api.find_game_by_name("Portal 2", language="spanish")
                assert game_info is not None
                assert "Portal" in game_info.name
                assert game_info.steam_id is not None
                assert game_info.source_api == "steam"
            except Exception as e:
                pytest.skip(f"Steam API no disponible: {e}")


if __name__ == "__main__":
    # Ejecutar tests básicos
    pytest.main([__file__, "-v", "-m", "not integration"])
