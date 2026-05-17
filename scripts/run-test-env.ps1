$env:APP_ENV = "test"
docker compose -f compose.test.yml --env-file .env.test up --build -d
python -m pytest
