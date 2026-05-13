.PHONY: bootstrap lint format typecheck test test-cov test-e2e docs docs-serve docker-build docker-run run-stdio run-http audit sbom catalog clean release-check

bootstrap:
	uv sync --extra dev --extra browser
	uv run pre-commit install

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run python scripts/check_no_branding.py

format:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run mypy src tests

test:
	uv run pytest -x

test-cov:
	uv run pytest --cov=src/nlm_mcp --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

test-e2e:
	uv run pytest -m e2e

docs:
	NO_MKDOCS_2_WARNING=1 uv run mkdocs build --strict

docs-serve:
	NO_MKDOCS_2_WARNING=1 uv run mkdocs serve

docker-build:
	docker build -f deploy/Dockerfile -t notebooklm-mcp-pro:dev .

docker-run: docker-build
	docker run --rm -p 8080:8080 \
		-v $(HOME)/.config/nlm-mcp:/home/appuser/.config/nlm-mcp:ro \
		notebooklm-mcp-pro:dev serve

run-stdio:
	uv run nlm-mcp stdio

run-http:
	uv run nlm-mcp serve --host 127.0.0.1 --port 8080

audit:
	uv run pip-audit
	uv run bandit -r src -ll

sbom:
	uv run cyclonedx-py environment --output-format json -o sbom.json
	@echo "SBOM written to sbom.json"

catalog:
	uv run python scripts/list_tools.py > docs/tools/catalog.md
	@echo "Tool catalog written to docs/tools/catalog.md"

clean:
	rm -rf dist/ build/ htmlcov/ .mypy_cache/ .ruff_cache/ .pytest_cache/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

release-check:
	@echo "Checking version consistency..."
	@TAG=$$(git describe --tags --abbrev=0 2>/dev/null || echo "none"); \
	PKG=$$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"); \
	echo "Latest tag: $$TAG  Package: $$PKG"
