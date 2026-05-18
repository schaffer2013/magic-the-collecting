# Roadmap

This document is both:

1. a tiered implementation checklist, ordered by practical delivery sequence
2. a handoff note for a future engineer or agent resuming the project without
   prior session context

## Project summary

`magic-the-collecting` is a local-first registration and validation service for
physical Magic: The Gathering collections.

The service accepts raw card images for a target collection, stores them as
**unverified cards**, processes them in the background, exposes a human-review
workflow, and creates trusted **collection cards** only after final validation.

Important domain decisions:

- Unverified evidence and trusted owned cards are separate concepts.
- Collections and trusted card instances use GUIDs.
- A collection may contain multiple copies of the same exact Scryfall printing.
- Human review is required before a card becomes trusted collection inventory.
- Raw images are service-owned after intake and should not be deleted until at
  least 24 hours after verification.
- Duplicate-image prevention is scoped to one collection and should target
  accidental rapid re-submission.

## Current implementation snapshot

Implemented:

- FastAPI application with integrated responsive server-rendered UI
- PostgreSQL-oriented data model and Alembic migration foundation
- local prod-like and test Compose definitions
- separate unverified/trusted card models
- collection creation, summaries, intake, review selection, verification,
  transfer, and CSV export APIs
- optional four-point intake geometry with original, overlay, and warped
  recognition images
- DB-backed worker loop that advances one `unprocessed` card to
  `machine_recognized`
- responsive UI pages for collections, collection detail, queue, and review
- mobile-friendly manual intake UI with upload/camera capture and reusable
  draggable default bounding boxes
- automated tests using isolated temporary test storage
- root-level entrypoint script for starting the local production-like stack
- host-run local setup/start entrypoints for work before Docker is available

Known intentional gaps:

- no authentication yet
- review decisions are persisted, but unreadable-card follow-up workflows are
  still intentionally minimal

## Tier 0 — Preserve project hygiene

- [x] Keep `API.md` updated whenever the public contract changes.
- [x] Keep meaningful work off `main` until it is ready to merge.
- [x] Maintain separate prod-like and test local environments.
- [x] Verify Compose stacks end-to-end on a machine with Docker installed.
- [x] Add a host-run local workflow for the current pre-Docker phase.
- [x] Add a short contributor/dev workflow section once the first full Docker run
  has been proven.

## Tier 1 — Finish the first usable vertical slice

Goal: make the current workflow genuinely usable from intake through human
verification.

- [x] Replace placeholder catalog metadata with real Scryfall-backed canonical
  lookup for verified printing IDs.
- [x] Integrate fuzzy-enigma max-accuracy recognition into the worker path.
- [x] Persist ordered machine candidates, confidence, and debug evidence.
- [x] Add browser-side human verification submission from the review UI.
- [x] Show canonical reference image beside the raw uploaded card image.
- [x] Add review decisions for:
  - exactly correct
  - right card, wrong printing
  - wrong card
  - unreadable / insufficient evidence
- [x] Add browser UI controls for the already-supported collection-scoped
  oldest/newest/random review navigation.
- [x] Schedule duplicate-hash cleanup and verified-image cleanup jobs.

## Tier 2 — Make it dependable for real collection work

Goal: improve reliability, observability, and operator confidence.

- [ ] Add authentication and authorization for sorter clients and human users.
- [x] Define and implement a consistent API error envelope.
- [x] Add pagination to large list endpoints.
- [ ] Decide whether review selection needs reservation/locking semantics.
- [x] Decide repeated-verification behavior for already verified evidence.
- [ ] Add structured logs and metrics for intake, processing, review, retries,
  queue depth, and image cleanup. Core intake/processing/verification/transfer
  logs are in place; broader metrics remain.
- [ ] Add backup/export guidance for the production database and raw-image store.
- [x] Add upload constraints and validation for supported image formats/sizes.

## Tier 3 — Improve collection operations

Goal: make the service pleasant beyond the minimum registration workflow.

- [x] Add UI controls for transferring trusted cards between collections.
- [x] Add UI controls for trusted and unverified CSV export.
- [x] Add collection search/filtering by name, set, collector number, finish, and
  Scryfall ID.
- [x] Add bulk card-selection patterns in the collection UI.
- [ ] Add richer reviewer search for exact printing resolution.
- [ ] Add optional retained-image policy configuration.

## Tier 4 — Integrate with the sorter ecosystem

Goal: connect the service cleanly to the physical machine workflow.

- [ ] Add authenticated sorter client integration.
- [ ] Connect sorter submission flow to
  `POST /collections/{collection_id}/unverified-cards`.
- [ ] Surface collection summaries and service health in the sorter console.
- [ ] Link from sorter-side unresolved work into the service review UI.
- [ ] Confirm the sequence framework and registration service remain separate
  product tracks with stable API boundaries.

## Recommended next implementation order

1. Prove the Docker/Postgres prod-like and test stacks.
2. Replace placeholder catalog metadata with real Scryfall lookup.
3. Wire real machine recognition into the DB worker.
4. Complete browser-driven review submission and side-by-side reference images.
5. Add auth, error envelope, and metrics before broader use.

## Key files for a future handoff

- `README.md` — how to run the project locally
- `API.md` — consumer-facing HTTP contract
- `registration_service_requirements.md` — product requirements
- `AGENTS.md` — repo-specific working rules
- `src/registration_service/main.py` — current API and UI entrypoints
- `src/registration_service/models.py` — domain model

## Notes for the next engineer or agent

- Treat `API.md` as the public promise and keep it synchronized with code.
- Do not collapse `UnverifiedCard` and `CollectionCard`; that separation is
  deliberate.
- Do not reintroduce sorter run/pile/sequence details into the collection
  service API.
- Preserve test isolation from prod-like local state.
- Prefer small coherent branches and commits; merge finished work back to
  `main` intentionally.
