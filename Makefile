.PHONY: help setup lint typecheck test dev-frontend dev-api dev-all clean

help:
	@echo "Satori Internal Affairs - Development Commands"
	@echo ""
	@echo "  make setup         - Install all dependencies (Python venvs + npm install)"
	@echo "  make lint          - Run ruff across all Python packages"
	@echo "  make typecheck     - Run mypy across all Python packages"
	@echo "  make test          - Run pytest across all Python packages"
	@echo "  make dev-frontend  - Start SvelteKit dev server (port 5173)"
	@echo "  make dev-api       - Start satori-api FastAPI server (port 8000)"
	@echo "  make dev-all       - Print instructions to run both servers"
	@echo "  make clean         - Clean build artifacts and caches"

setup:
	@echo "Installing Python packages in development mode..."
	pip install -e packages/satori[dev]
	pip install -e packages/anamnesis[dev]
	pip install -e packages/llm-client[dev]
	pip install -e packages/satori-api[dev]
	@echo "Installing frontend dependencies..."
	cd packages/internal-affairs && npm install
	@echo "Setup complete!"

lint:
	@echo "Running ruff on all Python packages..."
	ruff check packages/satori/src packages/satori/tests
	ruff check packages/anamnesis/src packages/anamnesis/tests
	ruff check packages/llm-client/src packages/llm-client/tests
	ruff check packages/satori-api/src packages/satori-api/tests

typecheck:
	@echo "Running mypy on all Python packages..."
	mypy packages/satori/src
	mypy packages/anamnesis/src
	mypy packages/llm-client/src
	mypy packages/satori-api/src

test:
	@echo "Running pytest on all Python packages..."
	pytest packages/satori/tests
	pytest packages/anamnesis/tests
	pytest packages/llm-client/tests
	pytest packages/satori-api/tests

dev-frontend:
	@echo "Starting SvelteKit dev server (http://localhost:5173)..."
	cd packages/internal-affairs && npm run dev

dev-api:
	@echo "Starting satori-api FastAPI server (http://localhost:8000)..."
	cd packages/satori-api && uvicorn satori_api.main:app --reload --port 8000

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
