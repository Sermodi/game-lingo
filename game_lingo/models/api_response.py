"""
Modelos para respuestas de APIs externas.

Define estructuras de datos para normalizar respuestas de:
- Steam Store API
- RAWG API
- IGDB API
- APIs de traducción (DeepL, Google)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    """Respuesta base de API."""

    success: bool = Field(..., description="¿Respuesta exitosa?")
    status_code: int = Field(..., description="Código de estado HTTP")
    response_time_ms: int = Field(..., ge=0, description="Tiempo de respuesta en ms")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp de la respuesta",
    )
    raw_data: dict[str, Any] | None = Field(None, description="Datos crudos de la API")
    error_message: str | None = Field(None, description="Mensaje de error si aplica")


class SteamResponse(APIResponse):
    """Respuesta específica de Steam Store API."""

    app_id: int = Field(..., description="Steam App ID")
    name: str | None = Field(None, description="Nombre del juego")
    short_description: str | None = Field(None, description="Descripción corta")
    detailed_description: str | None = Field(None, description="Descripción detallada")
    about_the_game: str | None = Field(None, description="Acerca del juego")
    supported_languages: str | None = Field(None, description="Idiomas soportados")
    header_image: str | None = Field(None, description="URL imagen de cabecera")
    website: str | None = Field(None, description="Sitio web oficial")
    developers: list[str] = Field(default_factory=list, description="Desarrolladores")
    publishers: list[str] = Field(default_factory=list, description="Distribuidores")
    platforms: list[str] = Field(
        default_factory=list,
        description="Plataformas soportadas",
    )
    categories: list[str] = Field(default_factory=list, description="Categorías")
    genres: list[str] = Field(default_factory=list, description="Géneros")
    screenshots: list[str] = Field(
        default_factory=list,
        description="URLs de capturas de pantalla",
    )
    movies: list[str] = Field(default_factory=list, description="URLs de videos")
    release_date: str | None = Field(None, description="Fecha de lanzamiento")
    price_overview: dict[str, Any] | None = Field(
        None,
        description="Información de precio",
    )
    metacritic_score: int | None = Field(None, description="Puntuación de Metacritic")
    is_free: bool = Field(False, description="¿Es gratuito?")
    language: str = Field("english", description="Idioma de la respuesta")


class RAWGResponse(APIResponse):
    """Respuesta específica de RAWG API."""

    game_id: int = Field(..., description="RAWG Game ID")
    name: str | None = Field(None, description="Nombre del juego")
    description: str | None = Field(None, description="Descripción del juego")
    description_raw: str | None = Field(None, description="Descripción sin HTML")
    background_image: str | None = Field(None, description="Imagen de fondo")
    website: str | None = Field(None, description="Sitio web oficial")
    developers: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Desarrolladores",
    )
    publishers: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Distribuidores",
    )
    platforms: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Plataformas",
    )
    genres: list[dict[str, Any]] = Field(default_factory=list, description="Géneros")
    tags: list[dict[str, Any]] = Field(default_factory=list, description="Etiquetas")
    screenshots: list[dict[str, str]] = Field(
        default_factory=list,
        description="Capturas",
    )
    released: str | None = Field(None, description="Fecha de lanzamiento")
    metacritic: int | None = Field(None, description="Puntuación Metacritic")
    rating: float | None = Field(None, description="Puntuación promedio")
    esrb_rating: dict[str, Any] | None = Field(None, description="Clasificación ESRB")


class TranslationAPIResponse(APIResponse):
    """Respuesta de APIs de traducción."""

    source_text: str = Field(..., description="Texto original")
    translated_text: str = Field(..., description="Texto traducido")
    source_language: str = Field(..., description="Idioma origen")
    target_language: str = Field(..., description="Idioma destino")
    confidence: float | None = Field(
        None,
        ge=0,
        le=1,
        description="Confianza en la traducción",
    )
    provider: str = Field(..., description="Proveedor de traducción")
    characters_used: int = Field(..., ge=0, description="Caracteres utilizados")
    detected_language: str | None = Field(
        None,
        description="Idioma detectado automáticamente",
    )
