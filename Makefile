.PHONY: dev test migrate shell static clean

dev:
	python manage.py runserver --settings=alumni_platform.settings.dev

daphne:
	daphne -p 8000 alumni_platform.asgi:application

test:
	pytest tests/ -v --ds=alumni_platform.settings.dev

test-fast:
	pytest tests/ --ds=alumni_platform.settings.dev -x -q

coverage:
	pytest tests/ --ds=alumni_platform.settings.dev --cov=apps --cov-report=html --cov-report=term-missing

migrate:
	python manage.py migrate --settings=alumni_platform.settings.dev

migrations:
	python manage.py makemigrations --settings=alumni_platform.settings.dev

shell:
	python manage.py shell --settings=alumni_platform.settings.dev

static:
	python manage.py collectstatic --noinput --settings=alumni_platform.settings.dev

devusers:
	python manage.py create_dev_users --settings=alumni_platform.settings.dev

check:
	python manage.py check --settings=alumni_platform.settings.dev

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

worker:
	celery -A alumni_platform worker --loglevel=info

beat:
	celery -A alumni_platform beat --loglevel=info

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f web
