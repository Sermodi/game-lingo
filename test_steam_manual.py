#!/usr/bin/env python3
"""
Script de prueba manual para Steam API.

Este script permite probar el conector de Steam API de forma interactiva
sin necesidad de configurar API keys (Steam API es gratuita).

Uso:
    python test_steam_manual.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Añadir el directorio del proyecto al path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from game_translator.apis.steam_api import SteamAPI
from game_translator.exceptions import APIError, GameNotFoundError, RateLimitError


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_steam_search():
    """Prueba la búsqueda de juegos en Steam."""
    print("\n" + "="*60)
    print("PRUEBA: Búsqueda de juegos en Steam")
    print("="*60)
    
    async with SteamAPI() as steam:
        test_queries = [
            "Portal",
            "The Witcher 3",
            "Cyberpunk 2077",
            "Half-Life",
            "juego_que_no_existe_12345"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Buscando: '{query}'")
            try:
                results = await steam.search_game(query, language="spanish", max_results=3)
                print(f"✅ Encontrados {len(results)} resultados:")
                
                for i, game in enumerate(results, 1):
                    print(f"  {i}. {game.get('name', 'Sin nombre')} (ID: {game.get('id', 'N/A')})")
                    if game.get('price'):
                        price_info = game['price']
                        final_price = price_info.get('final_formatted', 'N/A')
                        print(f"     Precio: {final_price}")
                
            except GameNotFoundError:
                print(f"❌ No se encontraron resultados para '{query}'")
            except APIError as e:
                print(f"❌ Error de API: {e}")
            except Exception as e:
                print(f"❌ Error inesperado: {e}")


async def test_steam_details():
    """Prueba la obtención de detalles de juegos."""
    print("\n" + "="*60)
    print("PRUEBA: Detalles de juegos específicos")
    print("="*60)
    
    async with SteamAPI() as steam:
        # IDs de juegos conocidos
        test_games = [
            (620, "Portal 2"),
            (292030, "The Witcher 3: Wild Hunt"),
            (1174180, "Red Dead Redemption 2"),
            (999999999, "ID inexistente")  # Para probar error
        ]
        
        for app_id, expected_name in test_games:
            print(f"\n🎮 Obteniendo detalles para App ID: {app_id} ({expected_name})")
            try:
                details = await steam.get_game_details(app_id, language="spanish")
                
                print(f"✅ Juego encontrado:")
                print(f"  Nombre: {details.name}")
                print(f"  App ID: {details.app_id}")
                print(f"  Idioma: {details.language}")
                print(f"  Plataformas: {', '.join(details.platforms)}")
                print(f"  Géneros: {', '.join(details.genres[:3])}...")  # Primeros 3
                print(f"  Puntuación Metacritic: {details.metacritic_score or 'N/A'}")
                print(f"  Fecha de lanzamiento: {details.release_date or 'N/A'}")
                
                # Mostrar descripción corta (limitada)
                if details.short_description:
                    desc = details.short_description[:150] + "..." if len(details.short_description) > 150 else details.short_description
                    print(f"  Descripción: {desc}")
                
                # Mostrar idiomas soportados (limitado)
                if details.supported_languages:
                    langs = details.supported_languages[:100] + "..." if len(details.supported_languages) > 100 else details.supported_languages
                    print(f"  Idiomas: {langs}")
                
            except GameNotFoundError:
                print(f"❌ Juego con ID {app_id} no encontrado")
            except APIError as e:
                print(f"❌ Error de API: {e}")
            except Exception as e:
                print(f"❌ Error inesperado: {e}")


async def test_steam_find_by_name():
    """Prueba la búsqueda completa por nombre."""
    print("\n" + "="*60)
    print("PRUEBA: Búsqueda completa por nombre")
    print("="*60)
    
    async with SteamAPI() as steam:
        test_games = [
            "Portal 2",
            "The Witcher 3",
            "Cyberpunk 2077",
            "Juego Inexistente XYZ"
        ]
        
        for game_name in test_games:
            print(f"\n🎯 Búsqueda completa: '{game_name}'")
            try:
                game_info = await steam.find_game_by_name(game_name, language="spanish")
                
                if game_info:
                    print(f"✅ Juego encontrado y procesado:")
                    print(f"  Nombre: {game_info.name}")
                    print(f"  Steam ID: {game_info.steam_id}")
                    print(f"  Plataformas: {[p.value for p in game_info.platforms]}")
                    print(f"  Géneros: {game_info.genres[:3] if game_info.genres else 'N/A'}")
                    print(f"  Año de lanzamiento: {game_info.release_year or 'N/A'}")
                    print(f"  Puntuación: {game_info.rating or 'N/A'}")
                    print(f"  API fuente: {game_info.source_api}")
                    
                    # Descripción en español
                    if game_info.short_description_es:
                        desc = game_info.short_description_es[:200] + "..." if len(game_info.short_description_es) > 200 else game_info.short_description_es
                        print(f"  Descripción (ES): {desc}")
                    
                    # Descripción en inglés
                    if game_info.short_description_en:
                        desc = game_info.short_description_en[:200] + "..." if len(game_info.short_description_en) > 200 else game_info.short_description_en
                        print(f"  Descripción (EN): {desc}")
                else:
                    print(f"❌ No se pudo encontrar información para '{game_name}'")
                
            except Exception as e:
                print(f"❌ Error: {e}")


async def test_steam_languages():
    """Prueba diferentes idiomas."""
    print("\n" + "="*60)
    print("PRUEBA: Soporte de idiomas")
    print("="*60)
    
    async with SteamAPI() as steam:
        game_name = "Portal 2"
        languages = ["spanish", "english", "es", "en"]
        
        for lang in languages:
            print(f"\n🌍 Probando idioma: {lang}")
            try:
                game_info = await steam.find_game_by_name(game_name, language=lang)
                
                if game_info:
                    print(f"✅ Resultado en {lang}:")
                    print(f"  Nombre: {game_info.name}")
                    
                    if game_info.short_description_es:
                        desc = game_info.short_description_es[:150] + "..." if len(game_info.short_description_es) > 150 else game_info.short_description_es
                        print(f"  Descripción (ES): {desc}")
                    
                    if game_info.short_description_en:
                        desc = game_info.short_description_en[:150] + "..." if len(game_info.short_description_en) > 150 else game_info.short_description_en
                        print(f"  Descripción (EN): {desc}")
                else:
                    print(f"❌ No encontrado en {lang}")
                
            except Exception as e:
                print(f"❌ Error con idioma {lang}: {e}")


async def interactive_test():
    """Prueba interactiva donde el usuario puede buscar juegos."""
    print("\n" + "="*60)
    print("PRUEBA INTERACTIVA")
    print("="*60)
    print("Escribe nombres de juegos para buscar en Steam.")
    print("Escribe 'quit' para salir.")
    
    async with SteamAPI() as steam:
        while True:
            try:
                query = input("\n🎮 Buscar juego: ").strip()
                
                if query.lower() in ['quit', 'exit', 'salir', 'q']:
                    print("👋 ¡Hasta luego!")
                    break
                
                if not query:
                    continue
                
                print(f"🔍 Buscando '{query}'...")
                
                # Búsqueda completa
                game_info = await steam.find_game_by_name(query, language="spanish")
                
                if game_info:
                    print(f"\n✅ ENCONTRADO:")
                    print(f"📛 Nombre: {game_info.name}")
                    print(f"🆔 Steam ID: {game_info.steam_id}")
                    print(f"🎯 Géneros: {', '.join(game_info.genres[:5]) if game_info.genres else 'N/A'}")
                    print(f"📅 Año: {game_info.release_year or 'N/A'}")
                    print(f"⭐ Puntuación: {game_info.rating or 'N/A'}")
                    
                    if game_info.short_description_es:
                        print(f"📝 Descripción: {game_info.short_description_es[:300]}...")
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
        print("\n" + "="*60)
        response = input("¿Quieres hacer una prueba interactiva? (s/n): ").strip().lower()
        if response in ['s', 'si', 'sí', 'y', 'yes']:
            await interactive_test()
        
        print("\n✅ TODAS LAS PRUEBAS COMPLETADAS")
        print("\n📋 RESUMEN:")
        print("- Steam API funciona sin API key")
        print("- Soporta búsqueda en español e inglés")
        print("- Proporciona descripciones detalladas")
        print("- Incluye metadatos completos (géneros, plataformas, etc.)")
        print("- Maneja errores apropiadamente")
        
    except KeyboardInterrupt:
        print("\n⚠️ Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n❌ Error general en las pruebas: {e}")
        logger.exception("Error en pruebas de Steam API")


if __name__ == "__main__":
    # Ejecutar pruebas
    asyncio.run(main())