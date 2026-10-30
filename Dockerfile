FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml uv.lock LICENSE NOTICE.md ./
COPY src ./src
# uv is a build tool only; runtime dependencies come from the committed lock.
RUN pip install --no-cache-dir uv==0.9.8 \
    && uv export --frozen --no-dev --no-emit-project --format requirements-txt > requirements.txt \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt \
    && pip wheel --no-cache-dir --no-deps --wheel-dir /wheels .

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels \
    && useradd --system --uid 10001 app
USER 10001
EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=5s CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/healthz', timeout=3)"]
CMD ["uvicorn", "jellyfin_msx.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8090", "--workers", "1", "--no-access-log", "--no-proxy-headers"]
