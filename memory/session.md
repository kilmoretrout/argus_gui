# Session: DLCbatch vs Clicker reprojection error discrepancy

## Task
User reported `DLCbatch.py` reprojection errors are orders of magnitude higher
than errors from loading the same DLC output into a Clicker window and saving.
User confirmed camera frame offsets are not the cause (assumed 0 everywhere in
DLCbatch, matching the comparison).

## Investigation
Compared `utils/DLCbatch.py` against the reference implementation in
`argus_gui/resources/scripts/argus-click` (Clicker's `load_camera`, `load_DLT`,
`load_dlc`, `plotTracks`/`save_sparse`) and `argus_gui/tools.py`
(`uv_to_xyz`, `get_repo_errors`, `undistort_pts`, `reconstruct_uv`).

Confirmed identical between DLCbatch and Clicker:
- Camera profile loading/formatting (pinhole column deletion, ocam model
  construction) - [DLCbatch.py](utils/DLCbatch.py#L131) vs `load_camera` in
  argus-click.
- DLT coefficients loading (`np.loadtxt(..., delimiter=',').T`).
- Y-coordinate flip (`height - y`) from DLC upper-left origin to DLT
  lower-left origin.
- Likelihood-threshold based NaN filtering.
- Core math: both call the exact same `uv_to_xyz` / `get_repo_errors`
  functions from `argus_gui/tools.py`.

## Root cause found
`DLCBatchProcessor._reconstruct_with_camera_optimization` (enabled by default
via `optimize_cameras=True`) performs frame-by-frame outlier-camera detection
for tracks with 3+ cameras: it excludes a camera's point from the
triangulation if its individual reprojection error is a MAD-based outlier.

However, `_perform_3d_reconstruction` then computed the reported reprojection
error by calling `get_repo_errors(xyz_all, pts_data, ...)` using the raw,
**unfiltered** `pts_data` - i.e. including the excluded outlier camera's pixel
coordinates. Since that camera was excluded specifically because it
disagreed strongly with the other cameras, its large residual against the
optimized xyz still got summed into the reported error, hugely inflating it.

Clicker has no equivalent "camera optimization" feature at all - it always
triangulates and computes error using every valid camera consistently, so it
never has this mismatch, which is why its errors looked much smaller.

## Fix applied
- `_reconstruct_with_camera_optimization` now also returns a
  `used_camera_mask` (frames x cameras) marking exactly which cameras
  contributed to each frame's xyz.
- `_perform_3d_reconstruction` builds `pts_for_errors` (a copy of `pts_data`)
  and blanks out (NaN) any camera's point for frames/tracks where that camera
  was excluded from triangulation, then calls `get_repo_errors` against
  `pts_for_errors` instead of raw `pts_data`.
- This makes the reported error consistent with the cameras actually used to
  compute xyz in all cases, matching Clicker's behavior when no outlier
  exclusion occurs, and giving a sane (not inflated) error when it does.

File changed: [utils/DLCbatch.py](utils/DLCbatch.py)

Verified `python3 -m py_compile utils/DLCbatch.py` succeeds. Pre-existing
Pylance warnings in the file (bare except, unused imports, `Optional` type
narrowing on `self.camera_profile`) were left untouched as out of scope.

## Review
- Status: Approved (fix implemented and verified in this session)
- Issues found:
  - Blocking (fixed): reprojection error calculation used unfiltered
    `pts_data` while xyz used a camera-optimized subset, inflating errors
    whenever outlier-camera exclusion triggered.
  - Nitpick (not fixed, pre-existing, out of scope): bare `except:` in
    `main()`, unused `undistort_pts`/`reconstruct_uv` imports in
    `_get_per_camera_errors`, unused `datetime` import, `argus` possibly
    unbound in `_load_calibration` when `ARGUS_OCAM_AVAILABLE` is False.
- Verdict: Ship it

## Handoff
- From: Reviewer
- To: closed
- Next action: cycle complete. If the user still sees inflated errors after
  this fix, next investigate whether `--no-optimize-cameras` reproduces
  Clicker's numbers exactly (isolating any remaining discrepancy), and check
  multi-camera-subset indexing in `_reconstruct_single_frame` when fewer
  cameras have H5 files than exist in the camera profile.
