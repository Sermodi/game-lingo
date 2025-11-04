"""
Compatibilidad: reexportar `GameInfo` desde `models.game`.

Algunos tests importan `game_translator.models.game_info.GameInfo` — este módulo
provee una capa de compatibilidad sin duplicar definiciones.
"""

from .game import GameInfo

__all__ = ["GameInfo"]
