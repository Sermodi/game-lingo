"""
Sistema de caché inteligente para GameDescriptionTranslator.

Características:
- Persistencia en disco con SQLite
- TTL (Time To Live) configurable
- Compresión automática para ahorrar espacio
- Limpieza automática de entradas expiradas
- Soporte asíncrono
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
import zlib
from pathlib import Path
from typing import Any, Union

from ..config import settings
from ..exceptions import CacheError
from ..models.game import TranslationResult

logger = logging.getLogger(__name__)


class Cache:
    """
    Sistema de caché persistente con SQLite.

    Optimizado para almacenar resultados de traducción con:
    - TTL automático
    - Compresión de datos grandes
    - Limpieza periódica
    - Estadísticas de uso
    """

    def __init__(
        self,
        db_path: Union[Path, str, None] = None,
        ttl_hours: int = settings.CACHE_TTL_HOURS,
        compress_threshold: int = 1024,  # Comprimir si el tamaño > 1KB
        cleanup_interval: int = 3600,  # Limpiar cada hora
    ) -> None:
        """
        Inicializa el sistema de caché.

        Args:
            db_path: Ruta personalizada para la base de datos (opcional)
            ttl_days: TTL en días (opcional)
            compress_threshold: Umbral para comprimir datos (opcional)
            cleanup_interval: Intervalo de limpieza en segundos (opcional)
        """
        default_db = settings.CACHE_DIR / "cache.sqlite"
        self.db_path = Path(db_path) if db_path is not None else default_db
        self.ttl_seconds = ttl_hours * 3600
        self.compress_threshold = compress_threshold
        self.cleanup_interval = cleanup_interval
        self.max_size_mb = settings.CACHE_MAX_SIZE

        # Estadísticas
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets_count": 0,  # Renombrado de 'sets' para evitar conflicto con built-in set
            "deletes": 0,
            "cleanups": 0,
        }

        # Asegurar directorio existe
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Inicializar base de datos
        self._init_database()

        logger.info(f"Cache initialized at: {self.db_path}")
        logger.info(f"TTL: {settings.CACHE_TTL_HOURS}h, Max size: {self.max_size_mb}MB")

    def _init_database(self) -> None:
        """Inicializa la estructura de la base de datos."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cache_entries (
                        key TEXT PRIMARY KEY,
                        value BLOB NOT NULL,
                        created_at REAL NOT NULL,
                        expires_at REAL NOT NULL,
                        access_count INTEGER DEFAULT 0,
                        last_accessed REAL NOT NULL,
                        compressed BOOLEAN DEFAULT FALSE,
                        size_bytes INTEGER DEFAULT 0
                    )
                """,
                )

                # Índices para optimizar consultas
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_expires_at
                    ON cache_entries(expires_at)
                """,
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_last_accessed
                    ON cache_entries(last_accessed)
                """,
                )

                conn.commit()

        except sqlite3.Error as e:
            raise CacheError(
                f"Failed to initialize cache database: {e}",
                operation="initialize",
            )

    async def get(self, key: str) -> TranslationResult | None:
        """
        Obtiene un valor del caché.

        Args:
            key: Clave del elemento

        Returns:
            TranslationResult si existe y no ha expirado, None en caso contrario
        """
        try:
            # Ejecutar en thread pool para no bloquear
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._get_sync,
                key,
            )

            if result:
                self.stats["hits"] += 1
                logger.debug(f"Cache hit for key: {key}")
            else:
                self.stats["misses"] += 1
                logger.debug(f"Cache miss for key: {key}")

            return result

        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self.stats["misses"] += 1
            return None

    def _get_sync(self, key: str) -> TranslationResult | None:
        """Versión síncrona de get para ejecutar en thread pool."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT value, expires_at, compressed, access_count
                    FROM cache_entries
                    WHERE key = ? AND expires_at > ?
                """,
                    (key, time.time()),
                )

                row = cursor.fetchone()
                if not row:
                    return None

                value_blob, _expires_at, compressed, access_count = row

                # Actualizar estadísticas de acceso
                conn.execute(
                    """
                    UPDATE cache_entries
                    SET access_count = ?, last_accessed = ?
                    WHERE key = ?
                """,
                    (access_count + 1, time.time(), key),
                )

                conn.commit()

                # Deserializar valor
                if compressed:
                    value_blob = zlib.decompress(value_blob)

                data = json.loads(value_blob.decode("utf-8"))
                return TranslationResult.parse_obj(data)

        except (sqlite3.Error, json.JSONDecodeError, zlib.error) as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None

    async def set_value(
        self,
        key: str,
        value: TranslationResult,
        ttl_override: int | None = None,
    ) -> bool:
        """
        Almacena un valor en el caché.

        Args:
            key: Clave del elemento
            value: Valor a almacenar
            ttl_override: TTL personalizado en segundos (opcional)

        Returns:
            True si se almacenó correctamente, False en caso contrario
        """
        try:
            # Ejecutar en thread pool
            success = await asyncio.get_event_loop().run_in_executor(
                None,
                self._set_sync,
                key,
                value,
                ttl_override,
            )

            if success:
                self.stats["sets"] += 1
                logger.debug(f"Cache set for key: {key}")

            return success

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    def _set_sync(
        self,
        key: str,
        value: TranslationResult,
        ttl_override: int | None = None,
    ) -> bool:
        """Versión síncrona de set_value para ejecutar en thread pool."""
        try:
            # Serializar valor (mode='json' convierte datetime a string automáticamente)
            data = value.model_dump(mode="json")
            value_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            value_bytes = value_json.encode("utf-8")

            # Comprimir si es grande
            compressed = False
            if len(value_bytes) > 1024:  # Comprimir si > 1KB
                value_bytes = zlib.compress(value_bytes, level=6)
                compressed = True

            # Calcular tiempos
            now = time.time()
            ttl = ttl_override or self.ttl_seconds
            expires_at = now + ttl

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cache_entries
                    (key, value, created_at, expires_at, last_accessed,
                     compressed, size_bytes, access_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                    (
                        key,
                        value_bytes,
                        now,
                        expires_at,
                        now,
                        compressed,
                        len(value_bytes),
                    ),
                )

                conn.commit()

            return True

        except (sqlite3.Error, json.JSONDecodeError, zlib.error, ValueError) as e:
            logger.error(f"Error storing in cache: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Elimina un elemento del caché.

        Args:
            key: Clave del elemento a eliminar

        Returns:
            True si se eliminó, False si no existía
        """
        try:
            deleted = await asyncio.get_event_loop().run_in_executor(
                None,
                self._delete_sync,
                key,
            )

            if deleted:
                self.stats["deletes"] += 1
                logger.debug(f"Cache delete for key: {key}")

            return deleted

        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    def _delete_sync(self, key: str) -> bool:
        """Versión síncrona de delete."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                conn.commit()
                return cursor.rowcount > 0

        except sqlite3.Error as e:
            logger.error(f"Error deleting from cache: {e}")
            return False

    async def clear(self) -> bool:
        """
        Limpia todo el caché.

        Returns:
            True si se limpió correctamente
        """
        try:
            await asyncio.get_event_loop().run_in_executor(None, self._clear_sync)
            logger.info("Cache cleared completely")
            return True

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    def _clear_sync(self) -> None:
        """Versión síncrona de clear."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache_entries")
            conn.commit()

    async def cleanup_expired(self) -> int:
        """
        Limpia entradas expiradas del caché.

        Returns:
            Número de entradas eliminadas
        """
        try:
            deleted_count = await asyncio.get_event_loop().run_in_executor(
                None,
                self._cleanup_expired_sync,
            )

            if deleted_count > 0:
                self.stats["cleanups"] += 1
                logger.info(f"Cleaned up {deleted_count} expired cache entries")

            return deleted_count

        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
            return 0

    def _cleanup_expired_sync(self) -> int:
        """Versión síncrona de cleanup_expired."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM cache_entries WHERE expires_at <= ?",
                    (time.time(),),
                )
                conn.commit()
                return cursor.rowcount

        except sqlite3.Error as e:
            logger.error(f"Error cleaning up expired entries: {e}")
            return 0

    async def get_stats(self) -> dict[str, Any]:
        """
        Obtiene estadísticas del caché.

        Returns:
            Diccionario con estadísticas de uso y tamaño
        """
        try:
            db_stats = await asyncio.get_event_loop().run_in_executor(
                None,
                self._get_db_stats,
            )

            # Combinar con estadísticas en memoria
            stats = {
                **self.stats,
                **db_stats,
                "hit_rate": (
                    self.stats["hits"] / (self.stats["hits"] + self.stats["misses"])
                    if (self.stats["hits"] + self.stats["misses"]) > 0
                    else 0.0
                ),
            }

            return stats

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return self.stats

    def _get_db_stats(self) -> dict[str, Any]:
        """Obtiene estadísticas de la base de datos."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Contar entradas totales y expiradas
                cursor = conn.execute("SELECT COUNT(*) FROM cache_entries")
                total_entries = cursor.fetchone()[0]

                cursor = conn.execute(
                    "SELECT COUNT(*) FROM cache_entries WHERE expires_at <= ?",
                    (time.time(),),
                )
                expired_entries = cursor.fetchone()[0]

                # Calcular tamaño total
                cursor = conn.execute("SELECT SUM(size_bytes) FROM cache_entries")
                total_size_bytes = cursor.fetchone()[0] or 0

                # Obtener tamaño del archivo de base de datos
                db_file_size = (
                    self.db_path.stat().st_size if self.db_path.exists() else 0
                )

                return {
                    "total_entries": total_entries,
                    "active_entries": total_entries - expired_entries,
                    "expired_entries": expired_entries,
                    "total_size_bytes": total_size_bytes,
                    "total_size_mb": total_size_bytes / (1024 * 1024),
                    "db_file_size_bytes": db_file_size,
                    "db_file_size_mb": db_file_size / (1024 * 1024),
                }

        except sqlite3.Error as e:
            logger.error(f"Error getting database stats: {e}")
            return {}

    async def optimize(self) -> bool:
        """
        Optimiza la base de datos del caché.

        Ejecuta VACUUM para compactar y reorganizar la base de datos.

        Returns:
            True si se optimizó correctamente
        """
        try:
            await asyncio.get_event_loop().run_in_executor(None, self._optimize_sync)
            logger.info("Cache database optimized")
            return True

        except Exception as e:
            logger.error(f"Error optimizing cache: {e}")
            return False

    def _optimize_sync(self) -> None:
        """Versión síncrona de optimize."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("VACUUM")
            conn.commit()

    def __str__(self) -> str:
        """Representación string del caché."""
        return f"Cache(db_path={self.db_path}, ttl={self.ttl_seconds}s)"

    def __repr__(self) -> str:
        """Representación detallada del caché."""
        return (
            f"Cache(db_path={self.db_path}, ttl_seconds={self.ttl_seconds}, "
            f"max_size_mb={self.max_size_mb}, stats={self.stats})"
        )
