# Legacy file only.
# Production does NOT use Docker/container deployment.
# Live stack: Ubuntu VM + virtualenv + gunicorn + systemd + nginx.
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer-cache friendly)
COPY requirements.txt .

# Install Python dependencies (gunicorn is already in requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create required runtime directories
RUN mkdir -p data/pdfs

# Cloud Run injects PORT=8080; expose that port in the image metadata
EXPOSE 8080

# Set production defaults (overridable via Cloud Run env vars)
ENV FLASK_ENV=production
ENV PORT=8080

# Health check — uses $PORT so it works if Cloud Run changes the port
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request, os; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT','8080') + '/api/auth/health')" || exit 1

# Run with gunicorn (NOT the Flask dev server)
# gunicorn.conf.py handles bind address, worker count, threads, and
# the on_starting hook that launches the background scheduler.
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
