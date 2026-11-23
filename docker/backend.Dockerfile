# Backend image (F-00.04). Python and dependencies are pinned by the base tag and uv.lock.
FROM ghcr.io/astral-sh/uv:0.11.28 AS uv

FROM python:3.12.12-slim-bookworm
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv PATH=/opt/venv/bin:$PATH
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY docs/README.md docs/README.md
COPY src src
RUN uv sync --frozen --no-dev
RUN useradd --create-home --uid 1000 mathlab
USER mathlab
CMD ["python", "-m", "mathlab.placeholder_service"]
