"""
Excepciones específicas para el módulo Game Description Translator.

Jerarquía de excepciones:
- GameTranslatorError (base)
  - APIError
    - RateLimitError
    - AuthenticationError
  - TranslationError
  - GameNotFoundError
  - CacheError
  - ValidationError
"""

from __future__ import annotations

from typing import Any


class GameTranslatorError(Exception):
    """Excepción base para todos los errores del módulo."""

    def __init__(self, message: str, details: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class APIError(GameTranslatorError):
    """Error relacionado con APIs externas."""

    def __init__(
        self,
        message: str,
        api_name: str,
        status_code: int | None = None,
        details: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.api_name = api_name
        self.status_code = status_code


class RateLimitError(APIError):
    """Error por exceder límites de velocidad de API."""

    def __init__(
        self,
        api_name: str,
        retry_after: int | None = None,
        message: str | None = None,
        status_code: int | None = None,
        details: dict[str, str] | None = None,
    ) -> None:
        if message:
            final_message = message
        else:
            final_message = f"Rate limit exceeded for {api_name} API"
            if retry_after:
                final_message += f". Retry after {retry_after} seconds"
        super().__init__(final_message, api_name, status_code or 429, details)
        self.retry_after = retry_after


class AuthenticationError(APIError):
    """Error de autenticación con APIs."""

    def __init__(
        self,
        api_name: str,
        message: str | None = None,
        status_code: int | None = None,
        details: dict[str, str] | None = None,
    ) -> None:
        # Permite pasar un mensaje personalizado o usar el por defecto
        if message:
            final_message = message
        else:
            final_message = f"Authentication failed for {api_name} API"
        super().__init__(final_message, api_name, status_code or 401, details)


class TranslationError(GameTranslatorError):
    """Error durante el proceso de traducción."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        source_text: str | None = None,
        details: dict[str, str] | None = None,
        **kwargs: dict[str, Any],
    ) -> None:
        # Guardar kwargs adicionales (p. ej. target_language, error_code) en details
        merged_details = dict(details or {})
        for k, v in kwargs.items():
            merged_details[str(k)] = str(v)
        super().__init__(message, merged_details)
        self.provider = provider
        self.source_text = source_text


class GameNotFoundError(GameTranslatorError):
    """Error cuando no se encuentra información del juego."""

    def __init__(
        self,
        game_identifier: str,
        platform: str | None = None,
        details: dict[str, str] | None = None,
    ) -> None:
        message = f"Game not found: {game_identifier}"
        if platform:
            message += f" on {platform}"
        super().__init__(message, details)
        self.game_identifier = game_identifier
        self.platform = platform


class CacheError(GameTranslatorError):
    """Error relacionado con el sistema de caché."""

    def __init__(
        self,
        message: str,
        operation: str,
        details: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.operation = operation


class ValidationError(GameTranslatorError):
    """Error de validación de datos de entrada."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: str | None = None,
        details: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.field = field
        self.value = value
