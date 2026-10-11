FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY packages/tri_core /packages/tri_core
RUN pip install --no-cache-dir /packages/tri_core

COPY services/worker /app
RUN pip install --no-cache-dir .

RUN useradd --create-home appuser
USER appuser

CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]
