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

The project is currently usable in two ways:

- **host-run local mode:** current practical path while Docker is not yet
  installed on the working machine; SQLite-backed, app on `http://localhost:8080`
- **future prod-like/test Docker stacks:** already scaffolded with `compose.yml`
  and `compose.test.yml`, but still waiting for end-to-end validation on a
  Docker-capable machine

### Host-run local mode

Initialize the repo, editable installs, fuzzy-enigma submodule, OCR extras, and
local recognition catalog. The first run downloads Scryfall bulk card data for
that catalog:

```powershell
.\entrypoints\setup-local-host.ps1
```

Start the app and background worker together:

```powershell
.\entrypoints\start-local-host.ps1 -Seed
```

This uses the default local SQLite database and local `data/` paths. It is the
right path for the present development session while Docker is unavailable.

### Docker stacks

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

Install only the parent app:

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
- collection detail controls for CSV exports plus single-card and batch transfers

The same pages use responsive layouts for desktop and mobile widths.

## Entrypoints

Convenience scripts live in `entrypoints/`.

- `start-local.ps1` starts the local production-like stack and prints the UI and
  API URLs in the terminal.
- `setup-local-host.ps1` initializes the host-run local environment, including
  the fuzzy-enigma submodule and local catalog.
- `start-local-host.ps1` starts the host-run app and background worker, then
  prints the UI and API URLs in the terminal.

## Background processing

The worker processes `unprocessed` cards one at a time through fuzzy-enigma and
moves them into the `machine_recognized` queue with ordered candidate IDs,
confidence, and review evidence. Canonical verified-card metadata is resolved
through Scrython.

## API

See [`API.md`](API.md) for the consumer-ready API contract. Keep it updated with
any route or payload changes.
