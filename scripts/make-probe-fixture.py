#!/usr/bin/env python3
"""Build pinned, reproducible system-prompt fixtures for the probe scripts.

Why this exists
---------------
On 2026-07-29 every model and engine comparison of the day was thrown away for
one reason: the "heavy" fixture was 23,280 tokens while the harness's real
per-turn prompt was 15,287. The fixture sat above the failure threshold, where
every configuration breaks, so every comparison returned "no difference" — an
artefact of the fixture, not a property of the configurations.

Two rules came out of that, and this script exists to make both mechanical:

1. Pin the input. A fixture assembled from the live working tree changes when
   you write up the results, so the measurement changes mid-experiment. Every
   byte here comes from a named git commit.
2. Size the fixture to the thing being simulated, not to a round number.

Token counts are model-specific
-------------------------------
A fixture is pinned by BYTES, not by tokens. Two models with different vocabs
tokenize the same bytes to different counts (Qwen3.6 and Laguna do not share a
tokenizer), so a fixture built to 15,287 Laguna tokens is not the same file as
one built to 15,287 Qwen tokens. The manifest records both the byte length and
the token count together with the server that counted them; compare fixtures by
sha256, and treat the token count as a property of a (fixture, model) pair.

Usage
-----
    # size against the model currently being served
    python scripts/make-probe-fixture.py --out /tmp/fx --tokens 671 --tokens 15287 \\
        --url http://127.0.0.1:8080

    # no server: size by bytes only (token count left unrecorded)
    python scripts/make-probe-fixture.py --out /tmp/fx --bytes 60000

Each run writes the fixtures plus `manifest.json` next to them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Fixed, ordered source lists. Order is part of a fixture's identity: reordering
# changes the bytes and invalidates comparison with older runs.
#
# `rules` reproduces what the harness actually injects — numbered rules and
# imperatives. An earlier version of this file called these "prose the model has
# no reason to act on". That was wrong, and the error mattered: at 26,048 tokens
# Qwythos answered
#     "Read RULE 8 + RULE 10 — need verification first:"
# with no tool call. The filler was not inert, it was competing with the user's
# request, and the model obeyed the filler. Filler SHAPE is therefore a variable,
# not a constant, and it gets its own flag so the two can be told apart:
# `--sources rules` measures the harness's real condition, `--sources neutral`
# measures size with the imperatives removed. Comparing them at one size is what
# separates "the prompt is too big" from "the prompt argues with the request".
SOURCE_SETS = {
    "rules": (
        "docs/core/CORE_CONCEPTS.md",
        "docs/core/DISTILLATION_GUIDE.md",
        "pi-rules/AGENTS.md",
        "docs/KNOWN_ISSUES.md",
    ),
    # Scraped web prose already vendored for the stealth-web tests: descriptive,
    # no instructions addressed to an agent.
    "neutral": (
        "tests/fixtures/ax-wikipedia-article.txt",
        "tests/fixtures/ax-docs-site.txt",
        "tests/fixtures/ax-news-homepage.txt",
    ),
}
DEFAULT_SOURCES = SOURCE_SETS["rules"]

# The probe asks the model to read a target file. If that file is described in
# the fixture, "I already have it" becomes a correct answer with no tool call
# and gets scored as a failure. Keep the two disjoint.
DEFAULT_TARGET = "scripts/verify-bridges.py"


class FixtureError(RuntimeError):
    pass


def read_pinned(commit: str, path: str, run=subprocess.run) -> str:
    """Return one source file's contents as of `commit`."""
    proc = run(
        ["git", "show", f"{commit}:{path}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise FixtureError(f"git show {commit}:{path} failed: {proc.stderr.strip()}")
    return proc.stdout


def build_source_text(commit: str, sources=DEFAULT_SOURCES, reader=read_pinned) -> str:
    """Concatenate the pinned sources, repeating them until long enough to cut.

    The sources total ~65 KB. Asking for a fixture larger than that has to come
    from somewhere, and repeating the same pinned bytes keeps the result
    deterministic — a fixture must be rebuildable byte-for-byte from a commit id
    alone.
    """
    parts = [reader(commit, path) for path in sources]
    if not any(part.strip() for part in parts):
        raise FixtureError("every pinned source was empty; wrong commit?")
    return "\n\n".join(parts)


def repeat_to_bytes(text: str, want_bytes: int) -> str:
    """Grow `text` by whole repetitions until it covers `want_bytes`, then cut.

    Cutting happens on a character boundary and the result is re-encoded, so the
    returned string's UTF-8 length can land a byte or two under the request when
    the cut falls inside a multi-byte character. That is fine: fixtures are
    compared by sha256, not by hitting an exact byte count.
    """
    if want_bytes <= 0:
        raise FixtureError("--bytes must be positive")
    chunk = text
    while len(chunk.encode("utf-8")) < want_bytes:
        chunk = chunk + "\n\n" + text
    lo, hi = 0, len(chunk)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if len(chunk[:mid].encode("utf-8")) <= want_bytes:
            lo = mid
        else:
            hi = mid - 1
    return chunk[:lo]


def count_tokens(url: str, text: str, opener=urllib.request.urlopen) -> int:
    """Ask the llama.cpp server how many tokens `text` is, for ITS model."""
    body = json.dumps({"content": text}).encode("utf-8")
    req = urllib.request.Request(
        f"{url.rstrip('/')}/tokenize",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with opener(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:  # server down, wrong port, still loading
        raise FixtureError(f"POST {url}/tokenize failed: {exc}") from exc
    tokens = payload.get("tokens")
    if not isinstance(tokens, list):
        raise FixtureError(f"unexpected /tokenize response: {payload!r}")
    return len(tokens)


def size_to_tokens(text: str, want_tokens: int, counter, tolerance: int = 25) -> tuple[str, int]:
    """Binary-search a byte length whose token count lands near `want_tokens`.

    Returns the sized text and its measured token count. `counter` takes a
    string and returns a token count, so the search is testable without a
    server.
    """
    if want_tokens <= 0:
        raise FixtureError("--tokens must be positive")
    # Seed from a measured bytes-per-token ratio rather than a guessed constant:
    # the ratio differs by roughly 2x between English prose and CJK, and this
    # repo's docs are a mix of both.
    sample = repeat_to_bytes(text, min(len(text.encode("utf-8")), 20000))
    sample_tokens = counter(sample)
    if sample_tokens <= 0:
        raise FixtureError("tokenizer returned no tokens for the sample")
    ratio = len(sample.encode("utf-8")) / sample_tokens

    lo, hi = 1, max(int(want_tokens * ratio * 2), 64)
    best: tuple[str, int] | None = None
    # Bounded: 24 halvings resolve any byte range this script can produce, and a
    # hung search against a live server is worse than an approximate fixture.
    for _ in range(24):
        mid = (lo + hi) // 2
        candidate = repeat_to_bytes(text, mid)
        got = counter(candidate)
        if best is None or abs(got - want_tokens) < abs(best[1] - want_tokens):
            best = (candidate, got)
        if abs(got - want_tokens) <= tolerance:
            return candidate, got
        if got < want_tokens:
            lo = mid + 1
        else:
            hi = mid - 1
        if lo > hi:
            break
    assert best is not None
    return best


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="directory to write fixtures into")
    ap.add_argument("--commit", default="HEAD", help="git commit to pin sources at (default: HEAD)")
    ap.add_argument("--tokens", type=int, action="append", default=[], help="target token count; repeatable")
    ap.add_argument("--bytes", type=int, action="append", default=[], help="target byte count; repeatable")
    ap.add_argument("--url", default="http://127.0.0.1:8080", help="llama.cpp server used to count tokens")
    ap.add_argument(
        "--sources",
        choices=sorted(SOURCE_SETS),
        default="rules",
        help="filler shape: 'rules' = the harness's own imperatives (default), 'neutral' = descriptive prose",
    )
    args = ap.parse_args(argv)

    if not args.tokens and not args.bytes:
        ap.error("give at least one --tokens or --bytes")

    # Resolve the commit so the manifest names a specific object, not a moving
    # ref. A fixture recorded as "HEAD" cannot be rebuilt after the next commit.
    resolved = subprocess.run(
        ["git", "rev-parse", args.commit], capture_output=True, text=True
    )
    if resolved.returncode != 0:
        print(f"cannot resolve commit {args.commit}: {resolved.stderr.strip()}", file=sys.stderr)
        return 2
    commit = resolved.stdout.strip()

    try:
        source = build_source_text(commit, SOURCE_SETS[args.sources])
    except FixtureError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    tag = "" if args.sources == "rules" else f"-{args.sources}"
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = []

    for want in args.bytes:
        text = repeat_to_bytes(source, want)
        path = out_dir / f"fixture{tag}-{len(text.encode('utf-8'))}b.txt"
        path.write_text(text, encoding="utf-8")
        entries.append(
            {
                "file": path.name,
                "bytes": len(text.encode("utf-8")),
                "tokens": None,
                "tokenizer_url": None,
                "sha256": sha256(text),
            }
        )

    if args.tokens:
        counter = lambda t: count_tokens(args.url, t)  # noqa: E731 - injected for tests
        for want in args.tokens:
            try:
                text, got = size_to_tokens(source, want, counter)
            except FixtureError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            path = out_dir / f"fixture{tag}-{got}tok.txt"
            path.write_text(text, encoding="utf-8")
            entries.append(
                {
                    "file": path.name,
                    "bytes": len(text.encode("utf-8")),
                    "tokens": got,
                    "requested_tokens": want,
                    "tokenizer_url": args.url,
                    "sha256": sha256(text),
                }
            )

    manifest = {
        "commit": commit,
        "source_set": args.sources,
        "sources": list(SOURCE_SETS[args.sources]),
        "target_file_excluded_from_fixture": DEFAULT_TARGET,
        "fixtures": entries,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    for entry in entries:
        tok = entry["tokens"]
        print(f"{entry['file']}  {entry['bytes']} bytes  {tok if tok is not None else '?'} tokens  {entry['sha256'][:12]}")
    print(f"manifest: {out_dir / 'manifest.json'} (commit {commit[:12]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
