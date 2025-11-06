#!/usr/bin/env python3
"""
Script de prueba manual para RAWG API.

Este script permite probar el conector de RAWG API de forma interactiva.
Requiere API key gratuita de RAWG (https://rawg.io/apidocs).

Uso:
    python tests/test_rawg_manual.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Añadir el directorio del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from game_lingo.apis.rawg_api import RAWGAPIConnector, search_rawg_game
from game_lingo.exceptions import (
    AuthenticationError,
    GameNotFoundError,
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_search_games():
    """Test de búsqueda de juegos."""
    print("\n" + "=" * 50)
    print("TEST: Búsqueda de juegos")
    print("=" * 50)

    # Obtener API key
    api_key = input(
        "Ingresa tu RAWG API key (o presiona Enter para usar variable de entorno): ",
    ).strip()
    if not api_key:
        import os

        api_key = os.getenv("RAWG_API_KEY")
        if not api_key:
            print("❌ No se encontró API key. Configura RAWG_API_KEY o ingresa una.")
            return

    try:
        async with RAWGAPIConnector(api_key) as connector:
            # Test búsquedas
            test_queries = [
                "The Witcher 3",
                "Cyberpunk 2077",
                "Grand Theft Auto V",
                "Minecraft",
                "Red Dead Redemption 2",
            ]

            for query in test_queries:
                try:
                    print(f"\n🔍 Buscando: '{query}'")
                    result = await connector.search_game(query, limit=5)

                    print(f"✅ Encontrados {result.count} juegos")
                    for i, game in enumerate(result.results[:3], 1):
                        print(
                            f"  {i}. {game['name']} (ID: {game['id']}, Rating: {game.get('rating', 'N/A')})",
                        )

                except GameNotFoundError:
                    print(f"❌ No se encontraron juegos para '{query}'")
                except Exception as e:
                    print(f"❌ Error buscando '{query}': {e}")

                # Pausa entre búsquedas para respetar rate limits
                await asyncio.sleep(1)

    except AuthenticationError as e:
        print(f"❌ Error de autenticación: {e}")
        print("Verifica que tu API key sea válida.")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")


async def test_game_details():
    """Test de obtención de detalles de juegos."""
    print("\n" + "=" * 50)
    print("TEST: Detalles de juegos")
    print("=" * 50)

    # Obtener API key
    api_key = input(
        "Ingresa tu RAWG API key (o presiona Enter para usar variable de entorno): ",
    ).strip()
    if not api_key:
        import os

        api_key = os.getenv("RAWG_API_KEY")
        if not api_key:
            print("❌ No se encontró API key.")
            return

    try:
        async with RAWGAPIConnector(api_key) as connector:
            # IDs de juegos conocidos en RAWG
            test_games = [
                (3328, "The Witcher 3: Wild Hunt"),
                (28, "Red Dead Redemption 2"),
                (3498, "Grand Theft Auto V"),
                (4200, "Portal 2"),
                (58175, "Cyberpunk 2077"),
            ]

            for game_id, expected_name in test_games:
                try:
                    print(
                        f"\n🎮 Obteniendo detalles del juego ID {game_id} ({expected_name})",
                    )
                    details = await connector.get_game_details(game_id)

                    print(f"✅ Nombre: {details['name']}")
                    print(f"   Fecha: {details.get('released', 'N/A')}")
                    print(f"   Rating: {details.get('rating', 'N/A')}")
                    print(f"   Metacritic: {details.get('metacritic', 'N/A')}")

                    # Mostrar plataformas
                    platforms = [
                        p["platform"]["name"] for p in details.get("platforms", [])
                    ]
                    print(f"   Plataformas: {', '.join(platforms[:5])}")

                    # Mostrar géneros
                    genres = [g["name"] for g in details.get("genres", [])]
                    print(f"   Géneros: {', '.join(genres)}")

                    # Descripción (truncada)
                    description = details.get(
                        "description_raw",
                        details.get("description", ""),
                    )
                    if description:
                        desc_preview = (
                            description[:100] + "..."
                            if len(description) > 100
                            else description
                        )
                        print(f"   Descripción: {desc_preview}")

                except GameNotFoundError:
                    print(f"❌ Juego ID {game_id} no encontrado")
                except Exception as e:
                    print(f"❌ Error obteniendo detalles del juego {game_id}: {e}")

                # Pausa entre llamadas
                await asyncio.sleep(1)

    except Exception as e:
        print(f"❌ Error inesperado: {e}")


async def test_find_by_name():
    """Test de búsqueda completa por nombre."""
    print("\n" + "=" * 50)
    print("TEST: Búsqueda completa por nombre")
    print("=" * 50)

    # Obtener API key
    api_key = input(
        "Ingresa tu RAWG API key (o presiona Enter para usar variable de entorno): ",
    ).strip()
    if not api_key:
        import os

        api_key = os.getenv("RAWG_API_KEY")
        if not api_key:
            print("❌ No se encontró API key.")
            return

    try:
        async with RAWGAPIConnector(api_key) as connector:
            test_games = [
                "The Witcher 3",
                "Cyberpunk 2077",
                "Minecraft",
                "Among Us",
                "Hades",
            ]

            for game_name in test_games:
                try:
                    print(f"\n🎯 Buscando información completa de: '{game_name}'")
                    game_info = await connector.find_game_by_name(game_name)

                    if game_info:
                        print(f"✅ Encontrado: {game_info.name}")
                        print(f"   ID externo: {game_info.external_id}")
                        print(f"   Fecha: {game_info.release_date}")
                        print(f"   Rating: {game_info.rating}")
                        print(f"   Plataformas: {', '.join(game_info.platforms[:3])}")
                        print(f"   Géneros: {', '.join(game_info.genres)}")
                        print(f"   Desarrolladores: {', '.join(game_info.developers)}")
                        print(f"   API fuente: {game_info.source_api}")

                        # Descripción truncada
                        if game_info.description:
                            desc_preview = (
                                game_info.description[:150] + "..."
                                if len(game_info.description) > 150
                                else game_info.description
                            )
                            print(f"   Descripción: {desc_preview}")
                    else:
                        print(f"❌ No se encontró información para '{game_name}'")

                except Exception as e:
                    print(f"❌ Error buscando '{game_name}': {e}")

                # Pausa entre búsquedas
                await asyncio.sleep(1)

    except Exception as e:
        print(f"❌ Error inesperado: {e}")


async def test_convenience_function():
    """Test de función de conveniencia."""
    print("\n" + "=" * 50)
    print("TEST: Función de conveniencia")
    print("=" * 50)

    # Obtener API key
    api_key = input(
        "Ingresa tu RAWG API key (o presiona Enter para usar variable de entorno): ",
    ).strip()
    if not api_key:
        import os

        api_key = os.getenv("RAWG_API_KEY")
        if not api_key:
            print("❌ No se encontró API key.")
            return

    try:
        print("🔧 Probando función de conveniencia search_rawg_game()")

        game_info = await search_rawg_game("Portal 2", api_key)

        if game_info:
            print("✅ Función de conveniencia exitosa!")
            print(f"   Juego: {game_info.name}")
            print(f"   Rating: {game_info.rating}")
            print(f"   API: {game_info.source_api}")
        else:
            print("❌ La función de conveniencia no devolvió resultados")

    except Exception as e:
        print(f"❌ Error en función de conveniencia: {e}")


async def interactive_mode():
    """Modo interactivo para pruebas personalizadas."""
    print("\n" + "=" * 50)
    print("MODO INTERACTIVO")
    print("=" * 50)

    # Obtener API key
    api_key = input(
        "Ingresa tu RAWG API key (o presiona Enter para usar variable de entorno): ",
    ).strip()
    if not api_key:
        import os

        api_key = os.getenv("RAWG_API_KEY")
        if not api_key:
            print("❌ No se encontró API key.")
            return

    try:
        async with RAWGAPIConnector(api_key) as connector:
            while True:
                print("\nOpciones:")
                print("1. Buscar juegos")
                print("2. Obtener detalles por ID")
                print("3. Búsqueda completa por nombre")
                print("4. Salir")

                choice = input("\nSelecciona una opción (1-4): ").strip()

                if choice == "1":
                    query = input("Ingresa el nombre del juego a buscar: ").strip()
                    if query:
                        try:
                            result = await connector.search_game(query)
                            print(f"\n✅ Encontrados {result.count} juegos:")
                            for i, game in enumerate(result.results[:10], 1):
                                print(f"  {i}. {game['name']} (ID: {game['id']})")
                        except Exception as e:
                            print(f"❌ Error: {e}")

                elif choice == "2":
                    try:
                        game_id = int(input("Ingresa el ID del juego: ").strip())
                        details = await connector.get_game_details(game_id)
                        print("\n✅ Detalles del juego:")
                        print(f"   Nombre: {details['name']}")
                        print(f"   Fecha: {details.get('released', 'N/A')}")
                        print(f"   Rating: {details.get('rating', 'N/A')}")
                    except ValueError:
                        print("❌ ID inválido. Debe ser un número.")
                    except Exception as e:
                        print(f"❌ Error: {e}")

                elif choice == "3":
                    query = input("Ingresa el nombre del juego: ").strip()
                    if query:
                        try:
                            game_info = await connector.find_game_by_name(query)
                            if game_info:
                                print("\n✅ Información completa:")
                                print(f"   Nombre: {game_info.name}")
                                print(
                                    f"   Plataformas: {', '.join(game_info.platforms)}",
                                )
                                print(f"   Géneros: {', '.join(game_info.genres)}")
                                print(f"   Rating: {game_info.rating}")
                            else:
                                print("❌ No se encontró el juego.")
                        except Exception as e:
                            print(f"❌ Error: {e}")

                elif choice == "4":
                    print("👋 ¡Hasta luego!")
                    break

                else:
                    print("❌ Opción inválida.")

                # Pausa entre operaciones
                await asyncio.sleep(0.5)

    except Exception as e:
        print(f"❌ Error en modo interactivo: {e}")


async def main():
    """Función principal."""
    print("🎮 RAWG API - Script de Prueba Manual")
    print("=====================================")
    print("Este script prueba el conector RAWG API.")
    print("Necesitas una API key gratuita de https://rawg.io/apidocs")

    while True:
        print("\n" + "=" * 50)
        print("MENÚ PRINCIPAL")
        print("=" * 50)
        print("1. Test de búsqueda de juegos")
        print("2. Test de detalles de juegos")
        print("3. Test de búsqueda completa por nombre")
        print("4. Test de función de conveniencia")
        print("5. Modo interactivo")
        print("6. Ejecutar todos los tests")
        print("7. Salir")

        choice = input("\nSelecciona una opción (1-7): ").strip()

        try:
            if choice == "1":
                await test_search_games()
            elif choice == "2":
                await test_game_details()
            elif choice == "3":
                await test_find_by_name()
            elif choice == "4":
                await test_convenience_function()
            elif choice == "5":
                await interactive_mode()
            elif choice == "6":
                await test_search_games()
                await test_game_details()
                await test_find_by_name()
                await test_convenience_function()
            elif choice == "7":
                print("👋 ¡Hasta luego!")
                break
            else:
                print("[ERROR] Opción inválida. Selecciona 1-7.")

        except KeyboardInterrupt:
            print("\n\n[!] Operación cancelada por el usuario.")
        except Exception as e:
            print(f"\n[ERROR] Error inesperado: {e}")
            logger.exception("Error en test manual")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Script terminado por el usuario.")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        logger.exception("Error fatal en script manual")
