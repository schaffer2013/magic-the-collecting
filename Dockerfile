FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -e .
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "registration_service.main:app", "--host", "0.0.0.0", "--port", "8080"]
