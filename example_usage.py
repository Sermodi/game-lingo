"""
Ejemplo de uso del Game Description Translator.

Este script muestra cómo usar el traductor para obtener descripciones
de juegos en español de diferentes formas:
1. Buscar juego por nombre
2. Traducir descripción en inglés directamente
3. Combinar nombre y descripción
"""

import asyncio
import logging
import sys
from pathlib import Path

from game_translator import GameDescriptionTranslator
from game_translator.models.game import Platform

# Añadir el directorio raíz al path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def example_1_search_by_name():
    """Ejemplo 1: Buscar juego solo por nombre."""
    print("\n" + "=" * 70)
    print("EJEMPLO 1: Buscar juego por nombre")
    print("=" * 70)

    translator = GameDescriptionTranslator()

    try:
        result = await translator.translate_game_description(
            game_identifier="Hollow Knight",
        )

        print(f"\nJuego: {result.game_info.name}")
        print(f"Éxito: {result.success}")
        print(f"Fuente: {result.source.value}")
        print(f"Confianza: {result.confidence:.2f}")
        print(f"APIs usadas: {', '.join(result.apis_used)}")
        print(f"Tiempo: {result.processing_time_ms}ms")

        if result.game_info.short_description_es:
            print("\nDescripción corta (ES):")
            print(
                (
                    result.game_info.short_description_es[:300] + "..."
                    if len(result.game_info.short_description_es) > 300
                    else result.game_info.short_description_es
                ),
            )

        if result.game_info.detailed_description_es:
            print("\nDescripción detallada (ES):")
            print(
                (
                    result.game_info.detailed_description_es[:300] + "..."
                    if len(result.game_info.detailed_description_es) > 300
                    else result.game_info.detailed_description_es
                ),
            )

        if result.warnings:
            print(f"\nAdvertencias: {result.warnings}")

    except Exception as e:
        print(f"[ERROR] {e}")
        logger.exception("Error detallado")


async def example_2_translate_description_only():
    """Ejemplo 2: Traducir descripción en inglés directamente."""
    print("\n" + "=" * 70)
    print("EJEMPLO 2: Traducir descripción en inglés directamente")
    print("=" * 70)

    english_description = """
    Welcome to the world of adventure! This game offers an immersive experience
    with stunning graphics and engaging gameplay. Explore vast worlds, battle
    powerful enemies, and discover hidden treasures. Your journey begins now!

    Features:
    - Open world exploration
    - Dynamic combat system
    - Rich story with multiple endings
    - Beautiful hand-drawn art style
    """

    translator = GameDescriptionTranslator()

    try:
        result = await translator.translate_description(
            english_description=english_description,
            game_name="Ejemplo de Juego",
        )

        print(f"\nJuego: {result.game_info.name}")
        print(f"Éxito: {result.success}")
        print(f"Fuente: {result.source.value}")
        print(f"Confianza: {result.confidence:.2f}")
        print(f"APIs usadas: {', '.join(result.apis_used)}")

        if result.game_info.short_description_es:
            print("\nDescripción traducida (ES):")
            print(result.game_info.short_description_es)

    except Exception as e:
        print(f"[ERROR] {e}")
        logger.exception("Error detallado")


async def example_3_name_and_description():
    """Ejemplo 3: Proporcionar nombre y descripción en inglés."""
    print("\n" + "=" * 70)
    print("EJEMPLO 3: Nombre de juego + descripción en inglés")
    print("=" * 70)

    translator = GameDescriptionTranslator()

    english_description = """
    In this action-packed platformer, you play as a brave explorer discovering
    ancient ruins and fighting against dark forces. Master unique abilities,
    solve challenging puzzles, and uncover the mysteries of a lost civilization.
    """

    try:
        result = await translator.translate_game_description(
            game_identifier="Adventure Explorer",
            english_description=english_description,
        )

        print(f"\nJuego: {result.game_info.name}")
        print(f"Éxito: {result.success}")
        print(f"Fuente: {result.source.value}")
        print(f"Confianza: {result.confidence:.2f}")

        if result.game_info.short_description_es:
            print("\nDescripción traducida (ES):")
            print(result.game_info.short_description_es)

    except Exception as e:
        print(f"[ERROR] {e}")
        logger.exception("Error detallado")


async def example_4_with_platform():
    """Ejemplo 4: Buscar juego con plataforma específica."""
    print("\n" + "=" * 70)
    print("EJEMPLO 4: Buscar juego con plataforma específica")
    print("=" * 70)

    translator = GameDescriptionTranslator()

    try:
        result = await translator.translate_game_description(
            game_identifier="The Legend of Zelda: Breath of the Wild",
            platform=Platform.NINTENDO_SWITCH,
        )

        print(f"\nJuego: {result.game_info.name}")
        print("Plataforma solicitada: Nintendo Switch")
        print(f"Éxito: {result.success}")
        print(f"Fuente: {result.source.value}")

        if result.game_info.platforms:
            print(
                f"Plataformas encontradas: {', '.join([p.value for p in result.game_info.platforms])}",
            )

        if result.game_info.short_description_es:
            print("\nDescripción (ES):")
            print(
                (
                    result.game_info.short_description_es[:300] + "..."
                    if len(result.game_info.short_description_es) > 300
                    else result.game_info.short_description_es
                ),
            )

    except Exception as e:
        print(f"[ERROR] {e}")
        logger.exception("Error detallado")


async def main():
    """Ejecuta todos los ejemplos."""
    print("=" * 70)
    print("EJEMPLOS DE USO - GAME DESCRIPTION TRANSLATOR")
    print("=" * 70)

    await example_1_search_by_name()
    await example_2_translate_description_only()
    await example_3_name_and_description()
    await example_4_with_platform()

    print("\n" + "=" * 70)
    print("[OK] EJEMPLOS COMPLETADOS")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[AVISO] Ejemplos interrumpidos por el usuario")
    except Exception as e:
        print(f"\n\n[ERROR] Error fatal: {e}")
        logger.exception("Error fatal")
