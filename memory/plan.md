# Plan: Make paired points optional in Wand calibration (unpaired-only support)

## Key finding
The GUI and CLI already accept an empty/absent paired-points file, and `sbaArgusDriver.getPointsAndExtArray` already has a working unpaired-only branch. The feature currently fails only because of **runtime crashes** in `OutlierWindow.buildData` (in `argus_gui/sbaDriver.py`) that reference paired-only variables when `nppts == 0`. Fixing those three crash sites is the minimal, correct change. No new SBA initialization path is needed.

## How the call path works (verified by planner subagent)
- GUI: `argus_gui/Argus.py::wand_go` (line ~1493) builds a subprocess command and passes `self.ppts.text()` and `self.uppts.text()` verbatim as `--paired_points` / `--unpaired_points`. There is no validation requiring the paired file. If the paired field is empty, an empty string is passed.
- Script: `argus_gui/resources/scripts/argus-wand`. Lines 160-168 set `paired_points = None` when `args.paired_points` is falsy. Lines 91-99 validate shapes only when the array is not `None`. Lines 102-106 already special-case `paired_points is None and unpaired_points is not None`. Undistortion loops (lines 265, 284, 303) are guarded by `type(x) is not type(None)`. The script already supports unpaired-only.
- Driver: `argus_gui/sbaDriver.py::sbaArgusDriver`. `rearrange` (121-124) and `getPointsAndExtArray` (168-227) already branch on `ppts is None` / `uppts is None`; the unpaired-only branch (213-227) sets `indices['paired'] = None`. `fix()` guards `npframes`/`nupframes` with `if self.ppts is not None` (333-341). The driver's data-prep already supports unpaired-only.
- SBA handoff: `getPointsAndExtArray` triangulates whatever correspondences exist via `multiTriangulator` (line 239) and passes them to `sba.SparseBundleAdjust` (line 292). Paired points are **not** used for camera pose initialization — they are treated identically to unpaired points for triangulation/BA. Paired data is used only to (a) define metric scale from the known wand length and (b) compute the Wand Score. Both are already guarded by `if self.nppts != 0` (scale block 694-703; wand-score block 767-773).

## Meaning of paired vs unpaired (cite: `docs/user-guide.md` lines 132-133, 163)
- **Paired points**: two Clicker tracks marking the two ends of a wand a constant distance apart. Shape = `4 * ncams` columns. Used to set metric scale (wand length) and to compute the Wand Score (`100 * std/mean` of reconstructed wand length).
- **Unpaired points**: one or more Clicker tracks of any object(s) visible in multiple synced cameras. Shape = a multiple of `2 * ncams` columns. Used purely to add triangulatable correspondences that improve camera extrinsics via bundle adjustment. No scale information.

## The actual blockers (crash sites in `argus_gui/sbaDriver.py`, `OutlierWindow.buildData`)
For unpaired-only, `nppts == 0`, so:
1. Lines ~730-732 (`self.paired = paired`, `self.pairedSet1 = pairedSet1`, `self.pairedSet2 = pairedSet2`): `paired`, `pairedSet1`, `pairedSet2` are only assigned inside `if self.nppts != 0:` (lines ~696-697, 721-723). When `nppts == 0` they are undefined → `NameError`.
2. Line ~774 (`WandOutputter(..., self.up, ...)`): `self.up` is only assigned inside `if self.nuppts != 0:` (line ~726). Safe for unpaired-only (nuppts>0), but undefined in the pre-existing paired-only case; set a default for robustness.
3. Lines ~771-772: the `else` branch prints "Wand score: not applicable" but never sets `self.wandscore`. When `Display results` is on, `init_UI` line ~551 (`f"Wand score: {self.wandscore}"`) → `AttributeError`.

**Verified against current source (argus_gui/sbaDriver.py):**
- Lines 721-723: `if self.nppts != 0: paired = ...; p1, p2, pairedSet1, pairedSet2 = ...`
- Lines 725-726: `if self.nuppts != 0: self.up = xyzs[...]`
- Lines 730-732: `self.paired = paired`, `self.pairedSet1 = pairedSet1`, `self.pairedSet2 = pairedSet2` — unconditional, but `paired`/`pairedSet1`/`pairedSet2` only exist if the block at 721-723 ran → `NameError` when `nppts == 0`.
- Line 774: `outputter = WandOutputter(..., self.up, ...)` — `self.up` only exists if 725-726 ran (fine when nuppts != 0, i.e. the unpaired-only case, but not robust in general).
- Lines 767-772: `if self.nppts != 0: self.wandscore = ...` / `else: print('\nWand score: not applicable')` — `self.wandscore` never set in the else branch → `AttributeError` at line 551 (`f"Wand score: {self.wandscore}"` in `init_UI`) when display is on.

## Changes to make

### Change 1 — `argus_gui/sbaDriver.py`, `OutlierWindow.buildData`
Before line 721 (`if self.nppts != 0:` — the second occurrence, the one right after the "now that we've applied the scale and alignment" comment), add defaults so `paired`/`pairedSet1`/`pairedSet2` are always bound:
```python
paired = None
pairedSet1 = None
pairedSet2 = None
```
Before line 725 (`if self.nuppts != 0:`), add `self.up = None`.
Leave the existing `if` blocks that populate these when data is present unchanged.

### Change 2 — `argus_gui/sbaDriver.py`, `OutlierWindow.buildData` (wand-score block, lines 767-772)
In the `else` branch, set the attribute so the UI can render it. Change:
```python
else:
    print('\nWand score: not applicable')
```
to also set `self.wandscore = 'not applicable'` (a string — it's interpolated into an f-string at line 551). Keep the `if self.nppts != 0:` branch computing the numeric score unchanged.

### Change 3 (optional, parallel dead code) — `argus_gui/graphers.py`, `wandGrapher`
`wandGrapher` (class at line ~618) is imported via `from .graphers import *` but is never instantiated (the live path is `sbaDriver.OutlierWindow`). It contains the same `nppts == 0` structural bug around lines ~1016-1044 and ~1070-1074. Apply the same two guards there only if time permits; not required for the feature. Skip unless trivial.

### Change 4 (optional UX) — `argus_gui/Argus.py`, `add` method (lines ~1066-1069)
Currently the output-name field auto-fills only when the paired file is chosen (`if button == self.ppts_button`). For unpaired-only workflows the user gets no default output name. Optionally add: if `button == self.uppts_button and onam.text() == "" and self.ppts.text() == ""`, set `onam` from `self.uppts.text().split(".")[0] + "_cal"`. Purely convenience; skip unless trivial.

## Explicitly NOT required
- No new SBA/pose-initialization path: triangulation and BA already run identically on unpaired-only correspondences.
- No relaxation of GUI validation: `wand_go` has no paired-required check.
- No change to the `argus-wand` script: it already maps an empty paired arg to `None` and guards all paired usage.

## Edge cases / guards to note for reviewer
- **Arbitrary scale**: Without paired points there is no wand length, so `factor = 1.0` and the reconstruction is in arbitrary (non-metric) units. This is expected behavior; the Wand Score is correctly reported as "not applicable".
- **Minimum correspondences**: unpaired-only runs need enough rows for `multiTriangulator`/SBA to converge — same requirement as today, no new guard needed.
- **Outlier removal loop**: `redo` already null-guards `indices['paired']` and `indices['unpaired']`, so "remove outliers and re-run" is safe with paired absent.

## Verification
No project test suite exists. Use:
1. Syntax check edited files: `python -m py_compile argus_gui/sbaDriver.py` (and `graphers.py`/`Argus.py` if touched).
2. Functional CLI test with only an unpaired file (no `--paired_points`), using a small synthesized `unpaired-xypts.csv` (columns = multiple of `2*ncams`) and matching camera profile. Run:
   ```
   python argus_gui/resources/scripts/argus-wand <cam_profile.txt> --unpaired_points <unpaired-xypts.csv> <out_prefix>
   ```
   Expected: completes without `NameError`/`AttributeError`; prints "Wand score: not applicable"; writes DLT coefficients / SBA profile / clicker profile / unpaired-points-xyz outputs; does not write paired-points-xyz.
3. Regression: rerun with both paired and unpaired files, confirm scale/Wand Score/paired output unchanged from before.

## Relevant files
- `argus_gui/sbaDriver.py` (primary — Changes 1 & 2)
- `argus_gui/resources/scripts/argus-wand` (no change; already supports None)
- `argus_gui/Argus.py` (optional Change 4)
- `argus_gui/output.py` (no change; `WandOutputter.output` already null-safe)
- `argus_gui/graphers.py` (optional Change 3; dead code)
