FROM python:3.12-slim
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY third_party/fuzzy-enigma-card-recognition ./third_party/fuzzy-enigma-card-recognition
COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x ./docker-entrypoint.sh \
    && pip install --no-cache-dir -e . \
    && pip install --no-cache-dir -e ./third_party/fuzzy-enigma-card-recognition[ocr]
ENV DATABASE_URL=sqlite:////app/data/registration_service.db \
    RAW_IMAGE_DIR=/app/data/raw-images \
    DB_AUTO_MIGRATE=true
VOLUME ["/app/data"]
EXPOSE 8080
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "registration_service.main:app", "--host", "0.0.0.0", "--port", "8080"]
