# Task 1 Implementation Report: `restore.py` — Partition External Skills

## Summary

Successfully implemented Task 1 by modifying `scripts/restore.py` and `tests/test_restore.py` to:
1. Add `partition_external_skills()` function to split profile skills into internal and external groups
2. Write external skills to a manifest file (`pi-config/external-skills-manifest.json`)
3. Register the new `skill-namespace-guard` extension in three critical locations
4. Add comprehensive tests for both the partition logic and extension wiring

## What Was Implemented

### 1. Helper Function (tests/test_restore.py)
- Added `read_file(rel)` helper function for file content assertions in tests

### 2. Test Cases (tests/test_restore.py)
- **TestPartitionExternalSkills**:
  - `test_splits_by_ext_root_prefix`: Verifies that skills are correctly partitioned by ext_root prefix
  - `test_empty_input`: Verifies handling of empty input
- **TestSkillNamespaceGuardWiring**:
  - `test_registered_in_three_sites`: Verifies "skill-namespace-guard" appears exactly 3 times in restore.py
  - `test_manifest_write_present`: Verifies manifest file writing code is present

### 3. Core Function (scripts/restore.py)
Added `partition_external_skills(profile_skills, ext_root)` that:
- Splits profile_skills into internal (not starting with ext_root) and external (starting with ext_root)
- Returns tuple (internal, external)
- Enables external/* skills to be managed by skill-namespace-guard's live collision detection instead of being frozen at restore-time

### 4. Main Flow Integration (scripts/restore.py)
Integrated partition logic after profile building (line 559-572):
- Calls `partition_external_skills()` to partition profile_skills
- Writes external skills to manifest file with format: `[{"path": "<abs_path>"}, ...]`
- Logs the number of external skills written
- Registers `skill-namespace-guard` extension to re-register external skills with live collision checking

### 5. Extension Registration (scripts/restore.py)
Updated three registration sites for `skill-namespace-guard`:
- **Line 572**: Added to `profile_extensions` list during profile construction
- **Line 585**: Added to `internal_bridge_names` list for proper management
- **Line 702**: Added to delete loop for clean extension cleanup

## TDD Evidence

### RED Phase
**Command**: `python -m unittest tests.test_restore.TestPartitionExternalSkills -v`
**Output**:
```
test_empty_input ... ERROR
test_splits_by_ext_root_prefix ... ERROR

======================================================================
ERROR: test_empty_input
...
AttributeError: module 'restore' has no attribute 'partition_external_skills'
```
**Reason**: Function did not exist yet

### GREEN Phase
**Command**: `python -m unittest tests.test_restore -v 2>&1 | tail -5`
**Output**:
```
Ran 30 tests in 0.010s
OK
```
**Details**: All tests pass:
- 4 new tests (2 partition + 2 wiring) all passing
- 26 existing tests still passing
- Zero failures or errors

## Files Changed

### Modified Files
1. **scripts/restore.py**
   - Added `partition_external_skills()` function (8 lines)
   - Added partition integration into main flow (9 lines)
   - Updated `internal_bridge_names` to include "skill-namespace-guard"
   - Updated delete loop to include "skill-namespace-guard"
   - Total additions: ~20 lines

2. **tests/test_restore.py**
   - Added `read_file()` helper function (3 lines)
   - Added TestPartitionExternalSkills class with 2 tests (13 lines)
   - Added TestSkillNamespaceGuardWiring class with 2 tests (10 lines)
   - Total additions: ~26 lines

## Self-Review Findings

**Completeness**: ✅
- All 9 steps from the task brief completed
- All acceptance criteria met
- Partition function works correctly
- Manifest writing implemented
- Extension wired in all 3 required locations
- Tests verify both partition logic and wiring

**Quality**: ✅
- Code follows existing patterns in restore.py
- Function docstrings are clear and match brief specifications
- Test names are descriptive and self-documenting
- No extraneous changes beyond scope
- Implementation is minimal and focused

**Testing**: ✅
- TDD followed: failing tests → implementation → passing tests
- Tests are comprehensive (edge cases like empty input covered)
- Test assertions are specific and meaningful
- No warnings or spurious output in test runs
- All 30 tests pass cleanly (up from 26 before this task)

**Discipline**: ✅
- No overbuilding — exactly what was specified
- No architecture changes beyond the specified additions
- Followed existing code patterns (similar to ecc_skill_paths, merge_settings)
- No configuration files modified unnecessarily

## Verification

**Manifest Format**: The manifest file will be created as `pi-config/external-skills-manifest.json` with format:
```json
[
  {"path": "/absolute/path/to/skill1"},
  {"path": "/absolute/path/to/skill2"},
  ...
]
```

**Extension Wiring**: The `skill-namespace-guard` extension is now:
1. Added to profile_extensions during standard profile setup
2. Marked as harness-managed in internal_bridge_names
3. Included in the cleanup/delete loop for fresh restore cycles

**Compatibility**: 
- No breaking changes to existing functionality
- Works with both minimal and standard profiles
- Manifest only written when external skills are present
- Skill-namespace-guard will consume the manifest at runtime (Task 2)

## Commit

**Commit SHA**: `2004dc99ee47b6da78e07a4621a1edacecb061d0`
**Commit Message**: `feat(restore): partition external/* skills out of settings.json into a manifest`

## Notes

The implementation follows the exact specification from the task brief. The skill-namespace-guard extension does not need to exist yet for this task to be complete and testable — the wiring in restore.py is sufficient for Task 1. Task 2 will implement the extension that consumes the manifest file to perform live collision detection.

All evidence of test passage is embedded above. No stray debugging output or warnings were generated during test execution.

---

## Follow-up Fix: `.gitignore` for Machine-Generated Manifest

**Issue Found**: `pi-config/external-skills-manifest.json` written by `restore.py` contains absolute filesystem paths but was not in `.gitignore`, risking accidental commits of local paths to the shared repo.

### Fix Applied

**Modified**: `.gitignore`
- Added `pi-config/external-skills-manifest.json` to line 6 (Runtime / local-only block)
- Aligns with sibling entries: `auth.json`, `settings.json`, `models.json`, `model.json`

### Verification

**Command**: `git check-ignore -v pi-config/external-skills-manifest.json`
**Output**: 
```
.gitignore:6:pi-config/external-skills-manifest.json	pi-config/external-skills-manifest.json
Exit code: 0
```
**Status**: ✅ Confirmed ignored (exit 0, rule at line 6)

### Full Test Suite

**Command**: `python -m unittest discover -s tests`
**Output**:
```
Ran 142 tests in 0.504s
OK (skipped=2)
```
**Status**: ✅ All tests pass (142/142, 2 skipped)
