# AI Checklist Suggestion Tool - Makefile

.PHONY: help install install-backend install-frontend run run-backend run-frontend build test clean docker-build docker-run docker-stop lint format

# Default target
help:
	@echo "AI Checklist Suggestion Tool - Available Commands:"
	@echo ""
	@echo "Installation:"
	@echo "  install          - Install all dependencies (backend + frontend)"
	@echo "  install-backend  - Install Python backend dependencies"
	@echo "  install-frontend - Install Node.js frontend dependencies"
	@echo ""
	@echo "Development:"
	@echo "  run              - Run both backend and frontend in development"
	@echo "  run-backend      - Run only the backend server"
	@echo "  run-frontend     - Run only the frontend development server"
	@echo ""
	@echo "Testing:"
	@echo "  test             - Run all tests"
	@echo "  test-backend     - Run backend tests"
	@echo "  test-frontend    - Run frontend tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             - Run linting on all code"
	@echo "  format           - Format code with black and prettier"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build     - Build Docker images"
	@echo "  docker-run       - Run with Docker Compose"
	@echo "  docker-stop      - Stop Docker containers"
	@echo ""
	@echo "Deployment:"
	@echo "  build            - Build production version"
	@echo "  clean            - Clean build artifacts"
	@echo "  deploy           - Deploy to production"

# Installation
install: install-backend install-frontend

install-backend:
	@echo "Installing backend dependencies..."
	cd backend && python -m venv venv
	cd backend && venv\Scripts\activate && pip install -r requirements.txt

install-frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

# Development
run: run-backend run-frontend

run-backend:
	@echo "Starting backend server..."
	cd backend && python app.py

run-frontend:
	@echo "Starting frontend development server..."
	cd frontend && npm start

# Testing
test: test-backend test-frontend

test-backend:
	@echo "Running backend tests..."
	cd backend && python -m pytest tests/ -v

test-frontend:
	@echo "Running frontend tests..."
	cd frontend && npm test -- --watchAll=false

# Code Quality
lint:
	@echo "Running linting..."
	cd backend && python -m flake8 . --max-line-length=88
	cd frontend && npm run lint

format:
	@echo "Formatting code..."
	cd backend && python -m black .
	cd frontend && npm run format

# Docker
docker-build:
	@echo "Building Docker images..."
	docker-compose build

docker-run:
	@echo "Starting Docker containers..."
	docker-compose up -d

docker-stop:
	@echo "Stopping Docker containers..."
	docker-compose down

# Development with Docker
docker-dev:
	@echo "Starting development environment with Docker..."
	docker-compose --profile dev up -d

docker-prod:
	@echo "Starting production environment with Docker..."
	docker-compose --profile prod up -d

# Build and Deployment
build:
	@echo "Building production version..."
	cd frontend && npm run build

clean:
	@echo "Cleaning build artifacts..."
	rm -rf frontend/build
	rm -rf backend/__pycache__
	rm -rf backend/*.pyc
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

deploy:
	@echo "Deploying to production..."
	docker-compose --profile prod up -d --build

# Database
db-init:
	@echo "Initializing database..."
	cd backend && python -c "from app import init_db; init_db()"

db-reset:
	@echo "Resetting database..."
	rm -f backend/users.db
	cd backend && python -c "from app import init_db; init_db()"

# Data generation
generate-data:
	@echo "Generating mock data..."
	cd backend && python generate_mock_data.py

# Health checks
health-check:
	@echo "Checking application health..."
	curl -f http://localhost:5000/api/health || echo "Backend not responding"
	curl -f http://localhost:3000 || echo "Frontend not responding"

# Logs
logs:
	@echo "Showing application logs..."
	docker-compose logs -f

logs-backend:
	@echo "Showing backend logs..."
	docker-compose logs -f backend

logs-frontend:
	@echo "Showing frontend logs..."
	docker-compose logs -f frontend-dev

# Backup and restore
backup:
	@echo "Creating backup..."
	docker-compose exec backend python -c "import sqlite3; import shutil; shutil.copy('users.db', '../backup/users_$(date +%Y%m%d_%H%M%S).db')"

restore:
	@echo "Restoring from backup..."
	@read -p "Enter backup filename: " filename; \
	docker-compose exec backend cp "../backup/$$filename" users.db

# Environment setup
setup-env:
	@echo "Setting up environment..."
	cp env.example .env
	@echo "Please edit .env file with your configuration"

# Security
security-check:
	@echo "Running security checks..."
	docker-compose exec backend python -c "import subprocess; subprocess.run(['safety', 'check'])"

# Performance
performance-test:
	@echo "Running performance tests..."
	cd backend && python -m pytest tests/test_performance.py -v

# Documentation
docs:
	@echo "Generating documentation..."
	cd backend && python -c "import pydoc; pydoc.writedoc('app')"

# Monitoring
monitor:
	@echo "Starting monitoring..."
	docker-compose exec backend python -c "import psutil; print('CPU:', psutil.cpu_percent(), '%'); print('Memory:', psutil.virtual_memory().percent, '%')" 