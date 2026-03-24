.PHONY: help install migrate run test lint collectstatic shell docker-up docker-down

help:
	@echo "AlumniAI — available commands:"
	@echo "  make install        Install Python dependencies"
	@echo "  make migrate        Run database migrations"
	@echo "  make run            Start development server"
	@echo "  make test           Run test suite"
	@echo "  make lint           Run flake8 linter"
	@echo "  make collectstatic  Collect static files"
	@echo "  make shell          Open Django shell"
	@echo "  make docker-up      Start all services via Docker Compose"
	@echo "  make docker-down    Stop Docker Compose services"
	@echo "  make worker         Start Celery worker"
	@echo "  make beat           Start Celery beat scheduler"
	@echo "  make check-deploy   Run Django deployment checks"

install:
	pip install -r requirements.txt

migrate:
	python manage.py migrate

run:
	python manage.py runserver

test:
	pytest tests/ --reuse-db -v

test-cov:
	pytest tests/ --reuse-db --cov=apps --cov-report=term-missing -v

lint:
	flake8 apps/ utils/ alumni_platform/ --max-line-length=120 --exclude=migrations

collectstatic:
	python manage.py collectstatic --noinput

shell:
	python manage.py shell

worker:
	celery -A alumni_platform worker --loglevel=info

beat:
	celery -A alumni_platform beat --loglevel=info

check-deploy:
	python manage.py check --deploy --settings=alumni_platform.settings.prod

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f web
