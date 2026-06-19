.PHONY: compile test check

PYTHON ?= python3

compile:
	$(PYTHON) -m compileall -f custom_components tests

test:
	$(PYTHON) -m pytest

check: compile test
