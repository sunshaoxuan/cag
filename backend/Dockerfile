FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git subversion ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY projects /projects

RUN python -m pip install --no-cache-dir .
RUN python -c "from tree_sitter_language_pack import prefetch; prefetch(['bash','c','cpp','csharp','go','java','javascript','kotlin','php','powershell','python','ruby','rust','sql','tsx','typescript'])"

EXPOSE 8000

CMD ["sh", "-c", "python -m app.migrations.legacy_baseline && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
