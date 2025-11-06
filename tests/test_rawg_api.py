"""
Tests unitarios para RAWG API Connector.

Incluye tests para:
- Búsqueda de juegos
- Obtención de detalles
- Manejo de errores
- Rate limiting
- Conversión de datos
"""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from aiohttp import ClientResponse

from game_lingo.apis.rawg_api import RAWGAPIConnector, RAWGResponse
from game_lingo.exceptions import (
    APIError,
    AuthenticationError,
    GameNotFoundError,
    RateLimitError,
    ValidationError,
)
from game_lingo.models import GameInfo, Platform


class TestRAWGResponse:
    """Tests para RAWGResponse."""

    def test_rawg_response_with_results(self):
        """Test RAWGResponse con resultados."""
        data = {
            "count": 100,
            "results": [
                {"id": 1, "name": "Test Game 1"},
                {"id": 2, "name": "Test Game 2"},
            ],
        }

        response = RAWGResponse(data)

        assert response.count == 100
        assert len(response.results) == 2
        assert response.has_results is True
        assert response.results[0]["name"] == "Test Game 1"

    def test_rawg_response_empty(self):
        """Test RAWGResponse sin resultados."""
        data = {"count": 0, "results": []}

        response = RAWGResponse(data)

        assert response.count == 0
        assert len(response.results) == 0
        assert response.has_results is False

    def test_rawg_response_missing_fields(self):
        """Test RAWGResponse con campos faltantes."""
        data = {}

        response = RAWGResponse(data)

        assert response.count == 0
        assert response.results == []
        assert response.has_results is False


class TestRAWGAPIConnector:
    """Tests para RAWGAPIConnector."""

    @pytest.fixture
    def mock_session(self):
        """Mock de aiohttp.ClientSession."""
        session = AsyncMock(spec=aiohttp.ClientSession)
        return session

    @pytest.fixture
    def connector(self, mock_session):
        """Conector RAWG con sesión mock."""
        with patch("game_lingo.apis.rawg_api.settings") as mock_settings:
            mock_settings.RAWG_API_KEY = "test_api_key"
            mock_settings.RAWG_BASE_URL = "https://api.rawg.io/api"
            mock_settings.API_TIMEOUT_SECONDS = 30
            mock_settings.MAX_RETRIES = 3

            # Crear un mock para el rate_limiter
            mock_rate_limiter = AsyncMock()
            mock_rate_limiter.wait_if_needed = AsyncMock()

            connector = RAWGAPIConnector(
                api_key="test_api_key", rate_limiter=mock_rate_limiter
            )
            connector.session = mock_session
            return connector

    def test_init_without_api_key(self):
        """Test inicialización sin API key."""
        with patch("game_lingo.apis.rawg_api.settings") as mock_settings:
            mock_settings.RAWG_API_KEY = ""

            with pytest.raises(AuthenticationError) as exc_info:
                RAWGAPIConnector()

            assert "RAWG API key is required" in str(exc_info.value)
            assert exc_info.value.api_name == "rawg"

    def test_init_with_api_key(self):
        """Test inicialización con API key."""
        with patch("game_lingo.apis.rawg_api.settings") as mock_settings:
            mock_settings.RAWG_BASE_URL = "https://api.rawg.io/api"

            connector = RAWGAPIConnector(api_key="test_key")

            assert connector.api_key == "test_key"
            assert connector.base_url == "https://api.rawg.io/api"

    @pytest.mark.asyncio
    async def test_search_game_success(self, connector, mock_session):
        """Test búsqueda exitosa de juegos."""
        # Mock response
        mock_response = AsyncMock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.json.return_value = {
            "count": 1,
            "results": [
                {
                    "id": 3498,
                    "name": "Grand Theft Auto V",
                    "rating": 4.47,
                    "released": "2013-09-17",
                },
            ],
        }

        mock_session.get.return_value.__aenter__.return_value = mock_response

        # Ejecutar la búsqueda (el rate_limiter ya está mockeado en el fixture)
        result = await connector.search_game("GTA V")

        # Verificar que se llamó al rate limiter
        connector.rate_limiter.wait_if_needed.assert_called_once_with("rawg")

        # Verificaciones
        assert isinstance(result, RAWGResponse)
        assert result.count == 1
        assert result.has_results is True
        assert result.results[0]["name"] == "Grand Theft Auto V"

        # Verificar llamada a la API
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert call_args[1]["params"]["search"] == "GTA V"
        assert call_args[1]["params"]["key"] == "test_api_key"

    @pytest.mark.asyncio
    async def test_search_game_not_found(self, connector, mock_session):
        """Test búsqueda sin resultados."""
        # Mock response vacía
        mock_response = AsyncMock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.json.return_value = {"count": 0, "results": []}

        mock_session.get.return_value.__aenter__.return_value = mock_response

        # Mock rate limiter
        with patch.object(connector.rate_limiter, "acquire", new_callable=AsyncMock):
            with pytest.raises(GameNotFoundError) as exc_info:
                await connector.search_game("NonexistentGame")

        assert "No games found for 'NonexistentGame' in RAWG" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_game_validation_error(self, connector):
        """Test validación de parámetros de búsqueda."""
        # Query vacío
        with pytest.raises(ValidationError) as exc_info:
            await connector.search_game("")
        assert "Search query cannot be empty" in str(exc_info.value)

        # Limit inválido
        with pytest.raises(ValidationError) as exc_info:
            await connector.search_game("test", limit=0)
        assert "Limit must be between 1 and 40" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            await connector.search_game("test", limit=50)
        assert "Limit must be between 1 and 40" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_game_api_error(self, connector, mock_session):
        """Test manejo de errores de API."""
        # Mock error de conexión
        mock_session.get.side_effect = aiohttp.ClientError("Connection failed")

        with patch.object(connector.rate_limiter, "acquire", new_callable=AsyncMock):
            with pytest.raises(APIError) as exc_info:
                await connector.search_game("test")

        assert "RAWG API request failed" in str(exc_info.value)
        assert exc_info.value.api_name == "rawg"

    @pytest.mark.asyncio
    async def test_get_game_details_success(self, connector, mock_session):
        """Test obtención exitosa de detalles."""
        # Mock response
        mock_response = AsyncMock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.json.return_value = {
            "id": 3498,
            "name": "Grand Theft Auto V",
            "description_raw": "An action-adventure game...",
            "rating": 4.47,
            "released": "2013-09-17",
            "platforms": [
                {"platform": {"name": "PC"}},
                {"platform": {"name": "PlayStation 4"}},
            ],
            "genres": [{"name": "Action"}, {"name": "Adventure"}],
            "developers": [{"name": "Rockstar North"}],
            "publishers": [{"name": "Rockstar Games"}],
        }

        mock_session.get.return_value.__aenter__.return_value = mock_response

        # Mock rate limiter
        with patch.object(connector.rate_limiter, "acquire", new_callable=AsyncMock):
            result = await connector.get_game_details(3498)

        # Verificaciones
        assert result["id"] == 3498
        assert result["name"] == "Grand Theft Auto V"
        assert "description_raw" in result

        # Verificar llamada a la API
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "3498" in call_args[0][0]  # URL contiene el ID
        assert call_args[1]["params"]["key"] == "test_api_key"

    @pytest.mark.asyncio
    async def test_get_game_details_validation_error(self, connector):
        """Test validación de parámetros de detalles."""
        # ID inválido
        with pytest.raises(ValidationError) as exc_info:
            await connector.get_game_details(0)
        assert "Game ID must be a positive integer" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            await connector.get_game_details(-1)
        assert "Game ID must be a positive integer" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_find_game_by_name_success(self, connector, mock_session):
        """Test búsqueda por nombre exitosa."""
        # Mock search response
        search_response = AsyncMock(spec=ClientResponse)
        search_response.status = 200
        search_response.json.return_value = {
            "count": 1,
            "results": [{"id": 3498, "name": "Grand Theft Auto V", "rating": 4.47}],
        }

        # Mock details response
        details_response = AsyncMock(spec=ClientResponse)
        details_response.status = 200
        details_response.json.return_value = {
            "id": 3498,
            "name": "Grand Theft Auto V",
            "description_raw": "An action-adventure game set in Los Santos...",
            "rating": 4.47,
            "released": "2013-09-17",
            "platforms": [{"platform": {"name": "PC"}}],
            "genres": [{"name": "Action"}],
            "developers": [{"name": "Rockstar North"}],
            "publishers": [{"name": "Rockstar Games"}],
            "short_screenshots": [{"image": "https://example.com/screenshot1.jpg"}],
        }

        # Configurar mocks para llamadas secuenciales
        mock_session.get.return_value.__aenter__.side_effect = [
            search_response,
            details_response,
        ]

        # Mock rate limiter
        with patch.object(connector.rate_limiter, "acquire", new_callable=AsyncMock):
            result = await connector.find_game_by_name("Grand Theft Auto V")

        # Verificaciones
        assert isinstance(result, GameInfo)
        assert result.name == "Grand Theft Auto V"
        assert result.source_api == "rawg"
        assert result.rawg_id == 3498
        assert any(
            p.lower() == "pc" for p in result.platforms
        )  # Verificar que 'pc' está en las plataformas (case-insensitive)
        assert result.genres == ["Action"]
        assert result.developer == "Rockstar North"
        assert result.publisher == "Rockstar Games"
        assert (
            result.short_description_en
            == "An action-adventure game set in Los Santos..."
        )
        assert result.screenshots == ["https://example.com/screenshot1.jpg"]

    @pytest.mark.asyncio
    async def test_find_game_by_name_not_found(self, connector, mock_session):
        """Test búsqueda por nombre sin resultados."""
        # Mock empty search response
        mock_response = AsyncMock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.json.return_value = {"count": 0, "results": []}

        mock_session.get.return_value.__aenter__.return_value = mock_response

        # Mock rate limiter
        with patch.object(connector.rate_limiter, "acquire", new_callable=AsyncMock):
            result = await connector.find_game_by_name("NonexistentGame")

        assert result is None

    def test_convert_to_game_info(self, connector):
        """Test conversión de datos RAWG a GameInfo."""
        rawg_data = {
            "id": 3498,
            "name": "Grand Theft Auto V",
            "description_raw": "An action-adventure game...",
            "rating": 4.47,
            "released": "2013-09-17",
            "platforms": [
                {"platform": {"name": "PC"}},
                {"platform": {"name": "PlayStation 4"}},
            ],
            "genres": [{"name": "Action"}, {"name": "Adventure"}],
            "developers": [{"name": "Rockstar North"}],
            "publishers": [{"name": "Rockstar Games"}],
            "metacritic": 97,
            "short_screenshots": [
                {"image": "https://example.com/screenshot1.jpg"},
                {"image": "https://example.com/screenshot2.jpg"},
            ],
        }

        result = connector._convert_to_game_info(rawg_data)

        assert isinstance(result, GameInfo)
        assert result.name == "Grand Theft Auto V"
        assert result.short_description_en == "An action-adventure game..."
        assert result.user_score == 4.47 * 2  # Convert from 5-point to 10-point scale
        assert result.release_date.year == 2013
        assert result.release_date.month == 9
        assert result.release_date.day == 17
        assert len(result.platforms) == 2
        assert any(p.value == "pc" for p in result.platforms)
        assert any(p.value == "ps4" for p in result.platforms)
        assert set(result.genres) == {"Action", "Adventure"}
        assert result.developer == "Rockstar North"
        assert result.publisher == "Rockstar Games"
        assert result.metacritic_score == 97
        assert len(result.screenshots) == 2
        assert result.source_api == "rawg"

    def test_clean_html(self, connector):
        """Test limpieza de HTML."""
        # Texto con HTML
        html_text = "<p>This is a <strong>test</strong> with &amp; entities.</p>"
        cleaned = connector._clean_html(html_text)
        assert cleaned == "This is a test with & entities."

        # Texto sin HTML
        plain_text = "This is plain text."
        cleaned = connector._clean_html(plain_text)
        assert cleaned == "This is plain text."

        # Texto vacío
        cleaned = connector._clean_html("")
        assert cleaned == ""

        # None
        cleaned = connector._clean_html(None)
        assert cleaned == ""

    @pytest.mark.asyncio
    async def test_handle_response_errors(self, connector):
        """Test manejo de errores de respuesta."""
        # Rate limit error
        response = AsyncMock(spec=ClientResponse)
        response.status = 429
        response.headers = {"Retry-After": "60"}

        with pytest.raises(RateLimitError) as exc_info:
            await connector._handle_response_errors(response)
        assert exc_info.value.api_name == "rawg"
        assert exc_info.value.retry_after == 60

        # Authentication error
        response.status = 401
        with pytest.raises(AuthenticationError) as exc_info:
            await connector._handle_response_errors(response)
        assert exc_info.value.api_name == "rawg"

        # Forbidden error
        response.status = 403
        with pytest.raises(APIError) as exc_info:
            await connector._handle_response_errors(response)
        assert exc_info.value.api_name == "rawg"
        assert exc_info.value.status_code == 403

        # Not found error
        response.status = 404
        with pytest.raises(GameNotFoundError):
            await connector._handle_response_errors(response)

        # Server error
        response.status = 500
        with pytest.raises(APIError) as exc_info:
            await connector._handle_response_errors(response)
        assert exc_info.value.api_name == "rawg"
        assert exc_info.value.status_code == 500

        # Client error
        response.status = 400
        response.text.return_value = "Bad request"
        with pytest.raises(APIError) as exc_info:
            await connector._handle_response_errors(response)
        assert exc_info.value.api_name == "rawg"
        assert exc_info.value.status_code == 400


@pytest.mark.integration
class TestRAWGAPIIntegration:
    """Tests de integración para RAWG API (requieren API key real)."""

    @pytest.mark.asyncio
    async def test_real_search(self):
        """Test de búsqueda real (requiere RAWG_API_KEY)."""
        import os

        api_key = os.getenv("RAWG_API_KEY")

        if not api_key:
            pytest.skip("RAWG_API_KEY not configured")

        async with RAWGAPIConnector(api_key) as connector:
            result = await connector.search_game("The Witcher 3")

            assert result.has_results
            assert any("witcher" in game["name"].lower() for game in result.results)

    @pytest.mark.asyncio
    async def test_real_game_details(self):
        """Test de detalles reales (requiere RAWG_API_KEY)."""
        import os

        api_key = os.getenv("RAWG_API_KEY")

        if not api_key:
            pytest.skip("RAWG_API_KEY not configured")

        async with RAWGAPIConnector(api_key) as connector:
            # The Witcher 3: Wild Hunt ID en RAWG
            details = await connector.get_game_details(3328)

            assert details["id"] == 3328
            assert "witcher" in details["name"].lower()
            assert "description_raw" in details or "description" in details

    @pytest.mark.asyncio
    async def test_real_find_by_name(self):
        """Test de búsqueda por nombre real (requiere RAWG_API_KEY)."""
        import os

        api_key = os.getenv("RAWG_API_KEY")

        if not api_key:
            pytest.skip("RAWG_API_KEY not configured")

        async with RAWGAPIConnector(api_key) as connector:
            game_info = await connector.find_game_by_name("Cyberpunk 2077")

            assert game_info is not None
            assert isinstance(game_info, GameInfo)
            assert "cyberpunk" in game_info.name.lower()
            assert game_info.source_api == "rawg"
