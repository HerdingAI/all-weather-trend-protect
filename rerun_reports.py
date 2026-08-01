"""
rerun_reports.py -- regenerate every risk-parity eval report on clean data.

WHY A DRIVER AND NOT A SHELL LOOP
---------------------------------
`--schemes` defaults to `",".join(SCHEME_ORDER)`, and SCHEME_ORDER grew from 6
to 50 entries across the nine TrendProtect rounds. Re-running an older round
today WITHOUT an explicit scheme list therefore silently produces a different,
much larger run (round 1 would become a 50-scheme run, not a 10-scheme one).

The documented invocations cannot be trusted either: docs/portfolio-flavors.md
omits --out-dir for round 1 (which would clobber output/risk_parity_eval) and
lists 42 schemes for asym8 where that report's own header shows 45.

So each round's configuration is recovered from the one artifact that recorded
what actually ran: the "- **Schemes:**" line in its own report_eval.md.

Runs are executed in parallel with BLAS pinned to one thread per process --
without pinning, each process spawns ~20 BLAS threads and oversubscription
makes the batch slower than running serially.

Usage:
    .venv/bin/python rerun_reports.py --list
    .venv/bin/python rerun_reports.py --jobs 4
    .venv/bin/python rerun_reports.py --only risk_parity_eval_asym9
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
PY = os.path.join(HERE, ".venv", "bin", "python")

# Round order matters only for reporting; execution is parallel.
EVAL_DIRS = [
    "risk_parity_eval",
    "risk_parity_eval_asym",
    "risk_parity_eval_asym2",
    "risk_parity_eval_asym2b",
    "risk_parity_eval_asym3",
    "risk_parity_eval_asym4",
    "risk_parity_eval_asym4b",
    "risk_parity_eval_asym5",
    "risk_parity_eval_asym6",
    "risk_parity_eval_asym7",
    "risk_parity_eval_asym8",
    "risk_parity_eval_asym9",
]

# Rounds 2b onward were run with a reduced bootstrap; earlier rounds used the
# argparse default (5000). --rolling-schemes is omitted throughout because the
# documented value is identical to the default.
BOOTSTRAP_2000_FROM = EVAL_DIRS.index("risk_parity_eval_asym2b")

SCHEMES_RE = re.compile(r"^- \*\*Schemes:\*\*\s*(.+?)\s+—", re.M)
SCORE_RE = re.compile(r"--score-mode\s+(asymmetric2|asymmetric|default)")


def parse_config(dirname: str) -> dict:
    """Recover a round's actual configuration from its committed report."""
    if dirname not in EVAL_DIRS:
        raise SystemExit(
            f"{dirname!r} is not a known eval round.\nKnown rounds:\n  "
            + "\n  ".join(EVAL_DIRS))
    report = os.path.join(OUT, dirname, "report_eval.md")
    if not os.path.exists(report):
        raise SystemExit(f"{dirname}: no report_eval.md to recover config from")
    text = open(report, encoding="utf-8").read()

    m = SCHEMES_RE.search(text)
    if not m:
        raise SystemExit(f"{dirname}: could not parse the '- **Schemes:**' line")
    schemes = [s.strip() for s in m.group(1).split(",") if s.strip()]

    score = SCORE_RE.search(text)
    return {
        "dir": dirname,
        "schemes": schemes,
        "score_mode": score.group(1) if score else "default",
        "bootstrap": 2000 if EVAL_DIRS.index(dirname) >= BOOTSTRAP_2000_FROM else None,
    }


def build_cmd(cfg: dict) -> list[str]:
    cmd = [PY, os.path.join(HERE, "risk_parity_eval.py"),
           "--schemes", ",".join(cfg["schemes"]),
           "--out-dir", os.path.join(OUT, cfg["dir"])]
    if cfg["score_mode"] != "default":
        cmd += ["--score-mode", cfg["score_mode"]]
    if cfg["bootstrap"]:
        cmd += ["--bootstrap", str(cfg["bootstrap"])]
    return cmd


def run_one(cfg: dict, log_dir: str, timeout: float) -> dict:
    env = dict(os.environ)
    env.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    log_path = os.path.join(log_dir, f"{cfg['dir']}.log")
    t0 = time.time()
    with open(log_path, "w") as log:
        try:
            # Bounded so a hung round cannot hold a --jobs slot forever and
            # stall the whole batch (the largest real round takes ~1h).
            rc = subprocess.run(build_cmd(cfg), stdout=log, stderr=subprocess.STDOUT,
                                cwd=HERE, env=env, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            log.write(f"\n\n*** killed by rerun_reports after {timeout}s ***\n")
            rc = -1
    return {**cfg, "rc": rc, "secs": time.time() - t0, "log": log_path}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", type=int, default=4,
                    help="Concurrent runs. Sized by RAM, not cores (default 4).")
    ap.add_argument("--only", action="append", default=None,
                    help="Run just this output dir (repeatable).")
    ap.add_argument("--list", action="store_true",
                    help="Print the recovered commands and exit.")
    ap.add_argument("--from-snapshot", metavar="PATH",
                    help="Recover configs from a configs.json written by an "
                         "earlier run, instead of re-parsing the reports. Use "
                         "when a report was corrupted by an interrupted write.")
    ap.add_argument("--timeout", type=float, default=6 * 3600,
                    help="Per-round wall-clock cap in seconds (default 6h). A "
                         "round that exceeds it is killed and reported rc=-1 "
                         "rather than holding a slot forever.")
    ap.add_argument("--log-dir", default=os.path.join(HERE, "output", "_rerun_logs"))
    args = ap.parse_args(argv)

    if args.jobs < 1:
        raise SystemExit(f"--jobs must be >= 1 (got {args.jobs})")

    targets = list(dict.fromkeys(args.only or EVAL_DIRS))   # de-dup: two runs
    if args.from_snapshot:                                  # into one out-dir race
        with open(args.from_snapshot) as fh:
            by_dir = {c["dir"]: c for c in json.load(fh)}
        missing = [d for d in targets if d not in by_dir]
        if missing:
            raise SystemExit(f"snapshot {args.from_snapshot} lacks: {missing}")
        cfgs = [by_dir[d] for d in targets]
    else:
        cfgs = [parse_config(d) for d in targets]

    if args.list:
        for c in cfgs:
            print(f"\n# {c['dir']}  ({len(c['schemes'])} schemes, "
                  f"score={c['score_mode']}, bootstrap={c['bootstrap'] or 'default'})")
            print(" ".join(build_cmd(c)))
        return 0

    # Longest-processing-time-first: cost scales with scheme count (2817 combos
    # x n_schemes), and asym9 is 50 schemes vs round 1's 6. Submitting in the
    # historical order would start the largest run last and leave it as a long
    # single-threaded tail after everything else has finished.
    cfgs.sort(key=lambda c: len(c["schemes"]), reverse=True)

    os.makedirs(args.log_dir, exist_ok=True)

    # Snapshot the recovered configs BEFORE running. Each run truncates the very
    # report it was parsed from (risk_parity_eval.py opens report_eval.md with
    # "w" as its last action), so an interrupt inside that write can leave a
    # 0-byte or half-flushed report -- and because every target is parsed up
    # front, one unparseable report then blocks re-running the other eleven.
    # The report is the only record of what ran; do not destroy it without a copy.
    # MERGE, never truncate: a `--only <round>` run would otherwise replace the
    # snapshot with a single entry and destroy the recovery record for the other
    # eleven rounds -- exactly when recovery matters most.
    snapshot = os.path.join(args.log_dir, "configs.json")
    merged = {}
    if os.path.exists(snapshot):
        try:
            with open(snapshot) as fh:
                merged = {c["dir"]: c for c in json.load(fh)}
        except (json.JSONDecodeError, KeyError, TypeError):
            print(f"  note: {snapshot} unreadable; starting a fresh snapshot")
    merged.update({c["dir"]: c for c in cfgs})
    tmp = f"{snapshot}.tmp.{os.getpid()}"
    with open(tmp, "w") as fh:
        json.dump(list(merged.values()), fh, indent=2)
    os.replace(tmp, snapshot)

    print(f"Re-running {len(cfgs)} eval rounds, {args.jobs} at a time, "
          f"BLAS pinned to 1 thread/process, largest first.")
    print(f"Logs: {args.log_dir}")
    print(f"Config snapshot: {snapshot}\n")

    results, t0 = [], time.time()
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futs = {pool.submit(run_one, c, args.log_dir, args.timeout): c for c in cfgs}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            status = "OK " if r["rc"] == 0 else f"FAIL(rc={r['rc']})"
            print(f"  [{len(results)}/{len(cfgs)}] {status} {r['dir']:32s} "
                  f"{r['secs']/60:5.1f} min  ({len(r['schemes'])} schemes)")

    print(f"\nWall clock: {(time.time()-t0)/60:.1f} min")
    failed = [r for r in results if r["rc"] != 0]
    if failed:
        print("\nFAILED runs (see logs):")
        for r in failed:
            print(f"  {r['dir']}  ->  {r['log']}")
        return 1
    print("All runs completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
