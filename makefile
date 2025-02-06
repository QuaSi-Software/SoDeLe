PYTHON_PATH = ./src:./bin

ifeq ($(OS),Windows_NT)
    PYTHON_EXEC = ./.venv/Scripts/python.exe
else
    PYTHON_EXEC = ./.venv/bin/python
endif

.PHONY: format
format:
	PYTHONPATH=$(PYTHON_PATH) $(PYTHON_EXEC) -m black --line-length 240 ./src

.PHONY: lint
lint: format
	PYTHONPATH=$(PYTHON_PATH) $(PYTHON_EXEC) -m flake8 ./src

.PHONY: typecheck
typecheck: lint format
	PYTHONPATH=$(PYTHON_PATH) $(PYTHON_EXEC) -m mypy --strict ./src

.PHONY: check
check: format lint typecheck

.PHONY: clean
clean:
	rm -rf ./src/__pycache__ ./src/.mypy_cache
	rm -f center.log

