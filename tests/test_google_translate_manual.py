"""
Script de tests manuales para Google Translate API.

Este script permite probar manualmente las funcionalidades del conector
de Google Translate API con una API key real.

Uso:
    python tests/test_google_translate_manual.py

Requisitos:
    - API key de Google Cloud Translation configurada en .env
    - Conexión a internet
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Añadir el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from game_lingo.apis.google_translate_api import (
    GoogleTranslateAPIConnector,
    translate_game_description,
    detect_language,
    AuthenticationError,
    RateLimitError,
    TranslationError,
    ValidationError,
)
from game_lingo.models.game import GameInfo


def load_api_key() -> str:
    """Carga la API key desde variables de entorno."""
    # Intentar cargar desde .env
    env_file = root_dir / ".env"
    if env_file.exists():
        from dotenv import load_dotenv

        load_dotenv(env_file)

    api_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
    if not api_key:
        print("❌ Error: GOOGLE_TRANSLATE_API_KEY no encontrada")
        print("Configura tu API key en el archivo .env:")
        print("GOOGLE_TRANSLATE_API_KEY=tu_api_key_aqui")
        sys.exit(1)

    return api_key


def test_supported_languages(connector: GoogleTranslateAPIConnector) -> None:
    """Test obtener idiomas soportados."""
    print("\n🌍 Probando obtener idiomas soportados...")

    try:
        languages = connector.get_supported_languages()
        print(f"✅ Encontrados {len(languages)} idiomas soportados")

        # Mostrar algunos idiomas comunes
        common_codes = ["en", "es", "fr", "de", "it", "pt", "ja", "ko", "zh"]
        print("\n📋 Idiomas comunes encontrados:")
        for lang in languages:
            if lang.code in common_codes:
                print(f"  • {lang}")

    except Exception as e:
        print(f"❌ Error obteniendo idiomas: {e}")


def test_language_detection(connector: GoogleTranslateAPIConnector) -> None:
    """Test detección de idioma."""
    print("\n🔍 Probando detección de idioma...")

    test_texts = [
        "Hello, how are you today?",
        "Hola, ¿cómo estás hoy?",
        "Bonjour, comment allez-vous?",
        "Guten Tag, wie geht es Ihnen?",
        "こんにちは、元気ですか？",
        "Привет, как дела?",
    ]

    for text in test_texts:
        try:
            detection = connector.detect_language(text)
            print(f"  📝 '{text[:30]}...' → {detection}")
        except Exception as e:
            print(f"  ❌ Error detectando '{text[:30]}...': {e}")


def test_simple_translation(connector: GoogleTranslateAPIConnector) -> None:
    """Test traducción simple."""
    print("\n🔄 Probando traducción simple...")

    test_cases = [
        ("Hello world", "es"),
        ("Good morning", "fr"),
        ("Thank you very much", "de"),
        ("How are you?", "ja"),
        ("Beautiful day", "it"),
    ]

    for text, target_lang in test_cases:
        try:
            result = connector.translate_text(text, target_language=target_lang)
            print(
                f"  🔄 '{text}' → '{result.translated_text}' ({result.detected_source_language} → {target_lang})"
            )
        except Exception as e:
            print(f"  ❌ Error traduciendo '{text}': {e}")


def test_batch_translation(connector: GoogleTranslateAPIConnector) -> None:
    """Test traducción en lote."""
    print("\n📦 Probando traducción en lote...")

    texts = ["Hello", "world", "How are you?", "Good morning", "Thank you"]

    try:
        results = connector.translate_batch(texts, target_language="es")
        print(f"✅ Traducidos {len(results)} textos en lote:")
        for original, result in zip(texts, results):
            print(f"  🔄 '{original}' → '{result.translated_text}'")
    except Exception as e:
        print(f"❌ Error en traducción en lote: {e}")


def test_game_description_translation(connector: GoogleTranslateAPIConnector) -> None:
    """Test traducción de descripción de juego."""
    print("\n🎮 Probando traducción de descripción de juego...")

    test_games = [
        GameInfo(
            name="Epic Adventure",
            description="Embark on an epic journey through mystical lands filled with dangerous creatures and ancient treasures. Master powerful spells and forge legendary weapons as you battle against the forces of darkness.",
            steam_id=12345,
        ),
        GameInfo(
            name="Space Explorer",
            description="Explore the vast cosmos in this thrilling space simulation. Build your own spaceship, discover new planets, and engage in epic space battles with alien civilizations.",
            steam_id=67890,
        ),
        GameInfo(
            name="Racing Championship",
            description="Experience the ultimate racing simulation with realistic physics and stunning graphics. Compete in various championships around the world and customize your dream car.",
            steam_id=11111,
        ),
    ]

    target_languages = ["es", "fr", "de"]

    for game in test_games:
        print(f"\n🎯 Juego: {game.name}")
        print(f"📝 Descripción original: {game.description[:100]}...")

        for target_lang in target_languages:
            try:
                translated_game = connector.translate_game_description(
                    game, target_language=target_lang
                )
                print(
                    f"  🌍 {target_lang.upper()}: {translated_game.description[:100]}..."
                )
            except Exception as e:
                print(f"  ❌ Error traduciendo a {target_lang}: {e}")


def test_convenience_functions(api_key: str) -> None:
    """Test funciones de conveniencia."""
    print("\n🛠️ Probando funciones de conveniencia...")

    # Test detect_language
    try:
        detection = detect_language("Hello world", api_key=api_key)
        print(f"✅ Detección de idioma: {detection}")
    except Exception as e:
        print(f"❌ Error en detect_language: {e}")

    # Test translate_game_description
    game = GameInfo(
        name="Test Game",
        description="This is a simple test game with basic gameplay mechanics.",
        steam_id=99999,
    )

    try:
        translated_game = translate_game_description(
            game=game, target_language="es", api_key=api_key
        )
        print(f"✅ Traducción de juego:")
        print(f"  📝 Original: {game.description}")
        print(f"  🌍 Traducido: {translated_game.description}")
    except Exception as e:
        print(f"❌ Error en translate_game_description: {e}")


def test_error_handling(connector: GoogleTranslateAPIConnector) -> None:
    """Test manejo de errores."""
    print("\n⚠️ Probando manejo de errores...")

    # Test texto vacío
    try:
        connector.translate_text("", target_language="es")
        print("❌ Debería haber fallado con texto vacío")
    except ValidationError:
        print("✅ ValidationError correctamente lanzado para texto vacío")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

    # Test idioma objetivo vacío
    try:
        connector.translate_text("Hello", target_language="")
        print("❌ Debería haber fallado con idioma objetivo vacío")
    except ValidationError:
        print("✅ ValidationError correctamente lanzado para idioma objetivo vacío")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

    # Test lista vacía en batch
    try:
        connector.translate_batch([], target_language="es")
        print("❌ Debería haber fallado con lista vacía")
    except ValidationError:
        print("✅ ValidationError correctamente lanzado para lista vacía")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")


def main() -> None:
    """Función principal."""
    print("🚀 Iniciando tests manuales de Google Translate API")
    print("=" * 60)

    # Cargar API key
    api_key = load_api_key()
    print(f"✅ API key cargada: {api_key[:10]}...")

    # Crear conector
    try:
        with GoogleTranslateAPIConnector(api_key=api_key) as connector:
            print("✅ Conector creado exitosamente")

            # Ejecutar tests
            test_supported_languages(connector)
            test_language_detection(connector)
            test_simple_translation(connector)
            test_batch_translation(connector)
            test_game_description_translation(connector)
            test_error_handling(connector)

    except AuthenticationError:
        print("❌ Error de autenticación: Verifica tu API key")
    except RateLimitError:
        print("❌ Límite de rate excedido: Espera un momento e intenta de nuevo")
    except TranslationError as e:
        print(f"❌ Error de traducción: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

    # Test funciones de conveniencia
    test_convenience_functions(api_key)

    print("\n" + "=" * 60)
    print("✅ Tests manuales completados")


def interactive_mode() -> None:
    """Modo interactivo para probar traducciones."""
    print("\n🎯 Modo interactivo - Presiona Ctrl+C para salir")
    print("=" * 50)

    api_key = load_api_key()

    try:
        with GoogleTranslateAPIConnector(api_key=api_key) as connector:
            while True:
                try:
                    print("\n📝 Opciones:")
                    print("1. Traducir texto")
                    print("2. Detectar idioma")
                    print("3. Ver idiomas soportados")
                    print("4. Salir")

                    choice = input("\n🔢 Elige una opción (1-4): ").strip()

                    if choice == "1":
                        text = input("📝 Texto a traducir: ").strip()
                        if not text:
                            print("❌ El texto no puede estar vacío")
                            continue

                        target_lang = input(
                            "🌍 Idioma objetivo (ej: es, fr, de): "
                        ).strip()
                        if not target_lang:
                            print("❌ El idioma objetivo no puede estar vacío")
                            continue

                        try:
                            result = connector.translate_text(
                                text, target_language=target_lang
                            )
                            print(f"🔄 Resultado: '{result.translated_text}'")
                            print(
                                f"📊 Detectado: {result.detected_source_language} → {result.target_language}"
                            )
                        except Exception as e:
                            print(f"❌ Error: {e}")

                    elif choice == "2":
                        text = input("📝 Texto para detectar idioma: ").strip()
                        if not text:
                            print("❌ El texto no puede estar vacío")
                            continue

                        try:
                            detection = connector.detect_language(text)
                            print(f"🔍 Resultado: {detection}")
                        except Exception as e:
                            print(f"❌ Error: {e}")

                    elif choice == "3":
                        try:
                            languages = connector.get_supported_languages()
                            print(f"\n🌍 Idiomas soportados ({len(languages)}):")
                            for i, lang in enumerate(
                                languages[:20]
                            ):  # Mostrar solo los primeros 20
                                print(f"  {lang}")
                            if len(languages) > 20:
                                print(f"  ... y {len(languages) - 20} más")
                        except Exception as e:
                            print(f"❌ Error: {e}")

                    elif choice == "4":
                        print("👋 ¡Hasta luego!")
                        break

                    else:
                        print("❌ Opción inválida")

                except KeyboardInterrupt:
                    print("\n👋 ¡Hasta luego!")
                    break
                except Exception as e:
                    print(f"❌ Error inesperado: {e}")

    except Exception as e:
        print(f"❌ Error inicializando conector: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        main()
