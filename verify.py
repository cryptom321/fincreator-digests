#!/usr/bin/env python3
"""Check FinCreator's published calls against this repository. Standard library only.

    python verify.py chain               # every digest file: roots, digest, chain
    python verify.py call 123            # one call: its hash, and where it is listed

`call` fetches the call's public record from the FinCreator API, recomputes
SHA-256 over the exact bytes it says were hashed, prints those bytes' fields so
you can compare them with what was published, and finds the hash in the digest
files here. Run it from a clone of this repository (or pass --repo).

What a match means: the call's stored fields are the ones that were
fingerprinted on the day the digest lists. It is tamper-evident, not
tamper-proof: an edit cannot be prevented, only made visible.
"""

import argparse
import glob
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_API = "https://fincreator-production.up.railway.app"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def chain_digest(doc):
    return sha256_hex(
        canonical(
            {
                "v": doc["v"],
                "kind": doc["kind"],
                "day": doc["day"],
                "prev_digest": doc["prev_digest"],
                "published_root": doc["published_root"],
                "closed_root": doc["closed_root"],
                "excluded_root": doc["excluded_root"],
            }
        )
    )


def load_digests(repo):
    docs = []
    for path in sorted(glob.glob(os.path.join(repo, "digests", "**", "*.json"), recursive=True)):
        with open(path, encoding="utf-8") as f:
            docs.append((os.path.relpath(path, repo), json.load(f)))
    return docs


def check_file(path, doc):
    problems = []
    for name in ("published", "closed", "excluded"):
        if sha256_hex(canonical(doc[name])) != doc[f"{name}_root"]:
            problems.append(f"{path}: {name}_root does not match its list")
    if chain_digest(doc) != doc["digest"]:
        problems.append(f"{path}: digest does not match its roots and prev_digest")
    return problems


def cmd_chain(args):
    docs = load_digests(args.repo)
    if not docs:
        print("No digest files found under digests/.")
        return 1
    problems = []
    for path, doc in docs:
        problems += check_file(path, doc)
    by_prev = {}
    for path, doc in docs:
        by_prev.setdefault(doc["prev_digest"], []).append((path, doc))
    # Walk the chain from the file with no predecessor.
    heads = by_prev.get(None, [])
    if len(heads) != 1:
        problems.append(f"expected one first file (prev_digest null), found {len(heads)}")
    walked, current = [], heads[0] if len(heads) == 1 else None
    while current is not None:
        walked.append(current[0])
        nxt = by_prev.get(current[1]["digest"], [])
        if len(nxt) > 1:
            problems.append(f"{current[0]}: {len(nxt)} files claim it as their predecessor")
        current = nxt[0] if len(nxt) == 1 else None
    if len(walked) != len(docs):
        problems.append(f"chain covers {len(walked)} of {len(docs)} files")
    for line in problems:
        print("MISMATCH", line)
    if not problems:
        print(f"OK: {len(docs)} files, every root and digest recomputes, one unbroken chain.")
        print(f"   first: {walked[0]}\n   last:  {walked[-1]}")
    return 1 if problems else 0


def fetch_call(api, signal_id):
    url = f"{api.rstrip('/')}/api/public/signals/{signal_id}"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        sys.exit(f"{url}: HTTP {exc.code}")


def find(docs, signal_id, key, value):
    hits = []
    for path, doc in docs:
        for list_name in ("published", "closed"):
            for entry in doc[list_name]:
                if entry["id"] == signal_id and entry.get(key) == value:
                    hits.append(path)
    return hits


def cmd_call(args):
    call = fetch_call(args.api, args.id)
    receipt = call.get("receipt")
    if not receipt:
        print(f"Call #{args.id} has not been fingerprinted yet.")
        return 1
    docs = load_digests(args.repo)
    ok = True
    for label, hash_key, payload_key in (("call", "call_hash", "call_payload"), ("outcome", "outcome_hash", "outcome_payload")):
        stored = receipt.get(hash_key)
        if not stored:
            continue
        payload = receipt.get(payload_key)
        if payload is None:
            print(f"{label}: {stored} (sealed: the hashed bytes are public once the call closes)")
        else:
            recomputed = sha256_hex(payload.encode("utf-8"))
            match = recomputed == stored
            ok &= match
            print(f"{label}: {stored}  bytes rehash {'MATCH' if match else 'MISMATCH -> ' + recomputed}")
            for field, value in json.loads(payload).items():
                print(f"    {field:<13}{value}")
        listed = find(docs, args.id, hash_key, stored)
        ok &= bool(listed)
        print(f"    listed in: {', '.join(listed) if listed else 'NOT FOUND in this clone (pull, or not yet pushed)'}")
    if receipt.get("fingerprinted_after_publish"):
        print(f"Note: fingerprinted {receipt['call_hashed_at'][:10]}; published earlier. "
              "The check covers the call from that date on.")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Verify FinCreator call fingerprints.")
    parser.add_argument("--repo", default=os.path.dirname(os.path.abspath(__file__)), help="path to a clone of this repository")
    parser.add_argument("--api", default=DEFAULT_API, help="FinCreator API base URL")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("chain")
    one = sub.add_parser("call")
    one.add_argument("id", type=int)
    args = parser.parse_args()
    return cmd_chain(args) if args.command == "chain" else cmd_call(args)


if __name__ == "__main__":
    sys.exit(main())
