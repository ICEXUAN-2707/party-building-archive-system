ARG PYTHON_IMAGE=python:3.12.14-slim-bookworm
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app manage.py ./
COPY --chown=app:app apps ./apps
COPY --chown=app:app config ./config
COPY --chown=app:app scripts/__init__.py scripts/docker_entrypoint.py ./scripts/
COPY --chown=app:app static ./static
COPY --chown=app:app templates ./templates

RUN mkdir -p /data/database /data/media /data/static /data/backups \
    && chown -R app:app /data

USER app

EXPOSE 8000

STOPSIGNAL SIGINT

ENTRYPOINT ["python", "/app/scripts/docker_entrypoint.py"]
