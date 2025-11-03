# Notas sobre Tests Asíncronos

## Estado Actual

Los tests asíncronos en el proyecto están correctamente configurados en `pyproject.toml` con:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

Esto significa que pytest-asyncio detectará automáticamente las funciones `async def test_*` y las ejecutará correctamente **sin necesidad del decorador `@pytest.mark.asyncio`**.

## Tests que NO Necesitan Corrección

Los siguientes archivos son **scripts de prueba manual** (no tests de pytest):
- `test_all_apis.py` - Script manual para probar todas las APIs
- `test_steam_manual.py` - Script manual para Steam API
- `tests/test_rawg_manual.py` - Script manual para RAWG API
- `tests/test_deepl_manual.py` - Script manual para DeepL API
- `tests/test_google_translate_manual.py` - Script manual para Google Translate API

Estos archivos:
- Se ejecutan directamente con `python test_*.py`
- NO son descubiertos por pytest
- NO necesitan decoradores de pytest
- Usan `asyncio.run()` en su `main()`

## Tests de Pytest

Los tests reales de pytest están en:
- `tests/test_steam_api.py`
- `tests/test_rawg_api.py`
- `tests/test_deepl_api.py`
- `tests/test_google_translate_api.py`

### Tests Síncronos (Correctos)
La mayoría de tests en estos archivos son **síncronos** y usan mocks, por lo que están correctos:
```python
def test_something(self):
    # Test síncrono - OK
    pass
```

### Tests Asíncronos (Ya Funcionan)
Los tests asíncronos existentes ya funcionan gracias a `asyncio_mode = "auto"`:
```python
async def test_async_function(self):
    # Funciona automáticamente sin decorador
    result = await some_async_call()
    assert result is not None
```

## Fallos Reportados

Los 27 tests fallidos reportados en el informe NO son por falta de decoradores, sino por:

1. **Mocks incorrectos de aiohttp** (warnings de coroutines no awaited)
2. **Tests que retornan valores** en lugar de usar `assert` (scripts manuales)
3. **Problemas de configuración** en tests de integración

## Recomendaciones

### Para Tests Unitarios
Los tests unitarios con mocks están bien. Los fallos son por:
- Mocks de `aiohttp.ClientSession` que necesitan ser AsyncMock
- Respuestas mockeadas que deben ser awaitable

### Para Scripts Manuales
Los scripts manuales funcionan correctamente. Los warnings de pytest son porque:
- Pytest los detecta por el nombre `test_*.py`
- Pero no son tests de pytest reales
- Solución: Renombrarlos a `manual_test_*.py` o moverlos fuera de `tests/`

### Para Tests de Integración
Los tests de integración necesitan:
- API keys configuradas en `.env`
- Conexión a internet
- Rate limiting respetado

## Conclusión

**NO es necesario añadir `@pytest.mark.asyncio` a ningún test** gracias a la configuración `asyncio_mode = "auto"`.

Los fallos de tests se deben a otros problemas (mocks, configuración, scripts manuales) que requieren correcciones específicas diferentes.

## Próximos Pasos

1. ✅ Configuración de pytest ya correcta
2. ⚠️ Renombrar scripts manuales para evitar confusión
3. ⚠️ Corregir mocks de aiohttp en tests unitarios
4. ⚠️ Documentar requisitos para tests de integración
