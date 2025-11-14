"""
Test manual para DeepL API.

Este script permite probar manualmente las funcionalidades del conector DeepL API.
Requiere una API key válida de DeepL.

Uso:
    python test_deepl_manual.py
"""

import os
import sys
from pathlib import Path

# Añadir el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import pytest
import pytest_asyncio

from game_lingo.apis.deepl_api import DeepLAPIConnector
from game_lingo.exceptions import AuthenticationError, TranslationError, ValidationError


# Fixture para el conector DeepL
@pytest_asyncio.fixture
async def deepl_connector():
    api_key = os.getenv("DEEPL_API_KEY")
    if not api_key:
        pytest.skip("DEEPL_API_KEY environment variable not set")
    async with DeepLAPIConnector(api_key=api_key) as connector:
        yield connector


@pytest.mark.asyncio()
async def test_usage_info(deepl_connector):
    """Test obtener información de uso de la API."""
    usage = await deepl_connector.get_usage()

    assert hasattr(usage, "character_count")
    assert hasattr(usage, "character_limit")
    assert hasattr(usage, "character_percentage")
    assert hasattr(usage, "character_limit_reached")

    print(f"✅ Caracteres usados: {usage.character_count:,}")
    print(f"✅ Límite de caracteres: {usage.character_limit:,}")
    print(f"✅ Porcentaje de uso: {usage.character_percentage}%")
    if usage.character_percentage > 80:
        print("[WARN] Advertencia: Cerca del límite de caracteres")

    # Verificaciones con aserciones
    assert isinstance(usage.character_count, int), "character_count debe ser un entero"
    assert isinstance(usage.character_limit, int), "character_limit debe ser un entero"
    assert (
        0 <= usage.character_percentage <= 100
    ), "El porcentaje debe estar entre 0 y 100"


@pytest.mark.asyncio()
async def test_supported_languages(deepl_connector):
    """Test obtener idiomas soportados."""
    # Obtener idiomas de origen
    source_languages = await deepl_connector.get_source_languages()

    # Obtener idiomas de destino
    target_languages = await deepl_connector.get_target_languages()

    # Verificar que hay idiomas disponibles
    assert len(source_languages) > 0
    assert len(target_languages) > 0

    # Verificar que los códigos de idioma son correctos
    assert any(lang.code == "EN" for lang in source_languages)
    assert any(lang.code == "ES" for lang in target_languages)

    print("\nIdiomas de origen soportados:")
    for lang in source_languages[:5]:  # Mostrar solo los primeros 5 para no saturar
        print(f"- {lang.name} ({lang.code})")

    print("\nIdiomas de destino soportados:")
    for lang in target_languages[:5]:  # Mostrar solo los primeros 5 para no saturar
        print(f"- {lang.name} ({lang.code})")


@pytest.mark.asyncio()
async def test_simple_translation(deepl_connector):
    """Test traducción simple."""
    test_texts = [
        ("Hello world", "ES"),
        ("Good morning", "ES"),
        ("Thank you very much", "ES"),
        ("How are you today?", "ES"),
    ]

    for text, target_lang in test_texts:
        result = await deepl_connector.translate_text(text, target_lang)
        print(f"✅ '{text}' -> '{result.text}'")

        # Verificaciones
        assert result.text, "El texto traducido no debe estar vacío"
        assert (
            result.detected_source_language == "EN"
        ), "El idioma de origen detectado debería ser inglés"

        if result.detected_source_language:
            print(f"   Idioma detectado: {result.detected_source_language}")


@pytest.mark.asyncio()
async def test_game_description_translation(deepl_connector):
    """Test traducción de descripciones de juegos."""
    game_descriptions = [
        "An epic fantasy adventure game with stunning visuals and immersive gameplay.",
        "Build and manage your own city in this strategic simulation game.",
        "Fast-paced action shooter with multiplayer battles and customizable weapons.",
        "Explore mysterious dungeons and collect powerful artifacts in this RPG.",
        "Race through challenging tracks with realistic physics and dynamic weather.",
    ]

    for i, description in enumerate(game_descriptions, 1):
        print(f"\n--- Juego {i} ---")
        print(f"Original: {description}")

        translated = await deepl_connector.translate_game_description(description, "ES")
        print(f"Traducido: {translated}")

        # Verificaciones
        assert translated, "La descripción traducida no debe estar vacía"
        assert (
            len(translated) > len(description) * 0.7
        ), "La traducción parece demasiado corta"


@pytest.mark.asyncio()
async def test_formality_levels(deepl_connector):
    """Test diferentes niveles de formalidad."""
    text = "How are you doing today?"
    target_lang = "DE"  # Alemán soporta formalidad
    formality_levels = ["default", "more", "less"]
    results = {}

    print(f"Texto original: {text}")
    print(f"Idioma destino: {target_lang}")

    for formality in formality_levels:
        result = await deepl_connector.translate_text(
            text,
            target_lang,
            formality=formality,
        )
        results[formality] = result.text
        print(f"✅ Formalidad '{formality}': {result.text}")

    # Verificar que hay diferencias entre los niveles de formalidad
    assert (
        len(set(results.values())) > 1
    ), "Los diferentes niveles de formalidad deberían producir traducciones diferentes"


@pytest.mark.asyncio()
async def test_convenience_function(deepl_connector):
    """Test función de conveniencia."""
    description = (
        "Embark on an epic journey through mystical lands filled with ancient secrets."
    )

    print(f"Original: {description}")
    translated = await deepl_connector.translate_game_description(description, "ES")
    print(f"Traducido: {translated}")

    # Verificaciones
    assert translated, "La traducción no debe estar vacía"
    assert (
        len(translated) > len(description) * 0.7
    ), "La traducción parece demasiado corta"
    assert (
        translated != description
    ), "El texto traducido debe ser diferente al original"


@pytest.mark.asyncio()
async def test_error_handling():
    """Test manejo de errores."""
    # Test con API key inválida
    print("\n1. Probando con API key inválida...")
    connector = DeepLAPIConnector(api_key="invalid_key")
    with pytest.raises(AuthenticationError):
        await connector.get_usage()
    print("[OK] Funcion de conveniencia funciono correctamente")

    # Test con idioma de destino inválido
    print("\n2. Probando con idioma de destino inválido...")
    connector = DeepLAPIConnector()
    with pytest.raises(TranslationError):
        await connector.translate_text("Hello", "XX")
    print("[OK] Error de validacion manejado correctamente")

    # Test con formalidad inválida
    print("[OK] Traduccion exitosa con formalidad preferida")
    connector = DeepLAPIConnector()
    with pytest.raises(ValidationError):
        await connector.translate_text("Hello", "ES", formality="invalid")
    print("[OK] Error de validacion manejado correctamente")


def run_all_tests():
    """Ejecuta todos los tests."""
    print("=== Iniciando tests manuales de DeepL API ===")
    print("=" * 50)

    # Verificar API key
    api_key = os.getenv("DEEPL_API_KEY")
    if not api_key:
        print(" Error: DEEPL_API_KEY no está configurada")
        print("Por favor, configura tu API key de DeepL en las variables de entorno")
        return False

    print(f" API Key configurada: {api_key[:8]}...")

    tests = [
        ("Información de Uso", test_usage_info),
        ("Idiomas Soportados", test_supported_languages),
        ("Traducción Simple", test_simple_translation),
        ("Descripción de Juegos", test_game_description_translation),
        ("Niveles de Formalidad", test_formality_levels),
        ("Función de Conveniencia", test_convenience_function),
        ("Manejo de Errores", test_error_handling),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results.append((test_name, success))
        except KeyboardInterrupt:
            print("\n[!] Tests interrumpidos por el usuario")
            break
        except Exception as e:
            print(f"[ERROR] Error inesperado en {test_name}: {e}")
            results.append((test_name, False))

    # Resumen
    print("\n" + "=" * 50)
    print(" RESUMEN DE TESTS")
    print("=" * 50)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = " PASS" if success else " FAIL"
        print(f"{status} {test_name}")

    print(f"\nResultado: {passed}/{total} tests pasaron")

    if passed == total:
        print("[OK] ¡Todos los tests pasaron!")
        return True
    print("[WARN] Algunos tests fallaron")
    return False


def interactive_mode():
    """Modo interactivo para probar traducciones."""
    print("\n Modo Interactivo - DeepL API")
    print("Escribe 'quit' para salir")
    print("-" * 40)

    try:
        with DeepLAPIConnector() as connector:
            while True:
                text = input("\nTexto a traducir: ").strip()
                if text.lower() in ["quit", "exit", "salir"]:
                    break

                if not text:
                    print("[!] Por favor, ingresa un texto")
                    continue

                target_lang = (
                    input("Idioma destino (ES, EN, FR, DE, etc.): ").strip().upper()
                )
                if not target_lang:
                    target_lang = "ES"

                try:
                    result = connector.translate_text(text, target_lang)
                    print(f" Traducción: {result.text}")
                    if result.detected_source_language:
                        print(f"   Idioma detectado: {result.detected_source_language}")

                except Exception as e:
                    print(f" Error: {e}")

    except KeyboardInterrupt:
        print("\n ¡Hasta luego!")
    except Exception as e:
        print(f" Error en modo interactivo: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test manual de DeepL API")
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Ejecutar en modo interactivo",
    )

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    else:
        success = run_all_tests()
        sys.exit(0 if success else 1)
