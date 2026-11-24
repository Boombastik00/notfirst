FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app
# alembic нужен в образе чтобы миграции можно было выполнять внутри контейнера
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
