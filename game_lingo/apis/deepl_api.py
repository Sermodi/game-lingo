"""
DeepL API connector para traducción de descripciones de juegos.

Este módulo proporciona una interfaz para interactuar con la API de DeepL
para traducir descripciones de juegos a diferentes idiomas.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    import types

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
    from ..core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


@dataclass
class DeepLUsage:
    """Información de uso de la API de DeepL."""

    character_count: int
    character_limit: int

    @property
    def usage_percentage(self) -> float:
        """Porcentaje de uso del límite de caracteres."""
        if self.character_limit == 0:
            return 0.0
        return (self.character_count / self.character_limit) * 100


@dataclass
class DeepLLanguage:
    """Información de idioma soportado por DeepL."""

    code: str
    name: str
    supports_formality: bool = False


@dataclass
class TranslationResult:
    """Resultado de una traducción."""

    text: str
    detected_source_language: Optional[str] = None
    source_language: Optional[str] = None
    target_language: str = ""


class DeepLAPIConnector:
    """
    Conector para la API de DeepL.

    Proporciona métodos para traducir texto usando la API de DeepL,
    con manejo de errores, rate limiting y cache.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        is_pro: bool = False,
        timeout: Optional[int] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Inicializa el conector DeepL API.

        Args:
            api_key: Clave de API de DeepL. Si no se proporciona, se usa la configuración.
            is_pro: Si True, usa la API Pro de DeepL. Si False, usa la API Free.
            timeout: Timeout para las peticiones HTTP en segundos.
            rate_limiter: Rate limiter para controlar uso de API (opcional)
        """
        self.api_key = api_key or settings.DEEPL_API_KEY
        self.is_pro = is_pro or settings.DEEPL_IS_PRO
        self.timeout = timeout or settings.TRANSLATION_TIMEOUT_SECONDS
        self.rate_limiter = rate_limiter

        if not self.api_key:
            raise AuthenticationError(
                api_name="deepl",
                message="DeepL API key is required",
                status_code=401,
            )

        # URL base según el tipo de cuenta
        if self.is_pro:
            self.base_url = "https://api.deepl.com/v2"
        else:
            self.base_url = "https://api-free.deepl.com/v2"

        self.session = self._create_session()
        self._last_request_time = 0.0  # Usar float para mantener precisión
        self._min_request_interval = 1.0 / settings.DEEPL_REQUESTS_PER_SECOND

        logger.info(f"DeepL API connector initialized (Pro: {self.is_pro})")

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
                "Authorization": f"DeepL-Auth-Key {self.api_key}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": f"GameDescriptionTranslator/{settings.VERSION}",
            },
        )

        return session

    def __enter__(self) -> DeepLAPIConnector:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[types.TracebackType],
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
        data: Optional[Dict[str, Any]] = None,
        method: str = "POST",
    ) -> requests.Response:
        """
        Realiza una petición HTTP a la API de DeepL.

        Args:
            endpoint: Endpoint de la API (ej: 'translate', 'usage')
            data: Datos para enviar en la petición
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

        try:
            logger.debug(f"Making {method} request to {url}")

            if method.upper() == "GET":
                response = self.session.get(url, timeout=self.timeout)
            else:
                response = self.session.post(url, data=data, timeout=self.timeout)

            self._handle_response_errors(response)
            return response

        except requests.exceptions.Timeout:
            raise APIError(
                api_name="deepl",
                message=f"Request timeout after {self.timeout}s",
                status_code=408,
            )
        except requests.exceptions.ConnectionError as e:
            raise APIError(
                api_name="deepl",
                message=f"Connection error: {e!s}",
                status_code=503,
            )
        except requests.exceptions.RequestException as e:
            raise APIError(
                api_name="deepl",
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
            TranslationError: Error específico de traducción (400, 456)
            APIError: Otros errores de la API
        """
        if response.status_code == 200:
            return

        try:
            error_data = response.json()
            error_message = error_data.get("message", "Unknown error")
        except (ValueError, KeyError):
            error_message = response.text or f"HTTP {response.status_code}"

        if response.status_code == 401:
            raise AuthenticationError(
                api_name="deepl",
                message=f"Invalid API key: {error_message}",
                status_code=401,
            )
        if response.status_code == 403:
            raise AuthenticationError(
                api_name="deepl",
                message=f"Access forbidden: {error_message}",
                status_code=403,
            )
        if response.status_code == 429:
            # DeepL puede incluir Retry-After header
            retry_after_header = response.headers.get("Retry-After")
            retry_after_seconds = 60  # Valor por defecto

            if retry_after_header:
                try:
                    retry_after_seconds = int(retry_after_header)
                except (ValueError, TypeError):
                    pass  # Usar el valor por defecto si no se puede convertir a entero

            raise RateLimitError(
                api_name="deepl",
                message=f"Rate limit exceeded: {error_message}",
                retry_after=retry_after_seconds,
                status_code=429,
            )
        if response.status_code == 400:
            raise TranslationError(
                message=f"Bad request: {error_message}",
                source_text="",
                provider="deepl",
                details={
                    "target_language": "",
                    "error_code": "bad_request",
                },
            )
        if response.status_code == 456:
            raise TranslationError(
                message=f"Quota exceeded: {error_message}",
                source_text="",
                provider="deepl",
                details={
                    "target_language": "",
                    "error_code": "quota_exceeded",
                },
            )
        raise APIError(
            api_name="deepl",
            message=f"API error: {error_message}",
            status_code=response.status_code,
        )

    def get_usage(self) -> DeepLUsage:
        """
        Obtiene información sobre el uso actual de la API.

        Returns:
            Información de uso de la API

        Raises:
            APIError: Error al obtener información de uso
        """
        try:
            response = self._make_request("usage", method="GET")
            data = response.json()

            return DeepLUsage(
                character_count=data.get("character_count", 0),
                character_limit=data.get("character_limit", 0),
            )

        except Exception as e:
            if isinstance(e, (APIError, AuthenticationError, RateLimitError)):
                raise
            raise APIError(
                api_name="deepl",
                message=f"Failed to get usage info: {e!s}",
                status_code=500,
            )

    def get_supported_languages(self, type_: str = "target") -> List[DeepLLanguage]:
        """
        Obtiene la lista de idiomas soportados.

        Args:
            type_: Tipo de idiomas ('source' o 'target')

        Returns:
            Lista de idiomas soportados

        Raises:
            APIError: Error al obtener idiomas
            ValidationError: Tipo de idioma inválido
        """
        if type_ not in ["source", "target"]:
            raise ValidationError(
                message=f"Invalid language type: {type_}. Must be 'source' or 'target'",
                field="type",
            )

        try:
            data = {"type": type_}
            response = self._make_request("languages", data=data)
            languages_data = response.json()

            languages = []
            for lang_data in languages_data:
                language = DeepLLanguage(
                    code=lang_data["language"],
                    name=lang_data["name"],
                    supports_formality=lang_data.get("supports_formality", False),
                )
                languages.append(language)

            logger.info(f"Retrieved {len(languages)} {type_} languages")
            return languages

        except Exception as e:
            if isinstance(
                e,
                (APIError, AuthenticationError, RateLimitError, ValidationError),
            ):
                raise
            raise APIError(
                api_name="deepl",
                message=f"Failed to get supported languages: {e!s}",
                status_code=500,
            )

    def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
        formality: Optional[str] = None,
        preserve_formatting: bool = True,
    ) -> TranslationResult:
        """
        Traduce un texto usando la API de DeepL.

        Args:
            text: Texto a traducir
            target_language: Idioma de destino (código ISO)
            source_language: Idioma de origen (opcional, se detecta automáticamente)
            formality: Nivel de formalidad ('default', 'more', 'less')
            preserve_formatting: Si preservar el formateo del texto

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

        if formality and formality not in ["default", "more", "less"]:
            raise ValidationError(
                message=f"Invalid formality: {formality}. Must be 'default', 'more', or 'less'",
                field="formality",
            )

        # Preparar datos de la petición
        data = {
            "text": text,
            "target_lang": target_language.upper(),
        }

        if source_language:
            data["source_lang"] = source_language.upper()

        if formality:
            data["formality"] = formality

        if preserve_formatting:
            data["preserve_formatting"] = "1"

        try:
            # Rate limiting (llamada síncrona a método async)
            if self.rate_limiter:
                # Usar asyncio.run para ejecutar el rate limiter async desde código síncrono
                try:
                    asyncio.run(
                        self.rate_limiter.wait_if_needed(
                            "deepl",
                            character_count=len(text),
                        ),
                    )
                except RuntimeError:
                    # Si ya hay un event loop corriendo, intentar usarlo
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(
                        self.rate_limiter.wait_if_needed(
                            "deepl",
                            character_count=len(text),
                        ),
                    )

            logger.info(f"Translating text to {target_language} (length: {len(text)})")
            response = self._make_request("translate", data=data)
            result_data = response.json()

            if not result_data.get("translations"):
                raise TranslationError(
                    message="No translation returned from API",
                    source_text=text,
                    provider="deepl",
                    details={
                        "target_language": target_language,
                        "error_code": "no_translation",
                    },
                )

            translation = result_data["translations"][0]

            result = TranslationResult(
                text=translation["text"],
                detected_source_language=translation.get("detected_source_language"),
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
                source_text=text,
                provider="deepl",
                details={
                    "target_language": target_language,
                    "error_code": "translation_failed",
                },
            )

    def translate_game_description(
        self,
        description: str,
        target_language: str = "ES",
        preserve_formatting: bool = True,
    ) -> str:
        """
        Traduce una descripción de juego a español (o idioma especificado).

        Args:
            description: Descripción del juego a traducir
            target_language: Idioma de destino (por defecto ES - español)
            preserve_formatting: Si preservar el formateo HTML/markdown

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
            result = self.translate_text(
                text=description,
                target_language=target_language,
                preserve_formatting=preserve_formatting,
            )

            return result.text

        except Exception as e:
            logger.error(f"Failed to translate game description: {e!s}")
            raise


def translate_game_description(
    description: str,
    target_language: str = "ES",
    api_key: Optional[str] = None,
) -> str:
    """
    Función de conveniencia para traducir una descripción de juego.

    Args:
        description: Descripción del juego a traducir
        target_language: Idioma de destino (por defecto ES - español)
        api_key: Clave de API de DeepL (opcional)

    Returns:
        Descripción traducida

    Raises:
        ValidationError: Parámetros inválidos
        TranslationError: Error en la traducción
        AuthenticationError: Error de autenticación
    """
    with DeepLAPIConnector(api_key=api_key) as connector:
        return connector.translate_game_description(description, target_language)
