# BFW-9000 · Simulador de Waterflooding
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=blsim.settings

WORKDIR /app

# Dependencias primero: aprovecha la cache de capas de Docker
COPY requirements.txt requirements-docker.txt ./
RUN pip install --upgrade pip && pip install -r requirements-docker.txt

COPY . .

# La base vive en un volumen para que sobreviva a la reconstruccion
ENV DJANGO_DB_PATH=/datos/db.sqlite3
RUN mkdir -p /datos

# Los estaticos se recogen en build; WhiteNoise los sirve sin necesidad de nginx
RUN DJANGO_DEBUG=0 DJANGO_SECRET_KEY=build python manage.py collectstatic --noinput

RUN chmod +x docker/entrypoint.sh

EXPOSE 8017
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "blsim.wsgi:application", \
     "--bind", "0.0.0.0:8017", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "120", \
     "--access-logfile", "-"]
