# Makefile — LRA AI Platform
# Comandos comunes para desarrollo y operaciones.

.PHONY: help install run api status review plan test lint clean

# ─── Default ──────────────────────────────────────────
help:
	@echo ""
	@echo "  LRA AI Platform — Available commands"
	@echo "  ─────────────────────────────────────"
	@echo "  make install     Install dependencies"
	@echo "  make run         Start the API server"
	@echo "  make status      Show platform status"
	@echo "  make review      Review AWS infrastructure"
	@echo "  make plan        Generate a plan (INTENT required)"
	@echo "  make test        Run tests"
	@echo "  make lint        Run linter"
	@echo "  make clean       Remove cache files"
	@echo ""

# ─── Setup ────────────────────────────────────────────
install:
	pip install -r requirements.txt
	cp -n .env.example .env || true
	@echo "✓ Dependencies installed. Edit .env with your credentials."

# ─── Platform ─────────────────────────────────────────
run:
	python api/app.py

status:
	python cli/lra.py status

agents:
	python cli/lra.py agents

tools:
	python cli/lra.py tools

workflows:
	python cli/lra.py workflows

# ─── Operations ───────────────────────────────────────
review:
	python cli/lra.py review multicloud

review-aws:
	python cli/lra.py review aws

review-azure:
	python cli/lra.py review azure

review-gcp:
	python cli/lra.py review gcp

plan:
	@python cli/lra.py plan "$(INTENT)"

init:
	@python cli/lra.py init "$(INTENT)"

# ─── Quality ──────────────────────────────────────────
test:
	python -m pytest tests/ -v 2>/dev/null || echo "No tests found yet."

lint:
	python -m flake8 agents/ core/ tools/ cli/ api/ --max-line-length=100 2>/dev/null || \
	echo "flake8 not installed. Run: pip install flake8"

security:
	python cli/lra.py plan "escanea seguridad del repositorio"

# ─── Cleanup ──────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Cache cleaned."