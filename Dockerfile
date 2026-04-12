FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create necessary directories
RUN mkdir -p logs media staticfiles

# Collect static files
RUN python manage.py collectstatic --noinput --settings=alumni_platform.settings.prod

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash alumniai
RUN chown -R alumniai:alumniai /app
USER alumniai

EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "alumni_platform.asgi:application"]
