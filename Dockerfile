FROM python:3.11-slim

# Avoid writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (optional but common for Pillow/qrcode)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libjpeg62-turbo zlib1g \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (leverages Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default environment values (can be overridden at runtime)
ENV FLASK_PORT=5000 \
    DATABASE_PATH=/app/app.db

# Expose the Flask port
EXPOSE 5000

# Run the app
CMD ["python", "app.py"]
