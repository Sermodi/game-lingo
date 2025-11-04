.PHONY: help format lint type-check test check clean

help:
	@echo "Comandos disponibles:"
	@echo "  make format      - Formatear código con black"
	@echo "  make lint        - Ejecutar ruff linter"
	@echo "  make type-check  - Ejecutar mypy type checker"
	@echo "  make test        - Ejecutar tests con pytest"
	@echo "  make check       - Ejecutar todos los checks (lint + type + test)"
	@echo "  make clean       - Limpiar archivos temporales"

format:
	@echo "Formateando código con black..."
	black game_lingo tests
	@echo "✓ Formato aplicado"

lint:
	@echo "Ejecutando ruff linter..."
	ruff check game_lingo
	@echo "✓ Linting completado"

lint-fix:
	@echo "Aplicando fixes automáticos de ruff..."
	ruff check game_lingo --fix
	@echo "✓ Fixes aplicados"

type-check:
	@echo "Ejecutando mypy type checker..."
	mypy game_lingo --ignore-missing-imports
	@echo "✓ Type checking completado"

test:
	@echo "Ejecutando tests..."
	pytest tests/ -v
	@echo "✓ Tests completados"

check: lint type-check
	@echo "✓ Todos los checks pasaron"

clean:
	@echo "Limpiando archivos temporales..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "✓ Limpieza completada"

# Para CI/CD
ci-check: format lint type-check
	@echo "✓ CI checks pasaron"
