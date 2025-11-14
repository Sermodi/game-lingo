#!/usr/bin/env python3
"""
Script para probar todas las APIs configuradas con juegos específicos.

Prueba:
1. RAWG API - Buscar juegos y verificar descripciones en español
2. Steam API - Buscar juegos y verificar descripciones en español
3. DeepL API - Traducir texto de prueba
4. Google Translate API - Traducir texto de prueba

Uso:
    python test_all_apis.py
"""

import asyncio
import logging
import sys
from pathlib import Path

from game_lingo.apis.deepl_api import DeepLAPIConnector
from game_lingo.apis.google_translate_api import GoogleTranslateAPIConnector
from game_lingo.apis.rawg_api import RAWGAPIConnector
from game_lingo.apis.steam_api import SteamAPI
from game_lingo.config import settings
from game_lingo.exceptions import GameNotFoundError

# Añadir el directorio del proyecto al path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Juegos a probar
TEST_GAMES = [
    "Silksong",
    "Expedition 33",
    "Donkey Kong Country Returns",
    "Oxygen Not Included",
]

# Texto de prueba para traductores
TEST_TEXT_EN = """
Welcome to the world of adventure! This game offers an immersive experience
with stunning graphics and engaging gameplay. Explore vast worlds, battle
powerful enemies, and discover hidden treasures. The story will keep you
enthralled from beginning to end.
"""


async def test_rawg_api() -> None:
    """Prueba RAWG API con los juegos especificados."""
    print("\n" + "=" * 70)
    print("TEST 1: RAWG API")
    print("=" * 70)

    if not settings.RAWG_API_KEY:
        print("[AVISO] RAWG_API_KEY no configurada. Saltando test de RAWG.")
        return

    try:
        async with RAWGAPIConnector(settings.RAWG_API_KEY) as connector:
            for game_name in TEST_GAMES:
                print(f"\nBuscando: '{game_name}'")
                try:
                    # Usar find_game_by_name para obtener detalles completos
                    game_info = await connector.find_game_by_name(
                        game_name,
                        exact_match=False,
                    )

                    if game_info:
                        print(f"[OK] Encontrado: {game_info.name}")
                        print(f"   ID: {game_info.rawg_id or 'N/A'}")
                        print(f"   Rating: {game_info.user_score or 'N/A'}")

                        # Buscar descripción
                        description = (
                            game_info.short_description_en
                            or game_info.detailed_description_en
                            or ""
                        )
                        if description:
                            # Verificar si parece estar en español
                            spanish_indicators = [
                                "el",
                                "la",
                                "de",
                                "en",
                                "con",
                                "para",
                                "que",
                                "los",
                                "las",
                            ]
                            words = description.lower().split()
                            spanish_word_count = sum(
                                1 for word in words[:20] if word in spanish_indicators
                            )

                            if spanish_word_count > 2:
                                print("   [OK] Descripcion parece estar en ESPANOL")
                                desc_preview = (
                                    description[:150] + "..."
                                    if len(description) > 150
                                    else description
                                )
                                print(f"   Preview: {desc_preview}")
                            else:
                                print("   [AVISO] Descripcion parece estar en INGLES")
                                desc_preview = (
                                    description[:150] + "..."
                                    if len(description) > 150
                                    else description
                                )
                                print(f"   Preview: {desc_preview}")
                        else:
                            print("   [AVISO] No hay descripcion disponible")
                    else:
                        print("[ERROR] No se encontraron resultados")

                except GameNotFoundError:
                    print(f"[ERROR] No se encontro '{game_name}' en RAWG")
                except Exception as e:
                    print(f"[ERROR] Error: {e}")

                await asyncio.sleep(1)  # Rate limiting

    except Exception as e:
        print(f"[ERROR] Error general en RAWG API: {e}")


async def test_steam_api() -> None:
    """Prueba Steam API con los juegos especificados."""
    print("\n" + "=" * 70)
    print("TEST 2: STEAM API")
    print("=" * 70)

    try:
        async with SteamAPI() as steam:
            for game_name in TEST_GAMES:
                print(f"\nBuscando: '{game_name}'")
                try:
                    # Buscar en Steam
                    results = await steam.search_game(
                        game_name,
                        language="spanish",
                        max_results=3,
                    )

                    if results:
                        game = results[0]
                        print(f"[OK] Encontrado: {game.get('name', 'N/A')}")
                        print(f"   ID: {game.get('id', 'N/A')}")

                        # Intentar obtener detalles completos
                        try:
                            game_id = game.get("id")
                            if game_id:
                                game_info = await steam.find_game_by_name(
                                    game_name,
                                    language="spanish",
                                )
                                if game_info:
                                    if game_info.short_description_es:
                                        print(
                                            "   [OK] Descripcion en ESPANOL encontrada",
                                        )
                                        desc_preview = (
                                            game_info.short_description_es[:150] + "..."
                                            if len(game_info.short_description_es) > 150
                                            else game_info.short_description_es
                                        )
                                        print(f"   Preview: {desc_preview}")
                                    elif game_info.short_description_en:
                                        print(
                                            "   [AVISO] Solo descripcion en INGLES disponible",
                                        )
                                        desc_preview = (
                                            game_info.short_description_en[:150] + "..."
                                            if len(game_info.short_description_en) > 150
                                            else game_info.short_description_en
                                        )
                                        print(f"   Preview: {desc_preview}")
                                    else:
                                        print(
                                            "   [AVISO] No hay descripcion disponible",
                                        )
                        except Exception as e:
                            print(f"   [AVISO] No se pudieron obtener detalles: {e}")
                    else:
                        print("[ERROR] No se encontraron resultados")

                except GameNotFoundError:
                    print(f"[ERROR] No se encontro '{game_name}' en Steam")
                except Exception as e:
                    print(f"[ERROR] Error: {e}")

                await asyncio.sleep(1)  # Rate limiting

    except Exception as e:
        print(f"[ERROR] Error general en Steam API: {e}")


def test_deepl_api() -> None:
    """Prueba DeepL API con texto de prueba."""
    print("\n" + "=" * 70)
    print("TEST 3: DEEPL API")
    print("=" * 70)

    if not settings.DEEPL_API_KEY:
        print("[AVISO] DEEPL_API_KEY no configurada. Saltando test de DeepL.")
        return

    try:
        deepl = DeepLAPIConnector(api_key=settings.DEEPL_API_KEY)
        print("\nTexto original (EN):")
        print(f"{TEST_TEXT_EN[:100]}...")

        # Verificar uso actual
        try:
            usage = deepl.get_usage()
            print("\nUso de DeepL:")
            print(f"   Caracteres usados: {usage.character_count:,}")
            print(f"   Limite: {usage.character_limit:,}")
            print(f"   Porcentaje: {usage.usage_percentage:.2f}%")
        except Exception as e:
            print(f"   [AVISO] No se pudo obtener uso: {e}")

        # Traducir
        print("\nTraduciendo a espanol...")
        result = deepl.translate_text(
            text=TEST_TEXT_EN,
            target_language="ES",
            source_language="EN",
        )

        print("[OK] Traduccion exitosa:")
        print(f"   Idioma detectado: {result.detected_source_language or 'EN'}")
        print("   Texto traducido:")
        print(f"   {result.text[:200]}...")

        deepl.session.close()

    except Exception as e:
        print(f"[ERROR] Error en DeepL API: {e}")
        logger.exception("Error detallado")


def test_google_translate_api() -> None:
    """Prueba Google Translate API con texto de prueba."""
    print("\n" + "=" * 70)
    print("TEST 4: GOOGLE TRANSLATE API")
    print("=" * 70)

    if not settings.GOOGLE_TRANSLATE_API_KEY:
        print(
            "[AVISO] GOOGLE_TRANSLATE_API_KEY no configurada. Saltando test de Google Translate.",
        )
        return

    try:
        google = GoogleTranslateAPIConnector(api_key=settings.GOOGLE_TRANSLATE_API_KEY)
        print("\nTexto original (EN):")
        print(f"{TEST_TEXT_EN[:100]}...")

        # Traducir
        print("\nTraduciendo a espanol...")
        result = google.translate_text(
            text=TEST_TEXT_EN,
            target_language="es",
            source_language="en",
        )

        print("[OK] Traduccion exitosa:")
        print(
            f"   Idioma detectado: {getattr(result, 'detected_source_language', getattr(result, 'detected_language', 'en'))}",
        )
        print(f"   Confianza: {getattr(result, 'confidence', 'N/A')}")
        print(f"   Caracteres usados: {getattr(result, 'characters_used', 'N/A')}")
        print("   Texto traducido:")
        translated_text = getattr(
            result,
            "translated_text",
            getattr(result, "text", ""),
        )
        print(f"   {translated_text[:200]}...")

        google.session.close()

    except Exception as e:
        print(f"[ERROR] Error en Google Translate API: {e}")
        logger.exception("Error detallado")


async def main() -> None:
    """Ejecuta todos los tests."""
    print("=" * 70)
    print("PRUEBA COMPLETA DE TODAS LAS APIs")
    print("=" * 70)
    print(f"\nJuegos a probar: {', '.join(TEST_GAMES)}")
    print("\nAPIs configuradas:")
    print(f"  - RAWG: {'[OK]' if settings.RAWG_API_KEY else '[NO]'}")
    print("  - Steam: [OK] (siempre disponible)")
    print(f"  - DeepL: {'[OK]' if settings.DEEPL_API_KEY else '[NO]'}")
    print(
        f"  - Google Translate: {'[OK]' if settings.GOOGLE_TRANSLATE_API_KEY else '[NO]'}",
    )

    await test_rawg_api()
    await test_steam_api()
    test_deepl_api()  # DeepL es síncrono
    test_google_translate_api()  # Google Translate es síncrono

    print("\n" + "=" * 70)
    print("[OK] PRUEBAS COMPLETADAS")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[AVISO] Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n\n[ERROR] Error fatal: {e}")
        logger.exception("Error fatal")
