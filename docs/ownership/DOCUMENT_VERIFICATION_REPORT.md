# Ownership pack verification report

Date: 2026-08-28

## Application inspected before authoring

- Exact packaged project path was used.
- Backend suite: 40 passed, one dependency warning.
- Frontend suite: 2 files, 10 tests passed.
- Production frontend build passed; only the standard large-chunk advisory appeared.
- DEM Terrain smoke passed with 640 x 480 output, approximately 841.2 to 5962.5 m and 15 artifacts.
- Real Photo AI/calibration smoke passed on CUDA using `depth-anything/Depth-Anything-V2-Large-hf` revision `7581137eff8d4e94f6e796d3baea0e9fa79b22d2`; the synthetic oracle produced 18 verified artifact hashes.
- Live browser runs completed for DEM Terrain, Photo AI and reference calibration; no console errors/warnings were observed.

## Documents inspected

- Both previous TerraFly study PDFs.
- TerraFly Critical Fix Spec PDF.
- Current source, tests, scripts, setup/release files, sample metadata, handoff reports and all current project documentation.

## PDF verification

| PDF | Pages | Blank pages | External links | Visual inspection |
|---|---:|---:|---:|---|
| Source-to-System Atlas | 33 | 0 | problem/source URLs shown as text | all pages rendered and inspected via four contact sheets; representative pages inspected at full resolution |
| Zero-to-Ownership Bootcamp | 25 | 0 | 41 clickable links | all pages rendered and inspected via three contact sheets; representative pages inspected at full resolution |

Both outputs are A4, unencrypted and contain no JavaScript. The editable Markdown, Mermaid, SVG annotations and build scripts are stored beside them.

## Scope boundary

No TerraFly runtime source was changed. Findings remain in `INCONSISTENCIES_AND_LIMITATIONS.md`; real Photo AI accuracy remains BLOCKED in `CLAIMS_LEDGER.md` and the model metric card.

