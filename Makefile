.PHONY: bootstrap lint format typecheck test cov smoke run-stdio run-http docker-build docker-run docs-serve clean release-dry

bootstrap:
	uv sync --extra dev --extra browser

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run python scripts/check_no_branding.py

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy src tests

test:
	uv run pytest

cov:
	uv run pytest --cov-fail-under=90

smoke:
	uv run sh scripts/smoke.sh

run-stdio:
	uv run nlm-mcp stdio

run-http:
	uv run nlm-mcp serve

docker-build:
	docker build -f deploy/Dockerfile -t notebooklm-mcp-pro:local .

docker-run:
	docker run --rm -p 8080:8080 --env-file .env notebooklm-mcp-pro:local

docs-serve:
	uv run mkdocs serve

clean:
	python -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in ['build','dist','htmlcov','.pytest_cache','.mypy_cache','.ruff_cache','site']]; [shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True) for p in pathlib.Path('.').glob('*.egg-info')]"

release-dry:
	uv run python -m build
