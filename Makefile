.PHONY: help setup lint typecheck test dev-frontend dev-api dev-all clean

help:
	@echo "Satori Internal Affairs - Development Commands"
	@echo ""
	@echo "  make setup         - Install all dependencies (uv workspace + npm install)"
	@echo "  make lint          - Run ruff across all Python packages"
	@echo "  make typecheck     - Run mypy across all Python packages"
	@echo "  make test          - Run pytest across all Python packages"
	@echo "  make dev-frontend  - Start SvelteKit dev server (port 5173)"
	@echo "  make dev-api       - Start satori-api FastAPI server (port 8000)"
	@echo "  make dev-all       - Print instructions to run both servers"
	@echo "  make clean         - Clean build artifacts and caches"

setup:
	@echo "Syncing uv workspace (single .venv from the committed uv.lock)..."
	uv sync --all-packages --all-extras
	@echo "Installing frontend dependencies..."
	cd packages/internal-affairs && npm install
	@echo "Setup complete!"

lint:
	@echo "Running ruff on all Python packages..."
	uv run --no-sync ruff check packages/satori/src packages/satori/tests
	uv run --no-sync ruff check packages/anamnesis/src packages/anamnesis/tests
	uv run --no-sync ruff check packages/llm-client/src packages/llm-client/tests
	uv run --no-sync ruff check packages/satori-api/src packages/satori-api/tests

typecheck:
	@echo "Running mypy on all Python packages..."
	uv run --no-sync mypy packages/satori/src
	uv run --no-sync mypy packages/anamnesis/src
	uv run --no-sync mypy packages/llm-client/src
	uv run --no-sync mypy packages/satori-api/src

test:
	@echo "Running pytest on all Python packages (coverage floor 90)..."
	uv run --no-sync pytest packages/satori/tests --cov=satori --cov-fail-under=90 -q
	uv run --no-sync pytest packages/anamnesis/tests --cov=anamnesis --cov-fail-under=90 -q
	# llm-client exempt from the floor until P2-H08 rewrites the provider
	# implementations and tests (audit/FABLE-REVIEW-2026-07-03.md §3).
	uv run --no-sync pytest packages/llm-client/tests --cov=llm_client -q
	uv run --no-sync pytest packages/satori-api/tests --cov=satori_api --cov-fail-under=90 -q

dev-frontend:
	@echo "Starting SvelteKit dev server (http://localhost:5173)..."
	cd packages/internal-affairs && npm run dev

dev-api:
	@echo "Starting satori-api FastAPI server (http://localhost:8000)..."
	uv run --no-sync uvicorn satori_api.main:app --reload --port 8000

dev-all:
	@echo ""
	@echo "Run both servers in separate terminals:"
	@echo "  Terminal 1:  make dev-api"
	@echo "  Terminal 2:  make dev-frontend"
	@echo ""
	@echo "Then open http://localhost:5173"

clean:
	@echo "Cleaning build artifacts and caches..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf packages/internal-affairs/.svelte-kit
	@echo "Clean complete!"
