"""
Google Translate API connector para traducción de descripciones de juegos.

Este módulo proporciona una interfaz para interactuar con la API de Google Translate
para traducir descripciones de juegos a diferentes idiomas.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import settings
from ..exceptions import (
    APIError,
    AuthenticationError,
    RateLimitError,
    TranslationError,
    ValidationError,
)

if TYPE_CHECKING:
    from types import TracebackType

    from ..core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


@dataclass
class GoogleLanguage:
    """Información de idioma soportado por Google Translate."""

    code: str
    name: str

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


@dataclass
class GoogleTranslationResult:
    """Resultado de una traducción de Google Translate."""

    def __init__(
        self,
        text: Optional[str] = None,
        translated_text: Optional[str] = None,
        detected_source_language: Optional[str] = None,
        source_language: Optional[str] = None,
        target_language: str = "",
        confidence: Optional[float] = None,
    ) -> None:
        self.text = text if text is not None else translated_text or ""
        self.detected_source_language = detected_source_language
        self.source_language = source_language
        self.target_language = target_language
        self.confidence = confidence

    @property
    def translated_text(self) -> str:
        return self.text

    def __str__(self) -> str:
        src = self.detected_source_language or "?"
        return f"{self.text} ({src} → {self.target_language})"


@dataclass
class GoogleDetectionResult:
    """Resultado de detección de idioma."""

    language: str
    confidence: float
    is_reliable: bool

    def __str__(self) -> str:
        reliability = "reliable" if self.is_reliable else "unreliable"
        return (
            f"{self.language} ({self.confidence * 100:.1f}% confidence, {reliability})"
        )


class GoogleTranslateAPIConnector:
    """
    Conector para la API de Google Translate.

    Proporciona métodos para traducir texto usando la API de Google Translate,
    con manejo de errores, rate limiting y detección de idioma.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        requests_per_second: Optional[int] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Inicializa el conector Google Translate API.

        Args:
            api_key: Clave de API de Google Cloud. Si no se proporciona, se usa la configuración.
            timeout: Timeout para las peticiones HTTP en segundos.
            rate_limiter: Rate limiter para controlar uso de API (opcional)
        """
        self.api_key = api_key or settings.GOOGLE_TRANSLATE_API_KEY
        self.timeout = timeout or settings.TRANSLATION_TIMEOUT_SECONDS
        # allow tests to pass a custom rate
        self.requests_per_second = (
            requests_per_second or settings.GOOGLE_TRANSLATE_REQUESTS_PER_SECOND
        )
        self.rate_limiter = rate_limiter

        if not self.api_key:
            raise AuthenticationError(
                api_name="google_translate",
                message="Google Translate API key is required",
            )

        self.base_url = settings.GOOGLE_TRANSLATE_BASE_URL
        self.session = self._create_session()
        self._last_request_time = 0.0
        self._min_request_interval = 1.0 / self.requests_per_second

        logger.info("Google Translate API connector initialized")

    def _create_session(self) -> requests.Session:
        """Crea una sesión HTTP configurada con reintentos."""
        session = requests.Session()

        # Configurar reintentos
        retry_strategy = Retry(
            total=settings.MAX_RETRIES,
            backoff_factor=settings.RETRY_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Headers por defecto
        session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": f"GameDescriptionTranslator/{settings.VERSION}",
            },
        )

        return session

    def __enter__(self) -> GoogleTranslateAPIConnector:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Context manager exit."""
        if hasattr(self, "session"):
            self.session.close()

    def _rate_limit(self) -> None:
        """Aplica rate limiting entre peticiones."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        method: str = "POST",
    ) -> requests.Response:
        """
        Realiza una petición HTTP a la API de Google Translate.

        Args:
            endpoint: Endpoint de la API (ej: 'translate', 'detect', 'languages')
            params: Parámetros de query string
            data: Datos JSON para enviar en la petición
            method: Método HTTP (GET, POST)

        Returns:
            Respuesta HTTP

        Raises:
            APIError: Error en la API
            RateLimitError: Límite de rate excedido
            AuthenticationError: Error de autenticación
        """
        self._rate_limit()

        url = f"{self.base_url}/{endpoint}"

        # Añadir API key a los parámetros
        if params is None:
            params = {}
        params["key"] = self.api_key

        try:
            logger.debug(f"Making {method} request to {url}")

            if method.upper() == "GET":
                response = self.session.get(url, params=params, timeout=self.timeout)
            else:
                response = self.session.post(
                    url,
                    params=params,
                    json=data,
                    timeout=self.timeout,
                )

            self._handle_response_errors(response)
            return response

        except requests.exceptions.Timeout:
            raise APIError(
                api_name="google_translate",
                message=f"Request timeout after {self.timeout}s",
                status_code=408,
            )
        except requests.exceptions.ConnectionError as e:
            raise APIError(
                api_name="google_translate",
                message=f"Connection error: {e!s}",
                status_code=503,
            )
        except requests.exceptions.RequestException as e:
            raise APIError(
                api_name="google_translate",
                message=f"Request error: {e!s}",
                status_code=500,
            )

    def _handle_response_errors(self, response: requests.Response) -> None:
        """
        Maneja errores en las respuestas de la API.

        Args:
            response: Respuesta HTTP

        Raises:
            AuthenticationError: Error de autenticación (401, 403)
            RateLimitError: Límite de rate excedido (429)
            TranslationError: Error específico de traducción (400)
            APIError: Otros errores de la API
        """
        if response.status_code == 200:
            return

        try:
            error_data = response.json()
            if "error" in error_data:
                error_info = error_data["error"]
                error_message = error_info.get("message", "Unknown error")
                error_code = error_info.get("code", response.status_code)
            else:
                error_message = "Unknown error"
                error_code = response.status_code
        except (ValueError, KeyError):
            error_message = response.text or f"HTTP {response.status_code}"
            error_code = response.status_code

        if response.status_code == 401:
            raise AuthenticationError(
                api_name="google_translate",
                message=f"Invalid API key: {error_message}",
                status_code=401,
            )
        if response.status_code == 403:
            raise AuthenticationError(
                api_name="google_translate",
                message=f"Access forbidden: {error_message}",
                status_code=403,
            )
        if response.status_code == 429:
            # Google puede incluir información de retry
            retry_after = 60  # Default retry after

            raise RateLimitError(
                api_name="google_translate",
                message=f"Rate limit exceeded: {error_message}",
                retry_after=retry_after,
                status_code=429,
            )
        if response.status_code == 400:
            raise TranslationError(
                message=f"Bad request: {error_message}",
                provider="google_translate",
                source_text="",
                details={"error_code": "bad_request", "target_language": ""},
            )
        raise APIError(
            api_name="google_translate",
            message=f"API error: {error_message}",
            status_code=response.status_code,
        )

    def get_supported_languages(
        self,
        target_language: str = "en",
    ) -> List[GoogleLanguage]:
        """
        Obtiene la lista de idiomas soportados.

        Args:
            target_language: Idioma en el que mostrar los nombres de los idiomas

        Returns:
            Lista de idiomas soportados

        Raises:
            APIError: Error al obtener idiomas
        """
        try:
            params = {"target": target_language}
            response = self._make_request("languages", params=params, method="GET")
            data = response.json()

            languages = []
            if "data" in data and "languages" in data["data"]:
                for lang_data in data["data"]["languages"]:
                    language = GoogleLanguage(
                        code=lang_data["language"],
                        name=lang_data.get("name", lang_data["language"]),
                    )
                    languages.append(language)

            logger.info(f"Retrieved {len(languages)} supported languages")
            return languages

        except Exception as e:
            if isinstance(e, (APIError, AuthenticationError, RateLimitError)):
                raise
            raise APIError(
                api_name="google_translate",
                message=f"Failed to get supported languages: {e!s}",
                status_code=500,
            )

    def detect_language(self, text: str) -> GoogleDetectionResult:
        """
        Detecta el idioma de un texto.

        Args:
            text: Texto para detectar el idioma

        Returns:
            Resultado de la detección

        Raises:
            ValidationError: Texto vacío
            APIError: Error en la detección
        """
        if not text or not text.strip():
            raise ValidationError(
                message="Text for language detection cannot be empty",
                field="text",
            )

        try:
            data = {"q": text}
            response = self._make_request("detect", data=data)
            result_data = response.json()

            if "data" not in result_data or "detections" not in result_data["data"]:
                raise APIError(
                    api_name="google_translate",
                    message="Invalid response format for language detection",
                    status_code=500,
                )

            detection = result_data["data"]["detections"][0][0]

            result = GoogleDetectionResult(
                language=detection["language"],
                confidence=detection.get("confidence", 0.0),
                is_reliable=detection.get("isReliable", False),
            )

            logger.info(
                f"Detected language: {result.language} (confidence: {result.confidence:.2f})",
            )
            return result

        except Exception as e:
            if isinstance(
                e,
                (APIError, AuthenticationError, RateLimitError, ValidationError),
            ):
                raise
            raise APIError(
                api_name="google_translate",
                message=f"Language detection failed: {e!s}",
                status_code=500,
            )

    def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
        format_: str = "text",
    ) -> GoogleTranslationResult:
        """
        Traduce un texto usando la API de Google Translate.

        Args:
            text: Texto a traducir
            target_language: Idioma de destino (código ISO)
            source_language: Idioma de origen (opcional, se detecta automáticamente)
            format_: Formato del texto ('text' o 'html')

        Returns:
            Resultado de la traducción

        Raises:
            ValidationError: Parámetros inválidos
            TranslationError: Error en la traducción
            APIError: Error de la API
        """
        # Validaciones
        if not text or not text.strip():
            raise ValidationError(
                message="Text to translate cannot be empty",
                field="text",
            )

        if not target_language:
            raise ValidationError(
                message="Target language is required",
                field="target_language",
            )

        if format_ not in ["text", "html"]:
            raise ValidationError(
                message=f"Invalid format: {format_}. Must be 'text' or 'html'",
                field="format",
            )

        # Preparar datos de la petición
        data = {
            "q": text,
            "target": target_language,
            "format": format_,
        }

        if source_language:
            data["source"] = source_language

        try:
            # Rate limiting (llamada síncrona a método async)
            if self.rate_limiter:
                # Usar asyncio.run para ejecutar el rate limiter async desde código síncrono
                try:
                    asyncio.run(
                        self.rate_limiter.wait_if_needed(
                            "google",
                            character_count=len(text),
                        ),
                    )
                except RuntimeError:
                    # Si ya hay un event loop corriendo, intentar usarlo
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(
                        self.rate_limiter.wait_if_needed(
                            "google",
                            character_count=len(text),
                        ),
                    )

            logger.info(f"Translating text to {target_language} (length: {len(text)})")
            response = self._make_request(
                "",
                data=data,
            )  # Endpoint vacío para translate
            result_data = response.json()

            if "data" not in result_data or "translations" not in result_data["data"]:
                raise TranslationError(
                    message="No translation returned from API",
                    provider="google_translate",
                    source_text=text,
                    details={
                        "target_language": target_language,
                        "error_code": "no_translation",
                    },
                )

            translation = result_data["data"]["translations"][0]

            result = GoogleTranslationResult(
                text=translation["translatedText"],
                detected_source_language=translation.get("detectedSourceLanguage"),
                source_language=source_language,
                target_language=target_language,
            )

            logger.info(
                f"Translation successful (detected source: {result.detected_source_language})",
            )
            return result

        except Exception as e:
            if isinstance(
                e,
                (
                    APIError,
                    AuthenticationError,
                    RateLimitError,
                    TranslationError,
                    ValidationError,
                ),
            ):
                raise
            raise TranslationError(
                message=f"Translation failed: {e!s}",
                provider="google_translate",
                source_text=text,
                details={
                    "target_language": target_language,
                    "error_code": "translation_failed",
                },
            )

    def translate_batch(
        self,
        texts: List[str],
        target_language: str,
        source_language: Optional[str] = None,
        format_: str = "text",
    ) -> List[GoogleTranslationResult]:
        """
        Traduce múltiples textos en una sola petición.

        Args:
            texts: Lista de textos a traducir
            target_language: Idioma de destino
            source_language: Idioma de origen (opcional)
            format_: Formato del texto ('text' o 'html')

        Returns:
            Lista de resultados de traducción

        Raises:
            ValidationError: Parámetros inválidos
            TranslationError: Error en la traducción
        """
        if not texts:
            raise ValidationError(
                message="Texts list cannot be empty",
                field="texts",
            )

        if not target_language:
            raise ValidationError(
                message="Target language is required",
                field="target_language",
            )

        # Filtrar textos vacíos
        valid_texts = [text for text in texts if text and text.strip()]
        if not valid_texts:
            raise ValidationError(
                message="No valid texts to translate",
                field="texts",
            )

        # Preparar datos de la petición
        data = {
            "q": valid_texts,
            "target": target_language,
            "format": format_,
        }

        if source_language:
            data["source"] = source_language

        try:
            logger.info(f"Translating {len(valid_texts)} texts to {target_language}")
            response = self._make_request("", data=data)
            result_data = response.json()

            if "data" not in result_data or "translations" not in result_data["data"]:
                raise TranslationError(
                    message="No translations returned from API",
                    provider="google_translate",
                    source_text=str(valid_texts),
                    details={
                        "target_language": target_language,
                        "error_code": "no_translations",
                    },
                )

            translations = result_data["data"]["translations"]
            results: List[GoogleTranslationResult] = []

            for translation in translations:
                result = GoogleTranslationResult(
                    text=translation["translatedText"],
                    detected_source_language=translation.get("detectedSourceLanguage"),
                    source_language=source_language,
                    target_language=target_language,
                )
                results.append(result)

            logger.info(f"Batch translation successful ({len(results)} texts)")
            return results

        except Exception as e:
            if isinstance(
                e,
                (
                    APIError,
                    AuthenticationError,
                    RateLimitError,
                    TranslationError,
                    ValidationError,
                ),
            ):
                raise
            raise TranslationError(
                message=f"Batch translation failed: {e!s}",
                provider="google_translate",
                source_text=str(texts),
                details={
                    "target_language": target_language,
                    "error_code": "batch_translation_failed",
                },
            )

    def translate_game_description(
        self,
        description: str | None = None,
        target_language: str = "es",
        preserve_html: bool = True,
    ) -> str:
        """
        Traduce una descripción de juego a español (o idioma especificado).

        Args:
            description: Descripción del juego a traducir
            target_language: Idioma de destino (por defecto es - español)
            preserve_html: Si preservar el formateo HTML

        Returns:
            Descripción traducida

        Raises:
            ValidationError: Descripción vacía o inválida
            TranslationError: Error en la traducción
        """
        if not description or not description.strip():
            raise ValidationError(
                message="Game description cannot be empty",
                field="description",
            )

        try:
            format_ = "html" if preserve_html else "text"
            result = self.translate_text(
                text=description,
                target_language=target_language,
                format_=format_,
            )

            return result.text

        except Exception as e:
            logger.error(f"Failed to translate game description: {e!s}")
            raise TranslationError(
                message=f"Failed to translate game description: {e!s}",
                provider="google_translate",
                source_text=description or "",
                details={
                    "target_language": target_language,
                    "error_code": "translation_failed",
                },
            ) from e


def translate_game_description(
    description: str | None = None,
    target_language: str = "es",
    api_key: Optional[str] = None,
    game: Any = None,
) -> str:
    """
    Función de conveniencia para traducir una descripción de juego.

    Args:
        description: Descripción del juego a traducir
        target_language: Idioma de destino (por defecto es - español)
        api_key: Clave de API de Google Translate (opcional)

    Returns:
        Descripción traducida

    Raises:
        ValidationError: Parámetros inválidos
        TranslationError: Error en la traducción
        AuthenticationError: Error de autenticación
    """
    with GoogleTranslateAPIConnector(api_key=api_key) as connector:
        # compat: if caller passed a GameInfo via `game` param, use its description
        if game is not None:
            # expected attribute in tests: description
            desc = getattr(game, "description", None)
            if not desc:
                raise ValidationError(
                    message="Game description cannot be empty",
                    field="description",
                )
            return connector.translate_game_description(desc, target_language)
        return connector.translate_game_description(description, target_language)


def detect_language(text: str, api_key: Optional[str] = None) -> GoogleDetectionResult:
    """
    Función de conveniencia para detectar el idioma de un texto.

    Args:
        text: Texto para detectar el idioma
        api_key: Clave de API de Google Translate (opcional)

    Returns:
        Resultado de la detección

    Raises:
        ValidationError: Texto vacío
        APIError: Error en la detección
    """
    with GoogleTranslateAPIConnector(api_key=api_key) as connector:
        return connector.detect_language(text)


# Compatibility aliases expected by the test-suite
# historic names: GoogleTranslateLanguage, GoogleTranslateDetection, GoogleTranslateResult
GoogleTranslateLanguage = GoogleLanguage
GoogleTranslateDetection = GoogleDetectionResult
GoogleTranslateResult = GoogleTranslationResult
