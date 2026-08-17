FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY qc_engine ./qc_engine

# Render (and most PaaS hosts) inject the port to bind via $PORT.
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn qc_engine.api:app --host 0.0.0.0 --port ${PORT}"]
