FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY deploy/footprints/requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install --requirement requirements.txt

COPY deploy/footprints/app.py ./
# Footprint statistics come from the package (eoforeststac.analytics); only
# the source is copied, without the package's own dependency pins
COPY eoforeststac/ ./eoforeststac/

RUN groupadd --system --gid 10001 eoforest && \
    useradd --system --uid 10001 --gid eoforest --no-create-home eoforest

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-server-header"]
