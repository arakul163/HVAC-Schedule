PYTHON ?= python3

.PHONY: setup clean test

setup:
	$(PYTHON) -m venv .venv
	.venv/bin/python -m pip install uv==0.9.6
	.venv/bin/uv pip install -r requirements-test.txt

clean:
	git clean -fdx

test:
	.venv/bin/pytest
