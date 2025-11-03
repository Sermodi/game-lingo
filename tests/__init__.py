"""
Tests para el módulo game_translator.

Estructura de tests:
- test_steam_api.py: Tests para Steam Store API
- test_rawg_api.py: Tests para RAWG API  
- test_deepl_api.py: Tests para DeepL API
- test_google_translate_api.py: Tests para Google Translate API
- test_translator.py: Tests para el traductor principal
- test_cache.py: Tests para el sistema de cache
- test_rate_limiter.py: Tests para rate limiting
- test_integration.py: Tests de integración completos

Configuración de pytest:
- Usar pytest-asyncio para tests async
- Marcar tests de integración con @pytest.mark.integration
- Usar mocks para tests unitarios
- Tests de integración requieren APIs reales
"""

__version__ = "1.0.0"