# RAGInspector — developer and release tasks
#
# One-command local stack (clean clone):
#   cp .env.example .env   # set SECRET_KEY
#   make bootstrap
#
# Requires: Docker Compose. test/lint also need local Python + Node
# (repo `.venv` is used when present).

.PHONY: help bootstrap up down migrate test lint typecheck seed \
	test-backend test-frontend test-sdk lint-backend lint-frontend \
	typecheck-backend typecheck-frontend format-backend \
	config config-prod config-test config-obs up-prod up-test up-obs \
	logs ps restart check-versions package-sdk release-check \
	security-bandit ci-local helm-validate sbom validate-release

COMPOSE ?= docker compose
COMPOSE_PROD ?= $(COMPOSE) -f docker-compose.prod.yml
COMPOSE_TEST ?= $(COMPOSE) -f docker-compose.test.yml
COMPOSE_OBS ?= $(COMPOSE) -f docker-compose.yml -f docker-compose.observability.yml
ROOT    := $(CURDIR)
NPM     ?= npm

ifeq ($(OS),Windows_NT)
  ifneq ($(wildcard $(ROOT)/.venv/Scripts/python.exe),)
    PYTHON := $(ROOT)/.venv/Scripts/python.exe
  else
    PYTHON ?= python
  endif
else
  ifneq ($(wildcard $(ROOT)/.venv/bin/python),)
    PYTHON := $(ROOT)/.venv/bin/python
  else
    PYTHON ?= python3
  endif
endif

help:
	@echo "RAGInspector Make targets"
	@echo ""
	@echo "  make bootstrap   ONE COMMAND: env check → build → up → migrate → health"
	@echo "  make up          Start full stack (docker compose up -d --build)"
	@echo "  make down        Stop stack"
	@echo "  make migrate     Apply Alembic migrations"
	@echo "  make test|lint|typecheck|seed"
	@echo "  make config-prod Validate production compose"
	@echo "  make up-prod     Production compose (.env.production)"
	@echo "  make up-test     Ephemeral test compose"
	@echo "  make up-obs      Dev stack + Prometheus/Grafana"
	@echo "  make helm-validate    Helm lint/template (needs helm CLI)"
	@echo "  make sbom             Generate CycloneDX SBOMs"
	@echo "  make validate-release Post-deploy API/UI health checks"
	@echo "  make package-sdk Build PyPI wheel/sdist"
	@echo "  make check-versions  Assert VERSION sync across packages"
	@echo "  make release-check   Local release gate (versions + package + compose)"
	@echo ""
	@echo "Windows: prefer .\\scripts\\setup.ps1 then .\\scripts\\bootstrap.ps1"
	@echo "         (Make recipes assume a POSIX shell — see docs/WINDOWS.md)"

bootstrap:
	@echo "==> Checking environment"
	@if [ ! -f .env ]; then \
	  echo "Missing .env — copying from .env.example"; \
	  cp .env.example .env; \
	  echo "Edit .env and set SECRET_KEY, then re-run make bootstrap"; \
	  exit 1; \
	fi
	@$(COMPOSE) config --quiet
	@echo "==> Building and starting stack"
	@$(COMPOSE) up -d --build
	@echo "==> Waiting for backend health"
	@i=0; \
	until $(COMPOSE) exec -T backend curl -fsS http://127.0.0.1:8000/live >/dev/null 2>&1; do \
	  i=$$((i+1)); \
	  if [ $$i -gt 60 ]; then echo "Backend health timeout"; exit 1; fi; \
	  sleep 5; \
	done
	@echo "==> Running migrations"
	@$(COMPOSE) run --rm backend alembic upgrade head
	@echo "==> Ready — API http://localhost:8000  UI http://localhost:3000"

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

migrate:
	$(COMPOSE) run --rm backend alembic upgrade head

seed:
	cd backend && "$(PYTHON)" scripts/seed_demo.py

test: test-backend test-sdk test-frontend

test-backend:
	cd backend && "$(PYTHON)" -m pytest tests/unit/ -q

test-sdk:
	cd sdk && "$(PYTHON)" -m unittest discover -s tests -v

test-frontend:
	cd frontend && $(NPM) test

lint: lint-backend lint-frontend

lint-backend:
	cd backend && "$(PYTHON)" -m ruff check app

lint-frontend:
	cd frontend && $(NPM) run lint

format-backend:
	cd backend && "$(PYTHON)" -m black app && "$(PYTHON)" -m isort app

typecheck: typecheck-backend typecheck-frontend

typecheck-backend:
	cd backend && "$(PYTHON)" -m mypy

typecheck-frontend:
	cd frontend && $(NPM) run typecheck

security-bandit:
	cd backend && "$(PYTHON)" -m pip install -q bandit && "$(PYTHON)" -m bandit -r app -ll -ii -x tests,alembic

logs:
	$(COMPOSE) logs -f --tail=100

ps:
	$(COMPOSE) ps

config:
	$(COMPOSE) config --quiet

config-prod:
	$(COMPOSE_PROD) --env-file .env.production config --quiet

config-test:
	$(COMPOSE_TEST) config --quiet

config-obs:
	$(COMPOSE_OBS) config --quiet

up-prod:
	$(COMPOSE_PROD) --env-file .env.production up -d --build

up-test:
	$(COMPOSE_TEST) up -d --build

up-obs:
	$(COMPOSE_OBS) up -d --build

restart:
	$(COMPOSE) restart

check-versions:
	@$(PYTHON) scripts/check_versions.py

package-sdk:
	cd sdk && "$(PYTHON)" -m pip install -q build twine \
	  && "$(PYTHON)" -m build \
	  && "$(PYTHON)" -m twine check dist/*

release-check: check-versions package-sdk config config-test
	@echo "Release checks passed"

ci-local: lint typecheck test release-check helm-validate
	@echo "Local CI subset passed"

helm-validate:
	"$(PYTHON)" scripts/validate_helm_chart.py

sbom:
	"$(PYTHON)" scripts/generate_sbom.py

validate-release:
	"$(PYTHON)" scripts/validate_release.py
