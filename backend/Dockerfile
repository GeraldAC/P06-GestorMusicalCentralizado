FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# En desarrollo el código se monta vía volume (ver docker-compose.yml).
# En producción se copiaría aquí: COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]