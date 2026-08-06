# 📜 Constitution — CK's Pi Code Agent Harness

> **Authority:** Human Architect (制憲者). ONLY human can modify this file.
> **Read-Only for:** All AI agents (Layer 2 Macro, Layer 3 Micro).
> **Last Updated:** 2026-08-06

## Mission Objective

Make the harness's own methodology actually run, and prove it with evidence from
real sessions rather than from unit tests.

## Non-Negotiable Constraints

These are not preferences. Violating one invalidates the work.

1. **Evidence at write time.** Every number in a report or commit message comes
   from a run made while writing it. If it cannot be verified then, no number is
   given. (`CLAUDE.md` § Evidence-Based Completion.)
2. **A guard that never fired is unvalidated, not working.** State before
   measuring what a run would have to *do* to trigger it, then check the runs
   against that.
3. **After a guard fires, diff the numbers it did not target.** Every tightening
   here has produced a new evasion: the citation gate took fabricated URLs from
   0 to 4 in the run where it took real ones from 0 to 10.
4. **Do not fork the vendored protocols.** C.A.S.E. and MECE-Autopilot live
   upstream in `external/`. The harness enforces them; it never reimplements
   them.
5. **Never report a refused change as done.** This binds the harness's own
   reports as much as the model's.
6. **Worker agents MUST NOT write outside their assigned task folder.**

## Domain-Specific Rules

- **Installed copies, not repo files.** Pi runs `~/.pi/agent/extensions/`.
  Editing `pi-extensions/` or `pi-skills/` requires
  `python scripts/setup.py --mode restore` before any test means anything.
- **Testing:** every guard gets unit tests AND is deliberately broken once to
  prove the tests can fail. A green suite that cannot go red measures nothing.
- **The probe is an instrument, not a boundary.** When
  `scripts/measure-triggers.py` cannot reach a condition, build a fixture that
  can — it took twenty minutes the first time and found three real defects.
- **Language:** Traditional Chinese (Taiwan usage) for prose to the architect;
  English for code, comments and commit messages.

## Escalation Policy

Three consecutive self-healing attempts on the same failure, then `status.txt`
goes to `ESCALATED` with the reason in `feedback.md`. The same budget every
guard in this harness uses, for the same reason: a rule declined three times
will not work on the fourth, and further attempts only deadlock.

## Definition of a finished decision

A decision is finished when it names what was measured, what it cost, what it
did **not** solve, and what would falsify it.

---
*This file is the Constitution. It defines the boundaries within which all AI agents operate. Violating any constraint is a critical error.*
