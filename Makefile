SHELL := /bin/bash
VENV := .venv
POETRY := $(VENV)/bin/poetry

.PHONY: install clean test

install: $(POETRY)
	@source $(VENV)/bin/activate && poetry install

$(POETRY): | $(VENV)
	@source $(VENV)/bin/activate && python -m pip install --upgrade pip setuptools wheel
	@source $(VENV)/bin/activate && python -m pip install poetry
	@# ensure poetry uses the in-project venv
	@source $(VENV)/bin/activate && poetry config virtualenvs.in-project true --local

$(VENV):
	@python3 -m venv $(VENV)

clean:
	@rm -rf $(VENV)
	@$(MAKE) install

test: install
	@source $(VENV)/bin/activate && { \
		TEST_DIRS=""; \
		for d in pytest/core pytest/phub pytest/rtube; do \
			[ -d $$d ] && TEST_DIRS="$$TEST_DIRS $$d"; \
		done; \
		if [ -z "$$TEST_DIRS" ]; then \
			echo "No test directories found."; \
			exit 0; \
		fi; \
		poetry run pytest $$TEST_DIRS || code=$$?; \
		if [ "$$code" = "5" ]; then \
			echo "No tests found. Skipping."; \
		elif [ -n "$$code" ]; then \
			exit "$$code"; \
		fi; \
	}
