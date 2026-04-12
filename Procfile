web: daphne -b 0.0.0.0 -p $PORT alumni_platform.asgi:application
worker: celery -A alumni_platform worker --loglevel=info
beat: celery -A alumni_platform beat --loglevel=info
