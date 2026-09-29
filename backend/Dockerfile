FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml constraints.txt ./
RUN pip install --no-cache-dir -c constraints.txt .
COPY app ./app
COPY alembic.ini ./
RUN useradd --create-home --uid 10001 portal
USER portal
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log --log-level critical"]
