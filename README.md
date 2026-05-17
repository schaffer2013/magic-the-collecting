# Magic: The Collecting

Local-first registration and validation service for physical Magic: The Gathering
collections.

## What exists

- FastAPI JSON API plus integrated responsive web UI
- PostgreSQL-oriented schema with GUID identifiers
- unverified intake records separated from trusted collection cards
- durable DB-backed recognition worker
- trusted and unverified CSV exports
- collection-scoped duplicate image protection

## Local environments

The project keeps manual use and automated testing separate:

- **prod-like stack:** `compose.yml`, app on `http://localhost:8080`
- **test stack:** `compose.test.yml`, app on `http://localhost:18080`

Copy the environment templates once:

```bash
cp .env.prod.example .env.prod
cp .env.test.example .env.test
```

Start the prod-like stack:

```bash
./entrypoints/start-local.ps1 -Build
```

Seed a default collection in a running local environment:

```bash
python -m registration_service.seed
```

Start only the test stack:

```bash
docker compose -f compose.test.yml --env-file .env.test up --build -d
```

Reset only test data:

```bash
./scripts/reset-test-env.ps1
```

## Local development

Install:

```bash
python -m pip install -e .[dev]
```

Run tests:

```bash
./scripts/run-test-env.ps1
```

`run-test-env.ps1` starts only the test Compose stack before running the suite.
The tests themselves also use isolated test settings and temporary storage, so
they do not touch the prod-like stack or its raw-image volume.

## UI

The integrated UI includes:

- collection overview
- collection detail pages
- recognition queues
- human-review pages

The same pages use responsive layouts for desktop and mobile widths.

## Entrypoints

Convenience scripts live in `entrypoints/`.

- `start-local.ps1` starts the local production-like stack and prints the UI and
  API URLs in the terminal.

## Background processing

The worker processes `unprocessed` cards one at a time and moves them into the
`machine_recognized` queue. The current recognition adapter is intentionally a
placeholder seam until fuzzy-enigma/Scryfall-backed recognition is integrated.

## API

See [`API.md`](API.md) for the consumer-ready API contract. Keep it updated with
any route or payload changes.
