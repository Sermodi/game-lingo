"""
Sistema de Rate Limiting inteligente para GameDescriptionTranslator.

Maneja límites específicos para cada API:
- Steam Store API: ~200 requests/5min por IP
- RAWG API: 20,000 requests/mes (gratuito)
- DeepL API: 500,000 caracteres/mes (gratuito)
- Google Translate: Según cuota configurada

Características:
- Rate limiting por API individual
- Ventanas deslizantes para precisión
- Backoff exponencial en caso de límites
- Persistencia de estado entre reinicios
- Monitoreo de uso en tiempo real
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..config import settings
from ..exceptions import RateLimitError

logger = logging.getLogger(__name__)


class APIRateLimit:
    """
    Configuración de rate limit para una API específica.
    """

    def __init__(
        self,
        requests_per_window: int,
        window_seconds: int,
        burst_limit: Optional[int] = None,
        character_limit: Optional[int] = None,
        character_window_seconds: Optional[int] = None,
    ) -> None:
        """
        Inicializa configuración de rate limit.

        Args:
            requests_per_window: Número máximo de requests por ventana
            window_seconds: Duración de la ventana en segundos
            burst_limit: Límite de burst (opcional)
            character_limit: Límite de caracteres (para APIs de traducción)
            character_window_seconds: Ventana para límite de caracteres
        """
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.burst_limit = burst_limit or requests_per_window
        self.character_limit = character_limit
        self.character_window_seconds = character_window_seconds or window_seconds

        # Estado interno
        self.request_times: deque[float] = deque()
        self.character_usage: deque[tuple[float, int]] = deque()
        self.last_request_time = 0.0
        self.consecutive_errors = 0
        self.backoff_until = 0.0


class RateLimiter:
    """
    Rate limiter inteligente con soporte multi-API.

    Características:
    - Límites específicos por API
    - Ventanas deslizantes precisas
    - Backoff exponencial automático
    - Persistencia de estado
    - Monitoreo de uso
    """

    def __init__(self, state_file: Optional[Union[Path, str]] = None) -> None:
        """
        Inicializa el rate limiter.

        Args:
            state_file: Archivo para persistir estado (opcional)
        """
        self.state_file = (
            Path(state_file)
            if state_file
            else settings.CACHE_DIR / "rate_limiter_state.json"
        )
        self.api_limits: Dict[str, APIRateLimit] = {}
        self.global_stats = {
            "total_requests": 0,
            "total_characters": 0,
            "rate_limit_hits": 0,
            "backoff_events": 0,
        }

        # Configurar límites por API
        self._setup_api_limits()

        # Cargar estado persistido
        self._load_state()

        logger.info("RateLimiter initialized with API limits")
        self._log_current_limits()

    def _setup_api_limits(self) -> None:
        """Configura límites específicos para cada API."""

        # Steam Store API - ~200 requests/5min por IP
        self.api_limits["steam"] = APIRateLimit(
            requests_per_window=settings.STEAM_RATE_LIMIT,
            window_seconds=300,  # 5 minutos
            burst_limit=50,  # Permitir burst inicial
        )

        # RAWG API - 20,000 requests/mes (gratuito)
        # Convertimos a ~27 requests/hora para distribución uniforme
        self.api_limits["rawg"] = APIRateLimit(
            requests_per_window=settings.RAWG_RATE_LIMIT,
            window_seconds=3600,  # 1 hora
            burst_limit=100,
        )

        # DeepL API - 500,000 caracteres/mes (gratuito)
        # ~694 caracteres/minuto para distribución uniforme
        self.api_limits["deepl"] = APIRateLimit(
            requests_per_window=settings.DEEPL_RATE_LIMIT,
            window_seconds=60,  # 1 minuto
            burst_limit=20,
            character_limit=settings.DEEPL_CHARACTER_LIMIT,
            character_window_seconds=60,
        )

        # Google Translate API - Según configuración
        self.api_limits["google"] = APIRateLimit(
            requests_per_window=settings.GOOGLE_RATE_LIMIT,
            window_seconds=60,  # 1 minuto
            burst_limit=50,
            character_limit=settings.GOOGLE_CHARACTER_LIMIT,
            character_window_seconds=60,
        )

    async def acquire(
        self,
        api_name: str,
        character_count: Optional[int] = None,
    ) -> bool:
        """
        Adquiere permiso para hacer una request a la API.

        Args:
            api_name: Nombre de la API
            character_count: Número de caracteres (para APIs de traducción)

        Returns:
            True si se puede proceder, False si hay que esperar

        Raises:
            RateLimitError: Si se exceden los límites configurados
        """
        if api_name not in self.api_limits:
            logger.warning(f"No rate limit configured for API: {api_name}")
            return True

        limit = self.api_limits[api_name]
        current_time = time.time()

        # Verificar backoff
        if current_time < limit.backoff_until:
            wait_time = limit.backoff_until - current_time
            raise RateLimitError(
                f"API {api_name} in backoff mode. Wait {wait_time:.1f}s",
            )

        # Limpiar ventana deslizante de requests
        self._cleanup_request_window(limit, current_time)

        # Verificar límite de requests
        if len(limit.request_times) >= limit.requests_per_window:
            oldest_request = limit.request_times[0]
            wait_time = oldest_request + limit.window_seconds - current_time

            if wait_time > 0:
                logger.warning(
                    f"Rate limit reached for {api_name}. Wait {wait_time:.1f}s",
                )
                self.global_stats["rate_limit_hits"] += 1
                return False

        # Verificar límite de caracteres (si aplica)
        if character_count and limit.character_limit:
            self._cleanup_character_window(limit, current_time)

            current_usage = sum(count for _, count in limit.character_usage)
            if current_usage + character_count > limit.character_limit:
                raise RateLimitError(
                    f"Character limit exceeded for {api_name}. "
                    f"Current: {current_usage}, Requested: {character_count}, "
                    f"Limit: {limit.character_limit}",
                )

        # Registrar request
        limit.request_times.append(current_time)
        limit.last_request_time = current_time

        if character_count and limit.character_limit:
            limit.character_usage.append((current_time, character_count))
            self.global_stats["total_characters"] += character_count

        self.global_stats["total_requests"] += 1

        # Guardar estado después de cada request para persistencia
        self._save_state()

        logger.debug(f"Rate limit acquired for {api_name}")
        return True

    async def wait_if_needed(
        self,
        api_name: str,
        character_count: Optional[int] = None,
    ) -> None:
        """
        Espera automáticamente si es necesario antes de proceder.

        Args:
            api_name: Nombre de la API
            character_count: Número de caracteres (opcional)
        """
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                if await self.acquire(api_name, character_count):
                    return

                # Calcular tiempo de espera
                if api_name in self.api_limits:
                    limit = self.api_limits[api_name]
                    if limit.request_times:
                        oldest_request = limit.request_times[0]
                        wait_time = oldest_request + limit.window_seconds - time.time()
                        wait_time = max(0.1, min(wait_time, 60))  # Entre 0.1s y 60s

                        logger.info(
                            f"Waiting {wait_time:.1f}s for {api_name} rate limit",
                        )
                        await asyncio.sleep(wait_time)

                retry_count += 1

            except RateLimitError as e:
                if "backoff" in str(e).lower():
                    # Extraer tiempo de espera del mensaje
                    wait_time = self._extract_wait_time(str(e))
                    logger.warning(f"Backoff required for {api_name}: {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise

                retry_count += 1

        raise RateLimitError(
            f"Failed to acquire rate limit for {api_name} after {max_retries} retries",
        )

    def report_error(self, api_name: str, error_type: str = "generic") -> None:
        """
        Reporta un error de API para activar backoff si es necesario.

        Args:
            api_name: Nombre de la API
            error_type: Tipo de error ("rate_limit", "server_error", etc.)
        """
        if api_name not in self.api_limits:
            return

        limit = self.api_limits[api_name]
        limit.consecutive_errors += 1

        # Activar backoff exponencial para errores de rate limit
        if error_type == "rate_limit" or limit.consecutive_errors >= 3:
            backoff_seconds = min(2**limit.consecutive_errors, 300)  # Max 5 minutos
            limit.backoff_until = time.time() + backoff_seconds

            self.global_stats["backoff_events"] += 1

            logger.warning(
                f"Activating backoff for {api_name}: {backoff_seconds}s "
                f"(consecutive errors: {limit.consecutive_errors})",
            )

    def report_success(self, api_name: str) -> None:
        """
        Reporta éxito de API para resetear contador de errores.

        Args:
            api_name: Nombre de la API
        """
        if api_name in self.api_limits:
            self.api_limits[api_name].consecutive_errors = 0

    def get_usage_stats(self, api_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso.

        Args:
            api_name: API específica (opcional, None para todas)

        Returns:
            Diccionario con estadísticas
        """
        if api_name and api_name in self.api_limits:
            limit = self.api_limits[api_name]
            current_time = time.time()

            # Limpiar ventanas
            self._cleanup_request_window(limit, current_time)
            self._cleanup_character_window(limit, current_time)

            current_usage = sum(count for _, count in limit.character_usage)

            return {
                "api": api_name,
                "current_requests": len(limit.request_times),
                "max_requests": limit.requests_per_window,
                "window_seconds": limit.window_seconds,
                "current_characters": current_usage,
                "max_characters": limit.character_limit,
                "consecutive_errors": limit.consecutive_errors,
                "backoff_until": limit.backoff_until,
                "last_request": limit.last_request_time,
            }

        # Estadísticas globales
        stats: Dict[str, Any] = {
            "global": self.global_stats.copy(),
            "apis": {},
        }

        for name in self.api_limits:
            stats["apis"][name] = self.get_usage_stats(name)

        return stats

    def reset_stats(self, api_name: Optional[str] = None) -> None:
        """
        Resetea estadísticas.

        Args:
            api_name: API específica (opcional, None para todas)
        """
        if api_name and api_name in self.api_limits:
            limit = self.api_limits[api_name]
            limit.request_times.clear()
            limit.character_usage.clear()
            limit.consecutive_errors = 0
            limit.backoff_until = 0.0
            logger.info(f"Reset stats for {api_name}")
        else:
            # Reset global
            for limit in self.api_limits.values():
                limit.request_times.clear()
                limit.character_usage.clear()
                limit.consecutive_errors = 0
                limit.backoff_until = 0.0

            self.global_stats = {
                "total_requests": 0,
                "total_characters": 0,
                "rate_limit_hits": 0,
                "backoff_events": 0,
            }
            logger.info("Reset all rate limiter stats")

    def _cleanup_request_window(self, limit: APIRateLimit, current_time: float) -> None:
        """Limpia requests fuera de la ventana actual."""
        cutoff_time = current_time - limit.window_seconds
        while limit.request_times and limit.request_times[0] < cutoff_time:
            limit.request_times.popleft()

    def _cleanup_character_window(
        self,
        limit: APIRateLimit,
        current_time: float,
    ) -> None:
        """Limpia uso de caracteres fuera de la ventana actual."""
        if not limit.character_window_seconds:
            return

        cutoff_time = current_time - limit.character_window_seconds
        while limit.character_usage and limit.character_usage[0][0] < cutoff_time:
            limit.character_usage.popleft()

    def _extract_wait_time(self, error_message: str) -> float:
        """Extrae tiempo de espera de mensaje de error."""
        try:
            # Buscar patrón "Wait X.Xs"
            import re

            match = re.search(r"Wait (\d+\.?\d*)s", error_message)
            if match:
                return float(match.group(1))
        except Exception:
            pass

        return 1.0  # Default 1 segundo

    def _log_current_limits(self) -> None:
        """Log de límites configurados."""
        for api_name, limit in self.api_limits.items():
            logger.info(
                f"Rate limit for {api_name}: "
                f"{limit.requests_per_window} requests/{limit.window_seconds}s",
            )
            if limit.character_limit:
                logger.info(
                    f"Character limit for {api_name}: "
                    f"{limit.character_limit} chars/{limit.character_window_seconds}s",
                )

    def _load_state(self) -> None:
        """Carga estado persistido desde archivo."""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file, encoding="utf-8") as f:
                state = json.load(f)

            # Restaurar estadísticas globales
            if "global_stats" in state:
                self.global_stats.update(state["global_stats"])

            # Restaurar estado de APIs (solo errores consecutivos y backoff)
            if "api_states" in state:
                for api_name, api_state in state["api_states"].items():
                    if api_name in self.api_limits:
                        limit = self.api_limits[api_name]
                        limit.consecutive_errors = api_state.get(
                            "consecutive_errors",
                            0,
                        )
                        limit.backoff_until = api_state.get("backoff_until", 0.0)

            logger.info("Rate limiter state loaded from disk")

        except Exception as e:
            logger.warning(f"Failed to load rate limiter state: {e}")

    def _save_state(self) -> None:
        """Guarda estado actual en archivo."""
        try:
            # Preparar estado para serialización
            state: Dict[str, Any] = {
                "global_stats": self.global_stats,
                "api_states": {},
                "timestamp": time.time(),
            }

            for api_name, limit in self.api_limits.items():
                state["api_states"][api_name] = {
                    "consecutive_errors": limit.consecutive_errors,
                    "backoff_until": limit.backoff_until,
                }

            # Asegurar directorio existe
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            # Escribir archivo
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

            logger.debug("Rate limiter state saved to disk")

        except Exception as e:
            logger.warning(f"Failed to save rate limiter state: {e}")

    def __del__(self) -> None:
        """Guarda estado al destruir el objeto."""
        try:
            self._save_state()
        except Exception:
            pass  # Ignorar errores en destructor
