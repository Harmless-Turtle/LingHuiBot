FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
COPY extra_package/ ./extra_package/

RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen

CMD ["uv", "run", "--frozen", "python", "bot.py"]
