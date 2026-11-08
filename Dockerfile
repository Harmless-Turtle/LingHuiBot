FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 tini \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY extra_package/ ./extra_package/

RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uv", "run", "--frozen", "python", "bot.py"]
