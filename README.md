# Magic: The Collecting

`magic-the-collecting` is the beginning of a registration and validation service
for a Magic: The Gathering card-sorting ecosystem.

The service is intended to:

- accept image-based registration jobs from a sorter
- store submitted images on the service side
- create unverified collection-card records at intake time
- later support review and exact-printing validation
- maintain collections as sets of owned card instances, including duplicate
  copies of the same exact printing

## Current status

The repository currently contains:

- product requirements for the registration service
- product requirements for the sorter sequence framework
- a first FastAPI service skeleton
- SQLite-backed models for collections, registration jobs, and collection cards
- multipart registration-job intake with raw-image storage
- collection listing and CSV export endpoints
- API documentation in [`API.md`](API.md)

## Development

Install the project and development dependencies:

```bash
python -m pip install -e .[dev]
```

Run tests:

```bash
python -m pytest
```

Run the service locally:

```bash
python -m uvicorn registration_service.main:app --reload
```

## API

The API contract is documented in [`API.md`](API.md). The repository also
contains `AGENTS.md`, which instructs future coding agents to keep the API
documentation current whenever endpoints or response shapes change.
