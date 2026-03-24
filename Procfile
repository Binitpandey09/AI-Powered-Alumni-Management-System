web: gunicorn --config gunicorn.conf.py alumni_platform.wsgi:application
worker: celery -A alumni_platform worker --loglevel=info
beat: celery -A alumni_platform beat --loglevel=info
