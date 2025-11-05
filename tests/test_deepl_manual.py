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

from game_lingo.apis.deepl_api import (
    DeepLAPIConnector,
    translate_game_description
)
from game_lingo.exceptions import (
    APIError,
    AuthenticationError,
    TranslationError,
    ValidationError
)


def test_usage_info():
    """Test obtener información de uso de la API."""
    print("\n=== Test: Información de Uso ===")
    
    try:
        with DeepLAPIConnector() as connector:
            usage = connector.get_usage()
            
            print(f"✅ Caracteres usados: {usage.character_count:,}")
            print(f"✅ Límite de caracteres: {usage.character_limit:,}")
            print(f"✅ Porcentaje de uso: {usage.usage_percentage:.2f}%")
            
            if usage.usage_percentage > 80:
                print("⚠️  Advertencia: Cerca del límite de caracteres")
            
            return True
            
    except AuthenticationError as e:
        print(f"❌ Error de autenticación: {e}")
        return False
    except APIError as e:
        print(f"❌ Error de API: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False


def test_supported_languages():
    """Test obtener idiomas soportados."""
    print("\n=== Test: Idiomas Soportados ===")
    
    try:
        with DeepLAPIConnector() as connector:
            # Idiomas de destino
            target_languages = connector.get_supported_languages("target")
            print(f"✅ Idiomas de destino disponibles: {len(target_languages)}")
            
            # Mostrar algunos idiomas importantes
            important_langs = ["ES", "EN", "FR", "DE", "IT", "PT"]
            for lang in target_languages:
                if lang.code in important_langs:
                    formality = " (soporta formalidad)" if lang.supports_formality else ""
                    print(f"   - {lang.code}: {lang.name}{formality}")
            
            # Idiomas de origen
            source_languages = connector.get_supported_languages("source")
            print(f"✅ Idiomas de origen disponibles: {len(source_languages)}")
            
            return True
            
    except APIError as e:
        print(f"❌ Error de API: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False


def test_simple_translation():
    """Test traducción simple."""
    print("\n=== Test: Traducción Simple ===")
    
    test_texts = [
        ("Hello world", "ES"),
        ("Good morning", "ES"),
        ("Thank you very much", "ES"),
        ("How are you today?", "ES")
    ]
    
    try:
        with DeepLAPIConnector() as connector:
            for text, target_lang in test_texts:
                result = connector.translate_text(text, target_lang)
                
                print(f"✅ '{text}' -> '{result.text}'")
                if result.detected_source_language:
                    print(f"   Idioma detectado: {result.detected_source_language}")
            
            return True
            
    except TranslationError as e:
        print(f"❌ Error de traducción: {e}")
        return False
    except APIError as e:
        print(f"❌ Error de API: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False


def test_game_description_translation():
    """Test traducción de descripciones de juegos."""
    print("\n=== Test: Traducción de Descripciones de Juegos ===")
    
    game_descriptions = [
        "An epic fantasy adventure game with stunning visuals and immersive gameplay.",
        "Build and manage your own city in this strategic simulation game.",
        "Fast-paced action shooter with multiplayer battles and customizable weapons.",
        "Explore mysterious dungeons and collect powerful artifacts in this RPG.",
        "Race through challenging tracks with realistic physics and dynamic weather."
    ]
    
    try:
        with DeepLAPIConnector() as connector:
            for i, description in enumerate(game_descriptions, 1):
                print(f"\n--- Juego {i} ---")
                print(f"Original: {description}")
                
                translated = connector.translate_game_description(description, "ES")
                print(f"Traducido: {translated}")
            
            return True
            
    except TranslationError as e:
        print(f"❌ Error de traducción: {e}")
        return False
    except ValidationError as e:
        print(f"❌ Error de validación: {e}")
        return False
    except APIError as e:
        print(f"❌ Error de API: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False


def test_formality_levels():
    """Test diferentes niveles de formalidad."""
    print("\n=== Test: Niveles de Formalidad ===")
    
    text = "How are you doing today?"
    target_lang = "DE"  # Alemán soporta formalidad
    
    formality_levels = ["default", "more", "less"]
    
    try:
        with DeepLAPIConnector() as connector:
            print(f"Texto original: {text}")
            print(f"Idioma destino: {target_lang}")
            
            for formality in formality_levels:
                result = connector.translate_text(
                    text, 
                    target_lang, 
                    formality=formality
                )
                print(f"✅ Formalidad '{formality}': {result.text}")
            
            return True
            
    except TranslationError as e:
        print(f"❌ Error de traducción: {e}")
        return False
    except APIError as e:
        print(f"❌ Error de API: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False


def test_convenience_function():
    """Test función de conveniencia."""
    print("\n=== Test: Función de Conveniencia ===")
    
    description = "Embark on an epic journey through mystical lands filled with ancient secrets."
    
    try:
        translated = translate_game_description(description, "ES")
        
        print(f"Original: {description}")
        print(f"✅ Traducido: {translated}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_error_handling():
    """Test manejo de errores."""
    print("\n=== Test: Manejo de Errores ===")
    
    try:
        with DeepLAPIConnector() as connector:
            # Test texto vacío
            try:
                connector.translate_text("", "ES")
                print("❌ Debería haber fallado con texto vacío")
            except ValidationError:
                print("✅ Error de validación capturado correctamente (texto vacío)")
            
            # Test idioma inválido
            try:
                connector.translate_text("Hello", "")
                print("❌ Debería haber fallado con idioma vacío")
            except ValidationError:
                print("✅ Error de validación capturado correctamente (idioma vacío)")
            
            # Test formalidad inválida
            try:
                connector.translate_text("Hello", "ES", formality="invalid")
                print("❌ Debería haber fallado con formalidad inválida")
            except ValidationError:
                print("✅ Error de validación capturado correctamente (formalidad inválida)")
            
            return True
            
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False


def run_all_tests():
    """Ejecuta todos los tests."""
    print("🚀 Iniciando tests manuales de DeepL API")
    print("=" * 50)
    
    # Verificar API key
    api_key = os.getenv('DEEPL_API_KEY')
    if not api_key:
        print("❌ Error: DEEPL_API_KEY no está configurada")
        print("Por favor, configura tu API key de DeepL en las variables de entorno")
        return False
    
    print(f"✅ API Key configurada: {api_key[:8]}...")
    
    tests = [
        ("Información de Uso", test_usage_info),
        ("Idiomas Soportados", test_supported_languages),
        ("Traducción Simple", test_simple_translation),
        ("Descripción de Juegos", test_game_description_translation),
        ("Niveles de Formalidad", test_formality_levels),
        ("Función de Conveniencia", test_convenience_function),
        ("Manejo de Errores", test_error_handling)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results.append((test_name, success))
        except KeyboardInterrupt:
            print("\n⚠️ Tests interrumpidos por el usuario")
            break
        except Exception as e:
            print(f"❌ Error inesperado en {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumen
    print("\n" + "="*50)
    print("📊 RESUMEN DE TESTS")
    print("="*50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResultado: {passed}/{total} tests pasaron")
    
    if passed == total:
        print("🎉 ¡Todos los tests pasaron!")
        return True
    else:
        print("⚠️ Algunos tests fallaron")
        return False


def interactive_mode():
    """Modo interactivo para probar traducciones."""
    print("\n🔄 Modo Interactivo - DeepL API")
    print("Escribe 'quit' para salir")
    print("-" * 40)
    
    try:
        with DeepLAPIConnector() as connector:
            while True:
                text = input("\nTexto a traducir: ").strip()
                if text.lower() in ['quit', 'exit', 'salir']:
                    break
                
                if not text:
                    print("⚠️ Por favor, ingresa un texto")
                    continue
                
                target_lang = input("Idioma destino (ES, EN, FR, DE, etc.): ").strip().upper()
                if not target_lang:
                    target_lang = "ES"
                
                try:
                    result = connector.translate_text(text, target_lang)
                    print(f"✅ Traducción: {result.text}")
                    if result.detected_source_language:
                        print(f"   Idioma detectado: {result.detected_source_language}")
                
                except Exception as e:
                    print(f"❌ Error: {e}")
    
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
    except Exception as e:
        print(f"❌ Error en modo interactivo: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test manual de DeepL API")
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Ejecutar en modo interactivo"
    )
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    else:
        success = run_all_tests()
        sys.exit(0 if success else 1)