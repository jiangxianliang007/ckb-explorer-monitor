FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/

# Run as non-root user
RUN useradd -r -u 1000 -s /sbin/nologin exporter
USER exporter

EXPOSE 9333

CMD ["python", "-m", "app.exporter"]
