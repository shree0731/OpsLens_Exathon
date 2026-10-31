.PHONY: help install test connect discover run-backend clean

PYTHON ?= python

help:
	@echo "OpsLens Development Makefile"
	@echo "  make install      - Install Python dependencies"
	@echo "  make connect      - Test Exasol connectivity"
	@echo "  make discover     - Run schema and audit view discovery"
	@echo "  make run-backend  - Start FastAPI backend"
	@echo "  make test         - Run test suite"
	@echo "  make clean        - Clean cache and build artifacts"

install:
	$(PYTHON) -m pip install -r requirements.txt

connect:
	$(PYTHON) -m backend.connectivity_test

discover:
	$(PYTHON) -m backend.discovery

run-backend:
	$(PYTHON) -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(PYTHON) -m pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
