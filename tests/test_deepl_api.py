"""
Tests unitarios para el conector DeepL API.
"""

from unittest.mock import Mock, patch

import pytest
from requests.exceptions import ConnectionError, Timeout

from game_lingo.apis.deepl_api import (
    DeepLAPIConnector,
    DeepLLanguage,
    DeepLUsage,
    TranslationResult,
    translate_game_description,
)
from game_lingo.exceptions import (
    APIError,
    AuthenticationError,
    RateLimitError,
    TranslationError,
    ValidationError,
)


class TestDeepLUsage:
    """Tests para la clase DeepLUsage."""

    def test_usage_percentage_calculation(self):
        """Test cálculo del porcentaje de uso."""
        usage = DeepLUsage(character_count=250000, character_limit=500000)
        assert usage.usage_percentage == 50.0

    def test_usage_percentage_zero_limit(self):
        """Test porcentaje cuando el límite es cero."""
        usage = DeepLUsage(character_count=1000, character_limit=0)
        assert usage.usage_percentage == 0.0

    def test_usage_percentage_full(self):
        """Test porcentaje cuando se alcanza el límite."""
        usage = DeepLUsage(character_count=500000, character_limit=500000)
        assert usage.usage_percentage == 100.0


class TestDeepLLanguage:
    """Tests para la clase DeepLLanguage."""

    def test_language_creation(self):
        """Test creación de objeto DeepLLanguage."""
        lang = DeepLLanguage(code="ES", name="Spanish", supports_formality=True)
        assert lang.code == "ES"
        assert lang.name == "Spanish"
        assert lang.supports_formality is True

    def test_language_default_formality(self):
        """Test valor por defecto de supports_formality."""
        lang = DeepLLanguage(code="EN", name="English")
        assert lang.supports_formality is False


class TestTranslationResult:
    """Tests para la clase TranslationResult."""

    def test_translation_result_creation(self):
        """Test creación de resultado de traducción."""
        result = TranslationResult(
            text="Hola mundo",
            detected_source_language="EN",
            source_language="EN",
            target_language="ES",
        )
        assert result.text == "Hola mundo"
        assert result.detected_source_language == "EN"
        assert result.source_language == "EN"
        assert result.target_language == "ES"


class TestDeepLAPIConnector:
    """Tests para la clase DeepLAPIConnector."""

    @pytest.fixture
    def mock_settings(self):
        """Mock de configuraciones."""
        with patch("game_lingo.apis.deepl_api.settings") as mock:
            mock.DEEPL_API_KEY = "test_api_key"
            mock.DEEPL_IS_PRO = False
            mock.TRANSLATION_TIMEOUT_SECONDS = 30
            mock.DEEPL_REQUESTS_PER_SECOND = 5
            mock.API_MAX_RETRIES = 3
            mock.API_RETRY_BACKOFF = 1
            mock.VERSION = "1.0.0"
            yield mock

    @pytest.fixture
    def connector(self, mock_settings):
        """Fixture del conector DeepL."""
        with patch("game_lingo.apis.deepl_api.DeepLAPIConnector._create_session"):
            return DeepLAPIConnector(api_key="test_key")

    def test_init_with_api_key(self, mock_settings):
        """Test inicialización con API key."""
        with patch("game_lingo.apis.deepl_api.DeepLAPIConnector._create_session"):
            connector = DeepLAPIConnector(api_key="custom_key")
            assert connector.api_key == "custom_key"
            assert connector.base_url == "https://api-free.deepl.com/v2"

    def test_init_pro_account(self, mock_settings):
        """Test inicialización con cuenta Pro."""
        with patch("game_lingo.apis.deepl_api.DeepLAPIConnector._create_session"):
            connector = DeepLAPIConnector(api_key="pro_key", is_pro=True)
            assert connector.base_url == "https://api.deepl.com/v2"

    def test_init_without_api_key(self, mock_settings):
        """Test inicialización sin API key."""
        mock_settings.DEEPL_API_KEY = ""
        with pytest.raises(AuthenticationError) as exc_info:
            DeepLAPIConnector()
        assert "DeepL API key is required" in str(exc_info.value)

    def test_context_manager(self, connector):
        """Test uso como context manager."""
        connector.session = Mock()

        with connector as ctx:
            assert ctx is connector

        connector.session.close.assert_called_once()

    @patch("time.sleep")
    @patch("time.time")
    def test_rate_limiting(self, mock_time, mock_sleep, connector):
        """Test rate limiting."""
        # time.time() se llama 2 veces: al inicio y al final
        mock_time.side_effect = [0.1, 0.3]  # current_time = 0.1, luego 0.3
        connector._last_request_time = 0  # last_request_time = 0
        connector._min_request_interval = 0.2  # min_interval = 0.2

        connector._rate_limit()

        # time_since_last = 0.1 - 0 = 0.1
        # sleep_time = 0.2 - 0.1 = 0.1 (pero el sleep real es 0.2)
        mock_sleep.assert_called_once_with(0.2 - 0.1)

    def test_handle_response_errors_success(self, connector):
        """Test manejo de respuesta exitosa."""
        response = Mock()
        response.status_code = 200

        # No debería lanzar excepción
        connector._handle_response_errors(response)

    def test_handle_response_errors_401(self, connector):
        """Test manejo de error 401."""
        response = Mock()
        response.status_code = 401
        response.json.return_value = {"message": "Invalid API key"}

        with pytest.raises(AuthenticationError) as exc_info:
            connector._handle_response_errors(response)
        assert "Invalid API key" in str(exc_info.value)

    def test_handle_response_errors_429(self, connector):
        """Test manejo de error 429 (rate limit)."""
        response = Mock()
        response.status_code = 429
        response.headers = {"Retry-After": "120"}
        response.json.return_value = {"message": "Rate limit exceeded"}

        with pytest.raises(RateLimitError) as exc_info:
            connector._handle_response_errors(response)
        assert exc_info.value.retry_after == 120

    def test_handle_response_errors_456(self, connector):
        """Test manejo de error 456 (quota exceeded)."""
        response = Mock()
        response.status_code = 456
        response.json.return_value = {"message": "Quota exceeded"}

        with pytest.raises(TranslationError) as exc_info:
            connector._handle_response_errors(response)
        assert "Quota exceeded" in str(exc_info.value)

    def test_make_request_timeout(self, connector):
        """Test timeout en petición."""
        connector.session = Mock()
        connector.session.post.side_effect = Timeout()

        with pytest.raises(APIError) as exc_info:
            connector._make_request("translate", {"text": "test"})
        assert "Request timeout" in str(exc_info.value)

    def test_make_request_connection_error(self, connector):
        """Test error de conexión."""
        connector.session = Mock()
        connector.session.post.side_effect = ConnectionError("Connection failed")

        with pytest.raises(APIError) as exc_info:
            connector._make_request("translate", {"text": "test"})
        assert "Connection error" in str(exc_info.value)

    def test_get_usage_success(self, connector):
        """Test obtener información de uso exitosamente."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "character_count": 150000,
            "character_limit": 500000,
        }

        connector._make_request = Mock(return_value=mock_response)

        usage = connector.get_usage()

        assert isinstance(usage, DeepLUsage)
        assert usage.character_count == 150000
        assert usage.character_limit == 500000
        connector._make_request.assert_called_once_with("usage", method="GET")

    def test_get_supported_languages_success(self, connector):
        """Test obtener idiomas soportados exitosamente."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {"language": "ES", "name": "Spanish", "supports_formality": True},
            {"language": "EN", "name": "English", "supports_formality": False},
        ]

        connector._make_request = Mock(return_value=mock_response)

        languages = connector.get_supported_languages("target")

        assert len(languages) == 2
        assert all(isinstance(lang, DeepLLanguage) for lang in languages)
        assert languages[0].code == "ES"
        assert languages[0].supports_formality is True
        connector._make_request.assert_called_once_with(
            "languages",
            data={"type": "target"},
        )

    def test_get_supported_languages_invalid_type(self, connector):
        """Test obtener idiomas con tipo inválido."""
        with pytest.raises(ValidationError) as exc_info:
            connector.get_supported_languages("invalid")
        assert "Invalid language type" in str(exc_info.value)

    def test_translate_text_success(self, connector):
        """Test traducción exitosa."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "translations": [{"text": "Hola mundo", "detected_source_language": "EN"}],
        }

        connector._make_request = Mock(return_value=mock_response)

        result = connector.translate_text("Hello world", "ES")

        assert isinstance(result, TranslationResult)
        assert result.text == "Hola mundo"
        assert result.detected_source_language == "EN"
        assert result.target_language == "ES"

    def test_translate_text_empty_text(self, connector):
        """Test traducción con texto vacío."""
        with pytest.raises(ValidationError) as exc_info:
            connector.translate_text("", "ES")
        assert "Text to translate cannot be empty" in str(exc_info.value)

    def test_translate_text_no_target_language(self, connector):
        """Test traducción sin idioma de destino."""
        with pytest.raises(ValidationError) as exc_info:
            connector.translate_text("Hello", "")
        assert "Target language is required" in str(exc_info.value)

    def test_translate_text_invalid_formality(self, connector):
        """Test traducción con formalidad inválida."""
        with pytest.raises(ValidationError) as exc_info:
            connector.translate_text("Hello", "ES", formality="invalid")
        assert "Invalid formality" in str(exc_info.value)

    def test_translate_text_no_translation_returned(self, connector):
        """Test cuando la API no retorna traducción."""
        mock_response = Mock()
        mock_response.json.return_value = {"translations": []}

        connector._make_request = Mock(return_value=mock_response)

        with pytest.raises(TranslationError) as exc_info:
            connector.translate_text("Hello", "ES")
        assert "No translation returned" in str(exc_info.value)

    def test_translate_game_description_success(self, connector):
        """Test traducción de descripción de juego exitosa."""
        connector.translate_text = Mock(
            return_value=TranslationResult(
                text="Descripción traducida",
                target_language="ES",
            ),
        )

        result = connector.translate_game_description("Game description")

        assert result == "Descripción traducida"
        connector.translate_text.assert_called_once_with(
            text="Game description",
            target_language="ES",
            preserve_formatting=True,
        )

    def test_translate_game_description_empty(self, connector):
        """Test traducción de descripción vacía."""
        with pytest.raises(ValidationError) as exc_info:
            connector.translate_game_description("")
        assert "Game description cannot be empty" in str(exc_info.value)


class TestConvenienceFunctions:
    """Tests para funciones de conveniencia."""

    @patch("game_lingo.apis.deepl_api.DeepLAPIConnector")
    def test_translate_game_description_function(self, mock_connector_class):
        """Test función de conveniencia para traducir descripción."""
        mock_connector = Mock()
        mock_connector.translate_game_description.return_value = "Descripción traducida"
        mock_connector_class.return_value.__enter__.return_value = mock_connector

        result = translate_game_description("Game description", "ES", "test_key")

        assert result == "Descripción traducida"
        mock_connector_class.assert_called_once_with(api_key="test_key")
        mock_connector.translate_game_description.assert_called_once_with(
            "Game description",
            "ES",
        )


@pytest.mark.integration
class TestDeepLAPIIntegration:
    """Tests de integración para DeepL API (requieren API key real)."""

    @pytest.fixture
    def real_connector(self):
        """Conector real para tests de integración."""
        import os

        api_key = os.getenv("DEEPL_API_KEY")
        if not api_key:
            pytest.skip("DEEPL_API_KEY not set")
        return DeepLAPIConnector(api_key=api_key)

    def test_real_get_usage(self, real_connector):
        """Test obtener uso real de la API."""
        usage = real_connector.get_usage()
        assert isinstance(usage, DeepLUsage)
        assert usage.character_count >= 0
        assert usage.character_limit > 0

    def test_real_get_supported_languages(self, real_connector):
        """Test obtener idiomas soportados reales."""
        languages = real_connector.get_supported_languages("target")
        assert len(languages) > 0
        assert any(lang.code == "ES" for lang in languages)

    def test_real_translate_text(self, real_connector):
        """Test traducción real."""
        result = real_connector.translate_text("Hello world", "ES")
        assert isinstance(result, TranslationResult)
        assert result.text.lower() in ["hola mundo", "hola, mundo"]
        assert result.target_language == "ES"

    def test_real_translate_game_description(self, real_connector):
        """Test traducción real de descripción de juego."""
        description = (
            "An epic adventure game with stunning graphics and immersive gameplay."
        )
        result = real_connector.translate_game_description(description, "ES")
        assert isinstance(result, str)
        assert len(result) > 0
        assert result != description  # Debería ser diferente al original
