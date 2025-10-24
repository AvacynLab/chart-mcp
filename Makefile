.PHONY: setup dev lint format typecheck test clean docker-build docker-run

export PYTHONPATH := src

setup:
	pip install -r requirements.txt
	pip install -e .

dev:
	uvicorn chart_mcp.app:app --host 0.0.0.0 --port 8000 --reload

lint:
	ruff check .

format:
	black src tests
	isort src tests

typecheck:
	mypy src

test:
	pytest --cov=src --cov-report=xml

clean:
	python -m chart_mcp.cli.cleanup

docker-build:
	docker build -f docker/Dockerfile -t chart-mcp:dev .

docker-run:
	docker run --rm -p 8000:8000 --env-file .env chart-mcp:dev
