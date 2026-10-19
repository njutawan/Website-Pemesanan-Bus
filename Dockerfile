# Image untuk service "web" di docker-compose.yml (development).
# Untuk produksi, gunakan Gunicorn (lihat deploy/nginx.conf & README).
FROM python:3.14-slim
LABEL org.opencontainers.image.version="1.1.0"
LABEL org.opencontainers.image.title="Nusantara Trans"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Layer dependensi dipisah agar cache build efektif
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Perintah lengkap (migrate + seed + runserver) ada di docker-compose.yml
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
