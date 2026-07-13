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

- **host-run local mode:** SQLite-backed, app on `http://localhost:8080`
- **prod-like/test Docker stacks:** validated local PostgreSQL-backed stacks
  defined by `compose.yml` and `compose.test.yml`

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

This uses the default local SQLite database and local `data/` paths.

### Docker stacks

Copy the environment templates once:

```bash
cp .env.prod.example .env.prod
cp .env.test.example .env.test
```

Start the prod-like stack from a local build:

```bash
./entrypoints/start-local.ps1 -Build
```

The production-like stack stores PostgreSQL data in the `prod_pgdata` Docker
volume and raw card images in the `prod_images` Docker volume. Those volumes are
not part of the application image, so rebuilding, tagging, or pushing the image
does not overwrite collection data. On container startup, `docker-entrypoint.sh`
runs Alembic migrations when `DB_AUTO_MIGRATE=true` so a new empty database is
instantiated automatically and an existing database is migrated in place.

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

### Building and deploying the Docker image

Set the image name you want to publish. You can add this to `.env.prod` or pass
it in the shell when running Compose:

```bash
APP_IMAGE=registry.example.com/magic-the-collecting:0.2.0
```

Build and push the app/worker image without including runtime databases or image
uploads:

```bash
docker compose --env-file .env.prod build app worker
docker compose --env-file .env.prod push app worker
```

On the deployment host, keep the same `compose.yml` and `.env.prod`, then pull
and start the published image without rebuilding it on that host:

```bash
docker compose --env-file .env.prod pull app worker
docker compose --env-file .env.prod up -d --no-build
```

For single-container SQLite experiments, mount `/app/data` to durable storage.
The image defaults to `sqlite:////app/data/registration_service.db`, which lets
the entrypoint create the database on first run without baking the database file
into the image. Production-like deployments should continue to use PostgreSQL via
`DATABASE_URL`.

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

## Contributor workflow

For normal local work:

1. Create or switch to a focused working branch.
2. Use `.\scripts\run-test-env.ps1` for the parent app test suite.
3. Use `.\entrypoints\start-local.ps1 -Build` when you need the full
   PostgreSQL-backed app plus worker stack.
4. Keep `API.md` synchronized with any public contract changes before merging.

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

Verified raw images are retained for at least 24 hours by default before worker
cleanup may remove them. Set `RAW_IMAGE_MIN_RETENTION_HOURS` in `.env.prod` when
you want a longer local grace period.

## Backups

For a local Docker deployment, treat the PostgreSQL data and raw-image volume as
separate assets:

```powershell
docker compose exec db pg_dump -U magic magic_collecting > magic_collecting.sql
docker run --rm -v mtg-collection_prod_images:/data -v ${PWD}:/backup alpine `
  tar -czf /backup/raw-images.tar.gz -C /data .
```

Restore the SQL dump into a fresh database with `psql`, and restore
`raw-images.tar.gz` into the `prod_images` volume before relying on image-backed
review history. The trusted-card CSV export is useful for portability, but it is
not a full backup because it does not include unverified evidence or review
history.

## API

See [`API.md`](API.md) for the consumer-ready API contract. Keep it updated with
any route or payload changes.
