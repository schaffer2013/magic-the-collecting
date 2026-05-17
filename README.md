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
- optional four-point intake bounding boxes with original, overlay, and warped
  recognition images

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
- manual image registration with upload/camera capture and optional draggable
  four-point bounding boxes
- review actions for oldest/newest/random queue navigation and browser-side
  human verification

The same pages use responsive layouts for desktop and mobile widths.

## Entrypoints

Convenience scripts live in `entrypoints/`.

- `start-local.ps1` starts the local production-like stack and prints the UI and
  API URLs in the terminal.

## Background processing

The worker processes `unprocessed` cards one at a time through fuzzy-enigma and
moves them into the `machine_recognized` queue with ordered candidate IDs,
confidence, and review evidence. Canonical verified-card metadata is resolved
through Scrython.

## API

See [`API.md`](API.md) for the consumer-ready API contract. Keep it updated with
any route or payload changes.
