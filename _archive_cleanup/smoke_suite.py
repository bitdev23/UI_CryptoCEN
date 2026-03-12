#!/usr/bin/env python3
"""One-command smoke suite for local/CI production-like checks."""

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_step(name: str, command: list[str]) -> dict:
    print(f"\n=== {name} ===")
    started = time.time()
    proc = subprocess.run(command, cwd=str(ROOT), text=True, capture_output=True)
    duration = round(time.time() - started, 2)

    if proc.stdout:
        print(proc.stdout.strip())
    if proc.stderr:
        print(proc.stderr.strip())

    ok = proc.returncode == 0
    status = 'PASS' if ok else 'FAIL'
    print(f"[{status}] {name} ({duration}s)")
    return {
        'name': name,
        'ok': ok,
        'code': proc.returncode,
        'duration_s': duration,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Run project smoke tests in one command')
    parser.add_argument(
        '--full',
        action='store_true',
        help='Include heavier KB isolation smoke (requires Supabase service role + local worker/server)',
    )
    args = parser.parse_args()

    python = sys.executable
    steps = [
        ('Auth Smoke', [python, 'test_auth_system.py']),
        ('Feature Smoke', [python, 'scripts/feature_smoke_test.py']),
        ('Prod Flow Smoke', [python, 'scripts/prod_smoke_check.py']),
    ]

    if args.full:
        steps.append(('KB Isolation Smoke', [python, 'scripts/kb_isolation_smoke.py']))

    results = [run_step(name, cmd) for name, cmd in steps]

    print('\n=== Smoke Suite Summary ===')
    failed = [item for item in results if not item['ok']]
    for item in results:
        marker = '✅' if item['ok'] else '❌'
        print(f"{marker} {item['name']} (exit={item['code']}, {item['duration_s']}s)")

    if failed:
        print(f"\nSuite failed: {len(failed)} step(s) failed.")
        return 1

    print('\nSuite passed: all smoke steps succeeded.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
