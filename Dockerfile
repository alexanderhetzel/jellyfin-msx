FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS builder
WORKDIR /build
COPY pyproject.toml uv.lock LICENSE NOTICE.md ./
COPY src ./src
COPY tools/requirements.txt ./uv-requirements.txt
# uv is a build tool only; runtime dependencies come from the committed lock.
RUN pip install --no-cache-dir --require-hashes --only-binary=:all: -r uv-requirements.txt \
    && uv export --frozen --no-dev --no-emit-project --format requirements-txt > requirements.txt \
    && uv export --frozen --only-group build --format requirements-txt > build-requirements.txt \
    && pip install --no-cache-dir --require-hashes --only-binary=:all: -r build-requirements.txt \
    && pip wheel --no-cache-dir --require-hashes --only-binary=:all: --no-deps --wheel-dir /wheels -r requirements.txt \
    && uv build --wheel --no-build-isolation --offline --out-dir /wheels

FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --no-deps --no-compile /wheels/* \
    && rm -rf /wheels \
    && useradd --system --uid 10001 app
USER 10001
EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=5s CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/healthz', timeout=3)"]
CMD ["uvicorn", "jellyfin_msx.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8090", "--workers", "1", "--no-access-log", "--no-proxy-headers"]
