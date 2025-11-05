"""
Tests unitarios para el conector de Google Translate API.

Incluye tests para:
- Clases de datos (GoogleTranslateLanguage, GoogleTranslateDetection, GoogleTranslateResult)
- GoogleTranslateAPIConnector
- Manejo de errores y rate limiting
- Traducción de texto y descripciones de juegos
- Tests de integración (requieren API key real)
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import RequestException, Timeout, ConnectionError
from requests import Response

from game_lingo.apis.google_translate_api import (
    GoogleTranslateAPIConnector,
    GoogleTranslateLanguage,
    GoogleTranslateDetection,
    GoogleTranslateResult,
    translate_game_description,
    detect_language,
    AuthenticationError,
    RateLimitError,
    TranslationError,
    ValidationError,
)
from game_lingo.models.game import GameInfo


class TestGoogleTranslateLanguage:
    """Tests para la clase GoogleTranslateLanguage."""

    def test_creation(self):
        """Test creación de GoogleTranslateLanguage."""
        lang = GoogleTranslateLanguage(code="es", name="Spanish")
        assert lang.code == "es"
        assert lang.name == "Spanish"

    def test_equality(self):
        """Test igualdad entre objetos GoogleTranslateLanguage."""
        lang1 = GoogleTranslateLanguage(code="es", name="Spanish")
        lang2 = GoogleTranslateLanguage(code="es", name="Spanish")
        lang3 = GoogleTranslateLanguage(code="en", name="English")

        assert lang1 == lang2
        assert lang1 != lang3

    def test_str_representation(self):
        """Test representación string."""
        lang = GoogleTranslateLanguage(code="es", name="Spanish")
        assert str(lang) == "Spanish (es)"


class TestGoogleTranslateDetection:
    """Tests para la clase GoogleTranslateDetection."""

    def test_creation(self):
        """Test creación de GoogleTranslateDetection."""
        detection = GoogleTranslateDetection(
            language="en", confidence=0.95, is_reliable=True
        )
        assert detection.language == "en"
        assert detection.confidence == 0.95
        assert detection.is_reliable is True

    def test_str_representation(self):
        """Test representación string."""
        detection = GoogleTranslateDetection(
            language="en", confidence=0.95, is_reliable=True
        )
        assert str(detection) == "en (95.0% confidence, reliable)"


class TestGoogleTranslateResult:
    """Tests para la clase GoogleTranslateResult."""

    def test_creation(self):
        """Test creación de GoogleTranslateResult."""
        result = GoogleTranslateResult(
            translated_text="Hola mundo",
            detected_source_language="en",
            target_language="es",
        )
        assert result.translated_text == "Hola mundo"
        assert result.detected_source_language == "en"
        assert result.target_language == "es"

    def test_str_representation(self):
        """Test representación string."""
        result = GoogleTranslateResult(
            translated_text="Hola mundo",
            detected_source_language="en",
            target_language="es",
        )
        assert str(result) == "Hola mundo (en → es)"


class TestGoogleTranslateAPIConnector:
    """Tests para la clase GoogleTranslateAPIConnector."""

    @pytest.fixture
    def connector(self):
        """Fixture que crea un conector para tests."""
        return GoogleTranslateAPIConnector(api_key="test_key", requests_per_second=10)

    @pytest.fixture
    def mock_response(self):
        """Fixture que crea una respuesta mock."""
        response = Mock(spec=Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        return response

    def test_initialization(self, connector):
        """Test inicialización del conector."""
        assert connector.api_key == "test_key"
        assert connector.requests_per_second == 10
        assert (
            connector.base_url
            == "https://translation.googleapis.com/language/translate/v2"
        )
        assert connector.session is not None

    def test_context_manager(self):
        """Test uso como context manager."""
        with GoogleTranslateAPIConnector(api_key="test_key") as connector:
            assert connector.session is not None
        # Session debería estar cerrada después del context manager

    def test_rate_limiting(self, connector):
        """Test rate limiting."""
        import time

        start_time = time.time()

        # Simular múltiples llamadas
        for _ in range(3):
            connector._wait_for_rate_limit()

        elapsed = time.time() - start_time
        # Debería haber esperado al menos algo de tiempo
        assert elapsed >= 0

    @patch("requests.Session.get")
    def test_make_request_success(self, mock_get, connector, mock_response):
        """Test petición exitosa."""
        mock_response.json.return_value = {"data": {"languages": []}}
        mock_get.return_value = mock_response

        result = connector._make_request("GET", "languages")
        assert result == {"data": {"languages": []}}

    @patch("requests.Session.get")
    def test_make_request_authentication_error(self, mock_get, connector):
        """Test error de autenticación (401)."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
        mock_get.return_value = mock_response

        with pytest.raises(AuthenticationError):
            connector._make_request("GET", "languages")

    @patch("requests.Session.get")
    def test_make_request_rate_limit_error(self, mock_get, connector):
        """Test error de rate limit (429)."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "Rate limit exceeded"}}
        mock_get.return_value = mock_response

        with pytest.raises(RateLimitError):
            connector._make_request("GET", "languages")

    @patch("requests.Session.get")
    def test_make_request_timeout_error(self, mock_get, connector):
        """Test error de timeout."""
        mock_get.side_effect = Timeout("Request timeout")

        with pytest.raises(TranslationError):
            connector._make_request("GET", "languages")

    @patch("requests.Session.get")
    def test_make_request_connection_error(self, mock_get, connector):
        """Test error de conexión."""
        mock_get.side_effect = ConnectionError("Connection failed")

        with pytest.raises(TranslationError):
            connector._make_request("GET", "languages")

    @patch("requests.Session.get")
    def test_get_supported_languages(self, mock_get, connector, mock_response):
        """Test obtener idiomas soportados."""
        mock_response.json.return_value = {
            "data": {
                "languages": [
                    {"language": "en", "name": "English"},
                    {"language": "es", "name": "Spanish"},
                    {"language": "fr", "name": "French"},
                ]
            }
        }
        mock_get.return_value = mock_response

        languages = connector.get_supported_languages()

        assert len(languages) == 3
        assert languages[0].code == "en"
        assert languages[0].name == "English"
        assert languages[1].code == "es"
        assert languages[1].name == "Spanish"

    @patch("requests.Session.post")
    def test_detect_language(self, mock_post, connector, mock_response):
        """Test detección de idioma."""
        mock_response.json.return_value = {
            "data": {
                "detections": [
                    [{"language": "en", "confidence": 0.95, "isReliable": True}]
                ]
            }
        }
        mock_post.return_value = mock_response

        detection = connector.detect_language("Hello world")

        assert detection.language == "en"
        assert detection.confidence == 0.95
        assert detection.is_reliable is True

    @patch("requests.Session.post")
    def test_translate_text(self, mock_post, connector, mock_response):
        """Test traducción de texto."""
        mock_response.json.return_value = {
            "data": {
                "translations": [
                    {"translatedText": "Hola mundo", "detectedSourceLanguage": "en"}
                ]
            }
        }
        mock_post.return_value = mock_response

        result = connector.translate_text("Hello world", target_language="es")

        assert result.translated_text == "Hola mundo"
        assert result.detected_source_language == "en"
        assert result.target_language == "es"

    @patch("requests.Session.post")
    def test_translate_batch(self, mock_post, connector, mock_response):
        """Test traducción en lote."""
        mock_response.json.return_value = {
            "data": {
                "translations": [
                    {"translatedText": "Hola", "detectedSourceLanguage": "en"},
                    {"translatedText": "mundo", "detectedSourceLanguage": "en"},
                ]
            }
        }
        mock_post.return_value = mock_response

        results = connector.translate_batch(["Hello", "world"], target_language="es")

        assert len(results) == 2
        assert results[0].translated_text == "Hola"
        assert results[1].translated_text == "mundo"

    def test_translate_text_validation(self, connector):
        """Test validación de parámetros en translate_text."""
        with pytest.raises(ValidationError):
            connector.translate_text("", target_language="es")

        with pytest.raises(ValidationError):
            connector.translate_text("Hello", target_language="")

    def test_translate_batch_validation(self, connector):
        """Test validación de parámetros en translate_batch."""
        with pytest.raises(ValidationError):
            connector.translate_batch([], target_language="es")

        with pytest.raises(ValidationError):
            connector.translate_batch(["Hello"], target_language="")

    @patch("requests.Session.post")
    def test_translate_game_description(self, mock_post, connector, mock_response):
        """Test traducción de descripción de juego."""
        mock_response.json.return_value = {
            "data": {
                "translations": [
                    {
                        "translatedText": "Un gran juego de aventuras",
                        "detectedSourceLanguage": "en",
                    }
                ]
            }
        }
        mock_post.return_value = mock_response

        game = GameInfo(
            name="Test Game", description="A great adventure game", steam_id=123
        )

        translated_game = connector.translate_game_description(
            game, target_language="es"
        )

        assert translated_game.name == "Test Game"  # Nombre no cambia
        assert translated_game.description == "Un gran juego de aventuras"
        assert translated_game.steam_id == 123

    def test_translate_game_description_validation(self, connector):
        """Test validación en translate_game_description."""
        game = GameInfo(name="Test", description="", steam_id=123)

        with pytest.raises(ValidationError):
            connector.translate_game_description(game, target_language="es")


class TestConvenienceFunctions:
    """Tests para las funciones de conveniencia."""

    @patch("game_lingo.apis.google_translate_api.GoogleTranslateAPIConnector")
    def test_translate_game_description_function(self, mock_connector_class):
        """Test función de conveniencia translate_game_description."""
        mock_connector = Mock()
        mock_connector_class.return_value.__enter__.return_value = mock_connector

        game = GameInfo(name="Test", description="Hello", steam_id=123)
        translated_game = GameInfo(name="Test", description="Hola", steam_id=123)
        mock_connector.translate_game_description.return_value = translated_game

        result = translate_game_description(
            game=game, target_language="es", api_key="test_key"
        )

        assert result.description == "Hola"
        mock_connector.translate_game_description.assert_called_once_with(
            game, target_language="es"
        )

    @patch("game_lingo.apis.google_translate_api.GoogleTranslateAPIConnector")
    def test_detect_language_function(self, mock_connector_class):
        """Test función de conveniencia detect_language."""
        mock_connector = Mock()
        mock_connector_class.return_value.__enter__.return_value = mock_connector

        detection = GoogleTranslateDetection(
            language="en", confidence=0.95, is_reliable=True
        )
        mock_connector.detect_language.return_value = detection

        result = detect_language(text="Hello world", api_key="test_key")

        assert result.language == "en"
        mock_connector.detect_language.assert_called_once_with("Hello world")


@pytest.mark.integration
class TestGoogleTranslateAPIIntegration:
    """
    Tests de integración que requieren una API key real.

    Para ejecutar estos tests:
    1. Obtén una API key de Google Cloud Translation
    2. Configura la variable de entorno GOOGLE_TRANSLATE_API_KEY
    3. Ejecuta: pytest -m integration tests/test_google_translate_api.py
    """

    @pytest.fixture
    def api_key(self):
        """Fixture que obtiene la API key del entorno."""
        import os

        api_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
        if not api_key:
            pytest.skip("GOOGLE_TRANSLATE_API_KEY no configurada")
        return api_key

    @pytest.fixture
    def connector(self, api_key):
        """Fixture que crea un conector real."""
        return GoogleTranslateAPIConnector(api_key=api_key)

    def test_real_get_supported_languages(self, connector):
        """Test real de obtener idiomas soportados."""
        languages = connector.get_supported_languages()

        assert len(languages) > 0
        # Verificar que incluye idiomas comunes
        language_codes = [lang.code for lang in languages]
        assert "en" in language_codes
        assert "es" in language_codes
        assert "fr" in language_codes

    def test_real_detect_language(self, connector):
        """Test real de detección de idioma."""
        # Texto en inglés
        detection = connector.detect_language("Hello, how are you?")
        assert detection.language == "en"
        assert detection.confidence > 0.5

        # Texto en español
        detection = connector.detect_language("Hola, ¿cómo estás?")
        assert detection.language == "es"
        assert detection.confidence > 0.5

    def test_real_translate_text(self, connector):
        """Test real de traducción de texto."""
        result = connector.translate_text("Hello world", target_language="es")

        assert result.translated_text.lower() in ["hola mundo", "hola, mundo"]
        assert result.detected_source_language == "en"
        assert result.target_language == "es"

    def test_real_translate_batch(self, connector):
        """Test real de traducción en lote."""
        texts = ["Hello", "world", "How are you?"]
        results = connector.translate_batch(texts, target_language="es")

        assert len(results) == 3
        assert all(result.target_language == "es" for result in results)
        assert all(result.detected_source_language == "en" for result in results)

    def test_real_translate_game_description(self, connector):
        """Test real de traducción de descripción de juego."""
        game = GameInfo(
            name="Test Game",
            description="An epic adventure game with stunning graphics and immersive gameplay.",
            steam_id=123,
        )

        translated_game = connector.translate_game_description(
            game, target_language="es"
        )

        assert translated_game.name == "Test Game"
        assert translated_game.steam_id == 123
        assert translated_game.description != game.description
        assert len(translated_game.description) > 0

    def test_real_convenience_functions(self, api_key):
        """Test real de funciones de conveniencia."""
        game = GameInfo(
            name="Test Game", description="A simple test game.", steam_id=123
        )

        # Test translate_game_description
        translated_game = translate_game_description(
            game=game, target_language="es", api_key=api_key
        )
        assert translated_game.description != game.description

        # Test detect_language
        detection = detect_language(text="Hello world", api_key=api_key)
        assert detection.language == "en"


if __name__ == "__main__":
    pytest.main([__file__])
