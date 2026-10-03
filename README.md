# FinCreator call digests

This repository is the public, append-only record of every trading call
FinCreator's signal engine publishes.

When a call is published, FinCreator fingerprints it with SHA-256: the
symbol, direction, timeframe, entry, stop, target, mode, publish time and
expiry. When it closes, the close time, reason, price and result get a
fingerprint too. Once a day, just after 00:00 UTC, the day's fingerprints are
committed here as one file. The file also lists any call excluded from the
track record that day, with the reason.

## What this proves, and what it does not

**Tamper-evident, not tamper-proof.** FinCreator can still edit a stored
call. Nothing here prevents that. What it does is make an edit visible:

- If someone changes a stored call later, the fingerprint you recompute from
  it no longer matches the one committed here on that day.
- To hide the change, they would have to rewrite that day's file and every
  file after it, since each file names the digest of the one before. They
  would also have to rewrite this repository's public history.

**Backfilled calls.** Calls published before fingerprinting began were
fingerprinted in one pass, recorded in `digests/backfill-<date>.json`. Their
check covers them from that date on. It says nothing about what they held
before.

## Layout

```
digests/YYYY/MM/YYYY-MM-DD.json   one file per UTC day (empty lists on a quiet day)
digests/backfill-YYYY-MM-DD.json  the one-off backfill of earlier calls
FORMAT.md                         exactly what is hashed, byte for byte
verify.py                         check the files and any call (Python 3, no dependencies)
```

## Check it yourself

```
git clone https://github.com/cryptom321/fincreator-digests && cd fincreator-digests
python verify.py chain        # every file's roots and digest recompute; one unbroken chain
python verify.py call 123     # call #123: its hash recomputes and is listed here
```

Every call has a public page at `/r/<id>` on the FinCreator site. It shows
the call, its fingerprint, and the exact bytes that were hashed, so you can
also check a call with any SHA-256 tool. The `/verify` page on the site
explains the same thing.
