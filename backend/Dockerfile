FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Install dependencies first (Docker layer caching: only re-runs if requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default command — overridden by docker-compose.yml to add --reload in dev
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
