# API guidelines

## Versioning
Public APIs are versioned in the URL path (`/v1/`, `/v2/`). Breaking changes require a new major version, and the
previous version is supported for at least **12 months** after the new one is released, with deprecation announced
in the changelog and in a `Sunset` response header.

## Errors
Errors use RFC 9457 problem details (`application/problem+json`) with a stable machine-readable `type` URI.

## Pagination
List endpoints use cursor-based pagination with a `next_cursor` field; offset pagination is not allowed on tables
expected to exceed 100,000 rows. The default page size is 50 and the maximum is 200.

## Idempotency
Every `POST` that creates a resource or moves money accepts an `Idempotency-Key` header. Keys are stored for
**24 hours**; a retry with the same key and body returns the original response.

## Rate limits
The default limit is **600 requests per minute** per API key, returned in `RateLimit-*` headers; exceeding it
returns HTTP 429 with a `Retry-After` header.
