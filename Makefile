.PHONY: setup dev lint format format-check lint-fix typecheck typecheck-strict test clean docker-build docker-run

export PYTHONPATH := src

# Bootstrap the Python tooling so contributors can run the API locally with
# the same dependency set used in CI.
setup:
	pip install -r requirements.txt
	pip install -e .

# Launch the FastAPI application with auto-reload for an efficient local dev
# loop.
dev:
	uvicorn chart_mcp.app:app --host 0.0.0.0 --port 8000 --reload

mcp-run:
	python -m chart_mcp.mcp_main

lint:
	ruff check .

format:
	black src tests
	isort src tests

format-check:
	black --check src tests
	isort --check-only src tests

lint-fix:
	ruff check --fix .
	black src tests
	isort src tests

typecheck:
	mypy src

typecheck-strict:
	mypy src

test:
	pytest --cov=src --cov-report=xml

clean:
	python -m chart_mcp.cli.cleanup

docker-build:
	docker build -f docker/Dockerfile -t chart-mcp:dev .

docker-run:
	docker run --rm -p 8000:8000 --env-file .env chart-mcp:dev
