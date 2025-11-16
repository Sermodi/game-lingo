"""
CLI (Command Line Interface) para GameLingo.

Permite usar el traductor desde la línea de comandos de forma interactiva.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from typing import Any, NoReturn

from . import __version__
from .core.translator import GameDescriptionTranslator
from .exceptions import GameNotFoundError, GameTranslatorError
from .models.game import Language, Platform

# Configurar UTF-8 para Windows
if sys.platform == "win32":
    # Configurar stdout y stderr para UTF-8
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    # Configurar la consola de Windows para UTF-8
    os.system("chcp 65001 > nul 2>&1")

# Configurar logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def setup_argparse() -> argparse.ArgumentParser:
    """Configura el parser de argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        prog="game-lingo",
        description="Multi-language video game description translator",
        epilog='Ejemplo: game-lingo search "Hollow Knight"',
    )

    # Subparsers para comandos principales
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Comando: config
    config_parser = subparsers.add_parser("config", help="Configuración de API keys")
    config_subparsers = config_parser.add_subparsers(
        dest="config_action",
        help="Acción de configuración",
    )

    # Subcomando: set
    set_parser = config_subparsers.add_parser("set", help="Establecer una clave API")
    set_parser.add_argument(
        "service",
        choices=["steam", "rawg", "deepl", "google_translate"],
        help="Servicio para configurar",
    )
    set_parser.add_argument("api_key", help="Clave API para el servicio")

    # Subcomando: show
    show_parser = config_subparsers.add_parser(
        "show",
        help="Mostrar configuración actual",
    )
    show_parser.add_argument(
        "--show-keys",
        action="store_true",
        help="Mostrar claves API (cuidado con la seguridad)",
    )

    # Comandos existentes
    for cmd in ["search", "translate", "describe", "info", "stats"]:
        subparsers.add_parser(cmd)

    # Argumentos globales
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Mostrar información detallada de depuración",
    )

    # Subcomandos
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Comando: search
    search_parser = subparsers.add_parser(
        "search",
        help="Buscar un juego y obtener su descripción en español",
    )
    search_parser.add_argument(
        "game_name",
        type=str,
        help="Nombre del juego a buscar",
    )
    search_parser.add_argument(
        "-p",
        "--platform",
        type=str,
        choices=["steam", "pc", "playstation", "xbox", "nintendo_switch", "mobile"],
        help="Plataforma específica (opcional)",
    )
    search_parser.add_argument(
        "--full",
        action="store_true",
        help="Mostrar descripción completa en lugar de la corta",
    )
    search_parser.add_argument(
        "-l",
        "--target-lang",
        type=str,
        default="es",
        help="Idioma destino (es, en, fr, de, ja, etc. - por defecto: es)",
    )

    # Comando: translate
    translate_parser = subparsers.add_parser(
        "translate",
        help="Traducir un texto directamente",
    )
    translate_parser.add_argument(
        "text",
        type=str,
        help="Texto a traducir (entre comillas si tiene espacios)",
    )
    translate_parser.add_argument(
        "-s",
        "--source",
        type=str,
        default="en",
        help="Idioma origen (por defecto: en)",
    )
    translate_parser.add_argument(
        "-t",
        "--target",
        type=str,
        default="es",
        help="Idioma destino (por defecto: es)",
    )
    translate_parser.add_argument(
        "--provider",
        type=str,
        choices=["deepl", "google", "auto"],
        default="auto",
        help="Proveedor de traducción (por defecto: auto)",
    )

    # Comando: describe
    describe_parser = subparsers.add_parser(
        "describe",
        help="Buscar juego con descripción proporcionada (usa nativa si existe, sino traduce)",
    )
    describe_parser.add_argument(
        "game_name",
        type=str,
        help="Nombre del juego",
    )
    describe_parser.add_argument(
        "description",
        type=str,
        help="Descripción del juego en inglés (entre comillas)",
    )
    describe_parser.add_argument(
        "--full",
        action="store_true",
        help="Mostrar descripción completa",
    )
    describe_parser.add_argument(
        "-l",
        "--target-lang",
        type=str,
        default="es",
        help="Idioma destino (es, en, fr, de, ja, etc. - por defecto: es)",
    )

    # Comando: info
    info_parser = subparsers.add_parser(
        "info",
        help="Obtener información detallada de un juego",
    )
    info_parser.add_argument(
        "game_name",
        type=str,
        help="Nombre del juego",
    )
    info_parser.add_argument(
        "-l",
        "--target-lang",
        type=str,
        default="es",
        help="Idioma destino (es, en, fr, de, ja, etc. - por defecto: es)",
    )

    # Comando: stats
    stats_parser = subparsers.add_parser(
        "stats",
        help="Mostrar estadísticas de uso de APIs y caché",
    )
    stats_parser.add_argument(
        "--reset",
        action="store_true",
        help="Resetear estadísticas después de mostrarlas",
    )

    return parser


def print_separator(char: str = "=", length: int = 70) -> None:
    """Imprime un separador visual."""
    print(char * length)


def print_game_result(
    result: Any,
    show_full: bool = False,
    target_lang: str = "es",
) -> None:
    """Imprime el resultado de búsqueda de un juego de forma formateada."""
    game = result.game_info

    print_separator()
    print(f"🎮 {game.name}")
    print_separator()

    # Información básica
    if game.steam_id:
        print(f"Steam ID: {game.steam_id}")
    if game.rawg_id:
        print(f"RAWG ID: {game.rawg_id}")

    if game.platforms:
        platforms_str = ", ".join([p.value for p in game.platforms[:5]])
        print(f"Plataformas: {platforms_str}")

    if game.genres:
        genres_str = ", ".join(game.genres[:5])
        print(f"Géneros: {genres_str}")

    if game.release_date:
        # Extraer solo el año si es una fecha completa
        if isinstance(game.release_date, str):
            year = (
                game.release_date.split("-")[0]
                if "-" in game.release_date
                else game.release_date
            )
            print(f"Año: {year}")
        else:
            print(f"Fecha: {game.release_date}")

    print()

    # Descripción en el idioma solicitado
    description = game.get_description(target_lang)

    # Fallback a inglés si no hay descripción en el idioma destino
    if not description:
        description = game.get_best_description_en()

    desc_type = "Descripción Completa" if show_full else "Descripción"

    if description:
        print(f"{desc_type}:")
        print(description)
        print()

    # Metadatos de traducción
    print_separator("-")
    print(f"Fuente: {result.source.value}")
    print(f"Confianza: {result.confidence:.2f}")
    print(f"Tiempo de procesamiento: {result.processing_time_ms}ms")

    if result.apis_used:
        print(f"APIs utilizadas: {', '.join(result.apis_used)}")

    print_separator()


def print_translation_result(result: Any) -> None:
    """Imprime el resultado de traducción de forma formateada."""
    print_separator()
    print("📝 Traducción")
    print_separator()

    # El resultado es un TranslationResult, obtener la descripción traducida
    description = (
        result.game_info.short_description_es
        or result.game_info.detailed_description_es
    )
    if description:
        print(description)
    else:
        print("(No se pudo traducir)")

    print()
    print_separator("-")
    print(f"Fuente: {result.source.value}")
    print(f"Confianza: {result.confidence:.2f}")
    print(f"Tiempo: {result.processing_time_ms}ms")

    if result.apis_used:
        print(f"APIs utilizadas: {', '.join(result.apis_used)}")

    print_separator()


async def cmd_search(args: argparse.Namespace) -> int:
    """Ejecuta el comando de búsqueda de juego."""
    try:
        translator = GameDescriptionTranslator()

        # Convertir plataforma si se especificó
        platform = None
        if args.platform:
            platform = Platform(args.platform.upper())

        # Obtener idioma destino
        target_lang = Language.from_string(args.target_lang)

        print(f"\n🔍 Buscando '{args.game_name}'...")
        if platform:
            print(f"   Plataforma: {platform.value}")
        print(f"   Idioma destino: {target_lang.value}")
        print()

        result = await translator.translate_game_description(
            game_identifier=args.game_name,
            platform=platform,
            target_lang=target_lang,
        )

        print_game_result(result, show_full=args.full, target_lang=target_lang.value)
        return 0

    except GameNotFoundError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        print(
            "   Intenta con otro nombre o sin especificar plataforma.",
            file=sys.stderr,
        )
        return 1

    except GameTranslatorError as e:
        print(f"\n❌ Error del traductor: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        logger.exception("Error inesperado")
        print(f"\n❌ Error inesperado: {e}", file=sys.stderr)
        return 1


async def cmd_translate(args: argparse.Namespace) -> int:
    """Ejecuta el comando de traducción directa."""
    try:
        translator = GameDescriptionTranslator()

        print("\n🔄 Traduciendo texto...")
        print()

        result = await translator.translate_description(
            english_description=args.text,
            game_name=None,
        )

        print_translation_result(result)
        return 0

    except GameTranslatorError as e:
        print(f"\n❌ Error de traducción: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        logger.exception("Error inesperado")
        print(f"\n❌ Error inesperado: {e}", file=sys.stderr)
        return 1


async def cmd_describe(args: argparse.Namespace) -> int:
    """Ejecuta el comando de búsqueda con descripción proporcionada."""
    try:
        translator = GameDescriptionTranslator()

        # Obtener idioma destino
        target_lang = Language.from_string(args.target_lang)

        print(f"\n🔍 Buscando '{args.game_name}' con descripción proporcionada...")
        print(f"   Idioma destino: {target_lang.value}")
        print()

        # Primero intentar buscar el juego
        try:
            result = await translator.translate_game_description(
                game_identifier=args.game_name,
                target_lang=target_lang,
            )

            # Si tiene descripción nativa en el idioma destino, usarla
            if result.game_info.has_description(target_lang):
                print(f"✅ Encontrada descripción nativa en {target_lang.value}")
                print_game_result(
                    result,
                    show_full=args.full,
                    target_lang=target_lang.value,
                )
                return 0
            print(
                f"[!] No hay descripción nativa en {target_lang.value}, traduciendo la proporcionada...",
            )
            print()
        except GameNotFoundError:
            print(
                "[!] Juego no encontrado en bases de datos, traduciendo descripción proporcionada...",
            )
            print()

        # Si no hay descripción nativa, traducir la proporcionada
        translation_result = await translator.translate_description(
            english_description=args.description,
            game_name=args.game_name,
            target_lang=target_lang,
        )

        # Mostrar resultado
        print_separator()
        print(f"[Game] {args.game_name}")
        print_separator()
        print()

        description = translation_result.game_info.get_description(target_lang)
        if description:
            print("Descripción (traducida):")
            print(description)
        else:
            print("(No se pudo traducir)")

        print()
        print_separator("-")
        print(f"Fuente: {translation_result.source.value}")
        print(f"Confianza: {translation_result.confidence:.2f}")
        print(f"Tiempo: {translation_result.processing_time_ms}ms")

        if translation_result.apis_used:
            print(f"APIs utilizadas: {', '.join(translation_result.apis_used)}")

        print_separator()

        return 0

    except GameTranslatorError as e:
        print(f"\n[!] Error: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        logger.exception("Error inesperado")
        print(f"\n[!] Error inesperado: {e}", file=sys.stderr)
        return 1


async def cmd_info(args: argparse.Namespace) -> int:
    """Ejecuta el comando de información detallada."""
    try:
        translator = GameDescriptionTranslator()

        # Obtener idioma destino
        target_lang = Language.from_string(args.target_lang)

        print(f"\n[Search] Obteniendo información de '{args.game_name}'...")
        print(f"   Idioma destino: {target_lang.value}")
        print()

        result = await translator.translate_game_description(
            game_identifier=args.game_name,
            target_lang=target_lang,
        )

        print_game_result(result, show_full=True, target_lang=target_lang.value)
        return 0

    except GameNotFoundError as e:
        print(f"\n[!] Error: {e}", file=sys.stderr)
        return 1

    except GameTranslatorError as e:
        print(f"\n[!] Error: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        logger.exception("Error inesperado")
        print(f"\n[!] Error inesperado: {e}", file=sys.stderr)
        return 1


async def cmd_stats(args: argparse.Namespace) -> int:
    """Ejecuta el comando de estadísticas."""
    try:
        translator = GameDescriptionTranslator()

        print("\n[Stats] Estadísticas de Uso")
        print_separator()
        print()

        # Estadísticas del Rate Limiter
        if translator.rate_limiter:
            print("[Rate Limiter] Uso de APIs")
            print_separator("-")
            print()
            print("[!] IMPORTANTE: Los límites usan ventanas deslizantes.")
            print("   Los requests se liberan automáticamente después de su ventana.")
            print("   'En uso ahora' = requests activos en la ventana actual")
            print("   'Total requests' (abajo) = histórico total desde el inicio")
            print()

            # Información de cada API con límites y disponibilidad
            apis_info = {
                "steam": {
                    "name": "Steam Store API",
                    "max_requests": 200,
                    "window": "5 minutos",
                    "max_chars": None,
                    "char_window": None,
                    "cost_free": True,
                    "cost_desc": "Gratuita",
                    "icon": "[Steam]",
                },
                "rawg": {
                    "name": "RAWG API",
                    "max_requests": 27,
                    "window": "1 hora",
                    "max_chars": None,
                    "char_window": None,
                    "cost_free": True,
                    "cost_desc": "Gratuita (requiere key)",
                    "icon": "[RAWG]",
                },
                "deepl": {
                    "name": "DeepL API",
                    "max_requests": 20,
                    "window": "1 minuto",
                    "max_chars": 500000,
                    "char_window": "1 mes",
                    "cost_free": True,
                    "cost_desc": "500k chars/mes gratis",
                    "icon": "[DeepL]",
                },
                "google": {
                    "name": "Google Translate",
                    "max_requests": 100,
                    "window": "1 minuto",
                    "max_chars": 500000,
                    "char_window": "1 mes",
                    "cost_free": True,
                    "cost_desc": "500k chars/mes gratis",
                    "icon": "[Google]",
                },
            }

            for api_name, info in apis_info.items():
                if api_name in translator.rate_limiter.api_limits:
                    api_limit = translator.rate_limiter.api_limits[api_name]

                    # Requests en la ventana actual (ventana deslizante)
                    requests_in_window = len(api_limit.request_times)
                    chars_in_window = sum(
                        char_count for _, char_count in api_limit.character_usage
                    )

                    print(f"\n{info['icon']} {info['name']}")
                    print(f"   {'─' * 50}")

                    # Requests - Ventana actual
                    requests_available = info["max_requests"] - requests_in_window
                    requests_percent = (
                        (requests_in_window / info["max_requests"] * 100)
                        if info["max_requests"] > 0
                        else 0
                    )

                    print(f"   [Stats] Requests (ventana de {info['window']}):")
                    print(
                        f"      En uso ahora: {requests_in_window}/{info['max_requests']} ({requests_percent:.1f}%)",
                    )
                    print(f"      Disponibles: {requests_available}")

                    if requests_in_window > 0:
                        print(
                            f"      [!] Nota: Los requests se liberan automáticamente después de {info['window']}",
                        )
                    else:
                        print(
                            f"      [OK] Ventana limpia - Puedes hacer {info['max_requests']} requests",
                        )

                    # Caracteres (solo para APIs de traducción)
                    if info["max_chars"]:
                        chars_available = info["max_chars"] - chars_in_window
                        chars_percent = (
                            (chars_in_window / info["max_chars"] * 100)
                            if info["max_chars"] > 0
                            else 0
                        )

                        print(
                            f"   [Stats] Caracteres (ventana de {info['char_window']}):",
                        )
                        print(
                            f"      En uso ahora: {chars_in_window:,}/{info['max_chars']:,} ({chars_percent:.1f}%)",
                        )
                        print(f"      Disponibles: {chars_available:,}")

                        if chars_in_window > 0:
                            print(
                                f"      [!] Nota: Se resetea cada {info['char_window']}",
                            )
                        else:
                            print("      [OK] Cuota completa disponible")

                    # Costo
                    status = "[OK] GRATIS" if info["cost_free"] else "[!] PAGO"
                    print(f"   [Cost] Costo: {status} - {info['cost_desc']}")

            # Estadísticas globales
            print()
            print("[Stats] Estadísticas Globales")
            print(
                f"   Total requests: {translator.rate_limiter.global_stats['total_requests']}",
            )
            print(
                f"   Total caracteres: {translator.rate_limiter.global_stats['total_characters']:,}",
            )
            print(
                f"   Rate limit hits: {translator.rate_limiter.global_stats['rate_limit_hits']}",
            )
            print(
                f"   Backoff events: {translator.rate_limiter.global_stats['backoff_events']}",
            )

            print()

        # Estadísticas del Caché
        if translator.cache:
            print()
            print("[Cache] Caché")
            print_separator("-")

            try:
                stats = await translator.cache.get_stats()

                print(f"\n   Entradas totales: {stats.get('total_entries', 0)}")
                print(f"   Entradas activas: {stats.get('active_entries', 0)}")
                print(f"   Entradas expiradas: {stats.get('expired_entries', 0)}")
                print(f"   Tamaño total: {stats.get('total_size_mb', 0):.2f} MB")

                if stats.get("total_requests", 0) > 0:
                    hit_rate = stats.get("hit_rate", 0) * 100
                    print(f"   Hit rate: {hit_rate:.1f}%")
                    print(f"   Hits: {stats.get('hits', 0)}")
                    print(f"   Misses: {stats.get('misses', 0)}")

            except Exception as e:
                print(f"   [!] No se pudieron obtener estadísticas: {e}")

            print()

        # Resumen de costos y proyección
        print()
        print("[Cost] Análisis de Costos")
        print_separator("-")
        print()

        # Calcular uso total de caracteres de traducción
        total_translation_chars = 0
        if translator.rate_limiter:
            for api_name in ["deepl", "google"]:
                if api_name in translator.rate_limiter.api_limits:
                    api_limit = translator.rate_limiter.api_limits[api_name]
                    chars = sum(
                        char_count for _, char_count in api_limit.character_usage
                    )
                    total_translation_chars += chars

        print("   [Stats] Uso Actual:")
        print(f"      Total caracteres traducidos: {total_translation_chars:,}")

        # Proyección mensual (asumiendo uso constante)
        if translator.rate_limiter.global_stats["total_requests"] > 0:
            # Estimación simple basada en uso actual
            chars_per_request = (
                total_translation_chars
                / translator.rate_limiter.global_stats["total_requests"]
                if translator.rate_limiter.global_stats["total_requests"] > 0
                else 0
            )

            print()
            print("[Stats] Proyección Mensual (si continúa este ritmo):")

            # Proyección para 1000 requests/mes
            projected_1k = int(chars_per_request * 1000)
            print(f"      Con 1,000 requests/mes: ~{projected_1k:,} caracteres")

            # Proyección para 10000 requests/mes
            projected_10k = int(chars_per_request * 10000)
            print(f"      Con 10,000 requests/mes: ~{projected_10k:,} caracteres")

            # Verificar si excede límites gratuitos
            print()
            print("   [Cost] Evaluación de Costos:")
            if projected_1k <= 500000:
                print("      [OK] Con 1k req/mes: GRATIS (dentro del límite)")
            else:
                excess = projected_1k - 500000
                print(f"      [!] Con 1k req/mes: Excede {excess:,} caracteres")
                print("         DeepL Pro: ~€5.49/mes")
                print(f"         Google Translate: ~${(excess / 1000000) * 20:.2f}/mes")

            if projected_10k <= 500000:
                print("      [OK] Con 10k req/mes: GRATIS (dentro del límite)")
            else:
                excess = projected_10k - 500000
                print(f"      [!] Con 10k req/mes: Excede {excess:,} caracteres")
                print("         DeepL Pro: ~€24.99/mes o más")
                print(f"         Google Translate: ~${(excess / 1000000) * 20:.2f}/mes")

        print()
        print("   [Info] Información de Planes:")
        print("      • DeepL Free: 500,000 caracteres/mes [OK] GRATIS")
        print("      • DeepL Pro Starter: 1M chars/mes - €5.49/mes")
        print("      • DeepL Pro Advanced: 10M chars/mes - €24.99/mes")
        print("      • Google Translate: 500k chars/mes gratis, luego $20/1M chars")
        print()
        print("   [Tips] Tips para Optimizar:")
        print("      • El caché reduce ~60-80% las peticiones repetidas")
        print("      • Steam y RAWG son siempre gratuitas (usa primero)")
        print("      • Solo se traduce cuando no hay descripción nativa")
        print()

        print_separator()

        if args.reset:
            print("\n[!] Función de reset no implementada aún")

        return 0

    except Exception as e:
        logger.exception("Error obteniendo estadísticas")
        print(f"\n[!] Error: {e}", file=sys.stderr)
        return 1


def show_help() -> None:
    """Muestra ayuda cuando no se especifica comando."""
    print("\nUso: game-lingo <comando> [opciones]")
    print("\nComandos disponibles:")
    print("  config              Configurar claves API y preferencias")
    print("  search <término>     Buscar juegos por nombre")
    print("  translate <texto>    Traducir texto de un juego")
    print("  describe <juego>     Obtener descripción de un juego")
    print("  info <id>            Mostrar información detallada de un juego")
    print("  stats                Mostrar estadísticas de uso")
    print("\nConfiguración:")
    print("  game-lingo config set <servicio> <clave_api>  Configurar una clave API")
    print(
        "  game-lingo config show                        Mostrar configuración actual",
    )
    print(
        "  game-lingo config show --show-keys            Mostrar claves API (con precaución)",
    )
    print("\nEjemplos:")
    print("  game-lingo config set steam TU_CLAVE_DE_STEAM")
    print('  game-lingo search "The Witcher 3"')
    print('  game-lingo translate "Embark on an epic journey" --source en --target es')
    print('  game-lingo describe "Hollow Knight"')
    print("  game-lingo info 292030")
    print("  game-lingo stats")
    print("\nPara ayuda detallada de un comando: game-lingo <comando> -h")


async def async_main(args: argparse.Namespace) -> None:
    """Función principal asíncrona."""
    try:
        if args.command == "config":
            cmd_config(args)
            return

        translator = GameDescriptionTranslator()

        if args.command == "search":
            await cmd_search(args)
        elif args.command == "translate":
            await cmd_translate(args)
        elif args.command == "describe":
            await cmd_describe(args)
        elif args.command == "info":
            await cmd_info(args)
        elif args.command == "stats":
            await cmd_stats(args)
        else:
            show_help()
            sys.exit(1)
    except (GameNotFoundError, GameTranslatorError) as e:
        logger.error("Error: %s", str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario.")
        sys.exit(0)


def cmd_config(args: argparse.Namespace) -> None:
    """Maneja los comandos de configuración."""
    from .config import CONFIG_FILE, configure_api_key, settings

    if args.config_action == "set":
        # Configurar una clave API
        configure_api_key(args.service, args.api_key)
        print(f"✅ Clave API para {args.service} configurada correctamente.")
        print(f"Configuración guardada en: {CONFIG_FILE}")

    elif args.config_action == "show":
        # Mostrar configuración actual
        print("\n🔧 Configuración actual:")
        print(f"Archivo de configuración: {CONFIG_FILE}")
        print("\n🔑 Servicios configurados:")

        services = {
            "steam": "Steam",
            "rawg": "RAWG",
            "deepl": "DeepL",
            "google_translate": "Google Translate",
        }

        for service, name in services.items():
            key = getattr(settings, f"{service.upper()}_API_KEY", "")
            status = "✅ Configurado" if key else "❌ No configurado"
            if args.show_keys and key:
                status = f"🔑 {key[:5]}...{key[-3:] if len(key) > 8 else ''}"
            print(f"  {name}: {status}")

        if not args.show_keys:
            print("\n💡 Usa '--show-keys' para ver las claves API (con precaución).")

    else:
        print("Uso: game-lingo config [set|show] [opciones]")
        print("\nEjemplos:")
        print("  game-lingo config set steam TU_CLAVE_DE_STEAM")
        print("  game-lingo config show")
        print("  game-lingo config show --show-keys")


def main() -> NoReturn:
    """Punto de entrada principal del CLI."""
    parser = setup_argparse()
    args = parser.parse_args()

    try:
        exit_code = asyncio.run(async_main(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[!] Operación cancelada por el usuario", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        logger.exception("Error fatal")
        print(f"\n[!] Error fatal: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
