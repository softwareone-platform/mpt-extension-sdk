.PHONY: bash build build-package check check-all down format review shell test help

DC = docker compose -f compose.yaml

help:
	@echo "Available commands:"
	@echo "  make bash             - Open a bash shell in the app container."
	@echo "  make build            - Build images."
	@echo "  make build-package    - Build package locally."
	@echo "  make check            - Check code quality with ruff."
	@echo "  make check-all        - Run checks and tests."
	@echo "  make down             - Stop and remove containers."
	@echo "  make format           - Format code."
	@echo "  make review           - Check the code in the cli by running CodeRabbit."
	@echo "  make shell            - Open Django shell."
	@echo "  make test             - Run tests."
	@echo "  make help             - Display this help message."

bash:
	  $(DC) run --rm -e PYTHONPATH=/extension_sdk -it app bash

build:
	  $(DC) build

build-package:
	  $(DC) run --rm app uv build

check:
	  $(DC) run --rm app bash -c "ruff format --check . && ruff check . && flake8 . && uv lock --check"

check-all: check test

down:
	  $(DC) down

format:
	  $(DC) run --rm app bash -c "ruff check --select I --fix . && ruff format ."

review:
	  coderabbit review --prompt-only

shell:
	  $(DC) run --rm -e PYTHONPATH=/extension_sdk -it app bash -c "swoext shell"

test:
	  $(DC) run --rm app pytest $(if $(args),$(args),.)
