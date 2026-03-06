# ============================================================================
# FinAI Makefile - Common Commands for Development
# ============================================================================

.PHONY: help install migrate run dev prod shell test clean lint format stop

SHELL := /bin/bash
PROJECT_DIR := $(shell pwd)
PYTHON := python3
MANAGE := $(PYTHON) manage.py
VENV := venv
VENV_BIN := $(VENV)/bin

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

help: ## Show this help message
	@echo "$(GREEN)===================================================$(NC)"
	@echo "$(GREEN)FinAI Development Commands$(NC)"
	@echo "$(GREEN)===================================================$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)make %-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

install: ## Install dependencies
	@echo "$(YELLOW)Installing dependencies...$(NC)"
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/pip install --upgrade pip setuptools wheel
	$(VENV_BIN)/pip install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

migrate: ## Run database migrations
	@echo "$(YELLOW)Running migrations...$(NC)"
	$(MANAGE) makemigrations core analytics documents compliance ai_plugins --noinput
	$(MANAGE) migrate --noinput
	@echo "$(GREEN)✓ Migrations completed$(NC)"

run: ## Run development server (default port 8000)
	@echo "$(YELLOW)Starting development server on http://localhost:8000$(NC)"
	$(MANAGE) runserver 0.0.0.0:8000

dev: run ## Alias for 'run'

port: ## Run dev server on custom port (use: make port PORT=3000)
	$(MANAGE) runserver 0.0.0.0:$(PORT)

prod: ## Run production server with Gunicorn
	@echo "$(YELLOW)Starting production server...$(NC)"
	bash run-prod.sh

shell: ## Open Django interactive shell
	$(MANAGE) shell_plus

createsuperuser: ## Create admin user
	@echo "$(YELLOW)Creating superuser...$(NC)"
	$(MANAGE) createsuperuser

test: ## Run tests
	@echo "$(YELLOW)Running tests...$(NC)"
	$(MANAGE) test

test-verbose: ## Run tests with verbose output
	$(MANAGE) test --verbosity=2

test-coverage: ## Run tests with coverage report
	coverage run --source='.' manage.py test
	coverage report
	coverage html

makemigrations: ## Create migrations
	@echo "$(YELLOW)Creating migrations...$(NC)"
	$(MANAGE) makemigrations core analytics documents compliance ai_plugins

showmigrations: ## Show migration status
	$(MANAGE) showmigrations

sqlmigrate: ## Show SQL for migration (use: make sqlmigrate APP=app NAME=migration_name)
	$(MANAGE) sqlmigrate $(APP) $(NAME)

lint: ## Run code linting (flake8)
	@echo "$(YELLOW)Running linting...$(NC)"
	flake8 . --exclude=$(VENV),*.pyc,__pycache__ --max-line-length=100

format: ## Format code with black
	@echo "$(YELLOW)Formatting code...$(NC)"
	black . --exclude=$(VENV)

format-check: ## Check code formatting without changes
	black . --exclude=$(VENV) --check

isort: ## Sort imports with isort
	@echo "$(YELLOW)Sorting imports...$(NC)"
	isort . --skip=$(VENV)

clean: ## Clean up temporary files and cache
	@echo "$(YELLOW)Cleaning up...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type f -name '.DS_Store' -delete
	rm -rf .pytest_cache .coverage htmlcov
	rm -rf *.egg-info dist build
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

superclean: clean ## Deep clean (includes venv)
	@echo "$(YELLOW)Deep cleaning...$(NC)"
	rm -rf $(VENV)
	rm -f db.sqlite3
	@echo "$(GREEN)✓ Deep clean complete$(NC)"

collectstatic: ## Collect static files
	@echo "$(YELLOW)Collecting static files...$(NC)"
	$(MANAGE) collectstatic --noinput
	@echo "$(GREEN)✓ Static files collected$(NC)"

compilemessages: ## Compile translation messages
	@echo "$(YELLOW)Compiling messages...$(NC)"
	$(MANAGE) compilemessages

requirements: ## Generate requirements.txt from pip freeze
	$(VENV_BIN)/pip freeze > requirements.txt
	@echo "$(GREEN)✓ requirements.txt updated$(NC)"

requirements-upgrade: ## Upgrade all dependencies
	@echo "$(YELLOW)Upgrading dependencies...$(NC)"
	$(VENV_BIN)/pip install --upgrade -r requirements.txt
	@echo "$(GREEN)✓ Dependencies upgraded$(NC)"

requirements-check: ## Check for outdated packages
	$(VENV_BIN)/pip list --outdated

dbshell: ## Open database shell
	$(MANAGE) dbshell

dumpdata: ## Export database data (use: make dumpdata FILE=data.json)
	$(MANAGE) dumpdata > $(FILE)
	@echo "$(GREEN)✓ Data exported to $(FILE)$(NC)"

loaddata: ## Import database data (use: make loaddata FILE=data.json)
	$(MANAGE) loaddata $(FILE)
	@echo "$(GREEN)✓ Data imported from $(FILE)$(NC)"

reset-db: ## Reset database (WARNING: destructive!)
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? (yes/no) " -r; \
	if [[ $$REPLY =~ ^[Yy][Ee][Ss]$$ ]]; then \
		rm -f db.sqlite3; \
		$(MANAGE) migrate; \
		@echo "$(GREEN)✓ Database reset$(NC)"; \
	fi

logs: ## View recent application logs
	@if [ -f "logs/django.log" ]; then tail -f logs/django.log; else echo "No logs found"; fi

logs-error: ## View error logs
	@if [ -f "logs/error.log" ]; then tail -f logs/error.log; else echo "No error logs found"; fi

setup: ## Initial project setup (install + migrate)
	@echo "$(GREEN)===================================================$(NC)"
	@echo "$(GREEN)FinAI Project Setup$(NC)"
	@echo "$(GREEN)===================================================$(NC)"
	$(MAKE) install
	$(MAKE) migrate
	$(MAKE) collectstatic
	@echo ""
	@echo "$(GREEN)✓ Setup complete!$(NC)"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your configuration"
	@echo "  2. Run: make createsuperuser"
	@echo "  3. Run: make run"
	@echo ""

health: ## Check application health
	@echo "$(YELLOW)Checking application health...$(NC)"
	@$(PYTHON) -c "import django; django.setup(); from django.core.management import call_command; call_command('check')"
	@echo "$(GREEN)✓ Application is healthy$(NC)"

info: ## Show project information
	@echo "$(GREEN)===================================================$(NC)"
	@echo "$(GREEN)FinAI Project Information$(NC)"
	@echo "$(GREEN)===================================================$(NC)"
	@echo "Python version: $$($(PYTHON) --version)"
	@echo "Django version: $$($(PYTHON) -m django --version)"
	@echo "Project directory: $(PROJECT_DIR)"
	@echo "Virtual environment: $(VENV)"
	@echo ""

version: ## Show versions
	@$(PYTHON) --version
	@$(PYTHON) -m django --version

.DEFAULT_GOAL := help
