# Registration Service API Contract

This is the consumer-facing contract for the registration service. Keep this
document synchronized with implementation changes to routes, fields, status
codes, state transitions, and CSV formats.

## 1. Core concepts

### Collections

A **collection** is a named container such as `General Collection` or
`Trade Binder`. Collections are API-managed resources.

### Unverified cards

An **unverified card** is intake evidence associated with one target collection.
It contains the submitted raw image, any optional expected Scryfall printing ID,
machine-recognition candidates, and its processing state.

Unverified-card states:

- `unprocessed` — accepted but not yet processed by the background worker
- `machine_recognized` — background recognition has produced candidate evidence
  and the card is eligible for human review
- `human_verified` — a reviewer has finalized the identity and the service has
  created a trusted collection-card instance

### Collection cards

A **collection card** is one trusted owned physical card instance. Multiple
collection cards may share the same Scryfall printing ID because a collection
may contain several copies of the same printing.

Trusted collection cards are created only after human verification. They have
stable GUID identifiers and can be moved from one collection to another without
changing their identity.

## 2. Common conventions

- All IDs exposed by the API are GUID strings unless noted otherwise.
- Timestamps are UTC ISO 8601 strings.
- List endpoints return JSON arrays unless documented otherwise.
- Raw images are service-owned after intake.
- Verified raw images are not deleted immediately. They become eligible for
  garbage collection only after they are at least 24 hours old.
- Duplicate intake detection is scoped to one collection and is based on exact
  image-content hashing. A duplicate image submitted again within the active
  hash window returns `409 Conflict`. Hash entries older than roughly one hour
  may be cleaned up.

## 3. Health

### `GET /health`

Returns service availability.

#### Response `200 OK`

```json
{
  "status": "ok"
}
```

#### Response fields

| Field | Type | Meaning |
|---|---|---|
| `status` | string | Current health summary. `ok` means the service is responding. |

## 4. Collections

### `POST /collections`

Creates a new collection.

#### Request body

```json
{
  "name": "General Collection",
  "description": "Primary long-term storage"
}
```

#### Request fields

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `name` | string | yes | Human-readable collection name. Must be unique. |
| `description` | string or null | no | Optional collection description. |

#### Response `201 Created`

```json
{
  "collection_id": "2f79ac7b-c85e-4d4c-a3a3-f1ab1cc079d7",
  "name": "General Collection",
  "description": "Primary long-term storage",
  "created_at": "2026-05-17T20:00:00Z"
}
```

#### Response fields

| Field | Type | Meaning |
|---|---|---|
| `collection_id` | GUID | Stable identifier for the collection. |
| `name` | string | Collection name. |
| `description` | string or null | Optional description supplied at creation. |
| `created_at` | timestamp | Time the collection was created. |

#### Errors

| Status | Meaning |
|---|---|
| `409 Conflict` | A collection with the same name already exists. |

### `GET /collections`

Lists all collections.

#### Response `200 OK`

Array of collection objects using the same fields returned by `POST /collections`.

### `GET /collections/{collection_id}/summary`

Returns state counts for one collection.

#### Path parameters

| Parameter | Type | Meaning |
|---|---|---|
| `collection_id` | GUID | Collection whose counts should be returned. |

#### Response `200 OK`

```json
{
  "collection_id": "2f79ac7b-c85e-4d4c-a3a3-f1ab1cc079d7",
  "unprocessed_count": 12,
  "machine_recognized_count": 5,
  "human_verified_unverified_count": 100,
  "trusted_collection_card_count": 100
}
```

#### Response fields

| Field | Type | Meaning |
|---|---|---|
| `collection_id` | GUID | Collection summarized. |
| `unprocessed_count` | integer | Number of intake records waiting for background recognition. |
| `machine_recognized_count` | integer | Number of intake records ready for human review. |
| `human_verified_unverified_count` | integer | Number of evidence records already human-verified. |
| `trusted_collection_card_count` | integer | Number of trusted owned card instances in the collection. |

### `GET /collections/{collection_id}/cards`

Lists trusted collection-card instances currently belonging to one collection.

#### Path parameters

| Parameter | Type | Meaning |
|---|---|---|
| `collection_id` | GUID | Collection to inspect. |

#### Response `200 OK`

```json
[
  {
    "collection_card_id": "69e21ef1-63db-4f24-80eb-3c5f1f1b7da1",
    "collection_id": "2f79ac7b-c85e-4d4c-a3a3-f1ab1cc079d7",
    "source_unverified_card_id": "fb34ce40-5cf0-45fa-b61f-9b8fe2821328",
    "scryfall_id": "verified-printing-id",
    "name": "Llanowar Elves",
    "set_code": "7ed",
    "collector_number": "253",
    "finish": "nonfoil",
    "validation_source": "human",
    "validated_at": "2026-05-17T20:10:00Z"
  }
]
```

#### Response fields

| Field | Type | Meaning |
|---|---|---|
| `collection_card_id` | GUID | Stable identifier for this owned physical card instance. |
| `collection_id` | GUID | Collection currently containing the card instance. |
| `source_unverified_card_id` | GUID or null | Intake record that produced this trusted card. |
| `scryfall_id` | string | Final exact-printing Scryfall ID. |
| `name` | string | Canonical card name derived by the service. |
| `set_code` | string | Canonical set code derived by the service. |
| `collector_number` | string | Canonical collector number derived by the service. |
| `finish` | string | Owned-copy finish, such as `nonfoil`, `foil`, `etched`, or `glossy`. |
| `validation_source` | string | Source of final validation. For v1, expected to be `human`. |
| `validated_at` | timestamp | Time human verification finalized the card. |

### `POST /collection-cards/{collection_card_id}/transfer`

Moves one trusted card instance to another collection.

#### Path parameters

| Parameter | Type | Meaning |
|---|---|---|
| `collection_card_id` | GUID | Specific owned card instance to move. |

#### Request body

```json
{
  "target_collection_id": "f58ad407-8718-44f7-8ebf-92d54d30ec67"
}
```

#### Request fields

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `target_collection_id` | GUID | yes | Destination collection for the existing card instance. |

#### Response `200 OK`

Returns the updated collection-card object.

### `POST /collection-cards/transfer`

Moves multiple trusted card instances atomically.

#### Request body

```json
{
  "collection_card_ids": [
    "69e21ef1-63db-4f24-80eb-3c5f1f1b7da1",
    "b9a2355d-43c4-4f68-a4a7-e0bd45858a15"
  ],
  "target_collection_id": "f58ad407-8718-44f7-8ebf-92d54d30ec67"
}
```

#### Request fields

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `collection_card_ids` | array of GUIDs | yes | Specific owned card instances to move. |
| `target_collection_id` | GUID | yes | Destination collection for all submitted instances. |

#### Behavior

- The batch is all-or-nothing.
- If any card cannot be transferred, no cards are moved.
- The failure response should list every submitted card ID that would fail.

#### Response `200 OK`

Returns an array of updated collection-card objects.

#### Response `409 Conflict`

```json
{
  "detail": "batch transfer could not be completed",
  "failures": [
    {
      "collection_card_id": "b9a2355d-43c4-4f68-a4a7-e0bd45858a15",
      "reason": "collection card not found"
    }
  ]
}
```

### `GET /collections/{collection_id}/export.csv`

Exports trusted collection cards only.

#### CSV columns

```text
collection_card_id,collection_id,source_unverified_card_id,scryfall_id,name,set_code,collector_number,finish,validation_source,validated_at
```

### `GET /collections/{collection_id}/unverified-cards/export.csv`

Exports unverified-card evidence records separately from the trusted collection
export.

#### CSV columns

```text
unverified_card_id,collection_id,card_state,raw_image_uri,expected_scryfall_id,machine_candidate_scryfall_ids,inducted_at
```

## 5. Intake

### `POST /collections/{collection_id}/unverified-cards`

Accepts one raw card image for one target collection and creates one unverified
card.

#### Path parameters

| Parameter | Type | Meaning |
|---|---|---|
| `collection_id` | GUID | Collection the card is intended to join after verification. |

#### Request content type

`multipart/form-data`

#### Form fields

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `raw_image` | file | yes | Raw image payload for the physical card. |
| `sorter_expected_scryfall_id` | string | no | Optional expected exact-printing Scryfall ID supplied as a hint, not authority. |
| `bounding_box` | JSON string | no | Optional four-point polygon as `[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]`, ordered clockwise from the upper-left card corner. |

#### Behavior

- The service records its own induction timestamp when the request is accepted.
- The service always stores the original uploaded image.
- If `bounding_box` is supplied, the service also stores a box-overlay image and
  a perspective-warped image; the warped image is the recognition input.
- If `bounding_box` is omitted, the whole image is used as the recognition input.
- The caller does not supply capture time, pile information, sequence numbers,
  or run identifiers.
- The service computes an image hash scoped to the target collection.
- If the same exact image was recently submitted to the same collection and the
  hash is still retained, the request fails with `409 Conflict`.

#### Response `201 Created`

```json
{
  "unverified_card_id": "fb34ce40-5cf0-45fa-b61f-9b8fe2821328",
  "collection_id": "2f79ac7b-c85e-4d4c-a3a3-f1ab1cc079d7",
  "card_state": "unprocessed",
  "raw_image_url": "/unverified-cards/fb34ce40-5cf0-45fa-b61f-9b8fe2821328/raw-image",
  "overlay_image_url": "/unverified-cards/fb34ce40-5cf0-45fa-b61f-9b8fe2821328/overlay-image",
  "recognition_image_url": "/unverified-cards/fb34ce40-5cf0-45fa-b61f-9b8fe2821328/recognition-image",
  "bounding_box": [[10, 10], [210, 12], [208, 310], [12, 308]],
  "expected_scryfall_id": "optional-hint-id",
  "machine_candidate_scryfall_ids": [],
  "inducted_at": "2026-05-17T20:05:00Z"
}
```

#### Response fields

| Field | Type | Meaning |
|---|---|---|
| `unverified_card_id` | GUID | Stable identifier for the evidence record. |
| `collection_id` | GUID | Target collection associated with the evidence. |
| `card_state` | string | Initial state, always `unprocessed` at intake. |
| `raw_image_url` | string | API path for retrieving the submitted image. |
| `overlay_image_url` | string or null | API path for the audit overlay image when a bounding box was supplied. |
| `recognition_image_url` | string | API path for the image used by recognition. |
| `bounding_box` | array or null | Four-point intake polygon when provided. |
| `expected_scryfall_id` | string or null | Optional sorter-provided identity hint. |
| `machine_candidate_scryfall_ids` | array of strings | Machine candidates. Empty until processing occurs. |
| `machine_confidence` | number or null | Confidence emitted by the machine recognizer. |
| `machine_review_reason` | string or null | Recognition-side reason the card may need human attention. |
| `inducted_at` | timestamp | Server-recorded acceptance time. |

#### Errors

| Status | Meaning |
|---|---|
| `404 Not Found` | Target collection does not exist. |
| `409 Conflict` | Duplicate image recently submitted to the same collection. |

## 6. Unverified cards and review

### `GET /collections/{collection_id}/unverified-cards`

Lists unverified-card evidence records associated with one collection.

#### Query parameters

| Parameter | Type | Required | Meaning |
|---|---|---:|---|
| `card_state` | enum | no | Optional filter: `unprocessed`, `machine_recognized`, or `human_verified`. |

#### Response `200 OK`

Array of unverified-card objects.

### `GET /collections/{collection_id}/review-cards/next`

Returns one `machine_recognized` card from a specific collection for human
review.

#### Path parameters

| Parameter | Type | Meaning |
|---|---|---|
| `collection_id` | GUID | Collection whose review queue should be sampled. |

#### Query parameters

| Parameter | Type | Required | Meaning |
|---|---|---:|---|
| `strategy` | enum | no | `oldest`, `newest`, or `random`. Default is `oldest`. `oldest` and `newest` are based on induction time. |

#### Response `200 OK`

```json
{
  "unverified_card_id": "fb34ce40-5cf0-45fa-b61f-9b8fe2821328",
  "collection_id": "2f79ac7b-c85e-4d4c-a3a3-f1ab1cc079d7",
  "card_state": "machine_recognized",
  "raw_image_url": "/unverified-cards/fb34ce40-5cf0-45fa-b61f-9b8fe2821328/raw-image",
  "expected_scryfall_id": "expected-printing-id",
  "machine_candidate_scryfall_ids": [
    "expected-printing-id",
    "alternate-printing-id"
  ],
  "inducted_at": "2026-05-17T20:05:00Z"
}
```

#### Response fields

| Field | Type | Meaning |
|---|---|---|
| `unverified_card_id` | GUID | Evidence record selected for review. |
| `collection_id` | GUID | Collection associated with the evidence. |
| `card_state` | string | Current evidence state. For this endpoint, always `machine_recognized`. |
| `raw_image_url` | string | API path for retrieving the raw submitted image. |
| `expected_scryfall_id` | string or null | Optional prior supplied during intake. |
| `machine_candidate_scryfall_ids` | array of strings | High-likelihood machine candidates ordered by confidence when available. |
| `machine_confidence` | number or null | Confidence emitted by fuzzy-enigma. |
| `machine_review_reason` | string or null | Recognition-side review reason when available. |
| `inducted_at` | timestamp | Intake time used for `oldest`/`newest` ordering. |

#### Errors

| Status | Meaning |
|---|---|
| `404 Not Found` | Collection does not exist, or it has no `machine_recognized` cards awaiting review. |

### `GET /unverified-cards/{unverified_card_id}/raw-image`

Returns the stored raw image for one unverified card.

#### Path parameters

| Parameter | Type | Meaning |
|---|---|---|
| `unverified_card_id` | GUID | Evidence record whose stored image should be returned. |

#### Response `200 OK`

Binary image payload using the stored media type where available.

### `GET /unverified-cards/{unverified_card_id}/overlay-image`

Returns the stored audit overlay image when intake supplied a bounding box.

### `GET /unverified-cards/{unverified_card_id}/recognition-image`

Returns the image used by the recognition worker. This is the warped card image
when a bounding box was supplied, otherwise a whole-image copy.

#### Errors

| Status | Meaning |
|---|---|
| `404 Not Found` | The unverified card or retained image cannot be found. |

### `POST /unverified-cards/{unverified_card_id}/verify`

Human-verifies one unverified card, marks it `human_verified`, and creates one
trusted collection-card instance.

#### Path parameters

| Parameter | Type | Meaning |
|---|---|---|
| `unverified_card_id` | GUID | Evidence record being finalized by the reviewer. |

#### Request body

```json
{
  "final_scryfall_id": "verified-printing-id",
  "finish": "nonfoil"
}
```

#### Request fields

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `final_scryfall_id` | string | yes | Final exact-printing Scryfall ID selected by the reviewer. |
| `finish` | enum | yes | Physical finish of this owned copy: `nonfoil`, `foil`, `etched`, or `glossy`. |

#### Behavior

- Canonical card fields such as name, set code, collector number, and language
  are derived by the service from the Scryfall printing ID.
- The request creates a new trusted collection-card instance linked to the
  source unverified card.
- The raw image remains retained until it is at least 24 hours old and later
  removed by garbage collection.

#### Response `200 OK`

Returns the created trusted collection-card object.

### `POST /unverified-cards/{unverified_card_id}/decision`

Records the human review outcome for one machine-recognized unverified card.
Use this endpoint for the browser review workflow when the reviewer needs to
distinguish a correct machine result from a corrected or unusable result.

#### Request body

```json
{
  "decision_kind": "right_card_wrong_printing",
  "final_scryfall_id": "verified-printing-id",
  "finish": "nonfoil",
  "notes": "Correct card, but the machine selected another printing."
}
```

#### Request fields

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `decision_kind` | enum | yes | One of `exactly_correct`, `right_card_wrong_printing`, `wrong_card`, or `unreadable`. |
| `final_scryfall_id` | string or null | conditionally | Required unless `decision_kind` is `unreadable`; final exact-printing ID selected by the reviewer. |
| `finish` | enum or null | conditionally | Required unless `decision_kind` is `unreadable`; owned-copy finish. |
| `notes` | string or null | no | Optional reviewer notes. |

#### Behavior

- Non-`unreadable` decisions also finalize the card and create the trusted
  collection-card instance.
- `unreadable` stores a review decision without creating trusted inventory.
- Any card with a review decision is removed from the pending review queue.
- A second decision for the same unverified card returns `409 Conflict`.

#### Response `200 OK`

```json
{
  "decision_kind": "right_card_wrong_printing",
  "collection_card": {
    "collection_card_id": "69e21ef1-63db-4f24-80eb-3c5f1f1b7da1",
    "collection_id": "2f79ac7b-c85e-4d4c-a3a3-f1ab1cc079d7",
    "source_unverified_card_id": "fb34ce40-5cf0-45fa-b61f-9b8fe2821328",
    "scryfall_id": "verified-printing-id",
    "name": "Llanowar Elves",
    "set_code": "7ed",
    "collector_number": "253",
    "finish": "nonfoil",
    "validation_source": "human",
    "validated_at": "2026-05-17T20:10:00Z"
  }
}
```

For `unreadable`, `collection_card` is `null`.

#### Errors

| Status | Meaning |
|---|---|
| `404 Not Found` | Unverified card does not exist. |
| `409 Conflict` | The card already has a review decision. |
| `422 Unprocessable Entity` | A final Scryfall ID or finish is missing for a decision that requires verification. |

### `GET /cards/search`

Searches Scryfall printings to help a human reviewer choose the exact final
printing.

#### Query parameters

| Parameter | Type | Required | Meaning |
|---|---|---:|---|
| `q` | string | yes | Scryfall search query. |

#### Response `200 OK`

```json
[
  {
    "scryfall_id": "verified-printing-id",
    "name": "Llanowar Elves",
    "set_code": "7ed",
    "collector_number": "253",
    "image_uri": "https://..."
  }
]
```

#### Response fields

| Field | Type | Meaning |
|---|---|---|
| `scryfall_id` | string | Exact-printing Scryfall ID. |
| `name` | string | Canonical card name. |
| `set_code` | string | Printing set code. |
| `collector_number` | string | Printing collector number. |
| `image_uri` | string or null | Canonical card image URL when available. |

## 7. Still-open contract items

The following decisions are not yet specified tightly enough to guarantee a
stable implementation contract:

1. Authentication scheme and credential roles.
2. Exact error payload shape shared across the API.
3. Whether review-card selection should reserve a card for a reviewer.
4. Whether a second verification attempt on the same unverified card is rejected
   or treated as an idempotent read of the existing collection card.
5. Whether list endpoints need pagination in v1.
6. Exact permitted raw-image formats and maximum upload size.
