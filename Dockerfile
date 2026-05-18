FROM python:3.12-slim
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY src ./src
COPY third_party/fuzzy-enigma-card-recognition ./third_party/fuzzy-enigma-card-recognition
RUN pip install --no-cache-dir -e . \
    && pip install --no-cache-dir -e ./third_party/fuzzy-enigma-card-recognition[ocr]
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "registration_service.main:app", "--host", "0.0.0.0", "--port", "8080"]
