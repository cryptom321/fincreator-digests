# Format v1

Version 1 is permanent. A change would be a v2 applied to new calls; v1 calls
and files are never rewritten.

## Canonical JSON

Canonical JSON is UTF-8, with keys sorted, no whitespace (`,` and `:` as
separators), and non-ASCII characters left as they are. In Python:
`json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()`.

A **hash** is the lower-case hex SHA-256 of those bytes.

## Field encoding

- **Prices**: the stored double, written as the shortest string that
  round-trips to it (Python `repr(float(x))`). For example `"64321.5"`,
  `"62000.0"`, `"1e-08"`.
- **Times**: UTC, ISO-8601, always with six fractional digits and a `Z`. For
  example `"2026-10-02T09:30:15.123456Z"`.
- **Missing values**: `null`.

## Call hash

The call hash is taken in the same transaction that publishes the call.

| key | meaning |
|---|---|
| `v` | `1` |
| `id` | call id |
| `symbol` | e.g. `"BTC/USDT"` |
| `direction` | `"long"` / `"short"` |
| `timeframe` | e.g. `"4h"` |
| `entry`, `stop`, `target` | prices |
| `mode` | `"conservative"` / `"growth"` |
| `published_at` | publish time |
| `expires_at` | expiry time, part of the call's terms |
| `salt` | 32 random hex characters, unique to the call |

The salt stops anyone from guessing a sealed call's contents from its hash.
It is published along with the rest of the call.

## Outcome hash

The outcome hash is taken in the same transaction that closes the call.

| key | meaning |
|---|---|
| `v` | `1` |
| `id` | call id |
| `call_hash` | the call's hash, which chains the outcome to the call |
| `closed_at` | close time |
| `reason` | `"target"` / `"stop"` / `"expired"`, or `null` when none was recorded |
| `close_price` | price |
| `result` | `"win"` / `"loss"` / `"breakeven"` (gross) |

## Digest file

Files are pretty-printed for reading. The hashes below are always taken over
canonical JSON, never over the file's own bytes.

```
{
  "v": 1,
  "kind": "daily" | "backfill",
  "day": "YYYY-MM-DD",
  "generated_at": time,
  "prev_digest": the previous file's digest, or null for the first,
  "published": [{"id", "call_hash", "basis"}],     basis: publish | late | backfill
  "closed":    [{"id", "outcome_hash", "basis"}],  basis: close | backfill
  "excluded":  [{"id", "reason", "excluded_at"}],
  "published_root": hash(published),
  "closed_root":    hash(closed),
  "excluded_root":  hash(excluded),
  "digest": hash({"v", "kind", "day", "prev_digest", "published_root", "closed_root", "excluded_root"}),
  "note": (backfill only)
}
```

What goes into a daily file:

- **published**: calls fingerprinted on that UTC day. `late` means the call
  was fingerprinted after it was published. That happens either at its close,
  for a call published before fingerprinting began, or through a nightly
  safety net that catches any call that missed its fingerprint at publish.
- **closed**: outcomes fingerprinted on that UTC day.
- **excluded**: calls excluded from the track record on that UTC day.

Files are chained in the order they were built, through `prev_digest`.

The **backfill** file covers everything from before the first daily file:

- the calls and outcomes fingerprinted in the one-off backfill;
- the exclusions made before the first daily file.

Only real, public calls are listed. Demo, paper, cancelled and deleted rows
never appear.
