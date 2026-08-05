# Measurements

Baselines produced by `scripts/measure-triggers.py --report`. Each line is one
run: date, scenario pass rates, and the notes from failing runs.

These exist so a prompt or routing change can be compared against what was there
before, rather than validated by a single manual run. Every prompt-shaping
decision in this harness was tuned blind until this file existed.

`trigger-baseline.jsonl` is append-only. Do not rewrite past entries — a baseline
that gets edited to match the current build is not a baseline.
