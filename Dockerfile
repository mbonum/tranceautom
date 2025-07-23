# Use Python base image
FROM python:3.12-slim

# Set working dir
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy app code
COPY . .

# Collect static files at build time
RUN python manage.py collectstatic --noinput

# Run migrations (optional, or do it in CI/CD)
# RUN python manage.py migrate

EXPOSE 8080

# Start uvicorn with Django's ASGI app
CMD ["uvicorn", "tranceautom.asgi:application", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
