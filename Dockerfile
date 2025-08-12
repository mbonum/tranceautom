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

# Copy and set permissions for entrypoint script
COPY entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

# Collect static files at build time
RUN python manage.py collectstatic --noinput

EXPOSE 8080

# Run the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
