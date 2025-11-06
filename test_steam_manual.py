#!/usr/bin/env python3
"""
Script de prueba manual para Steam API.

Este script permite probar el conector de Steam API de forma interactiva
sin necesidad de configurar API keys (Steam API es gratuita).

Uso:
    python -m pytest test_steam_manual.py -v
"""

import asyncio
import logging
import sys
from pathlib import Path

import pytest

# Añadir el directorio del proyecto al path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from game_lingo.apis.steam_api import SteamAPI
from game_lingo.exceptions import GameNotFoundError, RateLimitError

# Configurar logging para pruebas
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Fixture para la API de Steam
@pytest.fixture
def steam_api():
    """Fixture que proporciona una instancia de SteamAPI."""
    return SteamAPI()


# Juegos de prueba para diferentes escenarios
TEST_GAMES = [
    (620, "Portal 2"),
    (292030, "The Witcher 3: Wild Hunt"),
    (1174180, "Red Dead Redemption 2"),
]

# Consultas de búsqueda de prueba
TEST_SEARCH_QUERIES = ["Portal", "The Witcher 3", "Cyberpunk 2077", "Half-Life"]


@pytest.mark.asyncio
async def test_steam_search(steam_api):
    """Prueba la búsqueda de juegos en Steam."""
    for query in TEST_SEARCH_QUERIES:
        results = await steam_api.search_game(query, language="spanish", max_results=3)

        # Verificar que los resultados son una lista
        assert isinstance(
            results, list,
        ), f"Los resultados para '{query}' deberían ser una lista"

        # Verificar que hay al menos un resultado para consultas conocidas
        if query != "juego_que_no_existe_12345":
            assert len(results) > 0, f"Se esperaba al menos un resultado para '{query}'"

            # Verificar que cada resultado tiene los campos requeridos
            for game in results:
                assert "id" in game, "Cada juego debe tener un ID"
                assert "name" in game, "Cada juego debe tener un nombre"
                assert isinstance(
                    game["name"], str,
                ), "El nombre del juego debe ser una cadena"


@pytest.mark.asyncio
async def test_steam_search_nonexistent(steam_api):
    """Prueba la búsqueda de un juego que no existe."""
    with pytest.raises(GameNotFoundError):
        await steam_api.search_game("juego_que_no_existe_12345", language="spanish")


@pytest.mark.asyncio
async def test_steam_details(steam_api):
    """Prueba la obtención de detalles de juegos."""
    for app_id, expected_name in TEST_GAMES:
        details = await steam_api.get_game_details(app_id, language="spanish")

        # Verificaciones básicas
        assert (
            details is not None
        ), f"No se encontraron detalles para el juego con ID {app_id}"
        assert (
            details.name == expected_name
        ), f"El nombre del juego no coincide para ID {app_id}"
        assert details.app_id == app_id, "El ID de la aplicación no coincide"
        assert isinstance(
            details.platforms, list,
        ), "Las plataformas deben ser una lista"
        assert isinstance(details.genres, list), "Los géneros deben ser una lista"

        # Verificar que al menos hay una plataforma
        assert (
            len(details.platforms) > 0
        ), f"El juego {expected_name} debe tener al menos una plataforma"

        # Verificar que la descripción existe y es una cadena
        assert details.short_description is None or isinstance(
            details.short_description, str,
        ), "La descripción debe ser una cadena o None"


@pytest.mark.asyncio
async def test_steam_details_nonexistent(steam_api):
    """Prueba la obtención de detalles de un juego que no existe."""
    with pytest.raises(GameNotFoundError):
        await steam_api.get_game_details(999999999, language="spanish")


@pytest.mark.asyncio
async def test_steam_find_by_name(steam_api):
    """Prueba la búsqueda completa por nombre."""
    test_games = ["Portal 2", "The Witcher 3", "Cyberpunk 2077"]

    for game_name in test_games:
        game_info = await steam_api.find_game_by_name(game_name, language="spanish")

        # Verificaciones básicas
        assert game_info is not None, f"No se encontró información para '{game_name}'"
        assert game_info.name, "El nombre del juego no debe estar vacío"
        assert game_info.steam_id, "El ID de Steam no debe estar vacío"
        assert isinstance(
            game_info.platforms, list,
        ), "Las plataformas deben ser una lista"
        assert isinstance(game_info.genres, list), "Los géneros deben ser una lista"

        # Verificar que al menos hay una descripción
        assert (
            game_info.short_description_es or game_info.short_description_en
        ), f"El juego {game_name} debe tener al menos una descripción (ES o EN)"


@pytest.mark.asyncio
async def test_steam_find_by_name_nonexistent(steam_api):
    """Prueba la búsqueda de un juego que no existe."""
    with pytest.raises(GameNotFoundError):
        await steam_api.find_game_by_name("Juego Inexistente XYZ", language="spanish")


@pytest.mark.asyncio
async def test_steam_languages(steam_api):
    """Prueba diferentes idiomas."""
    test_text = "The quick brown fox jumps over the lazy dog"
    languages = ["spanish", "french", "german", "russian", "japanese"]

    for lang in languages:
        try:
            # Buscar un juego popular para probar el idioma
            results = await steam_api.search_game(
                "Portal", language=lang, max_results=1,
            )

            # Verificar que se obtuvieron resultados
            assert results, f"No se encontraron resultados para el idioma {lang}"

            game_id = results[0].get("id")
            if game_id:
                details = await steam_api.get_game_details(game_id, language=lang)

                # Verificaciones básicas
                assert (
                    details is not None
                ), f"No se encontraron detalles para el juego en {lang}"
                assert (
                    details.name
                ), f"El nombre del juego no debe estar vacío en {lang}"

        except Exception as e:
            pytest.fail(f"Error con el idioma {lang}: {e}")


# Tests para verificar el manejo de errores
@pytest.mark.asyncio
async def test_rate_limiting(steam_api):
    """Prueba el manejo de límites de tasa."""
    # Hacer múltiples solicitudes rápidamente para probar el límite de tasa
    with pytest.raises(RateLimitError):
        for _ in range(20):  # Número suficientemente alto para alcanzar el límite
            await steam_api.search_game("test", language="spanish")


@pytest.mark.asyncio
async def test_invalid_language(steam_api):
    """Prueba con un idioma no válido."""
    with pytest.raises(ValueError):
        await steam_api.search_game("Portal", language="invalid_language")


# Tests de integración
@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_steam_workflow(steam_api):
    """Prueba un flujo completo de búsqueda y obtención de detalles."""
    # 1. Buscar un juego
    results = await steam_api.search_game("Portal 2", language="spanish")
    assert results, "Debería encontrar al menos un resultado para 'Portal 2'"

    # 2. Obtener detalles del primer resultado
    game_id = results[0].get("id")
    assert game_id, "El ID del juego no debe estar vacío"

    details = await steam_api.get_game_details(game_id, language="spanish")
    assert details is not None, "Debería encontrar detalles para el juego"

    # 3. Verificar que los detalles básicos estén presentes
    assert details.name == "Portal 2", "El nombre del juego debería ser 'Portal 2'"
    assert details.app_id == game_id, "El ID del juego debería coincidir"
    assert isinstance(details.platforms, list), "Las plataformas deben ser una lista"
    assert len(details.platforms) > 0, "Debería tener al menos una plataforma"

    # 4. Buscar por nombre para obtener información completa
    game_info = await steam_api.find_game_by_name("Portal 2", language="spanish")
    assert game_info is not None, "Debería encontrar información para 'Portal 2'"
    assert game_info.steam_id == game_id, "El ID de Steam debería coincidir"
    assert (
        game_info.short_description_es or game_info.short_description_en
    ), "Debería tener al menos una descripción"


async def interactive_test():
    """Prueba interactiva donde el usuario puede buscar juegos."""
    print("\n" + "=" * 60)
    print("PRUEBA INTERACTIVA")
    print("=" * 60)
    print("Escribe nombres de juegos para buscar en Steam.")
    print("Escribe 'quit' para salir.")

    async with SteamAPI() as steam:
        while True:
            try:
                query = input("\n🎮 Buscar juego: ").strip()

                if query.lower() in ["quit", "exit", "salir", "q"]:
                    print("👋 ¡Hasta luego!")
                    break

                if not query:
                    continue

                print(f"🔍 Buscando '{query}'...")

                # Búsqueda completa
                game_info = await steam.find_game_by_name(query, language="spanish")

                if game_info:
                    print("\n✅ ENCONTRADO:")
                    print(f"📛 Nombre: {game_info.name}")
                    print(f"🆔 Steam ID: {game_info.steam_id}")
                    print(
                        f"🎯 Géneros: {', '.join(game_info.genres[:5]) if game_info.genres else 'N/A'}",
                    )
                    print(f"📅 Año: {game_info.release_year or 'N/A'}")
                    print(f"⭐ Puntuación: {game_info.rating or 'N/A'}")

                    if game_info.short_description_es:
                        print(
                            f"📝 Descripción: {game_info.short_description_es[:300]}...",
                        )
                else:
                    print("❌ No se encontró el juego")

            except KeyboardInterrupt:
                print("\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


async def main():
    """Función principal que ejecuta todas las pruebas."""
    print("🚀 INICIANDO PRUEBAS DE STEAM API")
    print("Steam Store API es gratuita y no requiere API key")
    print("Estas pruebas harán requests reales a Steam")

    try:
        # Ejecutar pruebas automáticas
        await test_steam_search()
        await test_steam_details()
        await test_steam_find_by_name()
        await test_steam_languages()

        # Preguntar si quiere prueba interactiva
        print("\n" + "=" * 60)
        response = (
            input("¿Quieres hacer una prueba interactiva? (s/n): ").strip().lower()
        )
        if response in ["s", "si", "sí", "y", "yes"]:
            await interactive_test()

        print("\n✅ TODAS LAS PRUEBAS COMPLETADAS")
        print("\n📋 RESUMEN:")
        print("- Steam API funciona sin API key")
        print("- Soporta búsqueda en español e inglés")
        print("- Proporciona descripciones detalladas")
        print("- Incluye metadatos completos (géneros, plataformas, etc.)")
        print("- Maneja errores apropiadamente")

    except KeyboardInterrupt:
        print("\n[!] Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n[ERROR] Error general en las pruebas: {e}")
        logger.exception("Error en pruebas de Steam API")


if __name__ == "__main__":
    # Ejecutar pruebas
    asyncio.run(main())
