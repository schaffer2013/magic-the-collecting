# API

This document is a living contract for the registration service API. Update it
whenever endpoint behavior, fields, status codes, or export shape change.

## Health

### `GET /health`

Returns service health.

```json
{"status":"ok"}
```

## Collections

Collections are first-class so the service can support more than one logical
collection. A collection may contain multiple owned copies of the same exact
printing. A submitted card appears in its target collection immediately as an
`unverified` collection-card record, then becomes `verified` after final review.

### `POST /collections`

Creates a collection.

Request:

```json
{
  "name": "Main collection",
  "description": "Optional"
}
```

Responses:

- `201 Created` with the collection
- `409 Conflict` when the name already exists

### `GET /collections`

Lists collections in creation order.

### `GET /collections/{collection_id}/cards`

Lists owned card instances for one collection.

Optional query parameter:

- `verification_state=unverified`
- `verification_state=verified`

### `GET /collections/{collection_id}/export.csv`

Exports the whole collection as CSV, one row per owned card instance.

Columns:

```text
collection_card_id,collection_id,job_id,verification_state,raw_image_uri,scryfall_id,name,set_code,collector_number,foil,language,validation_source,validated_at
```

## Registration jobs

### `POST /registration-jobs`

Creates one registration job per sorter card event, stores the raw uploaded
image on the service side, and creates one unverified collection-card record in
the target collection.

Request content type: `multipart/form-data`

Fields:

- `sorter_run_id`
- `sorter_card_seq`
- `collection_id`
- `captured_at`
- `source_pile`
- `destination_pile`
- `sorter_expected_scryfall_id` (optional)
- `sorter_recognition_payload` (optional)
- `raw_image` (file upload)

Responses:

- `201 Created` when the job is first created
- `200 OK` with the existing job when the same `(sorter_run_id, sorter_card_seq)`
  is retried

### `GET /registration-jobs/{job_id}`

Returns one job or `404 Not Found`.
