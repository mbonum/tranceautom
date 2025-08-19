FROM python:3.12-slim as builder

# Install build-time dependencies for Python packages
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt


# Create a non-root user and group for security
RUN groupadd --system app && useradd --system --gid app app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/

# Copy the application code
COPY . .

# Ensure the entrypoint is executable and set correct ownership
# The staticfiles directory will be created by the next command with the right owner
RUN chmod +x /app/entrypoint.sh && chown -R app:app /app

# Switch to the non-root user
USER app

# Collect static files as the 'app' user
RUN python manage.py collectstatic --noinput

EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]
