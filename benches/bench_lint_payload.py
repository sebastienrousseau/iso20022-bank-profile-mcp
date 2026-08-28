#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""What linting a payload against a clearing profile costs.

An agent working through a folder calls ``lint_payload`` once per file, and
a corporate's payment batch is not a single ``<PmtInf>`` — it is hundreds.
So the useful question is how the cost grows with the payload, and whether
it grows differently for different profiles.

Three things are measured:

* **Cost against payload size.** Read ``us/block``: flat means the linter
  scans the document once. Climbing means a rule is re-walking the tree it
  has already walked, which the fixtures — all small — would never show.

* **Cost per profile.** Profiles carry different numbers of rules, so they
  should differ. What would be a defect is one profile costing *far* more
  than its rule count explains, which usually means a rule compiled a
  pattern or re-read a definition on every call rather than once.

* **The entitlement check.** ``ACME_Premium`` is gated and the other four
  are not. Refusal should be the *cheapest* path, not the most expensive:
  a gate that does the work and then throws the answer away is both slow
  and a way to leak timing information about what the premium rules do.

Run::

    python benches/bench_lint_payload.py
    python benches/bench_lint_payload.py --json
    python benches/bench_lint_payload.py --quick     # what CI runs

Nothing here asserts a threshold: wall-clock is not comparable between
machines, and a flaky performance gate teaches people to ignore red. CI
runs ``--quick`` so a benchmark that has stopped compiling against the
current API fails the build instead of rotting into a file that reads as
verified and is not.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from iso20022_bank_profile_mcp import server  # noqa: E402

HEAD = (
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">'
    "<CstmrCdtTrfInitn>"
)
BLOCK = (
    "<PmtInf><Cdtr><PstlAdr>"
    "<StrtNm>Main St {i}</StrtNm><TwnNm>London</TwnNm><Ctry>GB</Ctry>"
    "</PstlAdr></Cdtr></PmtInf>"
)
TAIL = "</CstmrCdtTrfInitn></Document>"


def build(blocks: int) -> str:
    """A pain.001 carrying ``blocks`` credit-transfer blocks."""
    return HEAD + "".join(BLOCK.format(i=i) for i in range(blocks)) + TAIL


def _best(call, repeats: int) -> float:
    """Best-of timing after one untimed warm-up.

    The minimum is the least noisy estimator here — the mean follows
    whatever else the machine is doing. The warm-up keeps first-call import
    and definition-loading costs out of the measurement.
    """
    call()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        call()
        samples.append(time.perf_counter() - start)
    return min(samples)


def measure_size(blocks: int, profile: str, repeats: int) -> dict:
    payload = build(blocks)
    best = _best(lambda: server.lint_payload(payload, profile), repeats)
    return {
        "case": "by size",
        "profile": profile,
        "blocks": blocks,
        "bytes": len(payload),
        "ms": best * 1e3,
        "us_per_block": best * 1e6 / blocks,
    }


def measure_profiles(blocks: int, repeats: int) -> list[dict]:
    """Every profile on the same payload, entitled or not."""
    payload = build(blocks)
    rows = []
    for profile in server.list_profiles():
        pid = profile["profile_id"]

        def call(pid=pid):
            try:
                return server.lint_payload(payload, pid)
            except Exception:
                # A gated profile refuses. That is a result, not an error:
                # how quickly it refuses is exactly what we want to know.
                return None

        best = _best(call, repeats)
        rows.append(
            {
                "case": "by profile",
                "profile": pid,
                "tier": profile.get("tier"),
                "entitled": profile.get("entitled"),
                "blocks": blocks,
                "ms": best * 1e3,
            }
        )
    return rows


def run(quick: bool) -> dict:
    sizes = [10, 100] if quick else [10, 100, 1_000, 5_000]
    repeats = 3 if quick else 7
    return {
        "size": [measure_size(n, "CBPR+", repeats) for n in sizes],
        "profiles": measure_profiles(sizes[1], repeats),
    }


def render(results: dict) -> None:
    print("lint_payload against CBPR+, by payload size")
    print(f"{'blocks':>8}{'KiB':>9}{'ms':>10}{'us/block':>11}")
    for row in results["size"]:
        print(
            f"{row['blocks']:>8}{row['bytes'] / 1024:>9.1f}"
            f"{row['ms']:>10.2f}{row['us_per_block']:>11.1f}"
        )
    rows = results["size"]
    if len(rows) >= 2 and rows[0]["us_per_block"]:
        drift = rows[-1]["us_per_block"] / rows[0]["us_per_block"]
        print(
            f"  us/block at {rows[-1]['blocks']:,} is {drift:.2f}x the cost "
            f"at {rows[0]['blocks']:,}. Flat means one pass over the tree."
        )

    print("\nby profile, same payload")
    print(f"{'profile':>16}{'tier':>10}{'entitled':>10}{'ms':>10}")
    for row in results["profiles"]:
        print(
            f"{row['profile']:>16}{str(row['tier']):>10}"
            f"{str(row['entitled']):>10}{row['ms']:>10.3f}"
        )
    gated = [r for r in results["profiles"] if not r["entitled"]]
    allowed = [r for r in results["profiles"] if r["entitled"]]
    if gated and allowed:
        cheapest = min(r["ms"] for r in allowed)
        print(
            f"\n  Refusal costs {gated[0]['ms']:.3f} ms against "
            f"{cheapest:.3f} ms for the cheapest permitted profile. Refusing "
            f"should be the cheaper path: a gate that lints first and "
            f"discards the answer wastes the work and leaks timing about "
            f"rules the caller is not entitled to see."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--quick", action="store_true", help="small sizes, as CI runs"
    )
    args = parser.parse_args()

    results = run(quick=args.quick)
    if args.json:
        json.dump(results, sys.stdout, indent=1)
        print()
    else:
        render(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
